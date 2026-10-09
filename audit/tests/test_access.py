from django.test import Client, TestCase, override_settings

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog


class AccessRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        cls.plain = User.objects.register(email='docente@ifnmg.edu.br', name='Docente', role=cls.teacher)

    def setUp(self):
        self.client = Client(HTTP_USER_AGENT='Firefox/142.0')
        self.client.force_login(self.admin)

    def accesses(self):
        return AuditLog.objects.filter(action=catalog.ACCESS)

    def test_screen_access_is_recorded(self):
        self.assertEqual(self.client.get('/usuarios/').status_code, 200)
        entry = self.accesses().get()
        self.assertEqual(entry.user, self.admin)
        self.assertEqual(entry.resource, catalog.USER)
        self.assertEqual(entry.metadata, {'rota': 'user_list', 'caminho': '/usuarios/'})
        self.assertEqual(entry.origin, catalog.INTERFACE)
        self.assertEqual(entry.ip_address, '127.0.0.1')
        self.assertEqual(entry.user_agent, 'Firefox/142.0')

    def test_forwarded_ip_is_ignored_without_a_declared_proxy(self):
        self.client.get('/usuarios/', HTTP_X_FORWARDED_FOR='203.0.113.9')
        self.assertEqual(self.accesses().get().ip_address, '127.0.0.1')

    @override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1)
    def test_client_ip_comes_from_the_declared_proxy(self):
        self.client.get('/usuarios/', HTTP_X_FORWARDED_FOR='203.0.113.9')
        self.assertEqual(self.accesses().get().ip_address, '203.0.113.9')

    def test_each_screen_records_its_own_resource(self):
        superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=self.teacher)
        superadmin.set_superadmin(True)
        client = Client()
        client.force_login(superadmin)
        client.get('/perfis/')
        client.get('/usuarios/importacoes/')
        self.assertEqual(
            list(self.accesses().order_by('pk').values_list('resource', flat=True)),
            [catalog.ROLE, catalog.USER_IMPORT],
        )

    def test_htmx_fragment_is_not_an_access(self):
        response = self.client.get('/usuarios/?busca=ana', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='tabela-usuarios')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.accesses().exists())

    def test_htmx_modal_is_not_an_access(self):
        response = self.client.get('/usuarios/novo/', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='modal')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.accesses().exists())

    def test_same_route_without_javascript_is_an_access(self):
        self.assertEqual(self.client.get('/usuarios/novo/').status_code, 200)
        self.assertEqual(self.accesses().get().metadata['rota'], 'user_create')

    def test_refused_access_is_not_recorded(self):
        client = Client()
        client.force_login(self.plain)
        self.assertEqual(client.get('/usuarios/').status_code, 403)
        self.assertFalse(self.accesses().exists())

    def test_anonymous_redirect_is_not_recorded(self):
        self.assertEqual(Client().get('/usuarios/').status_code, 302)
        self.assertFalse(self.accesses().exists())

    def test_post_is_not_an_access(self):
        self.client.post('/usuarios/novo/', {'name': 'Nova', 'email': 'nova@ifnmg.edu.br', 'role': self.teacher.pk})
        self.assertTrue(User.objects.filter(email='nova@ifnmg.edu.br').exists())
        self.assertFalse(self.accesses().exists())

    def test_home_is_not_a_feature(self):
        self.assertEqual(self.client.get('/inicio/', follow=True).status_code, 200)
        self.assertFalse(self.accesses().exists())

    def test_template_download_is_not_an_access(self):
        self.teacher.set_permissions([permissions.USER_IMPORT])
        client = Client()
        client.force_login(self.plain)
        self.assertEqual(client.get('/usuarios/importacoes/modelo/').status_code, 200)
        self.assertFalse(self.accesses().exists())
