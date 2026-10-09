import re

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import Role, User
from accounts.tests.roles import requester_role
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'
INVALID_EMAIL = 'Informe um e-mail válido.'


class AuthenticationMessagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superadmin(email='ana@ifnmg.edu.br', name='Ana Souza', password=PASSWORD)

    def setUp(self):
        cache.clear()

    def test_login_nao_gera_mensagem(self):
        response = self.client.post('/contas/login/', {'login': 'ana@ifnmg.edu.br', 'password': PASSWORD})
        self.assertRedirects(response, '/inicio/', fetch_redirect_response=False)
        self.assertEqual(list(get_messages(response.wsgi_request)), [])

    def test_logout_mostra_sessao_encerrada(self):
        self.client.force_login(self.user)
        response = self.client.post('/contas/logout/', follow=True)
        self.assertContains(response, 'Sessão encerrada.')

    def test_credenciais_incorretas(self):
        response = self.client.post('/contas/login/', {'login': 'ana@ifnmg.edu.br', 'password': 'errada'})
        self.assertContains(
            response, 'E-mail ou senha incorretos. Confira os dados ou use &quot;Esqueci minha senha&quot;.',
        )

    def test_email_invalido_no_login_e_na_recuperacao(self):
        response = self.client.post('/contas/login/', {'login': 'ana', 'password': PASSWORD})
        self.assertContains(response, INVALID_EMAIL)
        response = self.client.post('/contas/senha/recuperar/', {'email': 'ana'})
        self.assertContains(response, INVALID_EMAIL)


@override_settings(SITE_URL='http://testserver')
class PasswordResetTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=requester_role(),
        )

    def setUp(self):
        configure_smtp()
        cache.clear()
        response = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'}, follow=True)
        self.done_page = response
        call_command('process_outbox', '--once')
        self.link = re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', mail.outbox[0].body).group(1)

    def test_aviso_de_envio_na_terceira_pessoa(self):
        self.assertContains(self.done_page, 'o link para definir a senha chega a ele em alguns minutos')

    def test_senhas_diferentes(self):
        form_url = self.client.get(self.link)['Location']
        response = self.client.post(form_url, {'password1': PASSWORD, 'password2': 'Outra-senha-456'})
        self.assertContains(response, 'As duas senhas informadas são diferentes.')


class ManagementScreensTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()
        cls.admin = User.objects.create_superadmin(email='admin@ifnmg.edu.br', name='Admin', password=PASSWORD)
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)
        cls.role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=[])

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_confirmacao_de_desativacao(self):
        response = self.client.get(f'/usuarios/{self.target.pk}/desativar/')
        self.assertContains(response, 'Desativar Maria Sousa?</h1>')
        self.assertContains(response, 'Desativar usuário</button>')
        self.assertNotContains(response, 'Cancelar')
        close_url = re.search(r'href="([^"]+)"[^>]*>Fechar</a>', response.content.decode()).group(1)
        self.assertEqual(close_url, '/usuarios/')
        self.assertTrue(User.objects.get(pk=self.target.pk).is_active)

    def test_perfil_sem_descricao(self):
        response = self.client.get(f'/perfis/{self.role.pk}/')
        self.assertContains(response, 'Sem descrição')

    def test_exclusao_de_perfil_com_usuarios_orienta_trocar_o_perfil(self):
        User.objects.register(email='joao@ifnmg.edu.br', name='João', role=self.role)
        response = self.client.post(f'/perfis/{self.role.pk}/excluir/', follow=True)
        self.assertContains(response, 'tem 1 usuário vinculado')
        self.assertContains(response, 'Troque o perfil desses usuários antes de excluí-lo.')

    def test_email_invalido_no_cadastro_e_na_edicao(self):
        response = self.client.post('/usuarios/novo/', {'name': 'Joana', 'email': 'joana', 'role': self.teacher.pk})
        self.assertContains(response, INVALID_EMAIL)
        response = self.client.post(f'/usuarios/{self.target.pk}/editar/', {'name': 'Maria', 'email': 'maria'})
        self.assertContains(response, INVALID_EMAIL)
