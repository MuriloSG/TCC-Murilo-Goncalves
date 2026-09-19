from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.views.defaults import permission_denied

from accounts.models import Role, User


class HomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=Role.objects.get(code='DOCENTE'),
        )

    def test_anonymous_is_redirected_to_login_with_next(self):
        response = self.client.get('/inicio/')
        self.assertRedirects(response, '/contas/login/?next=/inicio/', fetch_redirect_response=False)

    def test_requires_only_authentication(self):
        self.client.force_login(self.user)
        response = self.client.get('/inicio/')
        self.assertContains(response, 'Maria Sousa')
        self.assertContains(response, 'O seu perfil ainda não dá acesso a nenhuma funcionalidade')

    def test_login_redirects_to_home(self):
        self.user.set_password('Senha-forte-123')
        self.user.save()
        response = self.client.post(
            '/contas/login/', {'login': 'maria@ifnmg.edu.br', 'password': 'Senha-forte-123'},
        )
        self.assertRedirects(response, '/inicio/')

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.post('/contas/logout/')
        self.assertRedirects(response, '/contas/login/')
        self.assertRedirects(self.client.get('/inicio/'), '/contas/login/?next=/inicio/')


class ProjectRoutesTests(TestCase):
    def test_admin_does_not_exist(self):
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    def test_root_is_left_free(self):
        self.assertEqual(self.client.get('/').status_code, 404)


class PermissionDeniedPageTests(TestCase):
    def test_renders_friendly_403(self):
        request = RequestFactory().get('/usuarios/')
        request.user = User(email='maria@ifnmg.edu.br', name='Maria')
        response = permission_denied(request, PermissionDenied())
        self.assertEqual(response.status_code, 403)
        self.assertIn('Acesso restrito', response.content.decode())
