from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User


class AccessTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=cls.teacher)
        cls.superadmin.set_superadmin(True)

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def register(self, email, role):
        return User.objects.register(email=email, name=email.partition('@')[0], role=role)


class DeniedAccessTests(AccessTestCase):
    def test_denied_page_is_the_friendly_403(self):
        teacher = self.register('docente@ifnmg.edu.br', self.teacher)
        response = self.client_for(teacher).get('/usuarios/novo/')
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Acesso restrito', status_code=403)

    def test_denied_page_uses_the_access_denied_component(self):
        teacher = self.register('docente@ifnmg.edu.br', self.teacher)
        response = self.client_for(teacher).get('/usuarios/novo/')
        self.assertTemplateUsed(response, 'ui/components/access_denied.html')
        self.assertContains(response, 'Voltar para o início', status_code=403)

    def test_denial_comes_before_the_continuity_rule(self):
        viewer = Role.objects.create_role(code='LEITOR', name='Leitor', permissions=[permissions.USER_VIEW])
        reader = self.register('leitor@ifnmg.edu.br', viewer)
        response = self.client_for(reader).post(f'/usuarios/{self.superadmin.pk}/desativar/')
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'capacidade administrativa', status_code=403)
        self.assertTrue(User.objects.get(pk=self.superadmin.pk).is_active)


class RoleNameIndependenceTests(AccessTestCase):
    def test_administrator_without_a_permission_is_refused(self):
        admin = self.register('admin@ifnmg.edu.br', self.administrator)
        self.administrator.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_CREATE})
        response = self.client_for(admin).post(
            '/usuarios/novo/', {'name': 'Novo', 'email': 'novo@ifnmg.edu.br', 'role': self.teacher.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='novo@ifnmg.edu.br').exists())

    def test_teacher_with_a_permission_is_allowed(self):
        teacher = self.register('docente@ifnmg.edu.br', self.teacher)
        self.teacher.set_permissions([permissions.USER_VIEW])
        self.assertEqual(self.client_for(teacher).get('/usuarios/').status_code, 200)

    def test_different_roles_with_the_same_permissions_decide_alike(self):
        copy = Role.objects.create_role(
            code='COPIA', name='Cópia', permissions=permissions.ADMINISTRATIVE_CAPABILITY,
        )
        clients = [
            self.client_for(self.register('admin@ifnmg.edu.br', self.administrator)),
            self.client_for(self.register('copia@ifnmg.edu.br', copy)),
        ]
        for url in ['/usuarios/', '/usuarios/novo/', '/perfis/', '/perfis/novo/']:
            with self.subTest(url):
                self.assertEqual(len({client.get(url).status_code for client in clients}), 1)


class EntryPageTests(AccessTestCase):
    def test_superadmin_opens_the_first_menu_item(self):
        response = self.client_for(self.superadmin).get('/inicio/')
        self.assertRedirects(response, reverse('panel'), fetch_redirect_response=False)

    def test_opens_the_first_item_the_role_grants(self):
        reader = Role.objects.create_role(code='LEITOR', name='Leitor', permissions=[permissions.USER_VIEW])
        response = self.client_for(self.register('leitor@ifnmg.edu.br', reader)).get('/inicio/')
        self.assertRedirects(response, '/usuarios/', fetch_redirect_response=False)

    def test_role_without_modules_sees_the_notice(self):
        empty = Role.objects.create_role(code='VAZIO', name='Vazio', permissions=[])
        response = self.client_for(self.register('vazio@ifnmg.edu.br', empty)).get('/inicio/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O seu perfil ainda não dá acesso a nenhum módulo')
        self.assertNotContains(response, 'Voltar para o início')


class ChangesOnTheSameSessionTests(AccessTestCase):
    def test_role_change_removes_and_grants_access(self):
        user = self.register('maria@ifnmg.edu.br', self.administrator)
        client = self.client_for(user)
        self.assertEqual(client.get('/usuarios/').status_code, 200)
        user.change_role(self.teacher)
        self.assertEqual(client.get('/usuarios/').status_code, 403)
        user.change_role(self.administrator)
        self.assertEqual(client.get('/usuarios/').status_code, 200)

    def test_reactivated_user_logs_in_again_with_the_role_permissions(self):
        user = self.register('maria@ifnmg.edu.br', self.administrator)
        user.set_password('Senha-forte-123')
        user.save()
        user.deactivate()
        user.reactivate()
        client = Client()
        client.post('/contas/login/', {'login': 'maria@ifnmg.edu.br', 'password': 'Senha-forte-123'})
        self.assertEqual(client.get('/usuarios/').status_code, 200)

    def test_deactivated_superadmin_session_becomes_anonymous(self):
        self.register('admin@ifnmg.edu.br', self.administrator)
        client = self.client_for(self.superadmin)
        User.objects.get(pk=self.superadmin.pk).deactivate()
        response = client.get('/usuarios/')
        self.assertRedirects(response, '/contas/login/?next=/usuarios/', fetch_redirect_response=False)

    def test_superadmin_granted_and_revoked_by_command(self):
        user = self.register('maria@ifnmg.edu.br', self.teacher)
        client = self.client_for(user)
        self.assertEqual(client.get('/usuarios/').status_code, 403)
        call_command('set_superadmin', 'maria@ifnmg.edu.br', '--grant', stdout=StringIO())
        self.assertEqual(client.get('/usuarios/').status_code, 200)
        call_command('set_superadmin', 'maria@ifnmg.edu.br', '--revoke', stdout=StringIO())
        self.assertEqual(client.get('/usuarios/').status_code, 403)

    def test_never_defined_password_still_blocks_after_reactivation(self):
        user = self.register('maria@ifnmg.edu.br', self.teacher)
        user.deactivate()
        user.reactivate()
        client = Client()
        client.post('/contas/login/', {'login': 'maria@ifnmg.edu.br', 'password': 'qualquer-coisa'})
        self.assertNotIn('_auth_user_id', client.session)
