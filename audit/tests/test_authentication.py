import re

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings

from accounts.emails import PASSWORD_RESET
from accounts.models import Role, User
from accounts.utils import INVALID_TYPED_EMAIL, typed_email
from audit import catalog
from audit.models import AuditLog
from outbox.models import OutboxEntry
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


def reset_link(message):
    return re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', message.body).group(1)


@override_settings(SITE_URL='http://testserver')
class AuthenticationRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')

    def setUp(self):
        configure_smtp()
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
        cases = {
            'wrong password': ('maria@ifnmg.edu.br', 'outra-senha-qualquer'),
            'unknown email': ('ninguem@ifnmg.edu.br', PASSWORD),
            'inactive user': ('maria@ifnmg.edu.br', PASSWORD),
        }
        for case, (email, password) in cases.items():
            with self.subTest(case):
                if case == 'inactive user':
                    User.objects.filter(pk=self.user.pk).update(is_active=False)
                self.login(email, password)
                entry = self.entries(catalog.LOGIN_REFUSED).latest('pk')
                self.assertIsNone(entry.user)
                self.assertEqual(entry.metadata, {'email': email})
        self.assertEqual(self.entries(catalog.LOGIN_REFUSED).count(), 3)
        self.assertFalse(self.entries(catalog.LOGIN).exists())

    def test_refused_login_never_records_the_password(self):
        self.login(password='outra-senha-qualquer')
        entry = self.entries(catalog.LOGIN_REFUSED).get()
        gravado = f'{entry.metadata}{entry.old_values}{entry.new_values}{entry.user_agent}'
        self.assertNotIn('outra-senha-qualquer', gravado)

    def test_logout_is_recorded(self):
        self.login()
        self.client.post('/contas/logout/')
        entry = self.entries(catalog.LOGOUT).get()
        self.assertEqual(entry.user, self.user)

    def test_get_on_logout_is_not_recorded(self):
        self.login()
        self.client.get('/contas/logout/')
        self.assertFalse(self.entries(catalog.LOGOUT).exists())

    def test_password_recovery_request_is_recorded_for_any_email(self):
        for email in ('maria@ifnmg.edu.br', 'ninguem@ifnmg.edu.br'):
            with self.subTest(email):
                self.client.post('/contas/senha/recuperar/', {'email': email})
                entry = self.entries(catalog.PASSWORD_REQUESTED).latest('pk')
                self.assertEqual(entry.metadata, {'email': email})
                self.assertIsNone(entry.user)
        OutboxEntry.objects.exclude(kind=PASSWORD_RESET).delete()
        call_command('process_outbox', '--once')
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_is_recorded(self):
        self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        call_command('process_outbox', '--once')
        client = Client()
        form_url = client.get(reset_link(mail.outbox[0]))['Location']
        client.post(form_url, {'password1': 'Outra-senha-456', 'password2': 'Outra-senha-456'})
        entry = self.entries(catalog.PASSWORD_RESET).get()
        self.assertEqual(entry.user, self.user)
        self.assertNotIn('Outra-senha-456', f'{entry.metadata}{entry.new_values}{entry.old_values}')


class TypedEmailTests(SimpleTestCase):
    def test_only_an_email_is_kept_for_the_audit(self):
        self.assertEqual(typed_email(' maria@ifnmg.edu.br '), 'maria@ifnmg.edu.br')
        self.assertEqual(typed_email('Senha-forte-123'), INVALID_TYPED_EMAIL)
        self.assertEqual(typed_email(None), '')
