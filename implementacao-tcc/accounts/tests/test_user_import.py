from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts import permissions
from accounts.emails import PASSWORD_LINK
from accounts.imports import UserImport, concluded_message
from accounts.models import AdministrativeContinuityViolation, Permission, Role, RolePermission, User, UserRole
from accounts.tests.roles import management_role, requester_role
from config.testing import IsolatedCasesMixin
from imports.models import Import
from imports.reader import read_csv
from imports.tests.worker import confirm, preview, run_worker
from outbox.models import OutboxEntry

HEADER = 'E-mail;Nome;Perfil;Nome de usuário\n'


def create_user(email, name, role, **fields):
    user = User(email=email, name=name, **fields)
    user.set_unusable_password()
    user.save()
    UserRole.objects.create(user=user, role=role)
    return User.objects.get(pk=user.pk)


class UserImportTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()

    def setUp(self):
        self.admin = create_user('admin@ifnmg.edu.br', 'Admin', self.administrator)

    def preview(self, lines, executor=None):
        upload = SimpleUploadedFile('usuarios.csv', (HEADER + lines).encode())
        definition = UserImport()
        return preview(definition, read_csv(upload, definition), 'usuarios.csv', executor or self.admin)

    def confirm(self, importation, executor=None):
        return confirm(importation, UserImport(), executor or self.admin)

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
    def test_username_is_created_and_updated(self):
        with self.case('cadastro'):
            self.confirm(self.preview('ana@ifnmg.edu.br;Ana Souza;SOLICITACAO;Ana Souza\n'))
            self.assertEqual(User.objects.get(email='ana@ifnmg.edu.br').username, 'Ana Souza')
        with self.case('atualização'):
            aldo = create_user('aldo@ifnmg.edu.br', 'Aldo Gomes da Silva', self.teacher)
            row = self.row(self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;SOLICITACAO;Aldo Gomes\n'))
            self.assertEqual((row.action, row.target), ('update', str(aldo.pk)))
            self.assertEqual(row.changes, {'username': [None, 'Aldo Gomes']})
            self.confirm(self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;SOLICITACAO;Aldo Gomes\n'))
            self.assertEqual(User.objects.get(email='aldo@ifnmg.edu.br').username, 'Aldo Gomes')
        with self.case('célula vazia mantém'):
            user = create_user('aldo@ifnmg.edu.br', 'Aldo Gomes da Silva', self.teacher)
            User.objects.filter(pk=user.pk).update(username='Aldo Gomes')
            importation = self.preview('aldo@ifnmg.edu.br;Aldo Gomes da Silva;SOLICITACAO;\n')
            self.assertEqual(self.row(importation).action, 'unchanged')
            self.confirm(importation)
            self.assertEqual(User.objects.get(email='aldo@ifnmg.edu.br').username, 'Aldo Gomes')

    def test_username_refusals(self):
        with self.case('repetido no arquivo'):
            importation = self.preview(
                'ana@ifnmg.edu.br;Ana;SOLICITACAO;Aldo Gomes\n'
                'bruno@ifnmg.edu.br;Bruno;SOLICITACAO;ALDO GOMES\n'
            )
            self.assertEqual(importation.status, 'COM_ERROS')
            self.assertEqual(self.error_codes(importation, line=3), [('Nome de usuário', 'username_taken')])
        with self.case('de outro usuário'):
            user = create_user('aldo@ifnmg.edu.br', 'Aldo', self.teacher)
            User.objects.filter(pk=user.pk).update(username='Aldo Gomes')
            importation = self.preview('bruno@ifnmg.edu.br;Bruno;SOLICITACAO;aldo gomes\n')
            self.assertEqual(importation.status, 'COM_ERROS')
            self.assertEqual(self.error_codes(importation), [('Nome de usuário', 'username_taken')])
        with self.case('troca exige a permissão de editar'):
            create_user('aldo@ifnmg.edu.br', 'Aldo', self.teacher)
            executor = self.executor_with(permissions.USER_IMPORT)
            importation = self.preview('aldo@ifnmg.edu.br;Aldo;SOLICITACAO;Aldo Gomes\n', executor=executor)
            self.assertEqual(self.error_codes(importation), [('Nome de usuário', 'permission_denied')])


class ActionTests(UserImportTestCase):
    def test_creates_new_user_on_confirmation(self):
        importation = self.preview('ana@ifnmg.edu.br;Ana Souza;SOLICITACAO\n')
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())
        self.assertTrue(self.confirm(importation))
        user = User.objects.get(email='ana@ifnmg.edu.br')
        self.assertEqual((user.name, user.role, user.is_active), ('Ana Souza', self.teacher, True))
        self.assertIsNone(user.username)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.row(importation).created_object, str(user.pk))

    def test_changes_of_existing_users(self):
        with self.case('troca de perfil'):
            bruno = create_user('bruno@ifnmg.edu.br', 'Bruno Lima', self.teacher)
            row = self.row(self.preview('bruno@ifnmg.edu.br;Bruno Lima;GESTAO\n'))
            self.assertEqual((row.action, row.target), ('update', str(bruno.pk)))
            self.assertEqual(row.changes, {'role': ['SOLICITACAO', 'GESTAO']})
        with self.case('troca de nome'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            self.confirm(self.preview('bruno@ifnmg.edu.br;Bruno Lima;SOLICITACAO\n'))
            self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').name, 'Bruno Lima')
        with self.case('outra grafia sem alteração'):
            create_user('carla@ifnmg.edu.br', 'Carla Mendes', self.teacher)
            row = self.row(self.preview(' Carla@IFNMG.edu.br ;Carla Mendes;solicitacao\n'))
            self.assertEqual((row.action, row.changes, row.errors), ('unchanged', {}, []))
        with self.case('usuário de outro domínio'):
            create_user('eva@gmail.com', 'Eva', self.teacher)
            self.confirm(self.preview('eva@gmail.com;Eva Lima;SOLICITACAO\n'))
            self.assertEqual(User.objects.get(email='eva@gmail.com').name, 'Eva Lima')
        with self.case('usuário inativo'):
            create_user('eva@ifnmg.edu.br', 'Eva', self.teacher, is_active=False)
            importation = self.preview('eva@ifnmg.edu.br;Eva;GESTAO\n')
            self.assertEqual(self.row(importation).warnings, ['inactive_user'])
            self.confirm(importation)
            eva = User.objects.get(email='eva@ifnmg.edu.br')
            self.assertEqual(eva.role, self.administrator)
            self.assertFalse(eva.is_active)
        with self.case('e-mail nunca muda'):
            create_user('ana@ifnmg.edu.br', 'Ana', self.teacher)
            self.confirm(self.preview('ANA@ifnmg.edu.br;Ana;SOLICITACAO\n'))
            self.assertEqual(list(User.objects.filter(name='Ana').values_list('email', flat=True)), ['ana@ifnmg.edu.br'])

    def test_refused_lines(self):
        with self.case('perfil desconhecido'):
            importation = self.preview('davi@ifnmg.edu.br;Davi Rocha;COORDENACAO\n')
            self.assertEqual(importation.status, 'COM_ERROS')
            self.assertEqual(self.error_codes(importation), [('Perfil', 'unknown_role')])
            self.assertFalse(Role.objects.filter(code='COORDENACAO').exists())
        with self.case('e-mail de outro domínio'):
            importation = self.preview('davi@gmail.com;Davi Rocha;SOLICITACAO\n')
            self.assertEqual(self.error_codes(importation), [('E-mail', 'institutional_email')])
            self.assertFalse(User.objects.filter(email='davi@gmail.com').exists())
        with self.case('perfil de superadmin'):
            create_user('super@ifnmg.edu.br', 'Super', self.administrator, is_superadmin=True)
            refused = self.preview('super@ifnmg.edu.br;Super Admin;SOLICITACAO\n')
            self.assertEqual(self.error_codes(refused), [('Perfil', 'insufficient_authority')])
            executor = create_user('outro@ifnmg.edu.br', 'Outro', self.administrator, is_superadmin=True)
            self.confirm(self.preview('super@ifnmg.edu.br;Super Admin;SOLICITACAO\n', executor), executor)
            superadmin = User.objects.get(email='super@ifnmg.edu.br')
            self.assertEqual((superadmin.name, superadmin.role), ('Super Admin', self.teacher))
            self.assertTrue(superadmin.is_superadmin)


class PermissionTests(UserImportTestCase):
    def test_each_line_needs_the_permission_of_its_change(self):
        with self.case('perfil fora do alcance'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            executor = self.executor_with(
                permissions.USER_IMPORT, permissions.USER_CREATE, permissions.USER_CHANGE_ROLE,
            )
            importation = self.preview(
                'ana@ifnmg.edu.br;Ana;GESTAO\nbruno@ifnmg.edu.br;Bruno;GESTAO\n', executor,
            )
            self.assertEqual(self.error_codes(importation, 2), [('Perfil', 'insufficient_authority')])
            self.assertEqual(self.error_codes(importation, 3), [('Perfil', 'insufficient_authority')])
        with self.case('cadastro sem a permissão'):
            executor = self.executor_with(permissions.USER_IMPORT)
            importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO\n', executor)
            self.assertEqual(self.error_codes(importation), [(None, 'permission_denied')])
        with self.case('cada alteração'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            executor = self.executor_with(permissions.USER_IMPORT, permissions.USER_EDIT)
            importation = self.preview('bruno@ifnmg.edu.br;Bruno Lima;GESTAO\n', executor)
            self.assertEqual(self.error_codes(importation), [('Perfil', 'permission_denied')])
            self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').name, 'Bruno')
        with self.case('linhas sem alteração'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            executor = self.executor_with(permissions.USER_IMPORT)
            self.assertEqual(self.preview('bruno@ifnmg.edu.br;Bruno;SOLICITACAO\n', executor).status, 'VALIDADA')

    def test_permissions_are_checked_again_on_the_confirmation(self):
        with self.case('quem confirma tem menos permissões'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            importation = self.preview('bruno@ifnmg.edu.br;Bruno;GESTAO\n')
            executor = self.executor_with(permissions.USER_IMPORT)
            self.assertFalse(self.confirm(importation, executor))
            self.assertEqual(importation.status, 'COM_ERROS')
            self.assertEqual(User.objects.get(email='bruno@ifnmg.edu.br').role, self.teacher)
        with self.case('conferida na execução'):
            importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO\n')
            executor = self.executor_with(permissions.USER_IMPORT, permissions.USER_CREATE)
            importation.request_confirmation(UserImport(), executor)
            RolePermission.objects.filter(role__code='IMPORTACAO', permission__code=permissions.USER_CREATE).delete()
            run_worker(UserImport())
            importation.refresh_from_db()
            self.assertEqual((importation.status, importation.operation), ('COM_ERROS', None))
            self.assertFalse(User.objects.filter(email='ana@ifnmg.edu.br').exists())
        with self.case('outro administrador'):
            other = create_user('outro@ifnmg.edu.br', 'Outro', self.administrator)
            importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO\n')
            self.assertTrue(self.confirm(importation, other))
            self.assertEqual((importation.created_by, importation.resolved_by), (self.admin, other))


class ContinuityTests(UserImportTestCase):
    def test_continuity_is_checked_on_the_final_state(self):
        with self.case('rebaixa e promove'):
            other = create_user('outro@ifnmg.edu.br', 'Outro', self.teacher)
            importation = self.preview('admin@ifnmg.edu.br;Admin;SOLICITACAO\noutro@ifnmg.edu.br;Outro;GESTAO\n')
            self.assertEqual(importation.status, 'VALIDADA')
            self.assertTrue(self.confirm(importation))
            self.assertTrue(User.objects.get(pk=other.pk).has_administrative_capability())
            self.assertFalse(User.objects.get(pk=self.admin.pk).has_administrative_capability())
        with self.case('arquivo sem administrador'):
            importation = self.preview('admin@ifnmg.edu.br;Admin;SOLICITACAO\n')
            self.assertEqual(importation.status, 'COM_ERROS')
            self.assertEqual([error['code'] for error in importation.file_errors], ['administrative_continuity'])
            self.assertEqual(self.row(importation).errors, [])
            self.assertEqual(User.objects.get(pk=self.admin.pk).role, self.administrator)


class OutboxTests(UserImportTestCase):
    def links(self):
        return set(OutboxEntry.objects.filter(kind=PASSWORD_LINK).values_list('reference', flat=True))

    def test_only_created_users_get_the_link(self):
        with self.case('só os cadastrados'):
            create_user('bruno@ifnmg.edu.br', 'Bruno', self.teacher)
            create_user('carla@ifnmg.edu.br', 'Carla', self.teacher)
            importation = self.preview(
                'ana@ifnmg.edu.br;Ana;SOLICITACAO\ndavi@ifnmg.edu.br;Davi;SOLICITACAO\n'
                'bruno@ifnmg.edu.br;Bruno Lima;SOLICITACAO\ncarla@ifnmg.edu.br;Carla;SOLICITACAO\n'
            )
            self.assertEqual(self.links(), set())
            self.confirm(importation)
            emails = ['ana@ifnmg.edu.br', 'davi@ifnmg.edu.br']
            created = {str(pk) for pk in User.objects.filter(email__in=emails).values_list('pk', flat=True)}
            self.assertEqual(self.links(), created)
        with self.case('divergência'):
            importation = self.preview('ana@ifnmg.edu.br;Ana;SOLICITACAO\ndavi@ifnmg.edu.br;Davi;SOLICITACAO\n')
            create_user('davi@ifnmg.edu.br', 'Davi', self.teacher)
            self.assertFalse(self.confirm(importation))
            self.assertEqual(self.links(), set())


class ScreenEquivalenceTests(UserImportTestCase):
    """Cada recusa das telas tem uma linha equivalente na importação, com a mesma mensagem."""

    def screen_errors(self, url, data):
        self.client.force_login(self.admin)
        response = self.client.post(url, data)
        return {field: list(errors) for field, errors in response.context['form'].errors.items()}

    def test_same_messages_as_the_screens(self):
        with self.case('e-mail inválido'):
            screen = self.screen_errors('/usuarios/novo/', {'name': 'Davi', 'email': 'davi', 'role': self.teacher.pk})
            row = self.row(self.preview('davi;Davi;SOLICITACAO\n'))
            self.assertEqual([error['message'] for error in row.errors], screen['email'])
        with self.case('outro domínio'):
            screen = self.screen_errors('/usuarios/novo/', {'name': 'Davi', 'email': 'davi@gmail.com', 'role': self.teacher.pk})
            row = self.row(self.preview('davi@gmail.com;Davi;SOLICITACAO\n'))
            self.assertEqual([error['message'] for error in row.errors], screen['email'])
        with self.case('nome longo demais'):
            name = 'N' * 151
            screen = self.screen_errors(
                '/usuarios/novo/', {'name': name, 'email': 'davi@ifnmg.edu.br', 'role': self.teacher.pk},
            )
            row = self.row(self.preview(f'davi@ifnmg.edu.br;{name};SOLICITACAO\n'))
            self.assertEqual(row.errors, [{'column': 'Nome', 'code': 'max_length', 'message': screen['name'][0]}])
        with self.case('continuidade'):
            screen = self.screen_errors(f'/usuarios/{self.admin.pk}/perfil/', {'role': self.teacher.pk})
            importation = self.preview('admin@ifnmg.edu.br;Admin;SOLICITACAO\n')
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
