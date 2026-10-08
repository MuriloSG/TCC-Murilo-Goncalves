"""Bloqueio de `clear_data`, `delete_users` e `set_passwords` fora do ambiente local.

A recusa é conferida com `assertNumQueries(0)`: o comando para antes de consultar ou alterar o
banco e antes de perguntar qualquer coisa no terminal.
"""

from io import StringIO
from unittest import mock

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TestCase, TransactionTestCase, override_settings

from accounts.models import Role, User
from schedule.models import Space

PASSWORD = 'Senha-forte-123'
DEVELOPMENT_PASSWORD = 'senha123#'
COMMANDS = ('clear_data', 'delete_users', 'set_passwords')
OTHER_ENVIRONMENTS = ('producao', 'production', 'homologacao', 'staging', 'desenvolvimento', 'test')
AMBIGUOUS_VALUES = ('', ' ', 'LOCAL', 'Local', ' local', 'local ', 'local,producao', 'local producao', '1', 'true')
NON_TEXT_VALUES = (None, 1, True)


class CommandEnvironmentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        cls.user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=Role.objects.get(code='DOCENTE'))
        Space.objects.register('Sala 50')

    def snapshot(self):
        return sorted(User.objects.values_list('pk', 'password', 'is_active')), Space.objects.count()

    def run_command(self, command, *args):
        call_command(command, *args, stdout=StringIO())


class RefusedEnvironmentTests(CommandEnvironmentTestCase):
    def assertRefused(self, command, *args):
        before = self.snapshot()
        with (
            mock.patch('builtins.input') as prompt,
            self.assertNumQueries(0),
            self.assertRaises(CommandError) as raised,
        ):
            self.run_command(command, *args)
        prompt.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        return str(raised.exception)

    def test_production_staging_and_homologation_are_refused(self):
        for value in OTHER_ENVIRONMENTS:
            for command in COMMANDS:
                with self.subTest(command, environment=value), override_settings(ENVIRONMENT=value):
                    self.assertRefused(command, '--yes')

    def test_ambiguous_or_invalid_values_are_refused(self):
        for value in AMBIGUOUS_VALUES + NON_TEXT_VALUES:
            for command in COMMANDS:
                with self.subTest(command, environment=value), override_settings(ENVIRONMENT=value):
                    self.assertRefused(command, '--yes')

    def test_missing_setting_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command), override_settings():
                del settings.ENVIRONMENT
                self.assertRefused(command, '--yes')

    def test_debug_is_not_evidence_of_local_environment(self):
        for value in ('', 'producao'):
            for command in COMMANDS:
                with self.subTest(command, environment=value), override_settings(DEBUG=True, ENVIRONMENT=value):
                    self.assertRefused(command, '--yes')

    def test_refused_before_the_confirmation_question(self):
        for command in COMMANDS:
            with self.subTest(command), override_settings(ENVIRONMENT='producao'):
                self.assertRefused(command)

    def test_message_explains_the_refusal_without_exposing_configuration(self):
        for command in COMMANDS:
            with self.subTest(command), override_settings(ENVIRONMENT='producao-interna'):
                message = self.assertRefused(command, '--yes')
                self.assertIn(command, message)
                self.assertIn('máquina de desenvolvimento', message)
                self.assertIn('Nada foi alterado', message)
                self.assertIn('DJANGO_ENVIRONMENT=local', message)
                for secret in (
                    'producao-interna',
                    settings.SECRET_KEY,
                    settings.CREDENTIALS_KEY,
                    settings.DATABASES['default']['PASSWORD'],
                    DEVELOPMENT_PASSWORD,
                ):
                    self.assertNotIn(secret, message)


@override_settings(ENVIRONMENT='local')
class LocalEnvironmentTests(CommandEnvironmentTestCase):
    def test_set_passwords_runs(self):
        self.run_command('set_passwords', '--yes')
        for account in (self.superadmin, self.user):
            account.refresh_from_db()
            self.assertTrue(account.check_password(DEVELOPMENT_PASSWORD))

    def test_delete_users_runs(self):
        self.run_command('delete_users', '--yes')
        self.assertEqual(list(User.objects.all()), [self.superadmin])


@override_settings(ENVIRONMENT='local')
class LocalClearDataTests(TransactionTestCase):
    """O `TRUNCATE` do `clear_data` não roda dentro da transação do `TestCase`."""

    serialized_rollback = True

    def test_clear_data_runs_and_keeps_the_users(self):
        User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        Space.objects.register('Sala 50')
        call_command('clear_data', '--yes', stdout=StringIO())
        self.assertEqual(Space.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)
