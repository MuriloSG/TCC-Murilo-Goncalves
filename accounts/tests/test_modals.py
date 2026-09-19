import json

from django.contrib.messages import get_messages
from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User

HTMX = {'HX-Request': 'true'}


class ModalTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.create_superadmin(email='admin@ifnmg.edu.br', name='Ana Souza', password='Senha-forte-123')
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)
        cls.role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=[])

    def setUp(self):
        self.client.force_login(self.admin)

    def assertFragment(self, response):
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<html', content)
        self.assertRegex(content.lstrip()[:60], r'^<dialog class="modal[ "]')
        self.assertIn('aria-labelledby="modal-title"', content)
        self.assertIn('data-modal-close', content)

    def assertFullPage(self, response):
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('<html', content)
        self.assertIn('<section class="modal modal-page"', content)
        self.assertNotIn('<dialog', content)

    def assertClientRedirect(self, response, url):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Redirect'], url)


class FormModalTests(ModalTestCase):
    def routes(self):
        return {
            'Cadastrar usuário': (
                '/usuarios/novo/',
                {'name': 'Joana', 'email': 'maria@ifnmg.edu.br', 'role': self.teacher.pk},
                {'name': 'Joana', 'email': 'joana@ifnmg.edu.br', 'role': self.teacher.pk},
                '/usuarios/',
            ),
            'Editar usuário': (
                f'/usuarios/{self.target.pk}/editar/',
                {'name': '', 'email': 'maria'},
                {'name': 'Maria de Sousa', 'email': 'maria@ifnmg.edu.br'},
                '/usuarios/',
            ),
            'Trocar perfil': (
                f'/usuarios/{self.target.pk}/perfil/',
                {'role': ''},
                {'role': self.role.pk},
                '/usuarios/',
            ),
            'Criar perfil': (
                '/perfis/novo/',
                {'code': 'codigo invalido', 'name': ''},
                {'code': 'NOVO', 'name': 'Novo perfil', 'description': ''},
                None,
            ),
            'Editar perfil': (
                f'/perfis/{self.role.pk}/editar/',
                {'name': ''},
                {'name': 'Coordenação de curso', 'description': ''},
                f'/perfis/{self.role.pk}/',
            ),
            'Permissões do perfil': (
                f'/perfis/{self.role.pk}/permissoes/',
                {'permissions': ['NAO.EXISTE']},
                {'permissions': [permissions.USER_VIEW]},
                f'/perfis/{self.role.pk}/',
            ),
        }

    def snapshot(self):
        return (
            list(User.objects.order_by('pk').values_list('name', 'email', 'user_roles__role')),
            list(Role.objects.order_by('pk').values_list('code', 'name', 'description')),
            list(Role.objects.get(pk=self.role.pk).permissions.values_list('code', flat=True)),
        )

    def test_get_pelo_htmx_responde_so_o_fragmento(self):
        for title, (url, *_) in self.routes().items():
            with self.subTest(title=title):
                response = self.client.get(url, headers=HTMX)
                self.assertFragment(response)
                self.assertContains(response, f'{title}</h1>')

    def test_get_sem_htmx_responde_a_pagina_completa(self):
        for title, (url, *_) in self.routes().items():
            with self.subTest(title=title):
                response = self.client.get(url)
                self.assertFullPage(response)
                self.assertContains(response, f'{title}</h1>')

    def test_post_invalido_pelo_htmx_mantem_o_modal_sem_gravar(self):
        for title, (url, invalid, _valid, _success) in self.routes().items():
            with self.subTest(title=title):
                before = self.snapshot()
                response = self.client.post(url, invalid, headers=HTMX)
                self.assertFragment(response)
                self.assertContains(response, 'class="error"')
                self.assertEqual(self.snapshot(), before)

    def test_post_valido_pelo_htmx_responde_hx_redirect(self):
        for title, (url, _invalid, valid, success) in self.routes().items():
            with self.subTest(title=title):
                response = self.client.post(url, valid, headers=HTMX)
                if success is None:
                    continue
                self.assertClientRedirect(response, success)

    def test_criacao_pelo_htmx_abre_a_etapa_de_permissoes_no_mesmo_modal(self):
        response = self.client.post('/perfis/novo/', {'code': 'NOVO', 'name': 'Novo perfil', 'description': ''}, headers=HTMX)
        role = Role.objects.get(code='NOVO')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('HX-Redirect', response)
        self.assertEqual(
            json.loads(response['HX-Location']),
            {'path': f'/perfis/{role.pk}/permissoes/?etapa=2', 'target': '#modal', 'push': 'false'},
        )
        step = self.client.get(f'/perfis/{role.pk}/permissoes/?etapa=2', headers=HTMX).content.decode()
        self.assertIn('data-reload-on-close', step)
        self.assertIn('<p class="modal-step">Etapa 2 de 2</p>', step)
        self.assertIn('Permissões do perfil Novo perfil</h1>', step)
        self.assertIn('Perfil NOVO criado.', step)
        self.assertIn('action="/perfis/%d/permissoes/?etapa=2"' % role.pk, step)
        response = self.client.post(f'/perfis/{role.pk}/permissoes/?etapa=2', {'permissions': [permissions.USER_VIEW]}, headers=HTMX)
        self.assertClientRedirect(response, f'/perfis/{role.pk}/')

    def test_primeira_etapa_da_criacao(self):
        content = self.client.get('/perfis/novo/', headers=HTMX).content.decode()
        self.assertIn('<p class="modal-step">Etapa 1 de 2</p>', content)
        self.assertIn('Criar perfil</button>', content)
        self.assertNotIn('type="checkbox"', content)
        self.assertNotIn('data-reload-on-close', content)

    def test_cadastro_com_email_ja_usado_mostra_o_erro_no_campo(self):
        response = self.client.post(
            '/usuarios/novo/', {'name': 'Joana', 'email': 'maria@ifnmg.edu.br', 'role': self.teacher.pk}, headers=HTMX,
        )
        self.assertFragment(response)
        self.assertContains(response, 'id="id_email_error"')
        self.assertEqual(User.objects.filter(email='maria@ifnmg.edu.br').count(), 1)

    def test_sucesso_mantem_busca_e_filtro_da_lista_de_origem(self):
        response = self.client.post(
            f'/usuarios/{self.target.pk}/editar/',
            {'name': 'Maria de Sousa', 'email': 'maria@ifnmg.edu.br'},
            headers=HTMX | {'HX-Current-URL': 'http://testserver/usuarios/?q=maria&situacao=ativos'},
        )
        self.assertClientRedirect(response, '/usuarios/?q=maria&situacao=ativos')

    def test_sucesso_vindo_de_outra_tela_vai_para_o_destino_da_acao(self):
        response = self.client.post(
            f'/perfis/{self.role.pk}/editar/',
            {'name': 'Coordenação de curso', 'description': ''},
            headers=HTMX | {'HX-Current-URL': 'http://testserver/perfis/?pagina=2'},
        )
        self.assertClientRedirect(response, f'/perfis/{self.role.pk}/')


class ConfirmationModalTests(ModalTestCase):
    def routes(self):
        return {
            'Desativar Maria Sousa?': (f'/usuarios/{self.target.pk}/desativar/', '/usuarios/'),
            'Excluir o perfil Coordenação?': (f'/perfis/{self.role.pk}/excluir/', '/perfis/'),
        }

    def test_get_pelo_htmx_responde_so_o_fragmento(self):
        for title, (url, _success) in self.routes().items():
            with self.subTest(title=title):
                response = self.client.get(url, headers=HTMX)
                self.assertFragment(response)
                self.assertContains(response, f'{title}</h1>')
                self.assertContains(response, '<button class="btn-secondary" type="button" data-modal-close>Fechar</button>', html=True)

    def test_get_sem_htmx_responde_a_pagina_completa(self):
        for title, (url, _success) in self.routes().items():
            with self.subTest(title=title):
                response = self.client.get(url)
                self.assertFullPage(response)
                self.assertContains(response, f'{title}</h1>')

    def test_desativacao_pelo_htmx(self):
        response = self.client.get(f'/usuarios/{self.target.pk}/desativar/', headers=HTMX)
        self.assertContains(response, 'class="btn-danger"')
        self.assertContains(response, 'Desativar usuário</button>')
        response = self.client.post(f'/usuarios/{self.target.pk}/desativar/', headers=HTMX)
        self.assertClientRedirect(response, '/usuarios/')
        self.assertFalse(User.objects.get(pk=self.target.pk).is_active)

    def test_reativacao_pelo_htmx(self):
        self.target.deactivate()
        response = self.client.get(f'/usuarios/{self.target.pk}/reativar/', headers=HTMX)
        self.assertFragment(response)
        self.assertContains(response, 'Reativar Maria Sousa?</h1>')
        response = self.client.post(f'/usuarios/{self.target.pk}/reativar/', headers=HTMX)
        self.assertClientRedirect(response, '/usuarios/')
        self.assertTrue(User.objects.get(pk=self.target.pk).is_active)

    def test_exclusao_de_perfil_pelo_htmx(self):
        response = self.client.post(f'/perfis/{self.role.pk}/excluir/', headers=HTMX)
        self.assertClientRedirect(response, '/perfis/')
        self.assertFalse(Role.objects.filter(pk=self.role.pk).exists())

    def test_recusa_volta_para_a_origem_com_a_mensagem_de_erro(self):
        response = self.client.post(
            f'/usuarios/{self.admin.pk}/desativar/',
            headers=HTMX | {'HX-Current-URL': 'http://testserver/usuarios/?q=ana'},
        )
        self.assertClientRedirect(response, '/usuarios/?q=ana')
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)
        texts = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(any('capacidade administrativa' in text for text in texts), texts)

    def test_exclusao_recusada_volta_para_o_detalhe(self):
        User.objects.register(email='joao@ifnmg.edu.br', name='João', role=self.role)
        response = self.client.post(f'/perfis/{self.role.pk}/excluir/', headers=HTMX)
        self.assertClientRedirect(response, f'/perfis/{self.role.pk}/')
        self.assertTrue(Role.objects.filter(pk=self.role.pk).exists())
