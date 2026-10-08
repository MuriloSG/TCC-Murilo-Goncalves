"""Trava dos comandos destrutivos, com o banco local simulado no próprio banco de teste."""

import os
from contextlib import contextmanager
from io import StringIO
from unittest import mock

from django.conf import settings
from django.core.management import CommandError, call_command, get_commands
from django.core.management.commands import flush as django_flush
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.runner import DiscoverRunner

from accounts.models import Role, User
from accounts.utils import LOCAL_DATABASE_MARK, database_identity
from config import test_runner
from schedule.models import Space

PASSWORD = 'Senha-forte-123'
DEVELOPMENT_PASSWORD = 'senha123#'
COMMANDS = ('flush', 'clear_data', 'delete_users', 'set_passwords')
OTHER_ENVIRONMENTS = ('producao', 'production', 'homologacao', 'staging', 'desenvolvimento', 'test')
AMBIGUOUS_VALUES = ('', ' ', 'LOCAL', 'Local', ' local', 'local ', 'local,producao', 'local producao', '1', 'true')
NON_TEXT_VALUES = (None, 1, True)


def local_identity():
    return database_identity(connection.settings_dict)


def other_identities():
    config = connection.settings_dict
    return (
        f"producao.ifnmg.edu.br:{config['PORT']}/{config['NAME']}",
        f"{config['HOST']}:6543/{config['NAME']}",
        f"{config['HOST']}:{config['PORT']}/{os.environ['POSTGRES_DB']}",
        f"{config['HOST']}:{config['PORT']}/{config['NAME']} ",
        config['NAME'],
    )


def mark(value='local'):
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL {LOCAL_DATABASE_MARK} = %s", [value])


@contextmanager
def outside_test_runner():
    """Esvazia o registro do runner: o banco de teste passa a valer como um banco qualquer."""
    with mock.patch.object(test_runner, 'created_test_databases', set()):
        yield


@contextmanager
def local_settings(**overrides):
    values = {'ENVIRONMENT': 'local', 'LOCAL_DATABASE': local_identity(), **overrides}
    with outside_test_runner(), override_settings(**values):
        yield


def run(command, confirm=True):
    """Executa o comando; o `flush` delega a um `handle` nativo substituído, que não apaga nada."""
    with mock.patch.object(django_flush.Command, 'handle', return_value=None) as native:
        if command == 'flush':
            call_command('flush', interactive=False, verbosity=0, stdout=StringIO())
        else:
            call_command(command, *(['--yes'] if confirm else []), stdout=StringIO())
    return native


class CommandGuardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        cls.user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=Role.objects.get(code='DOCENTE'))
        Space.objects.register('Sala 50')

    def snapshot(self):
        return sorted(User.objects.values_list('pk', 'password', 'is_active')), Space.objects.count()

    def assertRefused(self, command, queries=0, confirm=True):
        before = self.snapshot()
        with (
            mock.patch('builtins.input') as prompt,
            mock.patch.object(django_flush.Command, 'handle', return_value=None) as native,
            self.assertNumQueries(queries),
            self.assertRaises(CommandError) as raised,
        ):
            if command == 'flush':
                call_command('flush', interactive=False, verbosity=0, stdout=StringIO())
            else:
                call_command(command, *(['--yes'] if confirm else []), stdout=StringIO())
        prompt.assert_not_called()
        native.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        message = str(raised.exception)
        self.assertIn(command, message)
        self.assertIn('Nada foi alterado', message)
        return message


class EnvironmentRefusalTests(CommandGuardTestCase):
    def test_other_environments_are_refused(self):
        for value in OTHER_ENVIRONMENTS:
            for command in COMMANDS:
                with self.subTest(command, environment=value), local_settings(ENVIRONMENT=value):
                    mark()
                    self.assertRefused(command)

    def test_ambiguous_or_invalid_values_are_refused(self):
        for value in AMBIGUOUS_VALUES + NON_TEXT_VALUES:
            for command in COMMANDS:
                with self.subTest(command, environment=value), local_settings(ENVIRONMENT=value):
                    self.assertRefused(command)

    def test_missing_environment_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command), local_settings():
                del settings.ENVIRONMENT
                self.assertRefused(command)

    def test_debug_is_not_evidence_of_local_environment(self):
        for command in COMMANDS:
            with self.subTest(command), local_settings(DEBUG=True, ENVIRONMENT=''):
                self.assertRefused(command)

    def test_refused_before_the_confirmation_question(self):
        for command in COMMANDS[1:]:
            with self.subTest(command), local_settings(ENVIRONMENT='producao'):
                self.assertRefused(command, confirm=False)


class DatabaseRefusalTests(CommandGuardTestCase):
    def test_missing_local_database_is_refused(self):
        for value in ('', None, 1):
            for command in COMMANDS:
                with self.subTest(command, local_database=value), local_settings(LOCAL_DATABASE=value):
                    mark()
                    self.assertRefused(command)
        for command in COMMANDS:
            with self.subTest(command, local_database='ausente'), local_settings():
                del settings.LOCAL_DATABASE
                self.assertRefused(command)

    def test_database_other_than_the_declared_one_is_refused(self):
        for identity in other_identities():
            for command in COMMANDS:
                with self.subTest(command, identity=identity), local_settings(LOCAL_DATABASE=identity):
                    mark()
                    self.assertRefused(command)

    def test_unmarked_database_is_refused_after_one_read(self):
        for command in COMMANDS:
            with self.subTest(command), local_settings():
                message = self.assertRefused(command, queries=1)
                self.assertIn('make mark-local-db', message)

    def test_database_marked_for_another_environment_is_refused(self):
        for value in ('producao', 'Local', ''):
            for command in COMMANDS:
                with self.subTest(command, mark=value), local_settings():
                    mark(value)
                    self.assertRefused(command, queries=1)

    def test_operational_database_with_a_test_name_is_refused(self):
        """O banco de teste fora do registro do runner e um nome `test_` configurado não liberam."""
        for name in ('test_' + os.environ['POSTGRES_DB'], 'test_agendamento', connection.settings_dict['NAME']):
            for command in COMMANDS:
                with (
                    self.subTest(command, name=name),
                    mock.patch.dict(connections['default'].settings_dict, NAME=name),
                    local_settings(),
                ):
                    self.assertRefused(command, queries=1)

    def test_effective_database_must_match_the_configured_name(self):
        with (
            local_settings(),
            mock.patch('accounts.utils.connected_database', return_value=('agendamento_producao', 'local')),
        ):
            for command in COMMANDS:
                with self.subTest(command):
                    self.assertRefused(command)

    def test_messages_do_not_expose_configuration(self):
        cases = (
            ({'ENVIRONMENT': 'producao-interna'}, 0),
            ({'LOCAL_DATABASE': 'producao-interna:5432/segredo'}, 0),
            ({}, 1),
        )
        secrets = (
            'producao-interna',
            'segredo',
            settings.SECRET_KEY,
            settings.CREDENTIALS_KEY,
            connection.settings_dict['PASSWORD'],
            connection.settings_dict['USER'],
            local_identity(),
            connection.settings_dict['NAME'],
            DEVELOPMENT_PASSWORD,
        )
        for overrides, queries in cases:
            for command in COMMANDS:
                with self.subTest(command, **overrides), local_settings(**overrides):
                    message = self.assertRefused(command, queries=queries)
                    self.assertIn('máquina de desenvolvimento', message)
                    for secret in secrets:
                        self.assertNotIn(secret, message)


class LocalDatabaseTests(CommandGuardTestCase):
    def test_set_passwords_runs(self):
        with local_settings():
            mark()
            run('set_passwords')
        for account in (self.superadmin, self.user):
            account.refresh_from_db()
            self.assertTrue(account.check_password(DEVELOPMENT_PASSWORD))

    def test_delete_users_runs(self):
        with local_settings():
            mark()
            run('delete_users')
        self.assertEqual(list(User.objects.all()), [self.superadmin])

    def test_flush_delegates_to_the_native_command(self):
        with local_settings():
            mark()
            run('flush').assert_called_once()


class LocalClearDataTests(TransactionTestCase):
    """O `TRUNCATE` do `clear_data` não roda dentro da transação do `TestCase`."""

    serialized_rollback = True

    def setUp(self):
        User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        Space.objects.register('Sala 50')

    def test_clear_data_runs_on_the_marked_local_database(self):
        with connection.cursor() as cursor:
            cursor.execute(f"SET {LOCAL_DATABASE_MARK} = 'local'")
        try:
            with local_settings():
                run('clear_data')
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f'RESET {LOCAL_DATABASE_MARK}')
        self.assertEqual(Space.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)

    def test_clear_data_runs_on_the_test_database_of_the_runner(self):
        with override_settings(ENVIRONMENT='', LOCAL_DATABASE=''):
            run('clear_data')
        self.assertEqual(Space.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)


class TestRunnerAuthorizationTests(CommandGuardTestCase):
    def test_project_flush_replaces_the_native_one(self):
        self.assertEqual(get_commands()['flush'], 'accounts')

    def test_test_database_created_by_the_runner_is_registered(self):
        self.assertIn(('default', connection.settings_dict['NAME']), test_runner.created_test_databases)

    def test_commands_run_on_the_test_database_without_local_configuration(self):
        with override_settings(ENVIRONMENT='', LOCAL_DATABASE=''):
            run('flush').assert_called_once()
            run('set_passwords')
            run('delete_users')
        self.assertEqual(list(User.objects.all()), [self.superadmin])
        self.superadmin.refresh_from_db()
        self.assertTrue(self.superadmin.check_password(DEVELOPMENT_PASSWORD))

    def test_registration_is_cleared_after_the_suite_even_on_failure(self):
        runner = test_runner.TestRunner(verbosity=0)
        for failure in (None, RuntimeError('falha ao remover')):
            registered = {('default', 'test_agendamento')}
            with (
                self.subTest(failure=failure),
                mock.patch.object(test_runner, 'created_test_databases', registered),
                mock.patch.object(DiscoverRunner, 'teardown_databases', side_effect=failure),
            ):
                if failure:
                    with self.assertRaises(RuntimeError):
                        runner.teardown_databases([])
                else:
                    runner.teardown_databases([])
                self.assertEqual(registered, set())
