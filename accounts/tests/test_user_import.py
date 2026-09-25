from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts import permissions
from accounts.emails import PASSWORD_LINK
from accounts.forms import INVALID_EMAIL_MESSAGE
from accounts.imports import UserImport, concluded_message
from accounts.models import AdministrativeContinuityViolation, Permission, Role, RolePermission, User, UserRole
from imports.models import Import
from imports.reader import read_csv
from outbox.models import OutboxEntry

HEADER = 'E-mail;Nome;Perfil;Nome de usuário\n'


def create_user(email, name, role, **fields):
    user = User(email=email, name=name, **fields)
    user.set_unusable_password()
    user.save()
    UserRole.objects.create(user=user, role=role)
    return User.objects.get(pk=user.pk)


class UserImportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')

    def setUp(self):
        self.admin = create_user('admin@ifnmg.edu.br', 'Admin', self.administrator)

    def preview(self, lines, executor=None):
        upload = SimpleUploadedFile('usuarios.csv', (HEADER + lines).encode())
        definition = UserImport()
        return Import.objects.preview(definition, read_csv(upload, definition), 'usuarios.csv', executor or self.admin)

    def confirm(self, importation, executor=None):
        return importation.confirm(UserImport(), executor or self.admin)

    def row(self, importation, line=2):
        return importation.rows.get(line_number=line)

    def error_codes(self, importation, line=2):
        return [(error['column'], error['code']) for error in self.row(importation, line).errors]

    def executor_with(self, *codes):
        role = Role.objects.create(code='IMPORTACAO', name='Importação')
        for permission in Permission.objects.filter(code__in=codes):
            RolePermission.objects.create(role=role, permission=permission)
        return create_user('importador@ifnmg.edu.br', 'Importador', role)


class UsernameTests(UserImportTestCase):
    def test_creates_with_username(self):
        self.confirm(self.preview('ana@ifnmg.edu.br;Ana Souza;DOCENTE;Ana Souza\n'))
        self.assertEqual(User.objects.get(email='ana@ifnmg.edu.br').username, 'Ana Souza')

    def test_creates_without_username(self):
        self.confirm(self.preview('ana@ifnmg.edu.br;Ana Souza;DOCENTE;\n'))
        self.assertIsNone(User.objects.get(email='ana@ifnmg.edu.br').username)

    def test_update_plan_shows_the_username_change(self):
        aldo = create_user('aldo@ifnmg.edu.br', 'Aldo Gomes da Silva', self.teacher)
        row = self.row(self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;DOCENTE;Aldo Gomes\n'))
        self.assertEqual((row.action, row.target), ('update', str(aldo.pk)))
        self.assertEqual(row.changes, {'username': [None, 'Aldo Gomes']})

    def test_update_applies_the_username(self):
        create_user('aldo@ifnmg.edu.br', 'Aldo Gomes da Silva', self.teacher)
        self.confirm(self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;DOCENTE;Aldo Gomes\n'))
        self.assertEqual(User.objects.get(email='aldo@ifnmg.edu.br').username, 'Aldo Gomes')

    def test_empty_cell_keeps_the_current_username(self):
        user = create_user('aldo@ifnmg.edu.br', 'Aldo Gomes da Silva', self.teacher)
        User.objects.filter(pk=user.pk).update(username='Aldo Gomes')
        importation = self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;DOCENTE;\n')
        self.assertEqual(self.row(importation).action, 'unchanged')
        self.confirm(importation)
        self.assertEqual(User.objects.get(email='aldo@ifnmg.edu.br').username, 'Aldo Gomes')

    def test_duplicate_username_in_the_same_file(self):
        importation = self.preview(
            'ana@ifnmg.edu.br;Ana;DOCENTE;Aldo Gomes\n'
            'bruno@ifnmg.edu.br;Bruno;DOCENTE;ALDO GOMES\n'
        )
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(self.error_codes(importation, line=3), [('Nome de usuário', 'username_taken')])

    def test_username_of_an_existing_user(self):
        user = create_user('aldo@ifnmg.edu.br', 'Aldo', self.teacher)
        User.objects.filter(pk=user.pk).update(username='Aldo Gomes')
        importation = self.preview('bruno@ifnmg.edu.br;Bruno;DOCENTE;aldo gomes\n')
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(self.error_codes(importation), [('Nome de usuário', 'username_taken')])

    def test_username_change_needs_the_edit_permission(self):
        create_user('aldo@ifnmg.edu.br', 'Aldo', self.teacher)
        executor = self.executor_with(permissions.USER_IMPORT)
        importation = self.preview('aldo@ifnmg.edu.br;Aldo;DOCENTE;Aldo Gomes\n', executor=executor)
        self.assertEqual(self.error_codes(importation), [('Nome de usuário', 'permission_denied')])


class ActionTests(UserImportTestCase):
    def test_creates_new_user_on_confirmation(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana Souza;DOCENTE\n')
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())
        self.assertTrue(self.confirm(importation))
        user = User.objects.get(email='ana@ifnmg.edu.br')
        self.assertEqual((user.name, user.role, user.is_active), ('Ana Souza', self.teacher, True))
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.row(importation).created_object, str(user.pk))

    def test_role_change_plan(self):
        bruno = create_user('bruno@ifnmg.edu.br', 'Bruno Lima', self.teacher)
        row = self.row(self.preview('bruno@ifnmg.edu.br;Bruno Lima;ADMINISTRADOR\n'))
        self.assertEqual((row.action, row.target), ('update', str(bruno.pk)))
        self.assertEqual(row.changes, {'role': ['DOCENTE', 'ADMINISTRADOR']})

    def test_name_change_is_applied(self):
        create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
        self.confirm(self.preview('bruno@ifnmg.edu.br;Bruno Lima;DOCENTE\n'))
        self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').name, 'Bruno Lima')

    def test_unchanged_with_other_spelling(self):
        create_user('carla@ifnmg.edu.br', 'Carla Mendes', self.teacher)
        row = self.row(self.preview(' Carla@IFNMG.edu.br ;Carla Mendes;docente\n'))
        self.assertEqual((row.action, row.changes, row.errors), ('unchanged', {}, []))

    def test_unknown_role(self):
        importation = self.preview('davi@ifnmg.edu.br;Davi Rocha;COORDENACAO\n')
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(self.error_codes(importation), [('Perfil', 'unknown_role')])
        self.assertFalse(Role.objects.filter(code='COORDENACAO').exists())

    def test_invalid_email_has_the_screen_message(self):
        row = self.row(self.preview('davi-ifnmg;Davi Rocha;DOCENTE\n'))
        self.assertEqual(row.errors, [{'column': 'E-mail', 'code': 'invalid', 'message': INVALID_EMAIL_MESSAGE}])

    def test_email_of_another_domain_is_not_registered(self):
        importation = self.preview('davi@gmail.com;Davi Rocha;DOCENTE\n')
        self.assertEqual(self.error_codes(importation), [('E-mail', 'institutional_email')])
        self.assertFalse(User.objects.filter(email='davi@gmail.com').exists())

    def test_existing_user_of_another_domain_is_still_updated(self):
        create_user('eva@gmail.com', 'Eva', self.teacher)
        self.confirm(self.preview('eva@gmail.com;Eva Lima;DOCENTE\n'))
        self.assertEqual(User.objects.get(email='eva@gmail.com').name, 'Eva Lima')

    def test_inactive_user_is_updated_and_stays_inactive(self):
        create_user('eva@ifnmg.edu.br', 'Eva', self.teacher, is_active=False)
        importation = self.preview('eva@ifnmg.edu.br;Eva;ADMINISTRADOR\n')
        self.assertEqual(self.row(importation).warnings, ['inactive_user'])
        self.confirm(importation)
        eva = User.objects.get(email='eva@ifnmg.edu.br')
        self.assertEqual(eva.role, self.administrator)
        self.assertFalse(eva.is_active)

    def test_superadmin_is_treated_like_any_user(self):
        create_user('super@ifnmg.edu.br', 'Super', self.administrator, is_superadmin=True)
        self.confirm(self.preview('super@ifnmg.edu.br;Super Admin;DOCENTE\n'))
        superadmin = User.objects.get(email='super@ifnmg.edu.br')
        self.assertEqual((superadmin.name, superadmin.role), ('Super Admin', self.teacher))
        self.assertTrue(superadmin.is_superadmin)

    def test_email_is_never_changed(self):
        create_user('ana@ifnmg.edu.br', 'Ana', self.teacher)
        self.confirm(self.preview('ANA@ifnmg.edu.br;Ana;DOCENTE\n'))
        self.assertEqual(list(User.objects.filter(name='Ana').values_list('email', flat=True)), ['ana@ifnmg.edu.br'])


class PermissionTests(UserImportTestCase):
    def test_create_without_create_permission(self):
        executor = self.executor_with(permissions.USER_IMPORT)
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE\n', executor)
        self.assertEqual(self.error_codes(importation), [(None, 'permission_denied')])

    def test_each_change_needs_its_permission(self):
        create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
        executor = self.executor_with(permissions.USER_IMPORT, permissions.USER_EDIT)
        importation = self.preview('bruno@ifnmg.edu.br;Bruno Lima;ADMINISTRADOR\n', executor)
        self.assertEqual(self.error_codes(importation), [('Perfil', 'permission_denied')])
        self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').name, 'Bruno')

    def test_unchanged_lines_need_only_import(self):
        create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
        executor = self.executor_with(permissions.USER_IMPORT)
        self.assertEqual(self.preview('bruno@ifnmg.edu.br;Bruno;DOCENTE\n', executor).status, 'VALIDADA')

    def test_confirmation_by_someone_with_fewer_permissions(self):
        create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
        importation = self.preview('bruno@ifnmg.edu.br;Bruno;ADMINISTRADOR\n')
        executor = self.executor_with(permissions.USER_IMPORT)
        self.assertFalse(self.confirm(importation, executor))
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').role, self.teacher)

    def test_confirmation_by_another_administrator(self):
        other = create_user('outro@ifnmg.edu.br', 'Outro', self.administrator)
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE\n')
        self.assertTrue(self.confirm(importation, other))
        self.assertEqual((importation.created_by, importation.resolved_by), (self.admin, other))


class ContinuityTests(UserImportTestCase):
    def test_demote_and_promote_in_the_same_file(self):
        other = create_user('outro@ifnmg.edu.br', 'Outro', self.teacher)
        importation = self.preview('admin@ifnmg.edu.br;Admin;DOCENTE\noutro@ifnmg.edu.br;Outro;ADMINISTRADOR\n')
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertTrue(self.confirm(importation))
        self.assertTrue(User.objects.get(pk=other.pk).has_administrative_capability())
        self.assertFalse(User.objects.get(pk=self.admin.pk).has_administrative_capability())

    def test_file_that_leaves_no_administrator(self):
        importation = self.preview('admin@ifnmg.edu.br;Admin;DOCENTE\n')
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual([error['code'] for error in importation.file_errors], ['administrative_continuity'])
        self.assertEqual(self.row(importation).errors, [])
        self.assertEqual(User.objects.get(pk=self.admin.pk).role, self.administrator)

    def test_screens_still_check_continuity_after_an_import(self):
        self.preview('ana@ifnmg.edu.br;Ana;DOCENTE\n')
        with self.assertRaises(AdministrativeContinuityViolation):
            self.admin.change_role(self.teacher)


class OutboxTests(UserImportTestCase):
    def links(self):
        return set(OutboxEntry.objects.filter(kind=PASSWORD_LINK).values_list('reference', flat=True))

    def test_only_created_users_get_the_link(self):
        create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
        create_user('carla@ifnmg.edu.br', 'Carla', self.teacher)
        importation = self.preview(
            'ana@ifnmg.edu.br;Ana;DOCENTE\ndavi@ifnmg.edu.br;Davi;DOCENTE\n'
            'bruno@ifnmg.edu.br;Bruno Lima;DOCENTE\ncarla@ifnmg.edu.br;Carla;DOCENTE\n'
        )
        self.assertEqual(self.links(), set())
        self.confirm(importation)
        emails = ['ana@ifnmg.edu.br', 'davi@ifnmg.edu.br']
        created = {str(pk) for pk in User.objects.filter(email__in=emails).values_list('pk', flat=True)}
        self.assertEqual(self.links(), created)

    def test_divergence_registers_no_link(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana;DOCENTE\ndavi@ifnmg.edu.br;Davi;DOCENTE\n')
        create_user('davi@ifnmg.edu.br', 'Davi', self.teacher)
        self.assertFalse(self.confirm(importation))
        self.assertEqual(self.links(), set())


class ScreenEquivalenceTests(UserImportTestCase):
    """Cada recusa das telas tem uma linha equivalente na importação, com a mesma mensagem."""

    def screen_errors(self, url, data):
        self.client.force_login(self.admin)
        response = self.client.post(url, data)
        return {field: list(errors) for field, errors in response.context['form'].errors.items()}

    def test_invalid_email(self):
        screen = self.screen_errors('/usuarios/novo/', {'name': 'Davi', 'email': 'davi', 'role': self.teacher.pk})
        row = self.row(self.preview('davi;Davi;DOCENTE\n'))
        self.assertEqual([error['message'] for error in row.errors], screen['email'])

    def test_email_of_another_domain(self):
        screen = self.screen_errors('/usuarios/novo/', {'name': 'Davi', 'email': 'davi@gmail.com', 'role': self.teacher.pk})
        row = self.row(self.preview('davi@gmail.com;Davi;DOCENTE\n'))
        self.assertEqual([error['message'] for error in row.errors], screen['email'])

    def test_name_too_long(self):
        name = 'N' * 151
        screen = self.screen_errors(
            '/usuarios/novo/', {'name': name, 'email': 'davi@ifnmg.edu.br', 'role': self.teacher.pk},
        )
        row = self.row(self.preview(f'davi@ifnmg.edu.br;{name};DOCENTE\n'))
        self.assertEqual(row.errors, [{'column': 'Nome', 'code': 'max_length', 'message': screen['name'][0]}])

    def test_continuity_message(self):
        screen = self.screen_errors(f'/usuarios/{self.admin.pk}/perfil/', {'role': self.teacher.pk})
        importation = self.preview('admin@ifnmg.edu.br;Admin;DOCENTE\n')
        self.assertEqual([error['message'] for error in importation.file_errors], screen['__all__'])


class ConcludedMessageTests(TestCase):
    def test_messages(self):
        cases = [
            ({'create': 2, 'update': 2}, 'Importação concluída. 2 usuários cadastrados e 2 atualizados. '
             'O link para definir a senha será enviado aos usuários cadastrados.'),
            ({'create': 1, 'update': 0}, 'Importação concluída. 1 usuário cadastrado. '
             'O link para definir a senha será enviado aos usuários cadastrados.'),
            ({'create': 0, 'update': 1}, 'Importação concluída. 1 usuário atualizado.'),
            ({'create': 0, 'update': 0}, 'Importação concluída. Nenhum usuário foi cadastrado ou alterado.'),
        ]
        for summary, message in cases:
            with self.subTest(summary):
                self.assertEqual(concluded_message(summary | {'unchanged': 0, 'errors': 0}), message)
