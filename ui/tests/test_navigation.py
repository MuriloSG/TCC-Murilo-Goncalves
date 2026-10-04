from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from ui.templatetags.ui import navigation


class NavigationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superadmin(email='ana@ifnmg.edu.br', name='Ana Maria Souza', password='Senha-forte-123')

    def user_with(self, *codes):
        suffix = 'ABCDEFGHIJ'[Role.objects.count() % 10]
        role = Role.objects.create_role(code=f'PERFIL_{suffix}', name=f'Perfil {suffix}', permissions=list(codes))
        return User.objects.register(email=f'usuario{suffix.lower()}@ifnmg.edu.br', name='João Lima', role=role)

    def menu(self, user, url):
        """Menu calculado pela templatetag para a requisição real, com o status da resposta."""
        self.client.force_login(user)
        response = self.client.get(url)
        items = navigation({'request': response.wsgi_request})
        return response, {item['label']: [child['label'] for child in item.get('children', [])] for item in items}, items


class GroupVisibilityTests(NavigationTestCase):
    def test_todas_as_permissoes_mostram_cada_item_no_seu_grupo(self):
        response, menu, _ = self.menu(self.admin, '/auditoria/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(menu), ['Painel', 'Agenda', 'Gestão acadêmica', 'Relatórios', 'Notificações', 'Administração', 'Configurações'])
        self.assertEqual(menu['Gestão acadêmica'], ['Ensalamento', 'Espaços', 'Disciplinas', 'Turmas'])
        self.assertEqual(menu['Administração'], ['Usuários', 'Perfis e permissões', 'Auditoria'])

    def test_cada_item_do_grupo_segue_a_propria_permissao(self):
        cases = (
            ('Gestão acadêmica', permissions.SPACE_VIEW, '/espacos/', ['Espaços'], 'Administração'),
            ('Administração', permissions.AUDIT_VIEW, '/auditoria/', ['Auditoria'], 'Gestão acadêmica'),
        )
        for group, code, url, children, absent in cases:
            with self.subTest(group=group):
                response, menu, _ = self.menu(self.user_with(code), url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(menu), [group])
                self.assertEqual(menu[group], children)
                self.assertNotIn(absent, menu)

    def test_um_item_do_grupo_nao_libera_os_demais(self):
        user = self.user_with(permissions.SPACE_VIEW)
        self.client.force_login(user)
        for url in ('/disciplinas/', '/turmas/', '/usuarios/', '/auditoria/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_visualizar_nao_libera_as_acoes_do_modulo(self):
        self.client.force_login(self.user_with(permissions.SPACE_VIEW, permissions.SUBJECT_VIEW))
        for url in ('/espacos/novo/', '/disciplinas/nova/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_acao_sem_visualizar_nao_mostra_o_item(self):
        _, menu, _ = self.menu(self.user_with(permissions.SPACE_CREATE, permissions.USER_IMPORT, permissions.PANEL_VIEW), '/inicio/')
        self.assertEqual(list(menu), ['Painel'])


class CurrentItemTests(NavigationTestCase):
    def test_grupo_da_pagina_atual_abre_com_o_item_marcado(self):
        cases = (
            ('/espacos/', 'Gestão acadêmica', 'Espaços'),
            ('/perfis/', 'Administração', 'Perfis e permissões'),
            ('/auditoria/', 'Administração', 'Auditoria'),
        )
        for url, group, child in cases:
            with self.subTest(url=url):
                _, _, items = self.menu(self.admin, url)
                current = [item for item in items if item['current']]
                self.assertEqual([item['label'] for item in current], [group])
                self.assertEqual([entry['label'] for entry in current[0]['children'] if entry['current']], [child])

    def test_item_independente_nao_abre_grupo(self):
        _, _, items = self.menu(self.admin, '/agenda/')
        self.assertEqual([item['label'] for item in items if item['current']], ['Agenda'])

    def test_grupo_aberto_na_barra_lateral_e_no_menu_do_celular(self):
        self.client.force_login(self.admin)
        content = self.client.get('/espacos/').content.decode()
        sidebar = content[content.index('<aside class="sidebar"'):content.index('</aside>')]
        drawer = content[content.index('<div class="topbar-panel">'):content.index('<header class="header">')]
        for area in (sidebar, drawer):
            with self.subTest(area=area[:30]):
                self.assertEqual(area.count('<details class="nav-group" open>'), 1)
                opened = area[area.index('<details class="nav-group" open>'):]
                opened = opened[:opened.index('</details>')]
                self.assertIn('Gestão acadêmica', opened)
                self.assertIn('<a href="/espacos/" aria-current="page">', opened)


class RoutesTests(NavigationTestCase):
    def test_links_do_menu_abrem_para_quem_tem_acesso(self):
        self.client.force_login(self.admin)
        _, _, items = self.menu(self.admin, '/inicio/')
        for entry in items:
            for target in entry.get('children') or [entry]:
                with self.subTest(item=target['label']):
                    self.assertEqual(self.client.get(target['url']).status_code, 200)

    def test_inicio_abre_o_primeiro_item_liberado(self):
        self.client.force_login(self.user_with(permissions.AUDIT_VIEW))
        self.assertRedirects(self.client.get(reverse('home')), '/auditoria/', fetch_redirect_response=False)
