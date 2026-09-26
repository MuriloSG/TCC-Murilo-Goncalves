import re

from django.test import TestCase

from accounts.models import Role, User


class ScreensTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.create_superadmin(email='admin@ifnmg.edu.br', name='Ana Souza', password='Senha-forte-123')
        cls.active = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)
        cls.inactive = User.objects.register(email='carla@ifnmg.edu.br', name='Carla Mendes', role=cls.teacher)
        cls.inactive.deactivate()
        cls.role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=[])

    def setUp(self):
        self.client.force_login(self.admin)

    def row(self, content, email):
        rows = re.findall(r'<tr>.*?</tr>', content, re.S)
        return next(row for row in rows if email in row)


class UserListScreenTests(ScreensTestCase):
    def test_selos_de_situacao_com_palavra_e_icone(self):
        content = self.client.get('/usuarios/').content.decode()
        active = re.search(r'<span class="badge tone-success">(<svg.*?</svg>)\s*Ativo</span>', self.row(content, 'maria@'), re.S)
        inactive = re.search(r'<span class="badge tone-info">(<svg.*?</svg>)\s*Inativo</span>', self.row(content, 'carla@'), re.S)
        self.assertIsNotNone(active)
        self.assertIsNotNone(inactive)
        self.assertIn('aria-hidden="true"', active.group(1))
        self.assertNotEqual(active.group(1), inactive.group(1))

    def test_botao_editar_com_aria_label_e_dica(self):
        row = self.row(self.client.get('/usuarios/').content.decode(), 'maria@')
        edit = re.search(r'<a class="icon-btn" href="/usuarios/\d+/editar/"[^>]*>.*?</a>', row, re.S).group(0)
        self.assertIn('aria-label="Editar"', edit)
        self.assertIn('hx-get="/usuarios/', edit)
        self.assertIn('<span class="tip" role="tooltip">Editar</span>', edit)
        self.assertIn('<span class="label">Editar</span>', edit)

    def test_mais_acoes_com_trocar_perfil_e_situacao(self):
        row = self.row(self.client.get('/usuarios/').content.decode(), 'maria@')
        self.assertRegex(row, r'<summary class="icon-btn" aria-label="Mais ações">')
        self.assertIn('<span class="tip" role="tooltip">Mais ações</span>', row)
        self.assertIn('Trocar perfil</a>', row)
        self.assertRegex(row, r'(?s)class="danger">.*?Desativar usuário</a>')
        inactive = self.row(self.client.get('/usuarios/').content.decode(), 'carla@')
        self.assertIn('Reativar usuário</a>', inactive)

    def test_menu_compacto_do_celular_com_todas_as_acoes(self):
        content = self.client.get('/usuarios/').content.decode()
        self.assertIn('<table class="data-table compact-rows">', content)
        menu = re.search(r'<details class="menu row-menu">.*?</details>', self.row(content, 'maria@'), re.S).group(0)
        self.assertIn('<summary class="icon-btn" aria-label="Mais ações">', menu)
        labels = re.findall(r'<a href="/usuarios/\d+/[^"]+" hx-get="[^"]+" hx-target="#modal"[^>]*>.*?</svg>\s*(.*?)</a>', menu, re.S)
        self.assertEqual(labels, ['Editar', 'Trocar perfil', 'Desativar usuário'])
        inactive = self.row(content, 'carla@')
        self.assertRegex(inactive, r'(?s)<details class="menu row-menu">.*?Reativar usuário</a>')

    def test_menu_compacto_segue_as_permissoes(self):
        role = Role.objects.create_role(code='EDICAO', name='Edição', permissions=['USUARIO.VISUALIZAR', 'USUARIO.EDITAR'])
        self.client.force_login(User.objects.register(email='joao@ifnmg.edu.br', name='João', role=role))
        menu = re.search(r'<details class="menu row-menu">.*?</details>', self.row(self.client.get('/usuarios/').content.decode(), 'maria@'), re.S).group(0)
        self.assertIn('Editar</a>', menu)
        self.assertNotIn('Trocar perfil', menu)
        self.assertNotIn('Desativar usuário', menu)

    def test_perfil_e_situacao_na_linha_de_resumo(self):
        row = self.row(self.client.get('/usuarios/').content.decode(), 'maria@')
        self.assertIn('<td class="cell-meta" data-label="Perfil">Docente</td>', row)
        self.assertIn('<td class="cell-meta" data-label="Situação">', row)

    def test_celulas_com_rotulo_da_coluna(self):
        row = self.row(self.client.get('/usuarios/').content.decode(), 'maria@')
        for label in ('Usuário', 'Perfil', 'Situação', 'Ações'):
            self.assertIn(f'data-label="{label}"', row)

    def test_acoes_seguem_as_permissoes(self):
        role = Role.objects.create_role(code='CONSULTA', name='Consulta', permissions=['USUARIO.VISUALIZAR'])
        self.client.force_login(User.objects.register(email='joao@ifnmg.edu.br', name='João', role=role))
        content = self.client.get('/usuarios/').content.decode()
        self.assertNotIn('aria-label="Editar"', content)
        self.assertNotIn('Mais ações', content)
        self.assertNotIn('Cadastrar usuário', content)

    def test_rodape_com_a_contagem(self):
        self.assertContains(
            self.client.get('/usuarios/'), 'Exibindo <strong>1</strong> a <strong>3</strong> de <strong>3</strong> usuários',
        )


class MessagesScreenTests(ScreensTestCase):
    def test_mensagem_de_erro_de_operacao(self):
        response = self.client.post(f'/usuarios/{self.admin.pk}/desativar/', follow=True)
        alert = re.search(r'<div class="alert tone-error" role="alert">(<svg.*?</svg>)\s*<p>(.*?)</p>', response.content.decode(), re.S)
        self.assertIsNotNone(alert)
        self.assertIn('aria-hidden="true"', alert.group(1))
        self.assertIn('capacidade administrativa', alert.group(2))

    def test_mensagem_de_sucesso(self):
        response = self.client.post(f'/usuarios/{self.active.pk}/desativar/', follow=True)
        self.assertRegex(
            response.content.decode(),
            r'<div class="alert tone-success" role="status"><svg[^>]*aria-hidden="true"[^>]*>.*?</svg>\s*'
            r'<p>Usuário maria@ifnmg.edu.br desativado.</p><button class="icon-btn alert-close" type="button" '
            r'data-message-close aria-label="Fechar mensagem" hidden>',
        )


class FormScreenTests(ScreensTestCase):
    def test_campo_com_erro(self):
        response = self.client.post('/usuarios/novo/', {'name': 'Joana', 'email': '', 'role': self.teacher.pk})
        email = re.search(r'<input[^>]*name="email"[^>]*>', response.content.decode()).group(0)
        self.assertIn('aria-invalid="true"', email)
        self.assertIn('aria-describedby="id_email_error"', email)
        self.assertRegex(response.content.decode(), r'<div class="error" id="id_email_error">\s*<p><svg')

    def test_campo_opcional(self):
        response = self.client.get('/perfis/novo/')
        self.assertContains(
            response, '<label id="id_description_rotulo" for="id_description">Descrição <span class="optional">(opcional)</span></label>', html=True,
        )
        self.assertContains(response, '<label id="id_name_rotulo" for="id_name">Nome</label>', html=True)

    def test_ajuda_associada_ao_campo(self):
        response = self.client.get('/perfis/novo/')
        code = re.search(r'<input[^>]*name="code"[^>]*>', response.content.decode()).group(0)
        self.assertIn('aria-describedby="id_code_helptext"', code)
        self.assertContains(response, 'id="id_code_helptext"')

    def test_permissoes_agrupadas_por_recurso(self):
        response = self.client.get(f'/perfis/{self.role.pk}/permissoes/')
        self.assertRegex(response.content.decode(), r'<summary>\s*<span class="checklist-group-name">Usuários</span>')
        self.assertContains(response, 'value="USUARIO.CRIAR"')

    def test_lista_de_permissoes_com_contagem(self):
        self.role.set_permissions(['USUARIO.VISUALIZAR', 'USUARIO.EDITAR'])
        content = self.client.get(f'/perfis/{self.role.pk}/permissoes/', headers={'HX-Request': 'true'}).content.decode()
        self.assertIn('<dialog class="modal modal-wide"', content)
        self.assertRegex(content, r'<strong><span data-checklist-selected>2</span> de 22</strong> permissões selecionadas')
        self.assertIn('<span class="count" data-checklist-group-count>2/7</span>', content)
        self.assertRegex(content, r'value="USUARIO.EDITAR"[^>]*checked')
        self.assertIn('<strong>USUARIO.EDITAR</strong> <span class="perm-description">Alterar nome e e-mail de usuário</span>', content)
        self.assertIn('Salvar permissões</button>', content)

    def test_busca_e_selecao_ficam_ocultas_sem_javascript(self):
        content = self.client.get(f'/perfis/{self.role.pk}/permissoes/').content.decode()
        self.assertIn('<div class="checklist-tools" data-checklist-tools hidden>', content)
        self.assertIn('<p class="checklist-unsaved" data-checklist-unsaved hidden>', content)
        self.assertRegex(content, r'<span data-checklist-selected>0</span> de 22</strong>')

    def test_campo_de_escolha_usa_o_componente(self):
        content = self.client.get('/usuarios/novo/').content.decode()
        self.assertRegex(content, r'<div class="select" data-select>')
        self.assertRegex(content, r'<div class="select-native select-wrap"><select name="role"')
        self.assertIn('data-select-trigger', content)
        self.assertIn('data-select-search', content)
        self.assertIn('role="listbox"', content)


class RoleScreenTests(ScreensTestCase):
    def test_estado_vazio_de_permissoes(self):
        response = self.client.get(f'/perfis/{self.role.pk}/')
        self.assertContains(response, '<p>Este perfil não concede nenhuma permissão.</p>', html=True)
        section = re.search(r'<section class="card" aria-labelledby="permissoes-perfil">.*?</section>', response.content.decode(), re.S)
        self.assertNotIn('<img', section.group(0))

    def test_cartoes_nao_aninhados(self):
        for url in ('/usuarios/', '/perfis/', f'/perfis/{self.role.pk}/', '/inicio/'):
            with self.subTest(url=url):
                content = self.client.get(url).content.decode()
                for section in re.findall(r'<section class="card".*?</section>', content, re.S):
                    self.assertEqual(section.count('class="card"'), 1)

    def test_um_botao_primario_por_tela(self):
        for url in ('/usuarios/', '/perfis/', f'/perfis/{self.role.pk}/', '/inicio/'):
            with self.subTest(url=url):
                self.assertLessEqual(self.client.get(url).content.decode().count('class="btn-primary"'), 1)

    def test_acoes_do_perfil_personalizado(self):
        row = self.row(self.client.get('/perfis/').content.decode(), 'COORDENACAO')
        for label in ('Editar', 'Alterar permissões', 'Excluir perfil'):
            self.assertIn(f'aria-label="{label}"', row)
        system = self.row(self.client.get('/perfis/').content.decode(), 'ADMINISTRADOR')
        self.assertNotIn('Excluir perfil', system)
