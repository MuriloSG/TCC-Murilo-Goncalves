"""Grade da semana de uma sala, montada das linhas de uma importação de ensalamento."""

from datetime import date

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import User
from imports.forms import ImportUploadForm
from imports.models import Import
from schedule.imports import SpaceAllocationImport
from schedule.models import Allocation, ClassGroup, Course, Semester, Space, Stage, Subject, Teacher, TimeSlot
from schedule.tests.test_import import CONTENT_TYPE, workbook_file
from schedule.timetable import CLASH, CONTINUED, ERROR, JOINT, SINGLE, room_week_from_import

SOURCES = settings.BASE_DIR / 'sources'
FRIDAY = date(2026, 9, 25)
SATURDAY = date(2026, 9, 26)

ACTIVITIES = {
    ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
    ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
    ('SEGUNDA ', '09:20 - 10:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
    ('SEGUNDA ', '07:20 - 08:10', 1): 'Estágio (Elza) (Sala Inexistente)',
    ('TERÇA', '07:20 - 08:10', 0): 'Cálculo III (Viviane) (2/6)',
    ('TERÇA', '07:20 - 08:10', 1): 'Cálculo III (Viviane) (2/6)',
    ('TERÇA', '08:10 - 09:00', 0): 'Física (Viviane) (HV 3)',
    ('TERÇA', '08:10 - 09:00', 1): 'Química (Elza) (HV 3)',
    ('TERÇA', '09:20 - 10:10', 1): 'Biologia (Fulano) (1/13)',
}


def preview(uploaded, executor, semester='2026/1'):
    definition = SpaceAllocationImport()
    form = ImportUploadForm(data={'own_semestre': semester}, files={'file': uploaded}, definition=definition)
    assert form.is_valid(), form.errors
    return Import.objects.preview(definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, executor)


def real_file(name):
    return SimpleUploadedFile(name, (SOURCES / name).read_bytes(), content_type=CONTENT_TYPE)


def line_of(importation, cell):
    return importation.rows.get(values__Célula=cell).line_number


class BuiltSpreadsheetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        cls.importation = preview(workbook_file(undergraduate=ACTIVITIES), executor)

    def week(self, space=None, today=FRIDAY):
        return room_week_from_import(self.importation, space, today)

    def test_spaces_follow_the_spreadsheet_list(self):
        week = self.week()
        self.assertEqual([option.name for option in week.spaces], ['1/13', '2/6', 'HV 3', 'Lab. de Madeira'])

    def test_first_space_is_the_default(self):
        self.assertEqual(self.week().space, '1/13')

    def test_unknown_space_falls_back_to_the_default(self):
        self.assertEqual(self.week('Sala 99').space, '1/13')

    def test_space_is_chosen_without_case(self):
        self.assertEqual(self.week('lab. de madeira').space, 'Lab. de Madeira')

    def test_rows_are_the_slots_of_both_sheets_in_order(self):
        starts = [row.start.strftime('%H:%M') for row in self.week().rows]
        self.assertEqual(starts, ['07:20', '08:10', '09:20', '13:20'])

    def test_consecutive_slots_become_one_block(self):
        monday = self.week().days[0].cells
        self.assertEqual(monday[0].span, 2)
        self.assertEqual(monday[0].end.strftime('%H:%M'), '09:00')
        self.assertIs(monday[1], CONTINUED)

    def test_block_does_not_cross_the_break(self):
        monday = self.week().days[0].cells
        self.assertEqual(monday[2].span, 1)
        self.assertEqual(monday[2].entries[0].subject, 'QUÍMICA ORGÂNICA')

    def test_entry_has_subject_group_course_teachers_and_stage(self):
        entry = self.week().days[0].cells[0].entries[0]
        self.assertEqual(
            (entry.subject, entry.class_group, entry.course, entry.teachers, entry.stage),
            ('QUÍMICA ORGÂNICA', '2º PERÍODO', 'BACHARELADO EM ENGENHARIA DE TESTE', ('Elza',), Stage.UNDERGRADUATE),
        )

    def test_block_keeps_the_lines_of_every_slot(self):
        cell = self.week().days[0].cells[0]
        expected = sorted([
            line_of(self.importation, f'Horário - Graduação!C{row}') for row in (3, 4)
        ])
        self.assertEqual(cell.lines, expected)

    def test_same_subject_and_teachers_are_joint_groups(self):
        cell = self.week('2/6').days[1].cells[0]
        self.assertEqual((cell.kind, cell.group_count), (JOINT, 2))

    def test_different_subjects_are_a_clash(self):
        week = self.week('HV 3')
        self.assertEqual(week.days[1].cells[1].kind, CLASH)
        self.assertEqual(week.clash_count, 1)
        self.assertEqual({option.name: option.has_clash for option in week.spaces}['HV 3'], True)
        self.assertEqual({option.name: option.has_clash for option in week.spaces}['2/6'], False)

    def test_one_group_is_single(self):
        self.assertEqual(self.week().days[0].cells[0].kind, SINGLE)

    def test_secondary_activity_has_its_stage(self):
        entry = self.week('HV 3').days[0].cells[3].entries[0]
        self.assertEqual((entry.subject, entry.stage), ('Biologia', Stage.SECONDARY))

    def test_error_entry_keeps_the_spreadsheet_text_and_line(self):
        cell = self.week().days[1].cells[2]
        entry = cell.entries[0]
        self.assertEqual((entry.state, entry.raw_text), (ERROR, 'Biologia (Fulano) (1/13)'))
        self.assertEqual(cell.lines, [line_of(self.importation, 'Horário - Graduação!D11')])
        self.assertIn('Fulano', cell.first_message)

    def test_counts_of_the_room(self):
        week = self.week()
        self.assertEqual((week.occupied, week.available), (4, 16))
        self.assertEqual(week.error_count, 1)

    def test_error_without_space_is_counted_outside(self):
        self.assertEqual(self.week().outside_error_count, 1)

    def test_room_without_activity(self):
        week = self.week('Lab. de Madeira')
        self.assertEqual((week.occupied, week.available, week.clash_count), (0, 20, 0))
        self.assertTrue(all(cell is None for day in week.days for cell in day.cells))

    def test_today_is_marked(self):
        self.assertEqual([day.is_today for day in self.week().days], [False, False, False, False, True])

    def test_weekend_has_no_today(self):
        self.assertFalse(any(day.is_today for day in self.week(today=SATURDAY).days))

    def test_day_labels(self):
        self.assertEqual([day.label for day in self.week().days], ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'])

    def test_reading_uses_one_query(self):
        with self.assertNumQueries(1):
            room_week_from_import(self.importation, 'HV 3', FRIDAY)

    def test_reading_writes_nothing(self):
        models = (Semester, Space, Teacher, Course, ClassGroup, Subject, TimeSlot, Allocation)
        before = [model.objects.count() for model in models]
        rows_before = list(self.importation.rows.values_list('line_number', 'action', 'errors'))
        for space in ('1/13', '2/6', 'HV 3', 'Lab. de Madeira'):
            room_week_from_import(self.importation, space, FRIDAY)
        self.assertEqual([model.objects.count() for model in models], before)
        self.assertEqual(list(self.importation.rows.values_list('line_number', 'action', 'errors')), rows_before)


class RealSpreadsheetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        cls.corrected = preview(real_file('planilha_example_corrigida.xlsx'), executor)
        cls.original = preview(real_file('planilha_example.xlsx'), executor)

    def test_corrected_spreadsheet_has_no_error(self):
        self.assertEqual(self.corrected.status, Import.Status.VALIDATED)

    def test_default_room_is_the_first_of_the_list(self):
        week = room_week_from_import(self.corrected, None, FRIDAY)
        self.assertEqual(week.space, '1/10')
        self.assertEqual(week.occupied, 28)

    def test_room_with_joint_groups_and_a_clash(self):
        week = room_week_from_import(self.corrected, '1/11', FRIDAY)
        kinds = {cell.kind for day in week.days for cell in day.cells if cell and cell is not CONTINUED}
        self.assertIn(JOINT, kinds)
        self.assertIn(CLASH, kinds)

    def test_nine_rooms_have_a_clash(self):
        week = room_week_from_import(self.corrected, None, FRIDAY)
        self.assertEqual(sum(option.has_clash for option in week.spaces), 9)

    def test_error_card_shows_the_spreadsheet_text(self):
        week = room_week_from_import(self.original, 'HV 2', FRIDAY)
        entries = [entry for day in week.days for cell in day.cells if cell and cell is not CONTINUED for entry in cell.entries]
        wrong = [entry for entry in entries if entry.raw_text.startswith('Deontologia Veterinária')]
        self.assertTrue(wrong)
        self.assertTrue(all(entry.state == ERROR for entry in wrong))
        self.assertTrue(all(entry.lines for entry in wrong))
