from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from accounts import permissions
from accounts.models import Role, User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import management_role, requester_role


class HomeTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def register(self, email, role):
        return User.objects.register(email=email, name=email.partition('@')[0], role=role)


class HomeTests(HomeTestCase):
    def test_home_opens_the_first_granted_item_or_the_notice(self):
        with self.case('primeiro item'):
            reader = Role.objects.create_role(code='LEITOR', name='Leitor', permissions=[permissions.USER_VIEW])
            response = self.client_for(self.register('leitor@ifnmg.edu.br', reader)).get('/inicio/')
            self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)
        with self.case('sem módulos'):
            empty = Role.objects.create_role(code='VAZIO', name='Vazio', permissions=[])
            user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=empty)
            response = self.client_for(user).get('/inicio/')
            self.assertContains(response, 'Maria Sousa')
            self.assertContains(response, 'O seu perfil ainda não dá acesso a nenhum módulo')
            self.assertNotContains(response, 'Voltar para o início')
            self.assertTemplateUsed(response, 'ui/components/access_denied.html')


class DeniedAccessTests(HomeTestCase):
    def test_denied_page_is_the_friendly_403(self):
        teacher = self.register('docente@ifnmg.edu.br', self.teacher)
        response = self.client_for(teacher).get('/usuarios/novo/')
        self.assertContains(response, 'Acesso restrito', status_code=403)
        self.assertContains(response, 'Voltar para o início', status_code=403)
        self.assertTemplateUsed(response, 'ui/components/access_denied.html')

    def test_denial_comes_before_the_continuity_rule(self):
        superadmin = self.register('super@ifnmg.edu.br', self.teacher)
        superadmin.set_superadmin(True)
        viewer = Role.objects.create_role(code='LEITOR', name='Leitor', permissions=[permissions.USER_VIEW])
        reader = self.register('leitor@ifnmg.edu.br', viewer)
        response = self.client_for(reader).post(f'/usuarios/{superadmin.pk}/desativar/')
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'capacidade administrativa', status_code=403)
        self.assertTrue(User.objects.get(pk=superadmin.pk).is_active)
