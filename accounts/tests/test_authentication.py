from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase

from accounts.adapters import AccountAdapter
from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


class AuthenticationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()
        cls.administrator = management_role()

    def setUp(self):
        cache.clear()
        self.user = self.create_user('joao@ifnmg.edu.br')

    def create_user(self, email, role=None, password=PASSWORD):
        user = User.objects.register(email=email, name='João Silva', role=role or self.teacher)
        if password:
            user.set_password(password)
            user.save()
        return user

    def login(self, email='joao@ifnmg.edu.br', password=PASSWORD, client=None):
        return (client or self.client).post('/contas/login/', {'login': email, 'password': password})

    def is_authenticated(self, client=None):
        return '_auth_user_id' in (client or self.client).session

    def login_errors(self, response):
        return list(response.context['form'].non_field_errors())


class UsernameIsNotACredentialTests(AuthenticationTestCase):
    """O nome de usuário é identificador de domínio, e não credencial."""

    def test_username_does_not_authenticate(self):
        self.user.username = 'Aldo Gomes'
        self.user.save(update_fields=['username'])
        response = self.login(email='Aldo Gomes')
        self.assertFalse(self.is_authenticated())
        self.assertTrue(response.context['form'].errors)


class LoginPageTests(AuthenticationTestCase):
    def test_asks_only_email_and_password(self):
        response = self.client.get('/contas/login/')
        self.assertEqual(set(response.context['form'].fields), {'login', 'password', 'remember'})
        self.assertContains(response, 'type="email"')
        self.assertNotContains(response, 'username')

    def test_offers_password_recovery_and_no_signup(self):
        response = self.client.get('/contas/login/')
        self.assertContains(response, 'href="/contas/senha/recuperar/"')
        for text in ['signup', 'Cadastre-se', 'Cadastrar', 'Criar conta', 'criar uma conta']:
            self.assertNotContains(response, text)

    def test_signup_is_closed_in_the_adapter(self):
        self.assertFalse(AccountAdapter().is_open_for_signup(RequestFactory().get('/')))


class LoginTests(AuthenticationTestCase):
    def test_successful_login_redirects_to_home(self):
        response = self.login()
        self.assertRedirects(response, '/inicio/', fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_email_is_compared_ignoring_case(self):
        self.login('Joao@IFNMG.edu.br')
        self.assertTrue(self.is_authenticated())


class InvalidCredentialsTests(AuthenticationTestCase):
    def test_wrong_password_and_unknown_email_show_the_same_error(self):
        wrong = self.login(password='Outra-senha-456')
        unknown = self.login('inexistente@ifnmg.edu.br', 'Outra-senha-456')
        self.assertEqual(wrong.status_code, 200)
        self.assertTrue(self.login_errors(wrong))
        self.assertEqual(self.login_errors(wrong), self.login_errors(unknown))
        self.assertFalse(self.is_authenticated())

    def test_user_without_password_does_not_authenticate(self):
        self.create_user('novo@ifnmg.edu.br', password=None)
        for password in ['', '!', PASSWORD]:
            with self.subTest(password=password):
                self.login('novo@ifnmg.edu.br', password)
                self.assertFalse(self.is_authenticated())

    def test_too_many_failed_attempts_block_even_the_right_password(self):
        for _ in range(5):
            self.login(password='Outra-senha-456')
        response = self.login()
        self.assertFalse(self.is_authenticated())
        self.assertEqual(self.login_errors(response), [str(AccountAdapter.error_messages['too_many_login_attempts'])])


class InactiveUserTests(AuthenticationTestCase):
    def test_inactive_user_and_inactive_superadmin_do_not_authenticate(self):
        superadmin = self.create_user('super@ifnmg.edu.br')
        superadmin.set_superadmin(True)
        User.objects.filter(pk__in=[self.user.pk, superadmin.pk]).update(is_active=False)
        unknown = self.login_errors(self.login('inexistente@ifnmg.edu.br'))
        for email in ['joao@ifnmg.edu.br', 'super@ifnmg.edu.br']:
            with self.subTest(email):
                response = self.login(email)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.login_errors(response), unknown)
                self.assertFalse(self.is_authenticated())

    def test_reactivation_restores_the_login(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        User.objects.get(pk=self.user.pk).reactivate()
        self.login()
        self.assertTrue(self.is_authenticated())

    def test_session_of_deactivated_user_becomes_anonymous(self):
        self.login()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        response = self.client.get('/inicio/')
        self.assertRedirects(response, '/contas/login/?next=/inicio/', fetch_redirect_response=False)


class SessionsAfterChangeByAnotherTests(AuthenticationTestCase):
    """Trocar o e-mail ou o perfil de outra conta encerra as sessões dela, e só dela."""

    def setUp(self):
        super().setUp()
        self.admin = self.create_user('admin@ifnmg.edu.br', role=self.administrator)
        self.bystander = self.create_user('maria@ifnmg.edu.br')
        self.target_client, self.other_client = Client(), Client()
        self.login(client=self.target_client)
        self.login('maria@ifnmg.edu.br', client=self.other_client)
        self.second_target_client = Client()
        self.login(client=self.second_target_client)

    def logged_in(self, client):
        response = client.get('/inicio/')
        return not response.get('Location', '').startswith('/contas/login/')

    def target(self):
        return User.objects.get(pk=self.user.pk)

    def test_email_change_by_another_ends_every_session_of_the_account(self):
        self.target().update_details(self.admin, name='João Silva', email='joao.silva@ifnmg.edu.br')
        self.assertFalse(self.logged_in(self.target_client))
        self.assertFalse(self.logged_in(self.second_target_client))
        self.assertTrue(self.logged_in(self.other_client))

    def test_role_change_by_another_ends_the_sessions(self):
        self.target().change_role(self.administrator, executor=self.admin)
        self.assertFalse(self.logged_in(self.target_client))
        self.assertTrue(self.logged_in(self.other_client))

    def test_ended_session_cannot_be_reused_and_a_new_login_works(self):
        cookie = self.target_client.cookies['sessionid'].value
        self.target().change_role(self.administrator, executor=self.admin)
        reused = Client()
        reused.cookies['sessionid'] = cookie
        response = reused.get('/inicio/')
        self.assertRedirects(response, '/contas/login/?next=/inicio/', fetch_redirect_response=False)
        fresh = Client()
        self.login('joao@ifnmg.edu.br', client=fresh)
        self.assertTrue(self.logged_in(fresh))

    def test_unchanged_email_and_role_keep_the_sessions(self):
        target = self.target()
        target.update_details(self.admin, name='João S. Silva', email=target.email)
        target.change_role(self.teacher, executor=self.admin)
        self.assertEqual(self.target().session_epoch, 0)
        self.assertTrue(self.logged_in(self.target_client))

    def test_own_change_keeps_the_own_sessions(self):
        target = self.target()
        target.update_details(target, name='João Silva', email='joao.silva@ifnmg.edu.br')
        self.assertTrue(self.logged_in(self.target_client))


class LogoutTests(AuthenticationTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_post_ends_the_session_and_redirects_to_login(self):
        response = self.client.post('/contas/logout/')
        self.assertRedirects(response, '/contas/login/')
        self.assertFalse(self.is_authenticated())
        self.assertRedirects(self.client.get('/inicio/'), '/contas/login/?next=/inicio/')

    def test_get_keeps_the_session(self):
        response = self.client.get('/contas/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.is_authenticated())


class EmailChangeTests(AuthenticationTestCase):
    def setUp(self):
        super().setUp()
        configure_smtp()
        self.client.post('/contas/senha/recuperar/', {'email': 'joao@ifnmg.edu.br'})
        executor = self.create_user('admin@ifnmg.edu.br', self.administrator)
        self.user.update_details(executor, name='João Silva', email='novo@ifnmg.edu.br')

    def test_only_the_new_email_authenticates(self):
        self.login('joao@ifnmg.edu.br')
        self.assertFalse(self.is_authenticated())
        self.login('novo@ifnmg.edu.br')
        self.assertTrue(self.is_authenticated())

