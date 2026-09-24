"""Marcação do componente de seleção, que é renderizada pelo servidor."""

from django.test import Client, TestCase

from accounts.models import Role, User


class SelectComponentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        cls.admin.set_superadmin(True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)

    def content(self, url='/usuarios/novo/'):
        return self.client.get(url).content.decode()

    def test_component_wraps_the_native_select(self):
        content = self.content()
        self.assertIn('<div class="select" data-select>', content)
        self.assertIn('<div class="select-native select-wrap"><select name="role"', content)

    def test_native_select_keeps_every_option(self):
        Role.objects.create_role(code='COORDENACAO', name='Coordenação')
        content = self.content()
        for name in ('Administrador', 'Docente', 'Coordenação'):
            with self.subTest(name=name):
                self.assertIn(f'>{name}</option>', content)

    def test_trigger_and_panel_start_hidden_for_the_no_javascript_case(self):
        content = self.content()
        self.assertIn('id="id_role_gatilho" aria-haspopup="listbox" aria-expanded="false"', content)
        self.assertIn('hidden data-select-trigger', content)
        self.assertIn('hidden data-select-panel', content)

    def test_panel_has_search_list_empty_state_and_more(self):
        content = self.content()
        self.assertIn('placeholder="Buscar"', content)
        self.assertIn('role="listbox"', content)
        self.assertIn('Nenhuma opção encontrada.', content)
        self.assertIn('Mostrar mais', content)

    def test_label_is_associated_with_the_trigger(self):
        content = self.content()
        self.assertIn('<label id="id_role_rotulo" for="id_role">Perfil</label>', content)
        self.assertIn('aria-labelledby="id_role_rotulo id_role_gatilho"', content)

    def test_every_choice_field_of_the_project_uses_the_component(self):
        for url in ('/usuarios/novo/', '/usuarios/', '/auditoria/'):
            with self.subTest(url=url):
                content = self.content(url)
                self.assertEqual(content.count('<select '), content.count('data-select-trigger'))
