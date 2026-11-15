import re

from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import requester_role

GRANTABLE = permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS
USER_GROUP = sum(code.startswith('USUARIO.') for code in GRANTABLE)


class ScreensTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()
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


class FormScreenTests(ScreensTestCase):
    def test_fields_are_accessible(self):
        with self.case('campo com erro'):
            response = self.client.post('/usuarios/novo/', {'name': 'Joana', 'email': '', 'role': self.teacher.pk})
            email = re.search(r'<input[^>]*name="email"[^>]*>', response.content.decode()).group(0)
            self.assertIn('aria-invalid="true"', email)
            self.assertIn('aria-describedby="id_email_error"', email)
            self.assertRegex(response.content.decode(), r'<div class="error" id="id_email_error">\s*<p><svg')
        with self.case('campo opcional'):
            response = self.client.get('/perfis/novo/')
            self.assertContains(
                response, '<label id="id_description_rotulo" for="id_description">Descrição <span class="optional">(opcional)</span></label>', html=True,
            )
            self.assertContains(response, '<label id="id_name_rotulo" for="id_name">Nome</label>', html=True)
        with self.case('ajuda associada'):
            response = self.client.get('/perfis/novo/')
            code = re.search(r'<input[^>]*name="code"[^>]*>', response.content.decode()).group(0)
            self.assertIn('aria-describedby="id_code_helptext"', code)
            self.assertContains(response, 'id="id_code_helptext"')

    def test_permission_checklist_is_grouped_and_counted(self):
        with self.case('agrupadas por recurso'):
            response = self.client.get(f'/perfis/{self.role.pk}/permissoes/')
            self.assertRegex(response.content.decode(), r'<summary>\s*<span class="checklist-group-name">Usuários</span>')
            self.assertContains(response, 'value="USUARIO.CRIAR"')
        with self.case('com contagem'):
            self.role.set_permissions(['USUARIO.VISUALIZAR', 'USUARIO.EDITAR'])
            content = self.client.get(f'/perfis/{self.role.pk}/permissoes/', headers={'HX-Request': 'true'}).content.decode()
            self.assertIn('<dialog class="modal modal-wide"', content)
            self.assertRegex(content, rf'<strong><span data-checklist-selected>2</span> de {len(GRANTABLE)}</strong> permissões selecionadas')
            self.assertIn(f'<span class="count" data-checklist-group-count>2/{USER_GROUP}</span>', content)
            self.assertRegex(content, r'value="USUARIO.EDITAR"[^>]*checked')
            self.assertIn('<strong>USUARIO.EDITAR</strong> <span class="perm-description">Alterar nome e e-mail de usuário</span>', content)
            self.assertIn('Salvar permissões</button>', content)
