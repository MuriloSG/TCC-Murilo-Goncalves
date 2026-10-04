from io import StringIO
from smtplib import SMTPException
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from accounts import permissions
from accounts.imports import UserImport
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from imports.reader import SourceRow
from outbox import handlers
from outbox.models import OutboxEntry
from outbox.worker import process_next
from system_settings.tests.base import configure_smtp


class ChangeRecordTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')

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
            {'email': 'ana@ifnmg.edu.br', 'name': 'Ana Souza', 'username': None, 'role': 'DOCENTE'},
        )
        self.assertEqual(entry.old_values, {})

    def test_update_records_only_the_changed_fields(self):
        self.user.update_details(self.admin, name='Ana Souza Lima', email='ana@ifnmg.edu.br')
        entry = self.entries(catalog.UPDATE, catalog.USER).get()
        self.assertEqual(entry.old_values, {'name': 'Ana Souza'})
        self.assertEqual(entry.new_values, {'name': 'Ana Souza Lima'})
        self.assertEqual(entry.resource_id, str(self.user.pk))

    def test_update_without_change_records_nothing(self):
        self.user.update_details(self.admin, name='Ana Souza', email='ana@ifnmg.edu.br')
        self.assertFalse(self.entries(catalog.UPDATE, catalog.USER).exists())

    def test_role_change_is_recorded(self):
        self.user.change_role(self.administrator)
        entry = self.entries(catalog.UPDATE, catalog.USER).get()
        self.assertEqual(entry.old_values, {'role': 'DOCENTE'})
        self.assertEqual(entry.new_values, {'role': 'ADMINISTRADOR'})

    def test_role_change_to_the_same_role_records_nothing(self):
        self.user.change_role(self.teacher)
        self.assertFalse(self.entries(catalog.UPDATE, catalog.USER).exists())

    def test_deactivation_and_reactivation(self):
        self.user.deactivate()
        self.user.reactivate()
        self.assertEqual(self.entries(catalog.DEACTIVATE).get().resource_id, str(self.user.pk))
        self.assertEqual(self.entries(catalog.ACTIVATE).get().resource_id, str(self.user.pk))

    def test_repeated_status_records_nothing(self):
        self.user.deactivate()
        self.user.deactivate()
        self.assertEqual(self.entries(catalog.DEACTIVATE).count(), 1)

    def test_refused_operation_records_nothing(self):
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

    def test_creation_is_recorded(self):
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

    def test_update_records_only_the_changed_fields(self):
        self.role.update_details(name='Coordenação de curso', description='Coordenação de curso')
        entry = self.entries(catalog.UPDATE, catalog.ROLE).get()
        self.assertEqual(entry.old_values, {'name': 'Coordenação'})
        self.assertEqual(entry.new_values, {'name': 'Coordenação de curso'})

    def test_permission_change_is_recorded(self):
        self.role.set_permissions([permissions.USER_VIEW, permissions.USER_CREATE])
        entry = self.entries(catalog.UPDATE, catalog.ROLE).get()
        self.assertEqual(entry.old_values, {'permissions': [permissions.USER_VIEW]})
        self.assertEqual(
            entry.new_values,
            {'permissions': sorted([permissions.USER_VIEW, permissions.USER_CREATE])},
        )

    def test_same_permissions_record_nothing(self):
        self.role.set_permissions([permissions.USER_VIEW])
        self.assertFalse(self.entries(catalog.UPDATE, catalog.ROLE).exists())

    def test_deletion_is_recorded(self):
        self.role.delete_role()
        entry = self.entries(catalog.DELETE, catalog.ROLE).get()
        self.assertEqual(entry.old_values['code'], 'COORDENACAO')
        self.assertEqual(entry.old_values['name'], 'Coordenação')

    def test_refused_deletion_records_nothing(self):
        system_role = Role.objects.get(code='DOCENTE')
        with self.assertRaises(ValidationError):
            system_role.delete_role()
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
                'Perfil': 'DOCENTE', 'Nome de usuário': '',
            })
            for number, email in enumerate(emails, start=2)
        ]

    def preview(self, *emails):
        return Import.objects.preview(self.definition, self.rows(*emails), 'usuarios.csv', self.admin)

    def test_preview_records_the_import_and_no_user(self):
        importation = self.preview('ana@ifnmg.edu.br', 'bruno@ifnmg.edu.br')
        entry = self.entries(catalog.CREATE, catalog.USER_IMPORT).get()
        self.assertEqual(entry.resource_id, str(importation.pk))
        self.assertEqual(entry.metadata['arquivo'], 'usuarios.csv')
        self.assertEqual(entry.metadata['linhas'], 2)
        self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())
        self.assertFalse(
            self.entries(catalog.CREATE, catalog.USER).filter(origin=catalog.IMPORTED).exists(),
        )

    def test_confirmation_records_the_import_and_each_user(self):
        importation = self.preview('ana@ifnmg.edu.br', 'bruno@ifnmg.edu.br')
        self.assertTrue(importation.confirm(self.definition, self.admin))
        entry = self.entries(catalog.IMPORT, catalog.USER_IMPORT).get()
        self.assertEqual(entry.metadata['cadastrados'], 2)
        created = self.entries(catalog.CREATE, catalog.USER).filter(origin=catalog.IMPORTED)
        self.assertEqual(created.count(), 2)
        self.assertEqual({item.user for item in created}, {self.admin})

    def test_discard_is_recorded(self):
        importation = self.preview('ana@ifnmg.edu.br')
        importation.discard(self.definition, self.admin)
        self.assertEqual(
            self.entries(catalog.DISCARD, catalog.USER_IMPORT).get().resource_id, str(importation.pk),
        )

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

    def test_sent_email_is_recorded_as_a_system_action(self):
        user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher)
        self.assertTrue(process_next())
        entry = self.entries(catalog.SEND, catalog.EMAIL).get()
        self.assertIsNone(entry.user)
        self.assertEqual(entry.origin, catalog.SYSTEM)
        self.assertEqual(entry.metadata, {'tipo': 'LINK_SENHA', 'referencia': str(user.pk)})

    def test_failed_send_is_recorded(self):
        OutboxEntry.objects.create(kind='FALHA', reference='1')
        self.assertTrue(process_next())
        entry = self.entries(catalog.FAIL, catalog.EMAIL).get()
        self.assertEqual(entry.metadata, {'tipo': 'FALHA', 'referencia': '1'})

    def test_retry_is_not_recorded(self):
        with override_settings(OUTBOX_MAX_ATTEMPTS=5):
            OutboxEntry.objects.create(kind='FALHA', reference='1')
            self.assertTrue(process_next())
        self.assertFalse(self.entries(catalog.FAIL, catalog.EMAIL).exists())
