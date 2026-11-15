from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User


class EditFormsShowCurrentValuesTests(TestCase):
    """O FormView sempre passa `initial`, e os formulários precisam combinar os dados atuais com ele."""

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

    def form(self, url):
        return self.client.get(url).context['form']

    def test_edit_forms_show_the_current_values(self):
        with self.subTest('usuário'):
            form = self.form(f'/usuarios/{self.target.pk}/editar/')
            self.assertEqual((form['name'].value(), form['email'].value()), ('Maria Sousa', 'maria@ifnmg.edu.br'))
            self.assertEqual(self.form(f'/usuarios/{self.target.pk}/perfil/')['role'].value(), self.role.pk)
        with self.subTest('perfil'):
            form = self.form(f'/perfis/{self.role.pk}/editar/')
            self.assertEqual((form['name'].value(), form['description'].value()), ('Coordenação', 'Coordenadores de curso'))
