from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from accounts import permissions
from accounts.models import Role, User


class HomeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def register(self, email, role):
        return User.objects.register(email=email, name=email.partition('@')[0], role=role)


class HomeTests(HomeTestCase):
    def test_opens_the_first_item_the_role_grants(self):
        reader = Role.objects.create_role(code='LEITOR', name='Leitor', permissions=[permissions.USER_VIEW])
        response = self.client_for(self.register('leitor@ifnmg.edu.br', reader)).get('/inicio/')
        self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)

    def test_without_modules_shows_the_restricted_access_notice(self):
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


class ChangesOnTheSameSessionTests(HomeTestCase):
    def test_role_change_ends_the_session_and_the_next_login_has_the_new_access(self):
        self.register('admin@ifnmg.edu.br', self.administrator)
        user = self.register('maria@ifnmg.edu.br', self.administrator)
        client = self.client_for(user)
        self.assertEqual(client.get('/usuarios/').status_code, 200)
        user.change_role(self.teacher)
        self.assertRedirects(client.get('/usuarios/'), '/contas/login/?next=/usuarios/', fetch_redirect_response=False)
        self.assertEqual(self.client_for(User.objects.get(pk=user.pk)).get('/usuarios/').status_code, 403)

    def test_superadmin_granted_and_revoked_by_command(self):
        self.register('admin@ifnmg.edu.br', self.administrator)
        user = self.register('maria@ifnmg.edu.br', self.teacher)
        client = self.client_for(user)
        self.assertEqual(client.get('/usuarios/').status_code, 403)
        call_command('set_superadmin', 'maria@ifnmg.edu.br', '--grant', stdout=StringIO())
        self.assertEqual(client.get('/usuarios/').status_code, 200)
        call_command('set_superadmin', 'maria@ifnmg.edu.br', '--revoke', stdout=StringIO())
        self.assertEqual(client.get('/usuarios/').status_code, 403)
