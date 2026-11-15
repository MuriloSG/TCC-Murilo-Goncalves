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
            crossing_lines,
            overlaps,
            physical_labels,
            physical_layout,
            project_models,
            segment_hits_rect,
        )

        tables, links = physical_layout(project_models())
        crossed = [
            (f'{links[a]["child"].name}.{links[a]["field"].column}', f'{links[b]["child"].name}.{links[b]["field"].column}')
            for a, b in crossing_lines(links)
        ]
        self.assertEqual(crossed, [])
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

    def test_physical_lines_have_no_small_steps_or_detours(self):
        from accounts.management.commands.export_er_diagram import MIN_JOG, PHYSICAL_COLUMNS, physical_layout, project_models

        column_of = {name: index for index, column in enumerate(PHYSICAL_COLUMNS) for name in column}
        _, links = physical_layout(project_models())
        for link in links:
            name = f'{link["child"].name}.{link["field"].column}'
            points = link['points']
            inner = list(zip(points, points[1:]))[1:-1]  # o primeiro e o último trecho são os tocos junto das tabelas
            steps = [round(abs(b[0] - a[0]) + abs(b[1] - a[1]), 3) for a, b in inner]
            self.assertTrue(all(step >= MIN_JOG for step in steps), f'{name}: {steps}')
            if column_of[link['child'].name] != column_of[link['parent'].name]:
                # Entre colunas, a linha vai direto: no máximo uma subida ou descida e nenhuma volta.
                length = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(points, points[1:]))
                direct = abs(points[-1][0] - points[0][0]) + abs(points[-1][1] - points[0][1])
                self.assertLessEqual(len(points), 4, name)
                self.assertAlmostEqual(length, direct, places=6, msg=name)

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
