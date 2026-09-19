import re

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase

from accounts.models import Role, User

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
        self.assertNotContains(response, 'Você saiu')

    def test_confirmacao_de_logout(self):
        self.client.force_login(self.user)
        response = self.client.get('/contas/logout/')
        self.assertContains(response, '<h1>Sair do sistema?</h1>', html=True)
        self.assertContains(response, '<a class="btn-secondary" href="/inicio/">Fechar</a>', html=True)

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
        self.assertContains(response, '<label for="id_email">E-mail</label>', html=True)


class PasswordResetTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=Role.objects.get(code='DOCENTE'),
        )

    def setUp(self):
        cache.clear()
        response = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'}, follow=True)
        self.done_page = response
        self.link = re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', mail.outbox[0].body).group(1)

    def test_aviso_de_envio_na_terceira_pessoa(self):
        self.assertContains(self.done_page, 'o link para definir a senha chega a ele em alguns minutos')
        for text in ('enviaremos', 'você receberá', 'Você'):
            self.assertNotContains(self.done_page, text)

    def test_email_sem_saudacao_nem_primeira_pessoa(self):
        body = mail.outbox[0].body
        self.assertTrue(body.startswith('Foi solicitada a definição ou a redefinição da senha desta conta'))
        for text in ('Olá', 'Recebemos', 'você'):
            self.assertNotIn(text, body)

    def test_senhas_diferentes(self):
        form_url = self.client.get(self.link)['Location']
        response = self.client.post(form_url, {'password1': PASSWORD, 'password2': 'Outra-senha-456'})
        self.assertContains(response, 'As duas senhas informadas são diferentes.')
        self.assertNotContains(response, 'Você')

    def test_redefinicao_sem_com_sucesso(self):
        form_url = self.client.get(self.link)['Location']
        response = self.client.post(form_url, {'password1': PASSWORD, 'password2': PASSWORD}, follow=True)
        self.assertContains(response, '<h1>Senha definida</h1>', html=True)
        self.assertNotContains(response, 'com sucesso')
        self.assertEqual(list(get_messages(response.wsgi_request)), [])


class ManagementScreensTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.create_superadmin(email='admin@ifnmg.edu.br', name='Admin', password=PASSWORD)
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)
        cls.role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=[])

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_pagina_de_acesso_negado(self):
        client = Client()
        client.force_login(self.target)
        response = client.get('/usuarios/')
        self.assertContains(
            response, 'Esta página exige uma permissão que o seu perfil não concede.', status_code=403,
        )
        self.assertContains(response, 'procure um administrador do sistema', status_code=403)
        self.assertNotContains(response, 'ocê', status_code=403)

    def test_pagina_inicial_sem_saudacao(self):
        client = Client()
        client.force_login(self.target)
        response = client.get('/inicio/')
        self.assertContains(response, '<h1 class="page-title">Início</h1>', html=True)
        self.assertNotContains(response, 'Olá')
        self.assertNotIn('!', response.content.decode().removeprefix('<!DOCTYPE html>'))

    def test_confirmacao_de_desativacao(self):
        response = self.client.get(f'/usuarios/{self.target.pk}/desativar/')
        self.assertContains(response, 'Desativar Maria Sousa?</h1>')
        self.assertContains(response, 'Desativar usuário</button>')
        self.assertContains(response, '<a class="btn-secondary" href="/usuarios/">Fechar</a>', html=True)
        self.assertNotContains(response, 'Cancelar')

    def test_confirmacao_de_reativacao(self):
        self.target.deactivate()
        response = self.client.get(f'/usuarios/{self.target.pk}/reativar/')
        self.assertContains(response, 'Reativar Maria Sousa?</h1>')
        self.assertContains(response, 'volta a poder entrar no sistema com a senha que já tinha')
        self.assertContains(response, 'Reativar usuário</button>')

    def test_fechar_volta_a_tela_de_origem_sem_alterar_dados(self):
        response = self.client.get(f'/usuarios/{self.target.pk}/desativar/')
        close_url = re.search(r'<a class="btn-secondary" href="([^"]+)">Fechar</a>', response.content.decode()).group(1)
        self.assertEqual(close_url, '/usuarios/')
        self.assertEqual(self.client.get(close_url).status_code, 200)
        self.assertTrue(User.objects.get(pk=self.target.pk).is_active)

    def test_situacao_inativo_oferece_reativar(self):
        self.target.deactivate()
        response = self.client.get('/usuarios/')
        self.assertContains(response, 'Inativo</span>')
        self.assertContains(response, f'href="/usuarios/{self.target.pk}/reativar/"')
        self.assertContains(response, 'aria-label="Reativar usuário"')

    def test_confirmacao_de_exclusao_de_perfil(self):
        response = self.client.get(f'/perfis/{self.role.pk}/excluir/')
        self.assertContains(response, 'Excluir o perfil Coordenação?</h1>')
        self.assertContains(response, 'é excluído de forma definitiva')
        self.assertContains(response, 'Excluir perfil</button>')
        self.assertContains(response, f'<a class="btn-secondary" href="/perfis/{self.role.pk}/">Fechar</a>', html=True)
        self.assertNotContains(response, 'Cancelar')

    def test_perfil_sem_descricao(self):
        response = self.client.get(f'/perfis/{self.role.pk}/')
        self.assertContains(response, '<dd>Sem descrição</dd>', html=True)
        self.assertNotContains(response, '—')

    def test_exclusao_de_perfil_com_usuarios_orienta_trocar_o_perfil(self):
        User.objects.register(email='joao@ifnmg.edu.br', name='João', role=self.role)
        response = self.client.post(f'/perfis/{self.role.pk}/excluir/', follow=True)
        self.assertContains(response, 'tem 1 usuário vinculado')
        self.assertContains(response, 'Troque o perfil desses usuários antes de excluí-lo.')

    def test_cadastro_de_usuario_sem_com_sucesso(self):
        response = self.client.post(
            '/usuarios/novo/', {'name': 'Joana', 'email': 'joana@ifnmg.edu.br', 'role': self.teacher.pk},
        )
        texts = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn(
            'Usuário joana@ifnmg.edu.br cadastrado. O link para definir a senha será enviado para joana@ifnmg.edu.br.',
            texts,
        )
        self.assertFalse(any('com sucesso' in text or '!' in text for text in texts))

    def test_email_invalido_no_cadastro_e_na_edicao(self):
        response = self.client.post('/usuarios/novo/', {'name': 'Joana', 'email': 'joana', 'role': self.teacher.pk})
        self.assertContains(response, INVALID_EMAIL)
        response = self.client.post(f'/usuarios/{self.target.pk}/editar/', {'name': 'Maria', 'email': 'maria'})
        self.assertContains(response, INVALID_EMAIL)
