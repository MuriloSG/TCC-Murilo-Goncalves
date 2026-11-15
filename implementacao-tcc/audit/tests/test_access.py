from django.test import Client, TestCase, override_settings
from config.testing import IsolatedCasesMixin

from accounts import permissions
from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from audit import catalog
from audit.models import AuditLog


class AccessRecordTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        cls.plain = User.objects.register(email='docente@ifnmg.edu.br', name='Docente', role=cls.teacher)

    def setUp(self):
        self.client = Client(HTTP_USER_AGENT='Firefox/142.0')
        self.client.force_login(self.admin)

    def accesses(self):
        return AuditLog.objects.filter(action=catalog.ACCESS)

    def test_screen_access_is_recorded_with_its_resource(self):
        with self.case('acesso à tela'):
            self.assertEqual(self.client.get('/usuarios/').status_code, 200)
            entry = self.accesses().get()
            self.assertEqual(entry.user, self.admin)
            self.assertEqual(entry.resource, catalog.USER)
            self.assertEqual(entry.metadata, {'rota': 'user_list', 'caminho': '/usuarios/'})
            self.assertEqual(entry.origin, catalog.INTERFACE)
            self.assertEqual(entry.ip_address, '127.0.0.1')
            self.assertEqual(entry.user_agent, 'Firefox/142.0')
        with self.case('recurso de cada tela'):
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
        with self.case('mesma rota sem JavaScript'):
            self.assertEqual(self.client.get('/usuarios/novo/').status_code, 200)
            self.assertEqual(self.accesses().get().metadata['rota'], 'user_create')

    def test_client_ip(self):
        with self.case('sem proxy declarado'):
            self.client.get('/usuarios/', HTTP_X_FORWARDED_FOR='203.0.113.9')
            self.assertEqual(self.accesses().get().ip_address, '127.0.0.1')
        with self.case('proxy declarado'):
            with override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1):
                self.client.get('/usuarios/', HTTP_X_FORWARDED_FOR='203.0.113.9')
                self.assertEqual(self.accesses().get().ip_address, '203.0.113.9')

    def test_what_is_not_an_access(self):
        with self.case('fragmento htmx'):
            response = self.client.get('/usuarios/?busca=ana', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='tabela-usuarios')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self.accesses().exists())
        with self.case('modal htmx'):
            response = self.client.get('/usuarios/novo/', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='modal')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self.accesses().exists())
        with self.case('acesso recusado'):
            client = Client()
            client.force_login(self.plain)
            self.assertEqual(client.get('/usuarios/').status_code, 403)
            self.assertFalse(self.accesses().exists())
        with self.case('anônimo redirecionado'):
            self.assertEqual(Client().get('/usuarios/').status_code, 302)
            self.assertFalse(self.accesses().exists())
        with self.case('POST'):
            self.client.post('/usuarios/novo/', {'name': 'Nova', 'email': 'nova@ifnmg.edu.br', 'role': self.teacher.pk})
            self.assertTrue(User.objects.filter(email='nova@ifnmg.edu.br').exists())
            self.assertFalse(self.accesses().exists())
        with self.case('início'):
            self.assertEqual(self.client.get('/inicio/', follow=True).status_code, 200)
            self.assertFalse(self.accesses().exists())
        with self.case('download do modelo'):
            self.teacher.set_permissions([permissions.USER_IMPORT])
            client = Client()
            client.force_login(self.plain)
            self.assertEqual(client.get('/usuarios/importacoes/modelo/').status_code, 200)
            self.assertFalse(self.accesses().exists())
