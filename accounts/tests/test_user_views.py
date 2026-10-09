from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, TransactionTestCase, override_settings

from accounts import permissions
from accounts.emails import PASSWORD_LINK
from accounts.models import Role, User
from outbox.models import OutboxEntry
from system_settings.tests.base import configure_smtp

ROUTES = {
    'list': ('/usuarios/', permissions.USER_VIEW),
    'create': ('/usuarios/novo/', permissions.USER_CREATE),
    'update': ('/usuarios/{pk}/editar/', permissions.USER_EDIT),
    'change_role': ('/usuarios/{pk}/perfil/', permissions.USER_CHANGE_ROLE),
    'deactivate': ('/usuarios/{pk}/desativar/', permissions.USER_CHANGE_STATUS),
    'reactivate': ('/usuarios/{pk}/reativar/', permissions.USER_CHANGE_STATUS),
}


class UserViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)

    def setUp(self):
        self.client.force_login(self.admin)

    def url(self, route, user=None):
        return ROUTES[route][0].format(pk=(user or self.target).pk)

    def user_with(self, *codes, email='limitado@ifnmg.edu.br'):
        code = email.partition('@')[0].upper()
        role = Role.objects.create_role(code=code, name=code, permissions=codes)
        return User.objects.register(email=email, name=code.capitalize(), role=role)

    def reload(self, user):
        return User.objects.get(pk=user.pk)


class AccessTests(UserViewsTestCase):
    def test_only_the_permission_of_the_route_is_needed(self):
        for route, (_, permission) in ROUTES.items():
            with self.subTest(route):
                user = self.user_with(permission, email=f'{route}@ifnmg.edu.br')
                client = Client()
                client.force_login(user)
                self.assertEqual(client.get(self.url(route)).status_code, 200)

    def test_active_superadmin_with_teacher_role_has_access(self):
        superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=self.teacher)
        superadmin.set_superadmin(True)
        self.client.force_login(superadmin)
        for route in ROUTES:
            with self.subTest(route):
                self.assertEqual(self.client.get(self.url(route)).status_code, 200)

    def test_list_shows_actions_allowed_to_the_user(self):
        response = self.client.get('/usuarios/')
        self.assertContains(response, 'maria@ifnmg.edu.br')
        self.assertContains(response, 'Cadastrar usuário')
        client = Client()
        client.force_login(self.user_with(permissions.USER_VIEW))
        response = client.get('/usuarios/')
        self.assertContains(response, 'maria@ifnmg.edu.br')
        for label in ['Cadastrar usuário', 'Editar', 'Trocar perfil', 'Desativar']:
            self.assertNotContains(response, label)


class CreateTests(UserViewsTestCase):
    data = {'name': 'Joana Lima', 'email': ' Joana@IFNMG.edu.br ', 'role': None}

    def post(self, **changes):
        data = self.data | {'role': self.teacher.pk} | changes
        return self.client.post('/usuarios/novo/', data, follow=True)

    def test_creates_with_username(self):
        self.post(username='  Aldo   Gomes  ')
        self.assertEqual(User.objects.get(email='joana@ifnmg.edu.br').username, 'Aldo Gomes')

    def test_refuses_username_already_taken(self):
        User.objects.register(
            email='aldo@ifnmg.edu.br', name='Aldo', role=self.teacher, username='Aldo Gomes',
        )
        response = self.post(username='ALDO GOMES')
        self.assertIn('username', response.context['form'].errors)
        self.assertFalse(User.objects.filter(email='joana@ifnmg.edu.br').exists())

    def test_form_has_no_password_nor_superadmin_field(self):
        response = self.client.get('/usuarios/novo/')
        self.assertEqual(set(response.context['form'].fields), {'name', 'email', 'username', 'role'})
        self.assertNotContains(response, 'type="password"')
        self.assertNotContains(response, 'superadmin')

    def test_refuses_invalid_data(self):
        cases = {
            'name': {'name': ''},
            'email': {'email': 'joana.ifnmg.edu.br'},
            'email of another domain': {'email': 'joana@gmail.com'},
            'role': {'role': ''},
        }
        for field, changes in cases.items():
            with self.subTest(field):
                response = self.post(**changes)
                self.assertIn(field.split()[0], response.context['form'].errors)
        self.assertFalse(User.objects.filter(name='Joana Lima').exists())
        self.assertEqual(mail.outbox, [])

    def test_refuses_more_than_one_role(self):
        response = self.post(role=[self.administrator.pk, self.teacher.pk])
        self.assertIn('role', response.context['form'].errors)
        self.assertFalse(User.objects.filter(email='joana@ifnmg.edu.br').exists())

    def test_refuses_email_in_use_ignoring_case_and_situation(self):
        User.objects.filter(pk=self.target.pk).update(is_active=False)
        response = self.post(email='MARIA@ifnmg.edu.br')
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.filter(email='maria@ifnmg.edu.br').count(), 1)


class CreateSendTests(TransactionTestCase):
    """O link sai em on_commit, que só roda sem a transação externa do TestCase."""

    serialized_rollback = True
    data = CreateTests.data

    def setUp(self):
        configure_smtp()
        cache.clear()
        self.teacher = Role.objects.get(code='DOCENTE')
        self.admin = User.objects.register(
            email='admin@ifnmg.edu.br', name='Admin', role=Role.objects.get(code='ADMINISTRADOR'),
        )
        self.client.force_login(self.admin)

    def post(self, **changes):
        data = self.data | {'role': self.teacher.pk} | changes
        return self.client.post('/usuarios/novo/', data, follow=True)

    def test_creates_user_and_registers_the_password_link(self):
        response = self.post(is_superadmin='on', password='Senha-forte-123', password1='Senha-forte-123')
        self.assertRedirects(response, '/usuarios/')
        user = User.objects.get(email='joana@ifnmg.edu.br')
        self.assertEqual(user.name, 'Joana Lima')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superadmin)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.role, self.teacher)
        self.assertEqual(mail.outbox, [])
        entry = OutboxEntry.objects.get(reference=str(user.pk))
        self.assertEqual((entry.kind, entry.status), (PASSWORD_LINK, 'A_ENVIAR'))
        self.assertContains(
            response,
            'Usuário joana@ifnmg.edu.br cadastrado. O link para definir a senha será enviado para joana@ifnmg.edu.br.',
        )

    def test_refused_creation_registers_no_link(self):
        self.post(email='Admin@ifnmg.edu.br')
        self.assertEqual(list(OutboxEntry.objects.values_list('reference', flat=True)), [str(self.admin.pk)])

    @override_settings(SITE_URL='http://testserver')
    def test_link_of_the_creation_is_the_same_route_of_the_recovery(self):
        self.post()
        call_command('process_outbox', '--once')
        Client().post('/contas/senha/recuperar/', {'email': 'joana@ifnmg.edu.br'})
        call_command('process_outbox', '--once')
        created, recovery = [message for message in mail.outbox if message.to == ['joana@ifnmg.edu.br']]
        prefix = 'http://testserver/contas/senha/redefinir/'
        self.assertIn(prefix, created.body)
        self.assertIn(prefix, recovery.body)


class UpdateTests(UserViewsTestCase):
    def test_changes_name_and_email_only(self):
        self.target.set_password('Senha-forte-123')
        self.target.save()
        password = self.target.password
        response = self.client.post(
            self.url('update'),
            {'name': 'Maria Souza', 'email': 'Maria.Souza@ifnmg.edu.br', 'is_superadmin': 'on', 'password': 'x'},
        )
        self.assertRedirects(response, '/usuarios/')
        target = self.reload(self.target)
        self.assertEqual((target.name, target.email), ('Maria Souza', 'maria.souza@ifnmg.edu.br'))
        self.assertEqual(target.password, password)
        self.assertFalse(target.is_superadmin)
        self.assertEqual(target.role, self.teacher)

    def test_refuses_username_of_another_user(self):
        other = User.objects.register(
            email='aldo@ifnmg.edu.br', name='Aldo', role=self.teacher, username='Aldo Gomes',
        )
        response = self.client.post(self.url('update'), {
            'name': self.target.name, 'email': self.target.email, 'username': 'aldo gomes',
        })
        self.assertIn('username', response.context['form'].errors)
        self.assertIsNone(self.reload(self.target).username)
        self.assertEqual(self.reload(other).username, 'Aldo Gomes')

    def test_form_has_no_password_field(self):
        response = self.client.get(self.url('update'))
        self.assertEqual(set(response.context['form'].fields), {'name', 'email', 'username'})
        self.assertNotContains(response, 'type="password"')

    def test_refuses_empty_name_and_email_of_another_user(self):
        for data in [{'name': '', 'email': 'maria@ifnmg.edu.br'}, {'name': 'Maria', 'email': 'Admin@ifnmg.edu.br'}]:
            with self.subTest(data):
                response = self.client.post(self.url('update'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        target = self.reload(self.target)
        self.assertEqual((target.name, target.email), ('Maria Sousa', 'maria@ifnmg.edu.br'))


class ChangeRoleTests(UserViewsTestCase):
    def test_changes_the_role(self):
        response = self.client.post(self.url('change_role'), {'role': self.administrator.pk, 'is_superadmin': 'on'})
        self.assertRedirects(response, '/usuarios/')
        target = self.reload(self.target)
        self.assertEqual(list(target.roles.all()), [self.administrator])
        self.assertFalse(target.is_superadmin)

    def test_refuses_more_than_one_role(self):
        response = self.client.post(self.url('change_role'), {'role': [self.administrator.pk, self.teacher.pk]})
        self.assertIn('role', response.context['form'].errors)
        self.assertEqual(list(self.reload(self.target).roles.all()), [self.teacher])

    def test_continuity_violation_is_shown_and_nothing_changes(self):
        response = self.client.post(self.url('change_role', self.admin), {'role': self.teacher.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'capacidade administrativa')
        self.assertEqual(list(self.reload(self.admin).roles.all()), [self.administrator])


class StatusTests(UserViewsTestCase):
    def test_deactivates_and_reactivates_by_post(self):
        self.assertRedirects(self.client.post(self.url('deactivate')), '/usuarios/')
        self.assertFalse(self.reload(self.target).is_active)
        self.assertRedirects(self.client.post(self.url('reactivate')), '/usuarios/')
        self.assertTrue(self.reload(self.target).is_active)

    def test_last_user_with_capability_cannot_deactivate_itself(self):
        response = self.client.post(self.url('deactivate', self.admin), follow=True)
        self.assertContains(response, 'capacidade administrativa')
        self.assertTrue(self.reload(self.admin).is_active)

    def test_user_deactivates_itself_when_another_keeps_the_capability(self):
        User.objects.register(email='outro@ifnmg.edu.br', name='Outro', role=self.administrator)
        self.client.post(self.url('deactivate', self.admin))
        self.assertFalse(self.reload(self.admin).is_active)
        self.assertRedirects(self.client.get('/usuarios/'), '/contas/login/?next=/usuarios/', fetch_redirect_response=False)
