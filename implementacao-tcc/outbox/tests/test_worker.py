import ast
import threading
from datetime import timedelta
from pathlib import Path
from smtplib import SMTPAuthenticationError, SMTPException
from unittest import mock

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, get_connection
from django.core.management import call_command
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from config.testing import IsolatedCasesMixin
from django.utils import timezone

import outbox
from outbox import handlers
from outbox.models import OutboxEntry
from outbox.worker import SmtpUnavailable, process_batch, process_next
from system_settings.tests.base import SMTP_PASSWORD, configure_smtp


def message_for(reference):
    return EmailMessage('Assunto', f'Corpo {reference}', to=[f'pessoa{reference}@ifnmg.edu.br'])


def discard(reference):
    return None


def failing(reference):
    raise SMTPException('servidor indisponível')


@override_settings(OUTBOX_MAX_ATTEMPTS=5, OUTBOX_RETRY_DELAYS=[60, 300, 900, 3600])
class ProcessTests(IsolatedCasesMixin, TestCase):
    def setUp(self):
        configure_smtp()
        patcher = mock.patch.dict(
            handlers._handlers,
            {'TESTE': message_for, 'DESCARTE': discard, 'FALHA': failing},
            clear=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def entry(self, kind='TESTE', **values):
        return OutboxEntry.objects.create(kind=kind, reference='1', **values)

    def test_sends_the_due_entries_of_the_batch(self):
        with self.case('envia e marca'):
            entry = self.entry()
            self.assertTrue(process_next())
            entry.refresh_from_db()
            self.assertEqual(entry.status, 'ENVIADO')
            self.assertIsNotNone(entry.sent_at)
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ['pessoa1@ifnmg.edu.br'])
        with self.case('nada a processar'):
            self.assertFalse(process_next())
        with self.case('tentativa futura'):
            entry = self.entry(next_attempt_at=timezone.now() + timedelta(minutes=5))
            self.assertFalse(process_next())
            entry.refresh_from_db()
            self.assertEqual(entry.status, 'A_ENVIAR')
            self.assertEqual(mail.outbox, [])
        with self.case('tamanho do lote'):
            for reference in range(3):
                OutboxEntry.objects.create(kind='TESTE', reference=str(reference))
            self.assertEqual(process_batch(2), 2)
            self.assertEqual(OutboxEntry.objects.filter(status='ENVIADO').count(), 2)

    def test_temporary_failure_schedules_the_next_attempt(self):
        with self.case('falha temporária'):
            entry = self.entry(kind='FALHA')
            before = timezone.now()
            with self.assertLogs('outbox', 'WARNING') as logs:
                process_next()
            entry.refresh_from_db()
            self.assertEqual((entry.status, entry.attempts), ('A_ENVIAR', 1))
            self.assertIn('SMTPException: servidor indisponível', entry.last_error)
            self.assertEqual(logs.output, [f'WARNING:outbox:Envio {entry.pk} (FALHA) falhou na tentativa 1: SMTPException.'])
            self.assertAlmostEqual(
                (entry.next_attempt_at - before).total_seconds(), 60, delta=5,
            )
        with self.case('intervalos'):
            with override_settings(OUTBOX_MAX_ATTEMPTS=8):
                for attempts, delay in ((2, 900), (6, 3600)):
                    with self.subTest(attempts=attempts), transaction.atomic():
                        entry = self.entry(kind='FALHA', attempts=attempts)
                        before = timezone.now()
                        with self.assertLogs('outbox', 'WARNING'):
                            process_next()
                        entry.refresh_from_db()
                        self.assertEqual(entry.attempts, attempts + 1)
                        self.assertAlmostEqual((entry.next_attempt_at - before).total_seconds(), delay, delta=5)
                        transaction.set_rollback(True)

    def test_limit_marks_failed_for_good(self):
        with self.case('limite'):
            entry = self.entry(kind='FALHA', attempts=4)
            with self.assertLogs('outbox', 'ERROR'):
                process_next()
            entry.refresh_from_db()
            self.assertEqual((entry.status, entry.attempts), ('FALHOU', 5))
        with self.case('não é retomada'):
            self.entry(status=OutboxEntry.Status.FAILED)
            self.assertFalse(process_next())

    def test_handler_problems_fail_the_entry(self):
        with self.case('sem tratador'):
            entry = self.entry(kind='DESCONHECIDO')
            with self.assertLogs('outbox', 'ERROR'):
                process_next()
            entry.refresh_from_db()
            self.assertEqual(entry.status, 'FALHOU')
        with self.case('erro de banco'):
            def broken(reference):
                with connection.cursor() as cursor:
                    cursor.execute('SELECT * FROM tabela_inexistente')

            handlers._handlers['QUEBRADO'] = broken
            entry = self.entry(kind='QUEBRADO')
            with self.assertLogs('outbox', 'WARNING'):
                process_next()
            entry.refresh_from_db()
            self.assertEqual((entry.status, entry.attempts), ('A_ENVIAR', 1))


class HandlerRegistryTests(TestCase):
    def test_registers_and_refuses_other_handler_for_same_kind(self):
        with mock.patch.dict(handlers._handlers, clear=True):
            handlers.register('TESTE', message_for)
            handlers.register('TESTE', message_for)
            self.assertIs(handlers.get_handler('TESTE'), message_for)
            with self.assertRaises(ImproperlyConfigured):
                handlers.register('TESTE', discard)


class IsolationTests(TestCase):
    def test_outbox_does_not_import_domain_apps(self):
        for path in Path(outbox.__file__).parent.rglob('*.py'):
            if 'tests' in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or '']
                else:
                    continue
                for name in names:
                    self.assertFalse(name.split('.')[0] == 'accounts', f'{path} importa {name}')


class ConcurrencyTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        configure_smtp()

    def test_locked_entry_is_skipped(self):
        entry = OutboxEntry.objects.create(kind='TESTE', reference='1')
        locked = threading.Event()
        release = threading.Event()

        def hold_lock():
            try:
                with transaction.atomic():
                    OutboxEntry.objects.select_for_update().get(pk=entry.pk)
                    locked.set()
                    release.wait(10)
            finally:
                connection.close()

        thread = threading.Thread(target=hold_lock)
        thread.start()
        locked.wait(10)
        try:
            with mock.patch.dict(handlers._handlers, {'TESTE': message_for}):
                self.assertFalse(process_next())
        finally:
            release.set()
            thread.join()
        entry.refresh_from_db()
        self.assertEqual(entry.status, 'A_ENVIAR')


class SmtpSettingsTests(IsolatedCasesMixin, TestCase):
    def setUp(self):
        patcher = mock.patch.dict(handlers._handlers, {'TESTE': message_for, 'FALHA': failing}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_entries_wait_for_a_valid_setting(self):
        with self.case('cadastro independe'):
            OutboxEntry.objects.enqueue('TESTE', 1)
            self.assertTrue(OutboxEntry.objects.filter(kind='TESTE', status='A_ENVIAR').exists())
        with self.case('sem configuração'):
            entry = OutboxEntry.objects.create(kind='TESTE', reference='1')
            before = entry.next_attempt_at
            for _ in range(3):
                with self.assertRaises(SmtpUnavailable):
                    process_batch(10)
            entry.refresh_from_db()
            self.assertEqual((entry.status, entry.attempts, entry.next_attempt_at), ('A_ENVIAR', 0, before))
            self.assertEqual(mail.outbox, [])
        with self.case('configuração inválida'):
            configure_smtp()
            entry = OutboxEntry.objects.create(kind='TESTE', reference='1')
            with override_settings(CREDENTIALS_KEY='outra-chave'), self.assertRaises(SmtpUnavailable):
                process_batch(10)
            entry.refresh_from_db()
            self.assertEqual((entry.status, entry.attempts), ('A_ENVIAR', 0))
            self.assertEqual(mail.outbox, [])
        with self.case('enviadas depois de configurar'):
            for reference in range(2):
                OutboxEntry.objects.create(kind='TESTE', reference=str(reference))
            with self.assertRaises(SmtpUnavailable):
                process_batch(10)
            configure_smtp()
            self.assertEqual(process_batch(10), 2)
            self.assertEqual(OutboxEntry.objects.filter(status='ENVIADO').count(), 2)

    def test_uses_the_stored_credentials_and_sender(self):
        configure_smtp(host='a.ifnmg.edu.br')
        OutboxEntry.objects.create(kind='TESTE', reference='1')
        with mock.patch('system_settings.models.get_connection', wraps=get_connection) as connect:
            process_batch(10)
            configure_smtp(host='b.ifnmg.edu.br')
            OutboxEntry.objects.create(kind='TESTE', reference='2')
            process_batch(10)
        hosts = [call.kwargs['host'] for call in connect.call_args_list if 'host' in call.kwargs]
        self.assertEqual(hosts, ['a.ifnmg.edu.br', 'b.ifnmg.edu.br'])
        self.assertEqual(connect.call_args_list[0].kwargs['password'], SMTP_PASSWORD)
        self.assertEqual({message.from_email for message in mail.outbox}, {'IFAgenda <agenda@ifnmg.edu.br>'})

    def test_smtp_failure_follows_retry_policy_without_password(self):
        configure_smtp()
        entry = OutboxEntry.objects.create(kind='TESTE', reference='1')
        error = SMTPAuthenticationError(535, b'credenciais recusadas')
        with mock.patch.object(EmailMessage, 'send', side_effect=error), self.assertLogs('outbox', 'WARNING'):
            process_batch(10)
        entry.refresh_from_db()
        self.assertEqual((entry.status, entry.attempts), ('A_ENVIAR', 1))
        self.assertNotIn(SMTP_PASSWORD, entry.last_error)
