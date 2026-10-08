"""Worker das importações: reserva, execução, novas tentativas, recusas e concorrência (D4, D5, D6)."""

import threading
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from imports import registry, worker
from imports.definitions import RowError
from imports.models import Import, ImportBusy, retry_delay
from imports.tests.definitions import GroupImport
from imports.tests.test_models import rows
from imports.tests.worker import confirm, preview, refresh, run_worker


class WorkerTestCase(TestCase):
    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = GroupImport()
        patcher = mock.patch.dict(registry._definitions, {self.definition.kind: self.definition})
        patcher.start()
        self.addCleanup(patcher.stop)

    def requested(self, *names):
        return Import.objects.request_preview(self.definition, rows(*names), 'grupos.csv', self.executor)

    def validated(self, *names):
        return preview(self.definition, rows(*names), 'grupos.csv', self.executor)


class BusinessStatusTests(WorkerTestCase):
    def test_status_has_only_business_situations(self):
        self.assertEqual(
            set(Import.Status.values),
            {'RECEBIDA', 'VALIDADA', 'PENDENTE', 'COM_ERROS', 'CONCLUIDA', 'DESCARTADA', 'FALHOU'},
        )
        self.assertNotIn('PROCESSANDO', Import.Status.values)
        names = {field.name for field in Import._meta.get_fields()}
        self.assertNotIn('previous_status', names)
        self.assertFalse(any('stale' in name for name in names))

    def test_request_keeps_the_business_status(self):
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, self.executor)
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', 'CONFIRMACAO'))
        importation = self.validated('Técnicos', 'DECIDIR')
        importation.request_refresh(self.executor)
        self.assertEqual((importation.status, importation.operation), ('PENDENTE', 'ATUALIZACAO'))

    def test_constraint_refuses_operation_contradicting_the_status(self):
        concluded = self.validated('Docentes')
        confirm(concluded, self.definition, self.executor)
        for status, operation in (('CONCLUIDA', 'CONFIRMACAO'), ('PENDENTE', 'CONFIRMACAO'), ('VALIDADA', 'PREVIA'), ('RECEBIDA', None)):
            with self.subTest(status=status, operation=operation):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Import.objects.filter(pk=concluded.pk).update(status=status, operation=operation)

    def test_pending_confirmation_still_counts_as_open_import_in_the_panel(self):
        from panel.indicators import OPEN_IMPORT_STATUSES

        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, self.executor)
        self.assertTrue(Import.objects.filter(pk=importation.pk, status__in=OPEN_IMPORT_STATUSES).exists())


class ReservationTests(WorkerTestCase):
    def test_reservation_counts_the_attempt_and_postpones_the_next_one(self):
        importation = self.requested('Docentes')
        reserved, definition = worker.reserve()
        self.assertEqual((reserved.pk, definition), (importation.pk, self.definition))
        importation.refresh_from_db()
        self.assertEqual(importation.attempts, 1)
        self.assertGreater(importation.next_attempt_at, timezone.now() + timedelta(seconds=25))
        self.assertEqual(importation.status, 'RECEBIDA')
        self.assertIsNone(worker.reserve())

    def test_crash_between_reservation_and_execution_is_retried_when_due(self):
        importation = self.requested('Docentes')
        worker.reserve()
        self.assertFalse(worker.process_next())
        Import.objects.filter(pk=importation.pk).update(next_attempt_at=timezone.now())
        self.assertTrue(worker.process_next())
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('VALIDADA', None, 0))

    @override_settings(IMPORT_MAX_ATTEMPTS=2)
    def test_repeated_crashes_exhaust_without_executing(self):
        importation = self.requested('Docentes')
        Import.objects.filter(pk=importation.pk).update(attempts=2)
        with mock.patch.object(Import, 'run_preview') as run_preview:
            self.assertTrue(worker.process_next())
        run_preview.assert_not_called()
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('FALHOU', None))
        self.assertTrue(AuditLog.objects.filter(action=catalog.IMPORT_FAIL, resource_id=str(importation.pk)).exists())

    @override_settings(IMPORT_RETRY_DELAYS=[30, 120])
    def test_retry_delays_repeat_the_last_one(self):
        self.assertEqual([retry_delay(n).total_seconds() for n in (1, 2, 3)], [30, 120, 120])

    def test_kind_without_definition_is_exhausted(self):
        importation = self.requested('Docentes')
        with mock.patch.dict(registry._definitions, {}, clear=True):
            worker.process_next()
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'FALHOU')
        self.assertIn('sem definição registrada', importation.last_error)


class FailureTests(WorkerTestCase):
    def test_unexpected_error_rolls_back_and_keeps_the_operation_pending(self):
        importation = self.validated('Docentes')
        with mock.patch.object(GroupImport, 'check_file', side_effect=RuntimeError('fora do ar')):
            self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('VALIDADA', 'CONFIRMACAO', 1))
        self.assertEqual(importation.last_error, 'RuntimeError: fora do ar')
        self.assertFalse(Group.objects.exists())
        Import.objects.filter(pk=importation.pk).update(next_attempt_at=timezone.now())
        run_worker(self.definition)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation, importation.last_error), ('CONCLUIDA', None, ''))
        self.assertEqual(Group.objects.filter(name='Docentes').count(), 1)

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_exhausted_refresh_keeps_the_status_and_the_plan(self):
        importation = self.validated('Docentes', 'DECIDIR')
        plan = importation.comparable()
        with mock.patch.object(Import, 'run_refresh', side_effect=RuntimeError('falha')):
            self.assertEqual(refresh(importation, self.definition, self.executor), 'PENDENTE')
        self.assertEqual((importation.operation, importation.outcome), (None, 'FALHA_ATUALIZACAO'))
        self.assertEqual(importation.comparable(), plan)

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_exhausted_confirmation_keeps_validated(self):
        importation = self.validated('Docentes')
        with mock.patch.object(Import, 'run_confirmation', side_effect=RuntimeError('falha')):
            self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual((importation.status, importation.operation, importation.outcome), ('VALIDADA', None, 'FALHA_CONFIRMACAO'))
        record = AuditLog.objects.get(action=catalog.IMPORT_FAIL)
        self.assertEqual(record.metadata['situacao'], 'VALIDADA')
        self.assertTrue(confirm(importation, self.definition, self.executor))

    def test_own_check_refusing_in_the_worker_is_not_retried(self):
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, self.executor)
        self.definition.refusal = 'Falta a permissão.'
        run_worker(self.definition)
        importation.refresh_from_db()
        self.assertEqual(
            (importation.status, importation.operation, importation.outcome, importation.outcome_message),
            ('VALIDADA', None, 'RECUSADA', 'Falta a permissão.'),
        )
        self.assertEqual((importation.revalidation_count, importation.attempts), (0, 0))
        self.assertFalse(Group.objects.exists())

    def test_rule_refusal_escaping_the_execution_is_not_retried(self):
        importation = self.requested('Docentes')
        with mock.patch.object(GroupImport, 'lock', side_effect=ValidationError('Semestre recusado.')):
            run_worker(self.definition)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation, importation.outcome_message), ('FALHOU', None, 'Semestre recusado.'))

    def test_row_refusal_is_a_business_result_and_not_a_failure(self):
        importation = self.validated('ERRO')
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('COM_ERROS', None, 0))

    def test_reader_errors_reach_the_preview(self):
        source = rows('Docentes')
        source[0].errors.append(RowError('Nome', 'required', 'Preencha a coluna Nome.'))
        importation = preview(self.definition, source, 'grupos.csv', self.executor)
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(importation.rows.get().errors[0]['code'], 'required')



class LoggingTests(WorkerTestCase):
    """Eventos do worker no log, só com número, tipo, operação e classe do erro."""

    def test_configuration_sends_the_project_loggers_to_stdout(self):
        handler = settings.LOGGING['handlers']['stdout']
        self.assertEqual((handler['class'], handler['stream']), ('logging.StreamHandler', 'ext://sys.stdout'))
        for name in settings.APP_LOGGERS:
            with self.subTest(name):
                self.assertEqual(settings.LOGGING['loggers'][name]['level'], settings.LOG_LEVEL)
                self.assertEqual(settings.LOGGING['loggers'][name]['handlers'], ['stdout'])
        self.assertEqual(settings.LOGGING['loggers']['django.request']['level'], 'ERROR')

    def test_preview_logs_start_and_completion(self):
        importation = self.requested('Docentes')
        with self.assertLogs('imports', 'INFO') as logs:
            run_worker(self.definition)
        self.assertEqual(logs.output, [
            f'INFO:imports:Importação {importation.pk} (GRUPO): PREVIA iniciada, tentativa 1.',
            f'INFO:imports:Importação {importation.pk} (GRUPO): PREVIA concluída, situação VALIDADA, resultado -.',
        ])

    def test_failure_logs_the_error_class_without_the_message(self):
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, self.executor)
        error = RuntimeError('linha 3: Ana Souza, ana.souza@ifnmg.edu.br')
        with mock.patch.object(GroupImport, 'check_file', side_effect=error), self.assertLogs('imports', 'DEBUG') as logs:
            run_worker(self.definition)
        warnings = [record for record in logs.records if record.levelname == 'WARNING']
        self.assertEqual(
            [record.getMessage() for record in warnings],
            [f'Importação {importation.pk} (GRUPO): CONFIRMACAO falhou na tentativa 1: RuntimeError.'],
        )
        for record in logs.records:
            self.assertNotIn('ana.souza', record.getMessage())
        self.assertTrue(any(record.exc_info for record in logs.records if record.levelname == 'DEBUG'))
        importation.refresh_from_db()
        self.assertEqual(importation.last_error, f'RuntimeError: {error}')

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_exhausted_failure_is_an_error(self):
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, self.executor)
        with (
            mock.patch.object(GroupImport, 'check_file', side_effect=RuntimeError('dado da planilha')),
            self.assertLogs('imports', 'ERROR') as logs,
        ):
            run_worker(self.definition)
        self.assertEqual(logs.output, [
            f'ERROR:imports:Importação {importation.pk} (GRUPO): CONFIRMACAO falhou na tentativa 1 '
            'e não será tentada de novo: RuntimeError.',
        ])

    def test_worker_command_logs_start_and_stop(self):
        with (
            mock.patch('imports.management.commands.process_imports.close_old_connections'),
            self.assertLogs('imports', 'INFO') as logs,
        ):
            call_command('process_imports', once=True)
        self.assertEqual(logs.output, [
            'INFO:imports:Worker das importações iniciado.',
            'INFO:imports:Worker das importações encerrado.',
        ])

class RequesterTests(WorkerTestCase):
    def test_execution_uses_the_requester_as_executor_and_auditor(self):
        other = User.objects.create(email='outro@ifnmg.edu.br', name='Outro')
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, other)
        run_worker(self.definition)
        importation.refresh_from_db()
        self.assertEqual(importation.resolved_by, other)
        record = AuditLog.objects.get(action=catalog.IMPORT)
        self.assertEqual((record.user, record.origin), (other, catalog.INTERFACE))

    def test_inactive_requester_is_refused_without_executing(self):
        other = User.objects.create(email='outro@ifnmg.edu.br', name='Outro')
        importation = self.validated('Docentes')
        importation.request_confirmation(self.definition, other)
        User.objects.filter(pk=other.pk).update(is_active=False)
        with mock.patch.object(Import, 'run_confirmation') as run_confirmation:
            run_worker(self.definition)
        run_confirmation.assert_not_called()
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation, importation.outcome), ('VALIDADA', None, 'RECUSADA'))
        self.assertEqual(importation.outcome_message, 'Quem pediu a confirmação está desativado. Nada foi aplicado.')

    def test_inactive_requester_of_the_preview_fails_it(self):
        importation = self.requested('Docentes')
        User.objects.filter(pk=self.executor.pk).update(is_active=False)
        run_worker(self.definition)
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'FALHOU')


class LockTimeoutTests(WorkerTestCase):
    @override_settings(IMPORT_LOCK_TIMEOUT=60)
    def test_execution_waits_for_locks_at_most_the_configured_time(self):
        seen = []

        def capture(importation, definition, executor):
            with connection.cursor() as cursor:
                cursor.execute('SHOW lock_timeout')
                seen.append(cursor.fetchone()[0])
            Import.run_refresh(importation, definition, executor)

        importation = self.requested('Docentes')
        with mock.patch.object(Import, 'run_preview', autospec=True, side_effect=capture):
            run_worker(self.definition)
        self.assertEqual(seen, ['1min'])


class CommandTests(WorkerTestCase):
    def test_once_processes_the_due_operations_and_discards_stale_connections(self):
        importation = self.requested('Docentes')
        with mock.patch('imports.management.commands.process_imports.close_old_connections') as close:
            call_command('process_imports', '--once')
        close.assert_called()
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'VALIDADA')


class ConcurrencyTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = GroupImport()
        patcher = mock.patch.dict(registry._definitions, {self.definition.kind: self.definition})
        patcher.start()
        self.addCleanup(patcher.stop)

    def holding_the_lock(self, importation):
        """Segura a trava da importação noutra conexão, como o worker durante a execução."""
        locked, release = threading.Event(), threading.Event()

        def hold():
            try:
                with transaction.atomic():
                    Import.objects.select_for_update().get(pk=importation.pk)
                    locked.set()
                    release.wait(10)
            finally:
                connection.close()

        thread = threading.Thread(target=hold)
        thread.start()
        locked.wait(5)
        return thread, release

    def test_second_worker_skips_the_import_being_executed(self):
        importation = preview(self.definition, rows('Docentes'), 'grupos.csv', self.executor)
        importation.request_confirmation(self.definition, self.executor)
        thread, release = self.holding_the_lock(importation)
        try:
            self.assertFalse(importation.execute_pending(self.definition))
        finally:
            release.set()
            thread.join()
        self.assertFalse(Group.objects.exists())

    def test_actions_on_a_locked_import_are_refused_without_waiting(self):
        importation = preview(self.definition, rows('Docentes'), 'grupos.csv', self.executor)
        thread, release = self.holding_the_lock(importation)
        try:
            for action in (
                lambda: importation.request_confirmation(self.definition, self.executor),
                lambda: importation.request_refresh(self.executor),
                lambda: importation.discard(self.definition, self.executor),
            ):
                started = timezone.now()
                with self.assertRaises(ImportBusy):
                    action()
                self.assertLess((timezone.now() - started).total_seconds(), 2)
        finally:
            release.set()
            thread.join()
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('VALIDADA', None))
