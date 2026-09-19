from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, TransactionTestCase, override_settings

from accounts import permissions
from accounts.emails import PASSWORD_LINK
from accounts.models import Role, User
from outbox.models import OutboxEntry

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
    def test_anonymous_is_redirected_to_login_with_next(self):
        client = Client()
        for route in ROUTES:
            with self.subTest(route):
                url = self.url(route)
                for method in (client.get, client.post):
                    response = method(url)
                    self.assertRedirects(response, f'/contas/login/?next={url}', fetch_redirect_response=False)
        self.assertTrue(self.reload(self.target).is_active)

    def test_authenticated_without_the_permission_gets_403(self):
        for route, (_, permission) in ROUTES.items():
            with self.subTest(route):
                others = permissions.ADMINISTRATIVE_CAPABILITY - {permission}
                user = self.user_with(*others, email=f'{route}@ifnmg.edu.br')
                client = Client()
                client.force_login(user)
                self.assertEqual(client.get(self.url(route)).status_code, 403)
                self.assertEqual(client.post(self.url(route), {'name': 'X', 'email': 'x@ifnmg.edu.br'}).status_code, 403)
        target = self.reload(self.target)
        self.assertEqual((target.name, target.is_active), ('Maria Sousa', True))
        self.assertEqual(User.objects.filter(email='x@ifnmg.edu.br').count(), 0)

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

    def test_session_of_deactivated_user_becomes_anonymous(self):
        User.objects.filter(pk=self.admin.pk).update(is_active=False)
        response = self.client.get('/usuarios/novo/')
        self.assertRedirects(response, '/contas/login/?next=/usuarios/novo/', fetch_redirect_response=False)

    def test_there_is_no_route_to_delete_a_user(self):
        self.assertEqual(self.client.post(f'/usuarios/{self.target.pk}/excluir/').status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_unknown_user_gives_404(self):
        self.assertEqual(self.client.get('/usuarios/999999/editar/').status_code, 404)

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

    def test_home_shows_the_users_shortcut_only_with_permission(self):
        self.assertContains(self.client.get('/inicio/'), 'href="/usuarios/"')
        client = Client()
        client.force_login(self.target)
        self.assertNotContains(client.get('/inicio/'), 'href="/usuarios/"')


class CreateTests(UserViewsTestCase):
    data = {'name': 'Joana Lima', 'email': ' Joana@IFNMG.edu.br ', 'role': None}

    def post(self, **changes):
        data = self.data | {'role': self.teacher.pk} | changes
        return self.client.post('/usuarios/novo/', data, follow=True)

    def test_form_has_no_password_nor_superadmin_field(self):
        response = self.client.get('/usuarios/novo/')
        self.assertEqual(set(response.context['form'].fields), {'name', 'email', 'role'})
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

    def test_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post('/usuarios/novo/', self.data | {'role': self.teacher.pk})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='joana@ifnmg.edu.br').exists())


class CreateSendTests(TransactionTestCase):
    """O link é disparado em transaction.on_commit, que só roda dentro da
    requisição sem a transação externa do TestCase."""

    serialized_rollback = True
    data = CreateTests.data

    def setUp(self):
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

    def test_edits_users_of_any_role(self):
        other_admin = User.objects.register(email='outro@ifnmg.edu.br', name='Outro', role=self.administrator)
        for user in (other_admin, self.target):
            with self.subTest(user.email):
                self.client.post(self.url('update', user), {'name': 'Nome Novo', 'email': user.email})
                self.assertEqual(self.reload(user).name, 'Nome Novo')

    def test_form_has_no_password_field(self):
        response = self.client.get(self.url('update'))
        self.assertEqual(set(response.context['form'].fields), {'name', 'email'})
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

    def test_changes_to_a_custom_role(self):
        coordination = Role.objects.create_role(code='COORDENACAO', name='Coordenação')
        self.client.post(self.url('change_role'), {'role': coordination.pk})
        self.assertEqual(list(self.reload(self.target).roles.all()), [coordination])

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
    def test_get_only_asks_for_confirmation(self):
        response = self.client.get(self.url('deactivate'))
        self.assertContains(response, 'Desativar Maria Sousa?</h1>')
        self.assertTrue(self.reload(self.target).is_active)

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

    def test_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url('deactivate')).status_code, 403)
        self.assertTrue(self.reload(self.target).is_active)
