from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase

from accounts.adapters import AccountAdapter
from accounts.models import User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import management_role, requester_role
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


class AuthenticationTestCase(IsolatedCasesMixin, TestCase):
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


class LoginTests(AuthenticationTestCase):
    def test_login_page_asks_only_email_and_password(self):
        with self.case('só e-mail e senha'):
            response = self.client.get('/contas/login/')
            self.assertEqual(set(response.context['form'].fields), {'login', 'password', 'remember'})
            self.assertContains(response, 'type="email"')
            self.assertNotContains(response, 'username')
        with self.case('recuperação de senha e sem cadastro'):
            response = self.client.get('/contas/login/')
            self.assertContains(response, 'href="/contas/senha/recuperar/"')
            for text in ['signup', 'Cadastre-se', 'Cadastrar', 'Criar conta', 'criar uma conta']:
                self.assertNotContains(response, text)
        with self.case('cadastro fechado no adaptador'):
            self.assertFalse(AccountAdapter().is_open_for_signup(RequestFactory().get('/')))
        with self.case('nome de usuário não autentica'):
            self.user.username = 'Aldo Gomes'
            self.user.save(update_fields=['username'])
            response = self.login(email='Aldo Gomes')
            self.assertFalse(self.is_authenticated())
            self.assertTrue(response.context['form'].errors)

    def test_login_with_the_email_in_any_case(self):
        with self.case('redireciona ao início'):
            response = self.login()
            self.assertRedirects(response, '/inicio/', fetch_redirect_response=False)
            self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        with self.case('e-mail sem diferenciar caixa'):
            self.login('Joao@IFNMG.edu.br')
            self.assertTrue(self.is_authenticated())


class InactiveUserTests(AuthenticationTestCase):
    def test_inactive_user_does_not_authenticate_and_loses_the_session(self):
        with self.case('inativos não autenticam'):
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
        with self.case('sessão vira anônima'):
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

    def test_change_by_another_ends_the_sessions(self):
        with self.case('e-mail trocado por outro'):
            self.target().update_details(self.admin, name='João Silva', email='joao.silva@ifnmg.edu.br')
            self.assertFalse(self.logged_in(self.target_client))
            self.assertFalse(self.logged_in(self.second_target_client))
            self.assertTrue(self.logged_in(self.other_client))
        with self.case('perfil trocado por outro'):
            self.target().change_role(self.administrator, executor=self.admin)
            self.assertFalse(self.logged_in(self.target_client))
            self.assertTrue(self.logged_in(self.other_client))
        with self.case('sessão encerrada não volta'):
            cookie = self.target_client.cookies['sessionid'].value
            self.target().change_role(self.administrator, executor=self.admin)
            reused = Client()
            reused.cookies['sessionid'] = cookie
            response = reused.get('/inicio/')
            self.assertRedirects(response, '/contas/login/?next=/inicio/', fetch_redirect_response=False)
            fresh = Client()
            self.login('joao@ifnmg.edu.br', client=fresh)
            self.assertTrue(self.logged_in(fresh))

    def test_unchanged_data_or_own_change_keep_the_sessions(self):
        with self.case('sem alteração'):
            target = self.target()
            target.update_details(self.admin, name='João S. Silva', email=target.email)
            target.change_role(self.teacher, executor=self.admin)
            self.assertEqual(self.target().session_epoch, 0)
            self.assertTrue(self.logged_in(self.target_client))
        with self.case('alteração própria'):
            target = self.target()
            target.update_details(target, name='João Silva', email='joao.silva@ifnmg.edu.br')
            self.assertTrue(self.logged_in(self.target_client))


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

