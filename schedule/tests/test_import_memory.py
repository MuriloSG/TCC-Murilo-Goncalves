"""Memória da execução da importação do ensalamento e etapa final (Change otimizar-consultas-do-sistema).

A memória guarda os registros resolvidos só durante a execução, e o que uma linha desfeita
criou deixa de valer para as linhas seguintes. As ofertas são sincronizadas depois das
linhas, só para as mantidas, e a trava das alocações não alcança outras tabelas.
"""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

from imports.execution import run
from imports.forms import ImportUploadForm
from imports.models import Import
from schedule.models import Allocation, ClassOffering, Subject, TeachingAssignment
from schedule.tests.test_import import PERIOD, ImportTestCase, workbook_file

REAL_APPLY = Allocation.objects.apply


def refusing_first(*args, **kwargs):
    """Recusa a primeira alocação e aplica as demais como sempre."""
    refusing_first.calls += 1
    if refusing_first.calls == 1:
        raise ValidationError({'space': ValidationError('Recusada pelo teste.', code='refused')})
    return REAL_APPLY(*args, **kwargs)


class ImportMemoryTests(ImportTestCase):
    def rows(self, uploaded):
        form = ImportUploadForm(
            data={'own_semestre': '2026/1', **PERIOD}, files={'file': uploaded}, definition=self.definition,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data['rows']

    def test_record_created_by_a_refused_row_is_created_again(self):
        """A chave estrangeira do PostgreSQL só é conferida no commit, por isso a alocação da
        segunda linha é conferida dentro da execução, antes do rollback."""
        rows = self.rows(workbook_file(
            undergraduate={
                ('SEGUNDA ', '07:20 - 08:10', 0): 'Física Nova (Elza) (1/13)',
                ('SEGUNDA ', '08:10 - 09:00', 0): 'Física Nova (Elza) (1/13)',
            },
            secondary={},
        ))
        refusing_first.calls = 0
        with transaction.atomic(), patch.object(Allocation.objects, 'apply', side_effect=refusing_first):
            plan = run(self.definition, rows, self.executor)
            subjects = list(Subject.objects.filter(name='Física Nova'))
            allocated = list(Allocation.objects.values_list('subject_id', flat=True))
            transaction.set_rollback(True)
        first, second = [row_plan for row, row_plan in plan.rows if row.values.get('Tipo') == 'ATIVIDADE']
        self.assertEqual([error.code for error in first.errors], ['refused'])
        self.assertEqual(second.errors, [])
        self.assertEqual(second.action, 'create')
        self.assertEqual(len(subjects), 1)
        self.assertEqual(allocated, [subjects[0].pk])

    def test_spellings_that_differ_only_in_case_use_the_same_subject(self):
        importation = self.conclude(workbook_file(
            undergraduate={
                ('SEGUNDA ', '07:20 - 08:10', 0): 'Química Geral (Elza) (1/13)',
                ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA GERAL (Elza) (1/13)',
            },
            secondary={},
        ))
        self.assertEqual(importation.status, Import.Status.CONCLUDED)
        self.assertEqual(list(Subject.objects.values_list('name', flat=True)), ['Química Geral'])
        self.assertEqual(Allocation.objects.filter(subject__name='Química Geral').count(), 2)

    def test_offering_comes_only_from_kept_rows(self):
        rows = self.rows(workbook_file(
            undergraduate={('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)'},
            secondary={('SEGUNDA-FEIRA', '13:20 - 14:10', 0): 'Biologia (Érica) (HV 3)'},
        ))
        refusing_first.calls = 0
        with transaction.atomic(), patch.object(Allocation.objects, 'apply', side_effect=refusing_first):
            plan = run(self.definition, rows, self.executor)
            offerings = set(ClassOffering.objects.values_list('subject__name', flat=True))
            assignments = set(TeachingAssignment.objects.values_list('teacher__name', flat=True))
            transaction.set_rollback(True)
        self.assertEqual(len([row for row, row_plan in plan.rows if row_plan.errors]), 1)
        self.assertEqual(offerings, {'Biologia'})
        self.assertEqual(assignments, {'Érica'})

    def test_preview_undoes_the_final_step(self):
        importation = self.preview()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertFalse(ClassOffering.objects.exists())
        self.assertFalse(TeachingAssignment.objects.exists())

    def test_lock_reaches_only_the_allocations(self):
        self.conclude()
        rows = self.rows(workbook_file())
        with transaction.atomic(), CaptureQueriesContext(connection) as context:
            run(self.definition, rows, self.executor)
            transaction.set_rollback(True)
        locks = [query['sql'] for query in context.captured_queries if 'FOR UPDATE' in query['sql']]
        allocation_locks = [sql for sql in locks if 'FROM "schedule_allocation"' in sql]
        self.assertEqual(len(allocation_locks), 1)
        self.assertNotIn('JOIN', allocation_locks[0])
        self.assertFalse([sql for sql in locks if '"schedule_space"' in sql or '"schedule_teacher"' in sql])
