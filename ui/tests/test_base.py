import re
from html.parser import HTMLParser

from django.contrib.staticfiles import finders
from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User
from notices import catalog
from notices.models import Notification
from ui.contrast import STYLES


def notify(user, title):
    return Notification.objects.notify(user, catalog.INFORMATION, title, 'Mensagem do comunicado.')


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

    def test_primeiro_focavel_e_o_link_para_o_conteudo(self):
        for url in ('/inicio/', '/usuarios/', '/perfis/'):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
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

    def test_sino_de_notificacoes_no_cabecalho_e_no_celular(self):
        notify(self.admin, 'Comunicado do sistema')
        notify(self.admin, 'Outro comunicado')
        content = self.client.get('/inicio/', follow=True).content.decode()
        header = content[content.index('<header class="header">'):content.index('</header>')]
        topbar = content[content.index('<div class="topbar">'):content.index('<header class="header">')]
        for area in (header, topbar):
            with self.subTest(area=area[:30]):
                self.assertIn(
                    '<details class="menu notifications" data-notifications'
                    ' data-notifications-panel="/notificacoes/sino/"'
                    ' data-notifications-channel="/ws/notificacoes/">',
                    area,
                )
                self.assertIn('<summary class="icon-btn" aria-label="Notificações, 2 não lidas">', area)
                self.assertIn('<span class="notifications-count" aria-hidden="true">2</span>', area)
        self.assertLess(header.index('data-notifications'), header.index('user-menu'))

    def test_painel_lista_as_notificacoes_do_usuario(self):
        lida = notify(self.admin, 'Comunicado lido')
        lida.mark_as_read()
        notify(self.admin, 'Comunicado novo')
        content = self.client.get('/inicio/', follow=True).content.decode()
        panel = content[content.index('<div class="notifications-panel">'):]
        panel = panel[:panel.index('</details>')]
        self.assertEqual(panel.count('<li class="notification'), 2)
        self.assertEqual(panel.count('<li class="notification is-unread">'), 1)
        self.assertIn(
            '<span class="notification-title">Comunicado novo<span class="sr-only"> (não lida)</span></span>',
            panel,
        )
        self.assertIn('<div class="notifications-filter" data-filter hidden>', panel)
        self.assertIn('<p class="notifications-empty" data-empty hidden>Nenhuma notificação não lida.</p>', panel)
        self.assertRegex(panel, r'<button class="notifications-read-all" type="submit">')

    def test_barra_lateral_recolhida_vem_do_cookie(self):
        self.client.cookies['menu_lateral'] = 'recolhido'
        self.assertContains(self.client.get('/inicio/', follow=True), '<div class="app-shell is-collapsed">')
        self.client.cookies['menu_lateral'] = 'expandido'
        self.assertContains(self.client.get('/inicio/', follow=True), '<div class="app-shell">')

    def test_confirmacao_de_saida_em_modal(self):
        response = self.client.get('/contas/logout/', headers={'HX-Request': 'true'})
        content = response.content.decode()
        self.assertTrue(content.lstrip().startswith('<dialog class="modal"'), content[:80])
        self.assertIn('Sair do sistema?</h1>', content)
        self.assertRegex(content, r'<form method="post" action="/contas/logout/">')
        self.assertNotIn('hx-post', content)
        self.assertIn('data-modal-close>Fechar</button>', content)
        self.assertIn('_auth_user_id', self.client.session)

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
        response = self.client.get('/inicio/', follow=True)
        self.assertContains(response, '<script src="/static/ui/js/htmx.min.js" defer></script>', html=True)
        self.assertRegex(response.content.decode(), r'<body hx-headers=\'\{"X-CSRFToken": "\w+"\}\'>')
        self.assertContains(response, '<div id="modal"></div>', html=True)


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


class BrandTests(LayoutTestCase):
    """Nome do sistema e ícone declarados no template base, para toda página."""

    ICONS = (
        '<link rel="icon" href="/static/ui/img/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/png" href="/static/ui/img/favicon-512.png" sizes="512x512">',
        '<link rel="apple-touch-icon" href="/static/ui/img/apple-touch-icon.png">',
    )

    def test_titulo_e_icone_em_toda_pagina(self):
        for user, url in ((None, '/contas/login/'), (None, '/calendario/'), (self.admin, '/inicio/')):
            with self.subTest(url=url):
                if user:
                    self.client.force_login(user)
                response = self.client.get(url, follow=True)
                self.assertContains(response, '· IFAgenda</title>')
                for icon in self.ICONS:
                    self.assertContains(response, icon, html=True)

    def test_arquivos_do_icone_existem(self):
        for path in ('ui/img/favicon.ico', 'ui/img/favicon-512.png', 'ui/img/apple-touch-icon.png'):
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find(path))
