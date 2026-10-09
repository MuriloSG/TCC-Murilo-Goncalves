from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.roles import management_role
from outbox.models import OutboxEntry
from system_settings.models import PASSWORD_FOR_NEW_DESTINATION_MESSAGE, SystemSetting
from system_settings.tests.base import SMTP_PASSWORD, configure_smtp

FORM = {
    'host': 'smtp.ifnmg.edu.br',
    'port': '587',
    'security': 'STARTTLS',
    'username': 'agenda',
    'password': SMTP_PASSWORD,
    'from_email': 'IFAgenda <agenda@ifnmg.edu.br>',
}


class SmtpViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='admin@ifnmg.edu.br', name='Ana Souza', role=management_role(),
        )
        cls.user.set_superadmin(True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_administrator_who_is_not_superadmin_is_refused(self):
        administrator = User.objects.register(
            email='outro@ifnmg.edu.br', name='Outro Admin', role=management_role(),
        )
        self.client.force_login(administrator)
        for name in ('settings_email', 'settings_email_update'):
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.assertEqual(self.client.post(reverse('settings_email_update'), FORM).status_code, 403)
        self.assertFalse(SystemSetting.objects.exists())

    def test_page_without_setting(self):
        response = self.client.get(reverse('settings_email'))
        self.assertIsNone(response.context['setting'])
        self.assertContains(response, 'Não configurado')

    def test_registers_through_the_form(self):
        response = self.client.post(reverse('settings_email_update'), FORM)
        self.assertRedirects(response, reverse('settings_email'), fetch_redirect_response=False)
        self.assertEqual(SystemSetting.objects.smtp().password, SMTP_PASSWORD)
        page = self.client.get(reverse('settings_email'))
        self.assertContains(page, 'Servidor de e-mail salvo.')
        self.assertContains(page, 'Configurado')

    def test_update_with_blank_password_keeps_it(self):
        configure_smtp(from_email='Antigo <antigo@ifnmg.edu.br>')
        self.client.post(reverse('settings_email_update'), FORM | {'password': ''})
        smtp = SystemSetting.objects.smtp()
        self.assertEqual((smtp.from_email, smtp.password), (FORM['from_email'], SMTP_PASSWORD))

    def test_new_host_with_blank_password_is_refused_on_the_field(self):
        configure_smtp(host='antigo.ifnmg.edu.br')
        response = self.client.post(reverse('settings_email_update'), FORM | {'password': ''})
        self.assertFormError(response.context['form'], 'password', PASSWORD_FOR_NEW_DESTINATION_MESSAGE)
        self.assertEqual(SystemSetting.objects.smtp().host, 'antigo.ifnmg.edu.br')

    def test_refusal_appears_on_the_field(self):
        response = self.client.post(reverse('settings_email_update'), FORM | {'security': 'NENHUMA'})
        self.assertFormError(
            response.context['form'], 'security', 'Use STARTTLS ou SSL/TLS para enviar usuário e senha.',
        )
        self.assertFalse(SystemSetting.objects.exists())

    def test_password_never_reaches_the_screen(self):
        configure_smtp()
        for name in ('settings_email', 'settings_email_update'):
            with self.subTest(name):
                response = self.client.get(reverse(name))
                self.assertNotContains(response, SMTP_PASSWORD)
                self.assertNotContains(response, SystemSetting.objects.get().value['password'])
        form = self.client.get(reverse('settings_email_update')).context['form']
        self.assertNotIn('password', form.initial)

    def test_page_shows_invalid_setting_and_pending_emails(self):
        SystemSetting.objects.create(kind='smtp', value={'host': 'x'})
        OutboxEntry.objects.enqueue('TESTE', 1)
        response = self.client.get(reverse('settings_email'))
        self.assertContains(response, 'Configuração inválida')
        self.assertEqual(response.context['pending'], OutboxEntry.objects.filter(status='A_ENVIAR').count())
        self.assertIn('TESTE', OutboxEntry.objects.values_list('kind', flat=True))

    def test_clears_through_the_confirmation(self):
        configure_smtp()
        response = self.client.post(reverse('settings_email_clear'))
        self.assertRedirects(response, reverse('settings_email'), fetch_redirect_response=False)
        self.assertFalse(SystemSetting.objects.exists())
        self.assertContains(self.client.get(reverse('settings_email')), 'Configuração do servidor de e-mail excluída.')

    def test_clear_without_setting_is_404(self):
        self.assertEqual(self.client.get(reverse('settings_email_clear')).status_code, 404)
