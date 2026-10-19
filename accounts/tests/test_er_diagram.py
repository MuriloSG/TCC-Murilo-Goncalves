import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase


def export():
    with tempfile.TemporaryDirectory() as directory:
        call_command('export_er_diagram', '--output', directory, stdout=StringIO())
        return {path.name: path.read_text(encoding='utf-8') for path in Path(directory).iterdir()}


class ExportErDiagramTests(TestCase):
    def test_writes_conceptual_physical_and_restrictions(self):
        self.assertEqual(set(export()), {'der-conceitual.dot', 'der-fisico.dot', 'restricoes.md'})

    def test_conceptual_uses_chen_notation_with_cardinalities(self):
        content = export()['der-conceitual.dot']
        self.assertIn('shape=diamond, label="solicita"', content)
        self.assertIn('Usuario:e -- r18 [taillabel="(1,1)"]; r18 -- Solicitacao:e [headlabel="(0,n)"];', content)
        self.assertIn('* Solicitação(id, data', content)

    def test_physical_lists_project_tables_with_columns_and_keys(self):
        content = export()['der-fisico.dot']
        self.assertIn('<B>accounts_user</B>', content)
        self.assertIn('schedule_allocation_teachers [', content)
        self.assertIn('<TD ALIGN="LEFT">NOT NULL</TD><TD ALIGN="LEFT">FK, UK</TD>', content)
        self.assertNotIn('auth_group', content)
        self.assertNotIn('account_emailaddress', content)

    def test_physical_cardinality_follows_nullability_and_uniqueness(self):
        content = export()['der-fisico.dot']
        self.assertIn('bookings_booking -- schedule_space [taillabel="(0,n)", headlabel="(1,1)"];', content)
        self.assertIn('schedule_allocation -- schedule_space [taillabel="(0,n)", headlabel="(0,1)"];', content)
        self.assertIn('bookings_booking -- bookings_bookingrequest [taillabel="(0,1)", headlabel="(1,1)"];', content)

    def test_restrictions_list_constraints_as_sql(self):
        content = export()['restricoes.md']
        self.assertIn('EXCLUDE USING GIST', content)
        self.assertIn('WHERE "status" = \'A_ENVIAR\'', content)
        self.assertNotIn(' object at 0x', content)

    def test_output_is_deterministic(self):
        self.assertEqual(export(), export())
