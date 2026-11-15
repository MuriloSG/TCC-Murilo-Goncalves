"""Worker das importações: reserva, execução, novas tentativas, recusas e concorrência."""

import threading
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from config.testing import IsolatedCasesMixin
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


class WorkerTestCase(IsolatedCasesMixin, TestCase):
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
    def test_constraint_refuses_operation_contradicting_the_status(self):
        concluded = self.validated('Docentes')
        confirm(concluded, self.definition, self.executor)
        for status, operation in (('CONCLUIDA', 'CONFIRMACAO'), ('PENDENTE', 'CONFIRMACAO'), ('VALIDADA', 'PREVIA'), ('RECEBIDA', None)):
            with self.subTest(status=status, operation=operation):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Import.objects.filter(pk=concluded.pk).update(status=status, operation=operation)


class ReservationTests(WorkerTestCase):
    def test_reservation_counts_the_attempt_and_postpones_the_next_one(self):
        with self.case('reserva'):
            importation = self.requested('Docentes')
            reserved, definition = worker.reserve()
            self.assertEqual((reserved.pk, definition), (importation.pk, self.definition))
            importation.refresh_from_db()
            self.assertEqual(importation.attempts, 1)
            self.assertGreater(importation.next_attempt_at, timezone.now() + timedelta(seconds=25))
            self.assertEqual(importation.status, 'RECEBIDA')
            self.assertIsNone(worker.reserve())
        with self.case('repete o último intervalo'):
            with override_settings(IMPORT_RETRY_DELAYS=[30, 120]):
                self.assertEqual([retry_delay(n).total_seconds() for n in (1, 2, 3)], [30, 120, 120])

    def test_crash_between_reservation_and_execution_is_retried_when_due(self):
        importation = self.requested('Docentes')
        worker.reserve()
        self.assertFalse(worker.process_next())
        Import.objects.filter(pk=importation.pk).update(next_attempt_at=timezone.now())
        self.assertTrue(worker.process_next())
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('VALIDADA', None, 0))

    def test_exhausted_without_executing(self):
        with self.case('quedas repetidas'):
            with override_settings(IMPORT_MAX_ATTEMPTS=2):
                importation = self.requested('Docentes')
                Import.objects.filter(pk=importation.pk).update(attempts=2)
                with mock.patch.object(Import, 'run_preview') as run_preview:
                    self.assertTrue(worker.process_next())
                run_preview.assert_not_called()
                importation.refresh_from_db()
                self.assertEqual((importation.status, importation.operation), ('FALHOU', None))
                self.assertTrue(AuditLog.objects.filter(action=catalog.IMPORT_FAIL, resource_id=str(importation.pk)).exists())
        with self.case('tipo sem definição'):
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

    def test_exhausted_operation_keeps_the_status(self):
        with self.case('atualização'):
            with override_settings(IMPORT_MAX_ATTEMPTS=1):
                importation = self.validated('Docentes', 'DECIDIR')
                plan = importation.comparable()
                with mock.patch.object(Import, 'run_refresh', side_effect=RuntimeError('falha')):
                    self.assertEqual(refresh(importation, self.definition, self.executor), 'PENDENTE')
                self.assertEqual((importation.operation, importation.outcome), (None, 'FALHA_ATUALIZACAO'))
                self.assertEqual(importation.comparable(), plan)
        with self.case('confirmação'):
            with override_settings(IMPORT_MAX_ATTEMPTS=1):
                importation = self.validated('Docentes')
                with mock.patch.object(Import, 'run_confirmation', side_effect=RuntimeError('falha')):
                    self.assertFalse(confirm(importation, self.definition, self.executor))
                self.assertEqual((importation.status, importation.operation, importation.outcome), ('VALIDADA', None, 'FALHA_CONFIRMACAO'))
                record = AuditLog.objects.get(action=catalog.IMPORT_FAIL)
                self.assertEqual(record.metadata['situacao'], 'VALIDADA')
                self.assertTrue(confirm(importation, self.definition, self.executor))

    def test_business_refusals_are_not_retried(self):
        with self.case('conferência própria'):
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
        with self.case('regra'):
            importation = self.requested('Docentes')
            with mock.patch.object(GroupImport, 'lock', side_effect=ValidationError('Semestre recusado.')):
                run_worker(self.definition)
            importation.refresh_from_db()
            self.assertEqual((importation.status, importation.operation, importation.outcome_message), ('FALHOU', None, 'Semestre recusado.'))
        with self.case('linha recusada'):
            importation = self.validated('ERRO')
            self.assertEqual((importation.status, importation.operation, importation.attempts), ('COM_ERROS', None, 0))


class LoggingTests(WorkerTestCase):
    """Eventos do worker no log, só com número, tipo, operação e classe do erro."""

    def test_failures_log_the_error_class_without_the_message(self):
        with self.case('falha'):
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
        with self.case('esgotada'):
            with override_settings(IMPORT_MAX_ATTEMPTS=1):
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

    def test_inactive_requester_is_refused(self):
        with self.case('sem executar'):
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
        with self.case('prévia falha'):
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
