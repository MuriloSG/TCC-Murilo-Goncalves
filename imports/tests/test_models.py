import ast
import threading
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase

import imports
from accounts.models import User
from imports.models import Import
from imports.reader import SourceRow
from imports.tests.definitions import GroupImport


def rows(*names):
    return [SourceRow(line_number, {'Nome': name}) for line_number, name in enumerate(names, start=2)]


class ImportTestCase(TestCase):
    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = GroupImport()

    def preview(self, *names):
        return Import.objects.preview(self.definition, rows(*names), 'grupos.csv', self.executor)


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
        self.assertEqual(importation.summary(), {'create': 2, 'update': 0, 'unchanged': 0, 'errors': 0})

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
        importation = Import.objects.preview(self.definition, source, 'grupos.csv', self.executor)
        row = importation.rows.get()
        self.assertIsNone(row.action)
        self.assertEqual(row.errors[0]['code'], 'required')

    def test_file_error(self):
        importation = self.preview('PROIBIDO')
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertEqual(importation.file_errors, [{'code': 'forbidden', 'message': 'Grupo proibido.'}])
        self.assertEqual(importation.rows.get().errors, [])

    def test_unexpected_error_creates_no_import(self):
        with self.assertRaises(RuntimeError):
            self.preview('Docentes', 'FALHA')
        self.assertFalse(Import.objects.exists())
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
        self.assertTrue(importation.confirm(self.definition, self.other))
        self.assertEqual(set(Group.objects.values_list('name', flat=True)), {'Docentes', 'Técnicos'})
        self.assertEqual(importation.status, 'CONCLUIDA')
        self.assertEqual(importation.resolved_by, self.other)
        self.assertIsNotNone(importation.resolved_at)
        row = importation.rows.get(line_number=2)
        self.assertEqual(row.created_object, str(Group.objects.get(name='Docentes').pk))

    def test_changed_data_gives_new_plan_without_applying(self):
        importation = self.preview('Docentes', 'Técnicos')
        Group.objects.create(name='Docentes')
        self.assertFalse(importation.confirm(self.definition, self.executor))
        self.assertEqual(list(Group.objects.values_list('name', flat=True)), ['Docentes'])
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertEqual(importation.revalidation_count, 1)
        self.assertEqual(importation.rows.get(line_number=2).action, 'unchanged')
        self.assertIsNone(importation.resolved_by)
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertEqual(importation.status, 'CONCLUIDA')

    def test_new_plan_with_errors(self):
        importation = self.preview('Docentes')
        Group.objects.create(name='PROIBIDO')
        self.assertFalse(importation.confirm(self.definition, self.executor))
        self.assertEqual(importation.status, 'COM_ERROS')
        self.assertFalse(Group.objects.filter(name='Docentes').exists())

    def test_unexpected_error_keeps_validated(self):
        importation = self.preview('Docentes', 'Técnicos')
        row = importation.rows.get(line_number=3)
        row.values = {'Nome': 'FALHA'}
        row.save()
        with self.assertRaises(RuntimeError):
            importation.confirm(self.definition, self.executor)
        importation.refresh_from_db()
        self.assertEqual(importation.status, 'VALIDADA')
        self.assertFalse(Group.objects.exists())

    def test_final_statuses_refuse_confirm_and_discard(self):
        concluded = self.preview('Docentes')
        concluded.confirm(self.definition, self.executor)
        with_errors = self.preview('ERRO')
        discarded = self.preview('Técnicos')
        discarded.discard(self.definition, self.executor)
        for importation in (concluded, with_errors, discarded):
            with self.subTest(status=importation.status):
                with self.assertRaises(ValidationError):
                    importation.confirm(self.definition, self.executor)
                with self.assertRaises(ValidationError):
                    importation.discard(self.definition, self.executor)
        self.assertEqual(list(Group.objects.values_list('name', flat=True)), ['Docentes'])

    def test_discard(self):
        importation = self.preview('Docentes')
        importation.discard(self.definition, self.other)
        self.assertEqual((importation.status, importation.resolved_by), ('DESCARTADA', self.other))
        self.assertFalse(Group.objects.exists())


class ConcurrentConfirmTests(TransactionTestCase):
    serialized_rollback = True

    def test_simultaneous_confirmations_apply_once(self):
        executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        importation = Import.objects.preview(GroupImport(), rows('Docentes'), 'grupos.csv', executor)
        results, barrier = [], threading.Barrier(2)

        def confirm():
            try:
                barrier.wait(5)
                results.append(Import.objects.get(pk=importation.pk).confirm(GroupImport(), executor))
            except ValidationError:
                results.append('recusada')
            finally:
                connection.close()

        threads = [threading.Thread(target=confirm) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results, key=str), [True, 'recusada'])
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
