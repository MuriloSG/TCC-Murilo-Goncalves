import re
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from accounts.emails import PASSWORD_LINK, password_link
from accounts.models import Role, User
from outbox.models import OutboxEntry
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


class PasswordLinkTests(TestCase):
    def setUp(self):
        configure_smtp()
        cache.clear()
        self.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=Role.objects.get(code='DOCENTE'),
        )

    def entry(self):
        return OutboxEntry.objects.get(kind=PASSWORD_LINK, reference=str(self.user.pk))

    def test_registration_registers_the_link_without_sending(self):
        self.assertEqual(self.entry().status, 'A_ENVIAR')
        self.assertEqual(mail.outbox, [])

    def test_superadmin_created_by_command_registers_no_link(self):
        User.objects.create_superadmin(email='super@ifnmg.edu.br', name='Super', password=PASSWORD)
        self.assertEqual(OutboxEntry.objects.count(), 1)

    @override_settings(SITE_URL='https://agendamento.exemplo.edu.br/')
    def test_link_uses_the_site_url_and_the_recovery_templates(self):
        message = password_link(self.user.pk)
        self.assertEqual(message.to, ['maria@ifnmg.edu.br'])
        self.assertTrue(message.subject.startswith('[IFAgenda] '))
        self.assertIn('https://agendamento.exemplo.edu.br/contas/senha/redefinir/', message.body)
        self.assertTrue(message.body.startswith('Foi solicitada a definição ou a redefinição da senha desta conta'))

    @override_settings(SITE_URL='http://testserver')
    def test_worker_sends_a_link_that_defines_the_password(self):
        call_command('process_outbox', '--once')
        self.assertEqual(self.entry().status, 'ENVIADO')
        link = re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', mail.outbox[0].body).group(1)
        client = Client()
        form_url = client.get(link)['Location']
        response = client.post(form_url, {'password1': PASSWORD, 'password2': PASSWORD})
        self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_link_goes_to_the_current_email(self):
        User.objects.filter(pk=self.user.pk).update(email='maria.sousa@ifnmg.edu.br')
        call_command('process_outbox', '--once')
        self.assertEqual(mail.outbox[0].to, ['maria.sousa@ifnmg.edu.br'])

    def test_discards_when_sending_no_longer_makes_sense(self):
        cases = {
            'inativo': lambda: User.objects.filter(pk=self.user.pk).update(is_active=False),
            'senha definida': lambda: (self.user.set_password(PASSWORD), self.user.save()),
            'inexistente': lambda: self.user.delete(),
        }
        for case, change in cases.items():
            with self.subTest(case):
                self.user = User.objects.register(
                    email=f'{case.replace(" ", ".")}@ifnmg.edu.br', name='Pessoa', role=Role.objects.get(code='DOCENTE'),
                )
                entry = self.entry()
                change()
                self.assertIsNone(password_link(entry.reference))
                call_command('process_outbox', '--once')
                entry.refresh_from_db()
                self.assertEqual(entry.status, 'DESCARTADO')
        self.assertEqual(
            [message.to for message in mail.outbox], [['maria@ifnmg.edu.br']],
        )

    def test_worker_does_not_consume_the_public_recovery_limit(self):
        with mock.patch('allauth.core.ratelimit.consume') as consume:
            call_command('process_outbox', '--once')
        consume.assert_not_called()
        self.assertEqual(len(mail.outbox), 1)
