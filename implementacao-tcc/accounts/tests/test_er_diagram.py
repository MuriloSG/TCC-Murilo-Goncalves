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
        self.assertIn('p18a -- r18 -- p18b;', content)
        self.assertEqual(content.count('fontsize=9, pos='), 2 * content.count('shape=diamond'))
        self.assertIn('* Solicitação(id, data', content)

    def test_conceptual_cardinalities_do_not_overlap(self):
        from accounts.management.commands.export_er_diagram import (
            LABEL_HEIGHT,
            LABEL_WIDTH,
            centered_rect,
            conceptual_layout,
            overlaps,
            place_cardinalities,
        )

        entities, relationships = conceptual_layout()
        labels = [centered_rect(*center, LABEL_WIDTH, LABEL_HEIGHT) for center, _ in place_cardinalities(entities, relationships)]
        boxes = [entity.rect() for entity in entities.values()]
        for index, label in enumerate(labels):
            self.assertFalse(any(overlaps(label, other) for other in labels[index + 1:] + boxes))

    def test_physical_lists_project_tables_with_columns_and_keys(self):
        content = export()['der-fisico.dot']
        self.assertIn('<B>accounts_user</B>', content)
        self.assertIn('schedule_allocation_teachers [', content)
        self.assertRegex(content, r'>NOT NULL</TD><TD ALIGN="LEFT" [^>]*>FK, UK</TD>')
        self.assertNotIn('auth_group', content)
        self.assertNotIn('account_emailaddress', content)

    def test_physical_lines_do_not_cross_tables_and_labels_do_not_overlap(self):
        from accounts.management.commands.export_er_diagram import (
            LABEL_HEIGHT,
            LABEL_WIDTH,
            centered_rect,
            overlaps,
            physical_labels,
            physical_layout,
            project_models,
            segment_hits_rect,
        )

        tables, links = physical_layout(project_models())
        for link in links:
            for start, end in zip(link['points'], link['points'][1:]):
                crossed = [
                    table.name for table in tables.values()
                    if table not in (link['child'], link['parent']) and segment_hits_rect(start, end, table.rect())
                ]
                self.assertEqual(crossed, [], f'{link["child"].name}.{link["field"].column}')
        labels = [centered_rect(*center, LABEL_WIDTH, LABEL_HEIGHT) for center, _ in physical_labels(tables, links)]
        boxes = [table.rect() for table in tables.values()]
        for index, label in enumerate(labels):
            self.assertFalse(any(overlaps(label, other) for other in labels[index + 1:] + boxes))

    def test_physical_cardinality_follows_nullability_and_uniqueness(self):
        content = export()['der-fisico.dot']
        self.assertIn('// bookings_booking.space_id -> schedule_space (0,n)/(1,1)', content)
        self.assertIn('// schedule_allocation.space_id -> schedule_space (0,n)/(0,1)', content)
        self.assertIn('// bookings_booking.request_id -> bookings_bookingrequest (0,1)/(1,1)', content)

    def test_restrictions_list_constraints_as_sql(self):
        content = export()['restricoes.md']
        self.assertIn('EXCLUDE USING GIST', content)
        self.assertIn('WHERE "status" = \'A_ENVIAR\'', content)
        self.assertNotIn(' object at 0x', content)

    def test_output_is_deterministic(self):
        self.assertEqual(export(), export())
