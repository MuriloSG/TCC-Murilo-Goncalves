import re
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from accounts.emails import PASSWORD_LINK, password_link
from accounts.models import User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import requester_role
from outbox.models import OutboxEntry
from system_settings.tests.base import configure_smtp

PASSWORD = 'Senha-forte-123'


class PasswordLinkTests(IsolatedCasesMixin, TestCase):
    def setUp(self):
        configure_smtp()
        cache.clear()
        self.user = User.objects.register(
            email='maria@ifnmg.edu.br', name='Maria Sousa', role=requester_role(),
        )

    def entry(self):
        return OutboxEntry.objects.get(kind=PASSWORD_LINK, reference=str(self.user.pk))

    def test_link_is_registered_only_for_users_without_a_password(self):
        with self.case('cadastro registra o link'):
            self.assertEqual(self.entry().status, 'A_ENVIAR')
            self.assertEqual(mail.outbox, [])
        with self.case('superadmin do comando'):
            User.objects.create_superadmin(email='super@ifnmg.edu.br', name='Super', password=PASSWORD)
            self.assertEqual(OutboxEntry.objects.count(), 1)

    def test_worker_sends_the_link_to_the_current_email(self):
        with self.case('endereço do site e modelos'):
            with override_settings(SITE_URL='https://agendamento.exemplo.edu.br/'):
                message = password_link(self.user.pk)
                self.assertEqual(message.to, ['maria@ifnmg.edu.br'])
                self.assertTrue(message.subject.startswith('[IFAgenda] '))
                self.assertIn('https://agendamento.exemplo.edu.br/contas/senha/redefinir/', message.body)
                self.assertTrue(message.body.startswith('Foi solicitada a definição ou a redefinição da senha desta conta'))
        with self.case('link define a senha'):
            with override_settings(SITE_URL='http://testserver'):
                call_command('process_outbox', '--once')
                self.assertEqual(self.entry().status, 'ENVIADO')
                link = re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', mail.outbox[0].body).group(1)
                client = Client()
                form_url = client.get(link)['Location']
                response = client.post(form_url, {'password1': PASSWORD, 'password2': PASSWORD})
                self.assertRedirects(response, '/contas/senha/redefinir/concluido/', fetch_redirect_response=False)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(PASSWORD))
        with self.case('e-mail atual'):
            User.objects.filter(pk=self.user.pk).update(email='maria.sousa@ifnmg.edu.br')
            call_command('process_outbox', '--once')
            self.assertEqual(mail.outbox[-1].to, ['maria.sousa@ifnmg.edu.br'])

    def test_discards_when_sending_no_longer_makes_sense(self):
        cases = {
            'inativo': lambda: User.objects.filter(pk=self.user.pk).update(is_active=False),
            'senha definida': lambda: (self.user.set_password(PASSWORD), self.user.save()),
            'inexistente': lambda: self.user.delete(),
        }
        for case, change in cases.items():
            with self.subTest(case):
                self.user = User.objects.register(
                    email=f'{case.replace(" ", ".")}@ifnmg.edu.br', name='Pessoa', role=requester_role(),
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
