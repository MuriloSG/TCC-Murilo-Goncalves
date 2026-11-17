from django.test import Client, TestCase

from accounts.models import User
from accounts.tests.roles import requester_role
from audit import catalog
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin

PASSWORD = 'Senha-forte-123'
NEW_PASSWORD = 'Outra-senha-456'


class ProfileTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=requester_role(), username='maria.sousa',
        )
        cls.user.set_password(PASSWORD)
        cls.user.save()
        cls.without_role = User.objects.create(email='joao@ifnmg.edu.br', name='João Lima')

    def setUp(self):
        self.client.force_login(self.user)

    def test_any_authenticated_user_opens_the_page(self):
        for user in (self.user, self.without_role):
            with self.case(user=user.email):
                client = Client()
                client.force_login(user)
                response = client.get('/perfil/')
                self.assertContains(response, 'Informações pessoais')
                self.assertContains(response, user.email)
        response = Client().get('/perfil/')
        self.assertRedirects(response, '/contas/login/?next=/perfil/', fetch_redirect_response=False)

    def test_changes_only_the_name(self):
        response = self.client.post(
            '/perfil/nome/', {'name': 'Maria S. Souza', 'email': 'outra@ifnmg.edu.br', 'username': 'outro'},
        )
        self.assertRedirects(response, '/perfil/', fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(
            (self.user.name, self.user.email, self.user.username),
            ('Maria S. Souza', 'maria@ifnmg.edu.br', 'maria.sousa'),
        )
        self.assertTrue(AuditLog.objects.filter(resource=catalog.USER, resource_id=self.user.pk).exists())

    def test_refuses_invalid_password_changes(self):
        cases = {
            'senha atual errada': {'current_password': 'errada', 'password1': NEW_PASSWORD, 'password2': NEW_PASSWORD},
            'senhas diferentes': {'current_password': PASSWORD, 'password1': NEW_PASSWORD, 'password2': 'x' + NEW_PASSWORD},
            'senha fraca': {'current_password': PASSWORD, 'password1': '12345678', 'password2': '12345678'},
        }
        for label, data in cases.items():
            with self.case(label):
                response = self.client.post('/perfil/senha/', data)
                self.assertEqual(response.status_code, 200)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(PASSWORD))

    def test_changes_password_keeping_the_current_session(self):
        other = Client()
        other.force_login(self.user)
        response = self.client.post(
            '/perfil/senha/', {'current_password': PASSWORD, 'password1': NEW_PASSWORD, 'password2': NEW_PASSWORD},
        )
        self.assertRedirects(response, '/perfil/', fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(self.client.get('/perfil/').status_code, 200)
        self.assertEqual(other.get('/perfil/').status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action=catalog.PASSWORD_CHANGED, resource_id=self.user.pk).exists())
