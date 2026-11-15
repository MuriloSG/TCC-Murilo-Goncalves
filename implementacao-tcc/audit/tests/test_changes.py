from io import StringIO
from smtplib import SMTPException
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from config.testing import IsolatedCasesMixin

from accounts import permissions
from accounts.imports import UserImport
from accounts.models import Role, User
from accounts.tests.roles import management_role, requester_role
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from imports.reader import SourceRow
from imports.tests.worker import confirm, preview
from outbox import handlers
from outbox.models import OutboxEntry
from outbox.worker import process_next
from system_settings.tests.base import configure_smtp


class ChangeRecordTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()

    def entries(self, action=None, resource=None):
        queryset = AuditLog.objects.all()
        if action:
            queryset = queryset.filter(action=action)
        if resource:
            queryset = queryset.filter(resource=resource)
        return queryset


class UserChangeTests(ChangeRecordTestCase):
    def setUp(self):
        self.user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana Souza', role=self.teacher)
        self.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=self.administrator)

    def test_registration_is_recorded(self):
        entry = self.entries(catalog.CREATE, catalog.USER).filter(resource_id=str(self.user.pk)).get()
        self.assertEqual(
            entry.new_values,
            {'email': 'ana@ifnmg.edu.br', 'name': 'Ana Souza', 'username': None, 'role': 'SOLICITACAO'},
        )
        self.assertEqual(entry.old_values, {})

    def test_changes_are_recorded(self):
        with self.case('só os campos alterados'):
            self.user.update_details(self.admin, name='Ana Souza Lima', email='ana@ifnmg.edu.br')
            entry = self.entries(catalog.UPDATE, catalog.USER).get()
            self.assertEqual(entry.old_values, {'name': 'Ana Souza'})
            self.assertEqual(entry.new_values, {'name': 'Ana Souza Lima'})
            self.assertEqual(entry.resource_id, str(self.user.pk))
        with self.case('troca de perfil'):
            self.user.change_role(self.administrator)
            entry = self.entries(catalog.UPDATE, catalog.USER).get()
            self.assertEqual(entry.old_values, {'role': 'SOLICITACAO'})
            self.assertEqual(entry.new_values, {'role': 'GESTAO'})
        with self.case('desativação e reativação'):
            self.user.deactivate()
            self.user.reactivate()
            self.assertEqual(self.entries(catalog.DEACTIVATE).get().resource_id, str(self.user.pk))
            self.assertEqual(self.entries(catalog.ACTIVATE).get().resource_id, str(self.user.pk))

    def test_operations_without_change_record_nothing(self):
        with self.case('edição sem mudança'):
            self.user.update_details(self.admin, name='Ana Souza', email='ana@ifnmg.edu.br')
            self.assertFalse(self.entries(catalog.UPDATE, catalog.USER).exists())
        with self.case('mesmo perfil'):
            self.user.change_role(self.teacher)
            self.assertFalse(self.entries(catalog.UPDATE, catalog.USER).exists())
        with self.case('mesma situação'):
            self.user.deactivate()
            self.user.deactivate()
            self.assertEqual(self.entries(catalog.DEACTIVATE).count(), 1)
        with self.case('operação recusada'):
            only_admin = User.objects.register(email='unico@ifnmg.edu.br', name='Único', role=self.administrator)
            User.objects.filter(pk=self.admin.pk).update(is_active=False)
            with self.assertRaises(ValidationError):
                only_admin.deactivate()
            self.assertFalse(self.entries(catalog.DEACTIVATE).exists())

    def test_superadmin_commands_are_recorded_as_system_actions(self):
        call_command('set_superadmin', 'ana@ifnmg.edu.br', '--grant', stdout=StringIO())
        entry = self.entries(catalog.UPDATE, catalog.USER).get()
        self.assertEqual(entry.new_values, {'superadmin': True})
        self.assertIsNone(entry.user)
        self.assertEqual(entry.origin, catalog.SYSTEM)


class RoleChangeTests(ChangeRecordTestCase):
    def setUp(self):
        self.role = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', description='Coordenação de curso',
            permissions=[permissions.USER_VIEW],
        )

    def test_role_changes_are_recorded(self):
        with self.case('cadastro'):
            entry = self.entries(catalog.CREATE, catalog.ROLE).get()
            self.assertEqual(
                entry.new_values,
                {
                    'code': 'COORDENACAO',
                    'name': 'Coordenação',
                    'description': 'Coordenação de curso',
                    'permissions': [permissions.USER_VIEW],
                },
            )
        with self.case('só os campos alterados'):
            self.role.update_details(name='Coordenação de curso', description='Coordenação de curso')
            entry = self.entries(catalog.UPDATE, catalog.ROLE).get()
            self.assertEqual(entry.old_values, {'name': 'Coordenação'})
            self.assertEqual(entry.new_values, {'name': 'Coordenação de curso'})
        with self.case('permissões'):
            self.role.set_permissions([permissions.USER_VIEW, permissions.USER_CREATE])
            entry = self.entries(catalog.UPDATE, catalog.ROLE).get()
            self.assertEqual(entry.old_values, {'permissions': [permissions.USER_VIEW]})
            self.assertEqual(
                entry.new_values,
                {'permissions': sorted([permissions.USER_VIEW, permissions.USER_CREATE])},
            )
        with self.case('exclusão'):
            self.role.delete_role()
            entry = self.entries(catalog.DELETE, catalog.ROLE).get()
            self.assertEqual(entry.old_values['code'], 'COORDENACAO')
            self.assertEqual(entry.old_values['name'], 'Coordenação')

    def test_role_operations_without_change_record_nothing(self):
        with self.case('mesmas permissões'):
            self.role.set_permissions([permissions.USER_VIEW])
            self.assertFalse(self.entries(catalog.UPDATE, catalog.ROLE).exists())
        with self.case('exclusão recusada'):
            role = requester_role()
            User.objects.register('ana@ifnmg.edu.br', 'Ana', role)
            with self.assertRaises(ValidationError):
                role.delete_role()
            self.assertFalse(self.entries(catalog.DELETE, catalog.ROLE).exists())


class ImportChangeTests(ChangeRecordTestCase):
    def setUp(self):
        self.definition = UserImport()
        self.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=self.administrator)
        self.admin.set_superadmin(True)

    def rows(self, *emails):
        return [
            SourceRow(number, {
                'E-mail': email, 'Nome': email.partition('@')[0],
                'Perfil': 'SOLICITACAO', 'Nome de usuário': '',
            })
            for number, email in enumerate(emails, start=2)
        ]

    def preview(self, *emails):
        return preview(self.definition, self.rows(*emails), 'usuarios.csv', self.admin)

    def test_confirmation_records_the_import_and_each_user(self):
        importation = self.preview('ana@ifnmg.edu.br', 'bruno@ifnmg.edu.br')
        self.assertTrue(confirm(importation, self.definition, self.admin))
        entry = self.entries(catalog.IMPORT, catalog.USER_IMPORT).get()
        self.assertEqual(entry.metadata['cadastrados'], 2)
        created = self.entries(catalog.CREATE, catalog.USER).filter(origin=catalog.IMPORTED)
        self.assertEqual(created.count(), 2)
        self.assertEqual({item.user for item in created}, {self.admin})

    def test_template_download_is_an_export(self):
        client = Client()
        client.force_login(self.admin)
        self.assertEqual(client.get('/usuarios/importacoes/modelo/').status_code, 200)
        entry = self.entries(catalog.EXPORT, catalog.USER_IMPORT).get()
        self.assertEqual(entry.metadata, {'arquivo': 'modelo-importacao-usuarios.csv'})
        self.assertEqual(entry.user, self.admin)


@override_settings(OUTBOX_MAX_ATTEMPTS=1)
class SystemActionTests(ChangeRecordTestCase):
    def setUp(self):
        configure_smtp()
        patcher = mock.patch.dict(handlers._handlers, {'FALHA': self.failing})
        patcher.start()
        self.addCleanup(patcher.stop)

    def failing(self, reference):
        raise SMTPException('servidor indisponível')

    def test_sending_emails_is_a_system_action(self):
        with self.case('envio'):
            user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher)
            self.assertTrue(process_next())
            entry = self.entries(catalog.SEND, catalog.EMAIL).get()
            self.assertIsNone(entry.user)
            self.assertEqual(entry.origin, catalog.SYSTEM)
            self.assertEqual(entry.metadata, {'tipo': 'LINK_SENHA', 'referencia': str(user.pk)})
        with self.case('falha'):
            OutboxEntry.objects.create(kind='FALHA', reference='1')
            self.assertTrue(process_next())
            entry = self.entries(catalog.FAIL, catalog.EMAIL).get()
            self.assertEqual(entry.metadata, {'tipo': 'FALHA', 'referencia': '1'})
        with self.case('nova tentativa'):
            with override_settings(OUTBOX_MAX_ATTEMPTS=5):
                OutboxEntry.objects.create(kind='FALHA', reference='1')
                self.assertTrue(process_next())
            self.assertFalse(self.entries(catalog.FAIL, catalog.EMAIL).exists())
