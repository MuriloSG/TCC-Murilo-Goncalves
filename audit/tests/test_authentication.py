import re

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase

from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog

PASSWORD = 'Senha-forte-123'


def reset_link(message):
    return re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', message.body).group(1)


class AuthenticationRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')

    def setUp(self):
        cache.clear()
        self.user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=self.teacher)
        self.user.set_password(PASSWORD)
        self.user.save()
        mail.outbox.clear()

    def entries(self, action):
        return AuditLog.objects.filter(action=action)

    def login(self, email='maria@ifnmg.edu.br', password=PASSWORD, client=None):
        return (client or self.client).post('/contas/login/', {'login': email, 'password': password})

    def test_login_is_recorded(self):
        self.login()
        entry = self.entries(catalog.LOGIN).get()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.resource, catalog.AUTHENTICATION)
        self.assertEqual(entry.resource_id, str(self.user.pk))
        self.assertEqual(entry.origin, catalog.INTERFACE)
        self.assertEqual(entry.ip_address, '127.0.0.1')

    def test_refused_login_is_recorded_without_the_user(self):
        self.login(password='outra-senha-qualquer')
        entry = self.entries(catalog.LOGIN_REFUSED).get()
        self.assertIsNone(entry.user)
        self.assertEqual(entry.metadata, {'email': 'maria@ifnmg.edu.br'})
        self.assertFalse(self.entries(catalog.LOGIN).exists())

    def test_refused_login_never_records_the_password(self):
        self.login(password='outra-senha-qualquer')
        entry = self.entries(catalog.LOGIN_REFUSED).get()
        gravado = f'{entry.metadata}{entry.old_values}{entry.new_values}{entry.user_agent}'
        self.assertNotIn('outra-senha-qualquer', gravado)

    def test_refused_login_of_inactive_user(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.login()
        entry = self.entries(catalog.LOGIN_REFUSED).get()
        self.assertIsNone(entry.user)
        self.assertEqual(entry.metadata, {'email': 'maria@ifnmg.edu.br'})

    def test_refused_login_of_unknown_email(self):
        self.login(email='ninguem@ifnmg.edu.br')
        self.assertEqual(self.entries(catalog.LOGIN_REFUSED).get().metadata, {'email': 'ninguem@ifnmg.edu.br'})

    def test_logout_is_recorded(self):
        self.login()
        self.client.post('/contas/logout/')
        entry = self.entries(catalog.LOGOUT).get()
        self.assertEqual(entry.user, self.user)

    def test_get_on_logout_is_not_recorded(self):
        self.login()
        self.client.get('/contas/logout/')
        self.assertFalse(self.entries(catalog.LOGOUT).exists())

    def test_password_recovery_request_is_recorded(self):
        self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        entry = self.entries(catalog.PASSWORD_REQUESTED).get()
        self.assertEqual(entry.metadata, {'email': 'maria@ifnmg.edu.br'})
        self.assertIsNone(entry.user)

    def test_request_for_unknown_email_is_recorded_alike(self):
        self.client.post('/contas/senha/recuperar/', {'email': 'ninguem@ifnmg.edu.br'})
        entry = self.entries(catalog.PASSWORD_REQUESTED).get()
        self.assertEqual(entry.metadata, {'email': 'ninguem@ifnmg.edu.br'})
        self.assertEqual(mail.outbox, [])

    def test_password_reset_is_recorded(self):
        self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        client = Client()
        form_url = client.get(reset_link(mail.outbox[0]))['Location']
        client.post(form_url, {'password1': 'Outra-senha-456', 'password2': 'Outra-senha-456'})
        entry = self.entries(catalog.PASSWORD_RESET).get()
        self.assertEqual(entry.user, self.user)
        self.assertNotIn('Outra-senha-456', f'{entry.metadata}{entry.new_values}{entry.old_values}')
