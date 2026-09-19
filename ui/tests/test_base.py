import re
from html.parser import HTMLParser

from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User
from ui.contrast import STYLES


class FocusableParser(HTMLParser):
    """Guarda os elementos focáveis na ordem do documento e os endereços de recursos."""

    FOCUSABLE = {'a', 'button', 'input', 'select', 'textarea', 'summary'}

    def __init__(self):
        super().__init__()
        self.focusable = []
        self.resources = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in self.FOCUSABLE and attributes.get('type') != 'hidden' and (tag != 'a' or 'href' in attributes):
            self.focusable.append([tag, attributes, ''])
            self.current = self.focusable[-1]
        if tag in {'link', 'script', 'img'}:
            self.resources.append(attributes.get('href') or attributes.get('src'))

    def handle_endtag(self, tag):
        if self.current and tag == self.current[0]:
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current[2] += data


def parse(response):
    parser = FocusableParser()
    parser.feed(response.content.decode())
    return parser


class LayoutTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superadmin(email='ana@ifnmg.edu.br', name='Ana Maria Souza', password='Senha-forte-123')
        role = Role.objects.create_role(code='SECRETARIA', name='Secretaria', permissions=[permissions.USER_VIEW])
        cls.clerk = User.objects.register(email='joao@ifnmg.edu.br', name='João Lima', role=role)


class AppLayoutTests(LayoutTestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_barra_lateral_com_simbolo_e_nome_do_sistema(self):
        response = self.client.get('/inicio/')
        content = response.content.decode()
        sidebar = content[content.index('<aside class="sidebar" id="menu-lateral">'):content.index('</aside>')]
        self.assertRegex(sidebar, r'<a class="brand" href="/inicio/">\s*<img src="/static/ui/img/simbolo-if.png" alt=""')
        self.assertIn('<span class="brand-name">Agendamento de espaços</span>', sidebar)
        self.assertIn('<span class="brand-campus">IFNMG Campus Salinas</span>', sidebar)
        self.assertIn('<nav class="side-nav" aria-label="Principal">', sidebar)

    def test_primeiro_focavel_e_o_link_para_o_conteudo(self):
        for url in ('/inicio/', '/usuarios/', '/perfis/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                tag, attributes, text = parse(response).focusable[0]
                self.assertEqual((tag, attributes.get('href'), text), ('a', '#conteudo', 'Ir para o conteúdo'))
                self.assertContains(response, '<main class="page" id="conteudo" tabindex="-1">')

    def test_item_atual_e_trilha_na_lista_de_usuarios(self):
        response = self.client.get('/usuarios/')
        self.assertRegex(response.content.decode(), r'<a href="/usuarios/" aria-current="page"><svg[^>]*>.*?</svg>\s*<span class="nav-text">Usuários</span></a>')
        self.assertNotRegex(response.content.decode(), r'<a href="/perfis/" aria-current="page">')
        crumbs = re.search(r'<nav class="crumbs" aria-label="Trilha de navegação">(.*?)</nav>', response.content.decode(), re.S)
        self.assertRegex(crumbs.group(1), r'<span aria-current="page">Usuários</span></li>\s*</ol>\s*$')

    def test_acoes_do_perfil_marcam_o_item_perfis(self):
        role = Role.objects.get(code='SECRETARIA')
        response = self.client.get(f'/perfis/{role.pk}/')
        self.assertRegex(response.content.decode(), r'<a href="/perfis/" aria-current="page">')

    def test_menu_do_usuario(self):
        response = self.client.get('/inicio/')
        content = response.content.decode()
        menu = content[content.index('<details class="menu user-menu">'):]
        menu = menu[:menu.index('</details>')]
        summary = menu[:menu.index('</summary>')]
        self.assertIn('<summary aria-label="Menu do usuário"><span class="avatar" aria-hidden="true">AS</span>', summary)
        self.assertNotIn('Ana Maria Souza', summary)
        dropdown = menu[menu.index('<div class="menu-list">'):]
        self.assertIn('<span class="who-name">Ana Maria Souza</span>', dropdown)
        self.assertIn('<span class="who-role">Administrador</span>', dropdown)
        self.assertRegex(menu, r'<a href="/contas/logout/" hx-get="/contas/logout/" hx-target="#modal"><svg[^>]*>.*?</svg>\s*Sair</a>')

    def test_menu_do_celular_sem_javascript(self):
        response = self.client.get('/inicio/')
        content = response.content.decode()
        topbar = content[content.index('<div class="topbar">'):content.index('<header class="header">')]
        self.assertRegex(topbar, r'<details class="topbar-menu">\s*<summary><svg[^>]*>.*?</svg>\s*Menu</summary>')
        self.assertIn('<nav class="side-nav" aria-label="Principal">', topbar)
        self.assertRegex(topbar, r'<a class="btn-secondary" href="/contas/logout/" hx-get="/contas/logout/" hx-target="#modal">')
        self.assertIn('Sair</a>', topbar)

    def test_rodape_da_barra_lateral_com_usuario_e_sair(self):
        content = self.client.get('/inicio/').content.decode()
        footer = content[content.index('<div class="sidebar-footer">'):content.index('</aside>')]
        self.assertIn('<span class="avatar" aria-hidden="true">AS</span>', footer)
        self.assertIn('<span class="who-name" title="Ana Maria Souza">Ana</span>', footer)
        self.assertRegex(footer, r'<a class="icon-btn" href="/contas/logout/" hx-get="/contas/logout/" hx-target="#modal" aria-label="Sair">')
        self.assertIn('<span class="tip" role="tooltip">Sair</span>', footer)

    def test_botao_de_recolher_a_barra_lateral(self):
        content = self.client.get('/inicio/').content.decode()
        self.assertRegex(
            content,
            r'<button class="icon-btn" type="button" data-sidebar-toggle aria-controls="menu-lateral" '
            r'aria-expanded="true" aria-label="Recolher menu lateral" hidden>',
        )
        self.assertIn('<div class="app-shell">', content)
        self.assertIn('<script src="/static/ui/js/sidebar.js" defer></script>', content)

    def test_barra_lateral_recolhida_vem_do_cookie(self):
        self.client.cookies['menu_lateral'] = 'recolhido'
        self.assertContains(self.client.get('/inicio/'), '<div class="app-shell is-collapsed">')
        self.client.cookies['menu_lateral'] = 'expandido'
        self.assertContains(self.client.get('/inicio/'), '<div class="app-shell">')

    def test_confirmacao_de_saida_em_modal(self):
        response = self.client.get('/contas/logout/', headers={'HX-Request': 'true'})
        content = response.content.decode()
        self.assertTrue(content.lstrip().startswith('<dialog class="modal"'), content[:80])
        self.assertIn('Sair do sistema?</h1>', content)
        self.assertRegex(content, r'<form method="post" action="/contas/logout/">')
        self.assertNotIn('hx-post', content)
        self.assertIn('data-modal-close>Fechar</button>', content)
        self.assertIn('_auth_user_id', self.client.session)

    def test_sair_pelo_modal_encerra_a_sessao(self):
        response = self.client.post('/contas/logout/')
        self.assertRedirects(response, '/contas/login/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_confirmacao_de_saida_sem_javascript_e_a_pagina(self):
        response = self.client.get('/contas/logout/')
        self.assertContains(response, '<header class="auth-panel">')
        self.assertContains(response, '<h1>Sair do sistema?</h1>', html=True)

    def test_navegacao_sem_permissao_de_perfis(self):
        self.client.force_login(self.clerk)
        response = self.client.get('/usuarios/')
        self.assertContains(response, 'href="/usuarios/"')
        self.assertNotContains(response, 'href="/perfis/"')
        self.assertNotContains(response, 'Perfis')

    def test_htmx_e_csrf_so_nas_paginas_autenticadas(self):
        response = self.client.get('/inicio/')
        self.assertContains(response, '<script src="/static/ui/js/htmx.min.js" defer></script>', html=True)
        self.assertRegex(response.content.decode(), r'<body hx-headers=\'\{"X-CSRFToken": "\w+"\}\'>')
        self.assertContains(response, '<div id="modal"></div>', html=True)


class AuthLayoutTests(LayoutTestCase):
    def test_login_com_painel_da_marca(self):
        response = self.client.get('/contas/login/')
        self.assertContains(response, '<header class="auth-panel">')
        self.assertContains(
            response,
            '<img class="auth-logo" src="/static/ui/img/logo-horizontal-negativo.png" '
            'alt="Instituto Federal Norte de Minas Gerais, Campus Salinas" width="813" height="225">',
            html=True,
        )
        self.assertContains(response, '<p class="auth-title">Agendamento de espaços</p>', html=True)
        self.assertContains(response, '<h1>Entrar</h1>', html=True)
        self.assertNotContains(response, 'class="sidebar"')
        self.assertEqual(parse(response).focusable[0][1].get('href'), '#conteudo')

    def test_campos_do_login_com_icone(self):
        response = self.client.get('/contas/login/')
        self.assertContains(response, '<label for="id_login">E-mail institucional</label>', html=True)
        self.assertContains(response, 'placeholder="nome.sobrenome@ifnmg.edu.br"')
        self.assertEqual(response.content.decode().count('<div class="control">'), 2)
        self.assertContains(response, 'Para obter acesso, procure um administrador do sistema.')


class ExternalResourcesTests(LayoutTestCase):
    def test_paginas_so_usam_enderecos_do_proprio_sistema(self):
        self.client.force_login(self.admin)
        for url in ('/inicio/', '/usuarios/', '/perfis/'):
            with self.subTest(url=url):
                for address in parse(self.client.get(url)).resources:
                    self.assertTrue(address.startswith('/') and not address.startswith('//'), address)
        self.client.logout()
        for address in parse(self.client.get('/contas/login/')).resources:
            self.assertTrue(address.startswith('/') and not address.startswith('//'), address)

    def test_fontes_servidas_pelo_projeto(self):
        css = STYLES.read_text(encoding='utf-8')
        addresses = re.findall(r'url\(\s*["\']?([^"\')]+)', css)
        self.assertEqual(len(addresses), 2)
        for address in addresses:
            self.assertTrue(address.startswith('../fonts/'), address)
        self.assertNotRegex(css, r'@import\s+url|https?://')
