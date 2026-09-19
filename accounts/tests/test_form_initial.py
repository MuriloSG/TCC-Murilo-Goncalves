import re

from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User


class EditFormsShowCurrentValuesTests(TestCase):
    """Os formulários de edição abrem com os dados atuais do alvo.

    O FormView sempre passa `initial`, mesmo vazio, e os formulários precisam
    combinar os dados atuais com ele, e não só usá-los quando `initial` falta.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superadmin(email='admin@ifnmg.edu.br', name='Admin', password='Senha-forte-123')
        cls.role = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', description='Coordenadores de curso',
            permissions=[permissions.USER_VIEW, permissions.USER_EDIT],
        )
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.role)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_edicao_de_usuario(self):
        content = self.client.get(f'/usuarios/{self.target.pk}/editar/').content.decode()
        self.assertRegex(content, r'<input[^>]*name="name"[^>]*value="Maria Sousa"')
        self.assertRegex(content, r'<input[^>]*name="email"[^>]*value="maria@ifnmg.edu.br"')

    def test_troca_de_perfil(self):
        content = self.client.get(f'/usuarios/{self.target.pk}/perfil/').content.decode()
        self.assertRegex(content, rf'<option value="{self.role.pk}" selected>Coordenação</option>')

    def test_edicao_de_perfil(self):
        content = self.client.get(f'/perfis/{self.role.pk}/editar/').content.decode()
        self.assertRegex(content, r'<input[^>]*name="name"[^>]*value="Coordenação"')
        self.assertIn('>\nCoordenadores de curso</textarea>', content)

    def test_permissoes_do_perfil(self):
        content = self.client.get(f'/perfis/{self.role.pk}/permissoes/').content.decode()
        checked = re.findall(r'<input[^>]*value="([A-Z_.]+)"[^>]*checked', content)
        self.assertEqual(sorted(checked), sorted([permissions.USER_VIEW, permissions.USER_EDIT]))
