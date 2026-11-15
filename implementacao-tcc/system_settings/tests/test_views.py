from django.test import TestCase
from config.testing import IsolatedCasesMixin
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


class SmtpViewTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.register(
            email='admin@ifnmg.edu.br', name='Ana Souza', role=management_role(),
        )
        cls.user.set_superadmin(True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_registers_updates_and_clears_through_the_screens(self):
        with self.case('cadastro'):
            response = self.client.post(reverse('settings_email_update'), FORM)
            self.assertRedirects(response, reverse('settings_email'), fetch_redirect_response=False)
            self.assertEqual(SystemSetting.objects.smtp().password, SMTP_PASSWORD)
            page = self.client.get(reverse('settings_email'))
            self.assertContains(page, 'Servidor de e-mail salvo.')
            self.assertContains(page, 'Configurado')
        with self.case('senha em branco mantém'):
            configure_smtp(from_email='Antigo <antigo@ifnmg.edu.br>')
            self.client.post(reverse('settings_email_update'), FORM | {'password': ''})
            smtp = SystemSetting.objects.smtp()
            self.assertEqual((smtp.from_email, smtp.password), (FORM['from_email'], SMTP_PASSWORD))
        with self.case('limpeza'):
            configure_smtp()
            response = self.client.post(reverse('settings_email_clear'))
            self.assertRedirects(response, reverse('settings_email'), fetch_redirect_response=False)
            self.assertFalse(SystemSetting.objects.exists())
            self.assertContains(self.client.get(reverse('settings_email')), 'Configuração do servidor de e-mail excluída.')

    def test_refusals_appear_on_the_field(self):
        with self.case('servidor novo sem senha'):
            configure_smtp(host='antigo.ifnmg.edu.br')
            response = self.client.post(reverse('settings_email_update'), FORM | {'password': ''})
            self.assertFormError(response.context['form'], 'password', PASSWORD_FOR_NEW_DESTINATION_MESSAGE)
            self.assertEqual(SystemSetting.objects.smtp().host, 'antigo.ifnmg.edu.br')
        with self.case('dado inválido'):
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
