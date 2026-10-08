"""Consultas da importação limitadas pelos registros distintos, e não pelas linhas."""

from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

from imports.models import Import
from imports.tests.worker import confirm
from schedule.tests.test_import import ImportTestCase, workbook_file

CELL = 'QUÍMICA ORGÂNICA (Elza) (1/13)'
SLOTS = ['07:20 - 08:10', '08:10 - 09:00', '09:20 - 10:10']
MAX_QUERIES_PER_ROW = 6


def activities(days):
    return {(day, slot, position): CELL for day in days for slot in SLOTS for position in (0, 1)}


SMALL = ['SEGUNDA ']
LARGE = ['SEGUNDA ', 'TERÇA']
ADDED_ROWS = len(activities(LARGE)) - len(activities(SMALL))


def sheet(days):
    return workbook_file(undergraduate=activities(days), secondary={})


class ImportQueryTests(ImportTestCase):
    def counted(self, operation):
        with CaptureQueriesContext(connection) as context:
            operation()
        return len(context.captured_queries)

    def preview_queries(self, days):
        return self.counted(lambda: self.preview(sheet(days)))

    def confirmation_queries(self, days):
        """Consultas da confirmação de uma primeira importação, desfeita no fim."""
        with transaction.atomic():
            importation = self.preview(sheet(days))
            self.assertEqual(importation.status, Import.Status.VALIDATED, self.errors_of(importation))
            total = self.counted(lambda: self.assertTrue(confirm(importation, self.definition, self.executor)))
            transaction.set_rollback(True)
        return total

    def assert_cost_per_row(self, small, large):
        per_row = (large - small) / ADDED_ROWS
        self.assertLessEqual(per_row, MAX_QUERIES_PER_ROW, f'{small} e {large} consultas: {per_row:.1f} por linha')

    def test_first_preview(self):
        self.assert_cost_per_row(self.preview_queries(SMALL), self.preview_queries(LARGE))

    def test_first_confirmation(self):
        self.assert_cost_per_row(self.confirmation_queries(SMALL), self.confirmation_queries(LARGE))

    def test_reimport_preview(self):
        self.conclude(sheet(LARGE))
        self.assert_cost_per_row(self.preview_queries(SMALL), self.preview_queries(LARGE))
