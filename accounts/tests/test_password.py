import re
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from accounts.emails import PASSWORD_RESET
from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from outbox.models import OutboxEntry
from system_settings.models import SystemSetting
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


def reset_link(message):
    return re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', message.body).group(1)


@override_settings(SITE_URL='http://testserver')
class PasswordFlowTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()

    def setUp(self):
        configure_smtp()
        cache.clear()
        self.user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=self.teacher)
        OutboxEntry.objects.all().delete()

    def request_link(self, email='maria@ifnmg.edu.br'):
        """Pede o link pela tela e roda o worker, que é quem fala com o SMTP."""
        response = self.client.post('/contas/senha/recuperar/', {'email': email})
        self.assertRedirects(response, '/contas/senha/recuperar/enviado/', fetch_redirect_response=False)
        call_command('process_outbox', '--once')

    def set_password(self, link, password=PASSWORD, client=None):
        client = client or Client()
        response = client.get(link)
        if response.status_code != 302:
            return response
        return client.post(response['Location'], {'password1': password, 'password2': password})

    def login(self, email='maria@ifnmg.edu.br', password=PASSWORD):
        client = Client()
        client.post('/contas/login/', {'login': email, 'password': password})
        return '_auth_user_id' in client.session


class UnusablePasswordTests(PasswordFlowTestCase):
    def test_registered_user_defines_the_password_through_the_link(self):
        self.request_link()
        response = self.set_password(reset_link(mail.outbox[0]))
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
        self.assertTrue(self.login())


class InactiveUserTests(PasswordFlowTestCase):
    def test_inactive_user_receives_no_email(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.request_link()
        self.assertEqual(mail.outbox, [])

    def test_link_issued_before_deactivation_does_not_reset_the_password(self):
        self.request_link()
        link = reset_link(mail.outbox[0])
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = self.set_password(link)

        self.assertTrue(response.context['token_fail'])
        self.assertFalse(User.objects.get(pk=self.user.pk).has_usable_password())

    def test_link_opened_before_deactivation_does_not_reset_the_password(self):
        self.request_link()
        client = Client()
        form_url = client.get(reset_link(mail.outbox[0]))['Location']
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        response = client.post(form_url, {'password1': PASSWORD, 'password2': PASSWORD})

        self.assertTrue(response.context['token_fail'])
        self.assertFalse(User.objects.get(pk=self.user.pk).has_usable_password())


class RecoveryRequestTests(PasswordFlowTestCase):
    def setUp(self):
        super().setUp()
        self.user.set_password(PASSWORD)
        self.user.save()

    def test_active_user_receives_the_link(self):
        self.request_link('Maria@IFNMG.edu.br')
        self.assertEqual([message.to for message in mail.outbox], [['maria@ifnmg.edu.br']])
        self.assertIn('/contas/senha/redefinir/', mail.outbox[0].body)

    def test_unknown_email_gets_the_same_response_and_no_email(self):
        known = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'}, follow=True)
        unknown = self.client.post('/contas/senha/recuperar/', {'email': 'inexistente@ifnmg.edu.br'}, follow=True)
        call_command('process_outbox', '--once')
        self.assertEqual(known.redirect_chain, unknown.redirect_chain)
        self.assertEqual(known.content, unknown.content)
        self.assertEqual(len(mail.outbox), 1)

    def test_too_many_requests_are_refused_without_email(self):
        for _ in range(5):
            self.request_link()
        response = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 5)

    def test_superadmin_recovers_the_access(self):
        self.user.set_superadmin(True)
        self.request_link()
        self.set_password(reset_link(mail.outbox[0]), 'Nova-senha-forte-456')
        self.assertTrue(self.login(password='Nova-senha-forte-456'))


class RecoveryWithoutSmtpTests(PasswordFlowTestCase):
    def test_request_is_answered_and_the_link_waits_in_the_outbox(self):
        SystemSetting.objects.all().delete()
        response = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        self.assertRedirects(response, '/contas/senha/recuperar/enviado/', fetch_redirect_response=False)
        self.assertEqual(mail.outbox, [])
        self.assertTrue(OutboxEntry.objects.filter(kind=PASSWORD_RESET, reference=str(self.user.pk)).exists())

    def test_failing_smtp_gives_the_same_response_for_known_and_unknown_email(self):
        with mock.patch('system_settings.models.SmtpSettings.connection', side_effect=OSError):
            known = self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'}, follow=True)
            unknown = self.client.post('/contas/senha/recuperar/', {'email': 'inexistente@ifnmg.edu.br'}, follow=True)
        self.assertEqual((known.status_code, known.redirect_chain), (unknown.status_code, unknown.redirect_chain))
        self.assertEqual(known.content, unknown.content)

    def test_repeated_requests_keep_a_single_pending_link(self):
        SystemSetting.objects.all().delete()
        for _ in range(3):
            self.client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        self.assertEqual(OutboxEntry.objects.filter(kind=PASSWORD_RESET).count(), 1)


class ResetTests(PasswordFlowTestCase):
    def setUp(self):
        super().setUp()
        self.user.set_password(PASSWORD)
        self.user.save()
        self.request_link()
        self.link = reset_link(mail.outbox[0])

    def assertLinkRefused(self, response):
        self.assertTrue(response.context['token_fail'])
        self.assertContains(response, 'Este link não é mais válido')
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(PASSWORD))

    def test_new_password_replaces_the_old_one_without_logging_in(self):
        client = Client()
        response = self.set_password(self.link, 'Nova-senha-forte-456', client)
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', client.session)
        self.assertContains(client.get(response['Location']), 'href="/contas/login/"')
        self.assertFalse(self.login())
        self.assertTrue(self.login(password='Nova-senha-forte-456'))

    def test_link_is_single_use(self):
        self.set_password(self.link, 'Nova-senha-forte-456')
        response = self.set_password(self.link, 'Terceira-senha-789')
        self.assertTrue(response.context['token_fail'])
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password('Nova-senha-forte-456'))

    def test_expired_link_is_refused(self):
        later = datetime.now() + timedelta(days=3, hours=1)
        with mock.patch.object(PasswordResetTokenGenerator, '_now', return_value=later):
            self.assertLinkRefused(self.set_password(self.link, 'Nova-senha-forte-456'))

    def test_email_change_invalidates_the_link(self):
        executor = User.objects.register(
            email='admin@ifnmg.edu.br', name='Admin', role=management_role(),
        )
        self.user.update_details(executor, name='Maria Sousa', email='maria.sousa@ifnmg.edu.br')
        self.assertLinkRefused(self.set_password(self.link, 'Nova-senha-forte-456'))

    def test_weak_passwords_are_refused_and_the_link_stays_valid(self):
        client = Client()
        form_url = client.get(self.link)['Location']
        for password in ['93847261530', 'password123', 'Ab1-x', 'Maria Sousa', 'maria@ifnmg']:
            with self.subTest(password):
                response = client.post(form_url, {'password1': password, 'password2': password})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors['password1'])
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(PASSWORD))
        response = client.post(form_url, {'password1': 'Nova-senha-forte-456', 'password2': 'Nova-senha-forte-456'})
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)

    def test_reset_invalidates_existing_sessions(self):
        other_browser = Client()
        other_browser.post('/contas/login/', {'login': 'maria@ifnmg.edu.br', 'password': PASSWORD})
        self.assertEqual(other_browser.get('/inicio/', follow=True).status_code, 200)
        self.request_link()
        response = self.set_password(reset_link(mail.outbox[-1]), 'Nova-senha-forte-456')
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
        response = other_browser.get('/inicio/', follow=True)
        self.assertRedirects(response, '/contas/login/?next=/inicio/', fetch_redirect_response=False)
