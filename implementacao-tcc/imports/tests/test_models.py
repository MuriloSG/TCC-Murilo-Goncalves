import ast
import threading
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

import imports
from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from imports.models import Import, ImportRow
from imports.reader import SourceRow
from imports.tests.definitions import GroupImport
from imports.tests.worker import confirm, preview, refresh, run_worker


def rows(*names):
    return [SourceRow(line_number, {'Nome': name}) for line_number, name in enumerate(names, start=2)]


class ImportTestCase(TestCase):
    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = GroupImport()

    def preview(self, *names):
        return preview(self.definition, rows(*names), 'grupos.csv', self.executor)


class PreviewTests(ImportTestCase):
    def test_preview_keeps_the_plan_and_rolls_back_the_domain(self):
        importation = self.preview('Docentes', 'Técnicos')
        self.assertFalse(Group.objects.exists())
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertEqual(
            (importation.kind, importation.file_name, importation.created_by), ('GRUPO', 'grupos.csv', self.executor),
        )
        first = importation.rows.get(line_number=2)
        self.assertEqual(
            (first.action, first.changes, first.values), ('create', {'name': [None, 'Docentes']}, {'Nome': 'Docentes'}),
        )
        self.assertIsNone(first.created_object)
        self.assertEqual(self.definition.locked, [2, 3])
        self.assertEqual(importation.summary(), {'create': 2, 'update': 0, 'unchanged': 0, 'pending': 0, 'errors': 0})

    def test_existing_record_is_unchanged_with_target(self):
        group = Group.objects.create(name='Docentes')
        row = self.preview('Docentes').rows.get()
        self.assertEqual((row.action, row.target), ('unchanged', str(group.pk)))

    def test_all_errors_at_once_including_database_errors(self):
        importation = self.preview('ERRO', 'BANCO', 'Docentes', 'ERRO')
        self.assertEqual(importation.status, 'COM_ERROS')
        errors = {row.line_number: row.errors for row in importation.rows.all()}
        self.assertEqual(errors[2], [{'column': 'Nome', 'code': 'refused', 'message': 'Nome recusado.'}])
        self.assertEqual(errors[3][0]['code'], 'database')
        self.assertEqual(errors[4], [])
        self.assertEqual(errors[5][0]['code'], 'refused')
        self.assertEqual(importation.rows.get(line_number=4).action, 'create')
        self.assertEqual(importation.summary()['errors'], 3)

    def test_reader_errors_skip_execution(self):
        source = rows('Docentes')
        source[0].errors.append(imports.definitions.RowError('Nome', 'required', 'Preencha a coluna Nome.'))
        importation = preview(self.definition, source, 'grupos.csv', self.executor)
        row = importation.rows.get()
        self.assertIsNone(row.action)
        self.assertEqual(row.errors[0]['code'], 'required')

    def test_file_error(self):
        importation = self.preview('PROIBIDO')
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(importation.file_errors, [{'code': 'forbidden', 'message': 'Grupo proibido.'}])
        self.assertEqual(importation.rows.get().errors, [])

    @override_settings(IMPORT_MAX_ATTEMPTS=1)
    def test_unexpected_error_exhausted_leaves_the_import_failed(self):
        importation = self.preview('Docentes', 'FALHA')
        self.assertEqual((importation.status, importation.operation), ('FALHOU', None))
        self.assertEqual(importation.outcome_message, 'A prévia não foi gerada por uma falha do sistema. Envie o arquivo de novo.')
        self.assertIn('RuntimeError', importation.last_error)
        self.assertFalse(Group.objects.exists())
        self.assertTrue(importation.is_deletable)

    def test_unexpected_error_with_attempts_left_keeps_the_preview_pending(self):
        importation = self.preview('Docentes', 'FALHA')
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('RECEBIDA', 'PREVIA', 1))
        self.assertFalse(importation.rows.exclude(action=None).exists())
        self.assertFalse(Group.objects.exists())

    def test_plan_is_deterministic(self):
        first = self.preview('AVISO 1', 'Docentes', 'ERRO')
        second = self.preview('AVISO 1', 'Docentes', 'ERRO')
        self.assertEqual(first.comparable(), second.comparable())


class ConfirmTests(ImportTestCase):
    def setUp(self):
        super().setUp()
        self.other = User.objects.create(email='outro@ifnmg.edu.br', name='Outro')

    def test_identical_plan_applies_and_records_who_confirmed(self):
        importation = self.preview('Docentes', 'Técnicos')
        self.assertTrue(confirm(importation, self.definition, self.other))
        self.assertEqual(set(Group.objects.values_list('name', flat=True)), {'Docentes', 'Técnicos'})
        self.assertEqual(importation.status, 'CONCLUIDA')
        self.assertEqual(importation.resolved_by, self.other)
        self.assertIsNotNone(importation.resolved_at)
        row = importation.rows.get(line_number=2)
        self.assertEqual(row.created_object, str(Group.objects.get(name='Docentes').pk))

    def test_changed_data_gives_new_plan_without_applying(self):
        importation = self.preview('Docentes', 'Técnicos')
        Group.objects.create(name='Docentes')
        self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual(list(Group.objects.values_list('name', flat=True)), ['Docentes'])
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertEqual(importation.revalidation_count, 1)
        self.assertEqual(importation.rows.get(line_number=2).action, 'unchanged')
        self.assertIsNone(importation.resolved_by)
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(importation.status, 'CONCLUIDA')

    def test_new_plan_with_errors(self):
        importation = self.preview('Docentes')
        Group.objects.create(name='PROIBIDO')
        self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertFalse(Group.objects.filter(name='Docentes').exists())

    def test_unexpected_error_keeps_validated(self):
        importation = self.preview('Docentes', 'Técnicos')
        row = importation.rows.get(line_number=3)
        row.values = {'Nome': 'FALHA'}
        row.save()
        self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual((importation.status, importation.operation, importation.attempts), ('VALIDADA', 'CONFIRMACAO', 1))
        self.assertIn('RuntimeError: falha inesperada', importation.last_error)
        self.assertGreater(importation.next_attempt_at, importation.requested_at)
        self.assertFalse(Group.objects.exists())
        self.assertEqual(importation.rows.get(line_number=3).action, 'create')

    def test_final_statuses_refuse_confirm_and_discard(self):
        concluded = self.preview('Docentes')
        confirm(concluded, self.definition, self.executor)
        with_errors = self.preview('ERRO')
        discarded = self.preview('Técnicos')
        discarded.discard(self.definition, self.executor)
        for importation in (concluded, with_errors, discarded):
            with self.subTest(status=importation.status):
                with self.assertRaises(ValidationError):
                    confirm(importation, self.definition, self.executor)
                with self.assertRaises(ValidationError):
                    importation.discard(self.definition, self.executor)
        self.assertEqual(list(Group.objects.values_list('name', flat=True)), ['Docentes'])

    def test_discard(self):
        importation = self.preview('Docentes')
        importation.discard(self.definition, self.other)
        self.assertEqual((importation.status, importation.resolved_by), ('DESCARTADA', self.other))
        self.assertFalse(Group.objects.exists())


class PendingTests(ImportTestCase):
    def test_pending_without_error_needs_decision_and_rolls_back_the_row(self):
        importation = self.preview('Docentes', 'DECIDIR')
        self.assertEqual(importation.status, 'PENDENTE')
        self.assertEqual(importation.get_status_display(), 'Precisa de decisão')
        row = importation.rows.get(line_number=3)
        self.assertEqual((row.action, row.pending), (None, [{'code': 'decidir', 'key': 'DECIDIR'}]))
        self.assertFalse(Group.objects.exists())
        self.assertEqual(importation.summary()['pending'], 1)
        self.assertEqual(self.definition.received.pk, importation.pk)

    def test_error_prevails_over_pending(self):
        self.assertEqual(self.preview('DECIDIR', 'ERRO').status, 'COM_ERROS')

    def test_pending_enters_the_comparison(self):
        importation = self.preview('Docentes', 'DECIDIR')
        Group.objects.create(name='DECIDIDO')
        self.assertNotEqual(importation.comparable(), self.preview('Docentes', 'DECIDIR').comparable())

    def test_needing_decision_is_not_confirmed_nor_deleted_but_is_discarded(self):
        importation = self.preview('DECIDIR')
        with self.assertRaises(ValidationError):
            confirm(importation, self.definition, self.executor)
        with self.assertRaises(ValidationError):
            importation.remove(self.definition, self.executor)
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'PENDENTE')
        importation.discard(self.definition, self.executor)
        self.assertEqual(importation.status, 'DESCARTADA')

    def test_refresh_replaces_the_plan_without_counting_divergence(self):
        importation = self.preview('Docentes', 'DECIDIR')
        Group.objects.create(name='DECIDIDO')
        self.assertEqual(refresh(importation, self.definition, self.executor), 'VALIDADA')
        self.assertEqual(importation.revalidation_count, 0)
        self.assertEqual(importation.rows.get(line_number=3).action, 'create')
        self.assertEqual(self.definition.received.pk, importation.pk)
        self.assertEqual(set(Group.objects.values_list('name', flat=True)), {'DECIDIDO'})
        self.assertFalse(AuditLog.objects.filter(action=catalog.UPDATE).exists())
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(importation.status, 'CONCLUIDA')

    def test_refresh_back_to_pending(self):
        importation = self.preview('Docentes', 'DECIDIR')
        Group.objects.create(name='DECIDIDO')
        refresh(importation, self.definition, self.executor)
        Group.objects.filter(name='DECIDIDO').delete()
        self.assertEqual(refresh(importation, self.definition, self.executor), 'PENDENTE')

    def test_unexpected_error_on_refresh_changes_nothing(self):
        importation = self.preview('Docentes', 'DECIDIR')
        row = importation.rows.get(line_number=2)
        row.values = {'Nome': 'FALHA'}
        row.save()
        self.assertEqual(refresh(importation, self.definition, self.executor), 'PENDENTE')
        self.assertEqual((importation.operation, importation.attempts), ('ATUALIZACAO', 1))
        self.assertEqual(importation.rows.get(line_number=2).action, 'create')

    def test_refresh_of_final_status_is_refused(self):
        importation = self.preview('Docentes')
        confirm(importation, self.definition, self.executor)
        with self.assertRaises(ValidationError):
            refresh(importation, self.definition, self.executor)

    def test_own_check_refuses_confirmation_without_reexecuting(self):
        importation = self.preview('Docentes')
        self.definition.refusal = 'Falta a permissão.'
        self.definition.locked = None
        with self.assertRaisesMessage(ValidationError, 'Falta a permissão.'):
            confirm(importation, self.definition, self.executor)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.revalidation_count), ('VALIDADA', 0))
        self.assertIsNone(self.definition.locked)
        self.assertFalse(Group.objects.exists())

    def test_confirmation_with_pending_after_changed_data(self):
        importation = self.preview('Docentes', 'DECIDIR')
        Group.objects.create(name='DECIDIDO')
        refresh(importation, self.definition, self.executor)
        Group.objects.filter(name='DECIDIDO').delete()
        self.assertFalse(confirm(importation, self.definition, self.executor))
        self.assertEqual((importation.status, importation.revalidation_count), ('PENDENTE', 1))


class RemoveTests(ImportTestCase):
    def test_discarded_and_with_errors_are_deleted_with_their_rows(self):
        discarded = self.preview('Docentes')
        discarded.discard(self.definition, self.executor)
        with_errors = self.preview('ERRO')
        for importation in (discarded, with_errors):
            with self.subTest(status=importation.status):
                importation.remove(self.definition, self.executor)
                self.assertFalse(Import.objects.filter(pk=importation.pk).exists())
        self.assertFalse(ImportRow.objects.exists())

    def test_pending_and_concluded_are_refused(self):
        pending = self.preview('Docentes')
        concluded = self.preview('Técnicos')
        confirm(concluded, self.definition, self.executor)
        for importation in (pending, concluded):
            with self.subTest(status=importation.status):
                with self.assertRaises(ValidationError):
                    importation.remove(self.definition, self.executor)
                self.assertTrue(Import.objects.filter(pk=importation.pk).exists())

    def test_deletion_is_audited_with_the_file_and_status(self):
        importation = self.preview('ERRO')
        importation.remove(self.definition, self.executor)
        record = AuditLog.objects.filter(action=catalog.DELETE).get()
        self.assertEqual(record.resource_id, str(importation.pk))
        self.assertEqual(record.metadata, {'arquivo': 'grupos.csv', 'situacao': 'COM_ERROS'})


class ConcurrentConfirmTests(TransactionTestCase):
    serialized_rollback = True

    def test_simultaneous_confirmations_apply_once(self):
        executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        definition = GroupImport()
        importation = preview(definition, rows('Docentes'), 'grupos.csv', executor)
        results, barrier = [], threading.Barrier(2)

        def request():
            try:
                barrier.wait(5)
                Import.objects.get(pk=importation.pk).request_confirmation(definition, executor)
                results.append('aceita')
            except ValidationError:
                results.append('recusada')
            finally:
                connection.close()

        threads = [threading.Thread(target=request) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), ['aceita', 'recusada'])
        run_worker(definition)
        run_worker(definition)
        importation.refresh_from_db()
        self.assertEqual((importation.status, importation.operation), ('CONCLUIDA', None))
        self.assertEqual(Group.objects.filter(name='Docentes').count(), 1)


class IsolationTests(TestCase):
    def test_engine_does_not_import_domain_apps(self):
        for path in Path(imports.__file__).parent.rglob('*.py'):
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
                    self.assertNotIn(name.split('.')[0], {'accounts', 'outbox'}, f'{path} importa {name}')
