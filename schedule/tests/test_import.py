"""Fluxo da importação de ensalamento pela máquina de estados do app `imports`.

A planilha destes testes é montada com a mesma estrutura da planilha real: linha de título
do curso, linha de cabeçalho por bloco de dia, coluna do dia, coluna do horário com as
linhas de intervalo e de almoço, colunas de turma e a aba de validação de dados com as duas
listas. O arquivo real é usado nos testes que conferem o comportamento diante dele.
"""

import io

from django.conf import settings
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from imports.forms import ImportUploadForm
from imports.models import Import
from schedule.imports import SpaceAllocationImport, concluded_message
from schedule.models import (
    Allocation,
    ClassGroup,
    Course,
    Origin,
    Semester,
    Space,
    Stage,
    Subject,
    Teacher,
    TimeSlot,
    Weekday,
)
from schedule.sheets import CATALOG_SHEET, SECONDARY_SHEET, UNDERGRADUATE_SHEET

SPREADSHEET = settings.BASE_DIR / 'sources' / 'planilha_example.xlsx'
CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

TEACHERS = ['Viviane', 'Elza', 'Eduardo Garrido', 'Thaís Rios', 'Gera Jr.', 'Érica']
SPACES = ['(1/13)', '(2/6)', '(HV 3)', 'Lab. de Madeira']
UNDERGRADUATE_SLOTS = ['07:20 - 08:10', '08:10 - 09:00', 'INTERVALO', '09:20 - 10:10']
SECONDARY_SLOTS = ['07:20 - 08:10', 'ALMOÇO', '13:20 - 14:10']


def grid(sheet, banner, headers, days, activities):
    """Monta uma aba de horário com blocos de dia, como na planilha real."""
    if banner:
        sheet['C1'] = banner
        sheet.merge_cells(start_row=1, start_column=3, end_row=1, end_column=2 + len(headers))
    row = 2
    for day, slots in days:
        sheet.cell(row, 1, 'DIA')
        sheet.cell(row, 2, 'HORÁRIO')
        for position, header in enumerate(headers):
            sheet.cell(row, 3 + position, header)
        row += 1
        for slot in slots:
            if slot == slots[0]:
                sheet.cell(row, 1, day)
            sheet.cell(row, 2, slot)
            for position in range(len(headers)):
                content = activities.get((day, slot, position))
                if content is not None:
                    sheet.cell(row, 3 + position, content)
            row += 1
    sheet.cell(row, 1, 'DIA')
    sheet.cell(row, 2, 'HORÁRIO')


def workbook_file(undergraduate=None, secondary=None, teachers=None, spaces=None, name='ensalamento.xlsx'):
    book = Workbook()
    book.remove(book.active)
    grid(
        book.create_sheet(UNDERGRADUATE_SHEET),
        'BACHARELADO EM ENGENHARIA DE TESTE',
        ['2º PERÍODO\nEng. Teste', '4º PERÍODO\nEng. Teste'],
        [('SEGUNDA ', UNDERGRADUATE_SLOTS), ('TERÇA', UNDERGRADUATE_SLOTS)],
        undergraduate if undergraduate is not None else {
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
        },
    )
    grid(
        book.create_sheet(SECONDARY_SHEET),
        'AGROINDÚSTRIA',
        ['1º ANO A\nAgroindústria'],
        [('SEGUNDA-FEIRA', SECONDARY_SLOTS)],
        secondary if secondary is not None else {
            ('SEGUNDA-FEIRA', '13:20 - 14:10', 0): 'Biologia (Érica) (HV 3)',
        },
    )
    catalog_sheet = book.create_sheet(CATALOG_SHEET)
    catalog_sheet['A1'] = 'Disciplina (Professor)'
    catalog_sheet['B1'] = 'Salas Disponíveis'
    for position, teacher in enumerate(teachers if teachers is not None else TEACHERS, start=2):
        catalog_sheet.cell(position, 1, teacher)
    for position, space in enumerate(spaces if spaces is not None else SPACES, start=2):
        catalog_sheet.cell(position, 2, space)
    stream = io.BytesIO()
    book.save(stream)
    return SimpleUploadedFile(name, stream.getvalue(), content_type=CONTENT_TYPE)


class ImportTestCase(TestCase):
    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = SpaceAllocationImport()

    def preview(self, uploaded=None, semester='2026/1'):
        form = ImportUploadForm(
            data={'own_semestre': semester},
            files={'file': uploaded if uploaded is not None else workbook_file()},
            definition=self.definition,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return Import.objects.preview(
            self.definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, self.executor,
        )

    def conclude(self, uploaded=None, semester='2026/1'):
        importation = self.preview(uploaded, semester)
        self.assertEqual(importation.status, Import.Status.VALIDATED, self.errors_of(importation))
        self.assertTrue(importation.confirm(self.definition, self.executor))
        return importation

    def errors_of(self, importation):
        return [
            (row.line_number, row.values.get('Célula'), row.errors)
            for row in importation.rows.all()
            if row.errors
        ]

    def allocation(self):
        return Allocation.objects.get(subject__name='QUÍMICA ORGÂNICA', time_slot__start_time='07:20')


class PreviewTests(ImportTestCase):
    def test_preview_plans_everything_and_changes_nothing(self):
        importation = self.preview()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(importation.rows.count(), len(TEACHERS) + len(SPACES) + 4)
        self.assertEqual(importation.summary()['create'], len(TEACHERS) + len(SPACES) + 4)
        for model in (Semester, Space, Teacher, Course, Subject, ClassGroup, TimeSlot, Allocation):
            self.assertFalse(model.objects.exists(), model.__name__)

    def test_preview_records_the_semester_in_every_row(self):
        importation = self.preview()
        self.assertEqual({row.values['Semestre'] for row in importation.rows.all()}, {'2026/1'})

    def test_catalog_rows_come_first_grouped_by_kind(self):
        rows = list(self.preview().rows.order_by('line_number'))
        kinds = [row.values['Tipo'] for row in rows]
        self.assertEqual(kinds[:len(SPACES)], ['SALA'] * len(SPACES))
        self.assertEqual(kinds[len(SPACES):len(SPACES) + len(TEACHERS)], ['DOCENTE'] * len(TEACHERS))
        self.assertEqual(set(kinds[len(SPACES) + len(TEACHERS):]), {'ATIVIDADE'})

    def test_catalog_row_keeps_the_raw_value_and_plans_the_clean_name(self):
        rows = list(self.preview().rows.order_by('line_number'))
        space_row = rows[0]
        self.assertEqual(space_row.values['Nome'], '(1/13)')
        self.assertEqual(space_row.values['Célula'], f'{CATALOG_SHEET}!B2')
        self.assertEqual(space_row.changes['name'], [None, '1/13'])
        teacher_row = next(row for row in rows if row.values['Tipo'] == 'DOCENTE')
        self.assertEqual(teacher_row.values['Nome'], 'Viviane')
        self.assertEqual(teacher_row.values['Célula'], f'{CATALOG_SHEET}!A2')

    def test_activity_row_keeps_the_values_of_the_spreadsheet(self):
        rows = list(self.preview().rows.order_by('line_number'))
        activity = next(row for row in rows if row.values['Célula'] == f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(activity.values['Dia'], 'SEGUNDA ')
        self.assertEqual(activity.values['Horário'], '07:20 - 08:10')
        self.assertEqual(activity.values['Turma'], '2º PERÍODO\nEng. Teste')
        self.assertEqual(activity.values['Curso'], 'BACHARELADO EM ENGENHARIA DE TESTE')
        self.assertEqual(activity.values['Atividade'], 'QUÍMICA ORGÂNICA (Elza) (1/13)')
        self.assertEqual(activity.changes, {'space': [None, '1/13'], 'teachers': [None, ['Elza']]})

    def test_file_without_the_catalog_sheet_is_refused(self):
        book = Workbook()
        book.remove(book.active)
        grid(book.create_sheet(UNDERGRADUATE_SHEET), 'CURSO', ['2º PERÍODO\nX'], [('SEGUNDA', ['07:20 - 08:10'])], {})
        grid(book.create_sheet(SECONDARY_SHEET), 'CURSO', ['1º ANO A\nX'], [('SEGUNDA', ['07:20 - 08:10'])], {})
        stream = io.BytesIO()
        book.save(stream)
        uploaded = SimpleUploadedFile('sem_catalogo.xlsx', stream.getvalue(), content_type=CONTENT_TYPE)
        form = ImportUploadForm(data={'own_semestre': '2026/1'}, files={'file': uploaded}, definition=self.definition)
        self.assertFalse(form.is_valid())
        self.assertIn(CATALOG_SHEET, form.errors['file'][0])
        self.assertFalse(Import.objects.exists())

    def test_empty_catalog_is_refused(self):
        form = ImportUploadForm(
            data={'own_semestre': '2026/1'},
            files={'file': workbook_file(teachers=[], spaces=[])},
            definition=self.definition,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('está vazia', form.errors['file'][0])

    def test_semester_is_required_in_the_upload(self):
        form = ImportUploadForm(data={}, files={'file': workbook_file()}, definition=self.definition)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['own_semestre'], ['Informe o semestre da planilha.'])
        self.assertFalse(Import.objects.exists())

    def test_semester_outside_the_format_is_refused_in_the_upload(self):
        form = ImportUploadForm(
            data={'own_semestre': '2026'}, files={'file': workbook_file()}, definition=self.definition,
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['own_semestre'], ['Informe o semestre no formato 2026/1.'])

    def test_unknown_teacher_is_an_error_of_the_activity_row(self):
        uploaded = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'Física (Agnaldo) (1/13)',
        })
        importation = self.preview(uploaded)
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(row.errors[0]['column'], 'Atividade')
        self.assertEqual(row.errors[0]['code'], 'docente_desconhecido')
        self.assertFalse(Teacher.objects.filter(name='Agnaldo').exists())

    def test_unknown_space_is_an_error_of_the_activity_row(self):
        uploaded = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'Física (Viviane) (Zoo I)',
        })
        importation = self.preview(uploaded)
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(row.errors[0]['code'], 'sala_desconhecida')


class ConfirmationTests(ImportTestCase):
    def test_confirmation_creates_the_semester_and_the_entities(self):
        self.conclude()
        self.assertEqual(list(Semester.objects.values_list('code', flat=True)), ['2026/1'])
        self.assertEqual(Teacher.objects.count(), len(TEACHERS))
        self.assertEqual(Space.objects.count(), len(SPACES))
        self.assertEqual(sorted(Space.objects.values_list('name', flat=True)), ['1/13', '2/6', 'HV 3', 'Lab. de Madeira'])
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(Subject.objects.count(), 3)
        self.assertEqual(ClassGroup.objects.count(), 3)
        self.assertEqual(Allocation.objects.count(), 4)

    def test_allocation_of_a_consecutive_block_is_not_merged(self):
        self.conclude()
        chemistry = Allocation.objects.filter(subject__name='QUÍMICA ORGÂNICA').order_by('time_slot__start_time')
        self.assertEqual(chemistry.count(), 2)
        self.assertEqual(
            [(str(item.time_slot), item.space.name) for item in chemistry],
            [('07:20 - 08:10', '1/13'), ('08:10 - 09:00', '1/13')],
        )

    def test_allocation_keeps_the_details_of_the_activity(self):
        self.conclude()
        allocation = self.allocation()
        self.assertEqual(allocation.semester.code, '2026/1')
        self.assertEqual(allocation.class_group.label, '2º PERÍODO')
        self.assertEqual(allocation.class_group.course.name, 'BACHARELADO EM ENGENHARIA DE TESTE')
        self.assertEqual(allocation.class_group.course.stage, Stage.UNDERGRADUATE)
        self.assertEqual(allocation.weekday, Weekday.MONDAY)
        self.assertEqual(allocation.space.name, '1/13')
        self.assertEqual([teacher.name for teacher in allocation.teachers.all()], ['Elza'])
        self.assertEqual(allocation.origin, Origin.IMPORTED)

    def test_secondary_sheet_gives_its_own_stage(self):
        self.conclude()
        group = ClassGroup.objects.get(label='1º ANO A')
        self.assertEqual(group.course.name, 'AGROINDÚSTRIA')
        self.assertEqual(group.course.stage, Stage.SECONDARY)
        self.assertEqual(group.allocations.count(), 1)

    def test_catalog_value_without_activity_becomes_a_record(self):
        self.conclude()
        self.assertTrue(Space.objects.filter(name='Lab. de Madeira').exists())
        self.assertFalse(Allocation.objects.filter(space__name='Lab. de Madeira').exists())
        self.assertTrue(Teacher.objects.filter(name='Gera Jr.').exists())

    def test_repeated_catalog_value_becomes_one_record(self):
        uploaded = workbook_file(teachers=['Viviane', 'Elza', 'Érica', 'viviane'], spaces=['(1/13)', '(2/6)', '(HV 3)'])
        importation = self.conclude(uploaded)
        self.assertEqual(Teacher.objects.filter(name__iexact='viviane').count(), 1)
        self.assertEqual(Teacher.objects.count(), 3)
        repeated = importation.rows.get(values__Nome='viviane')
        first = importation.rows.get(values__Nome='Viviane')
        self.assertEqual((first.action, repeated.action), ('create', 'unchanged'))
        self.assertIsNone(repeated.target)

    def test_space_of_another_import_outside_the_list_is_not_accepted(self):
        self.conclude()
        fewer = workbook_file(
            spaces=['(1/13)', '(2/6)'],
            secondary={('SEGUNDA-FEIRA', '13:20 - 14:10', 0): 'Biologia (Érica) (HV 3)'},
        )
        importation = self.preview(fewer)
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        row = importation.rows.get(values__Célula=f'{SECONDARY_SHEET}!C5')
        self.assertEqual(row.errors[0]['code'], 'sala_desconhecida')
        self.assertTrue(Space.objects.filter(name='HV 3').exists())

    def test_concluded_message_has_the_totals(self):
        importation = self.conclude()
        self.assertEqual(
            concluded_message(importation.summary()),
            f'Importação do ensalamento concluída. {len(TEACHERS) + len(SPACES) + 4} registros cadastrados.',
        )


class ReimportTests(ImportTestCase):
    def test_reimport_without_changes_leaves_everything_unchanged(self):
        self.conclude()
        counts = {model: model.objects.count() for model in (Space, Teacher, Course, Subject, ClassGroup, Allocation)}
        importation = self.conclude()
        summary = importation.summary()
        self.assertEqual(summary['create'], 0)
        self.assertEqual(summary['update'], 0)
        self.assertEqual(summary['unchanged'], importation.rows.count())
        for model, count in counts.items():
            self.assertEqual(model.objects.count(), count, model.__name__)

    def test_allocation_that_changed_space_is_updated(self):
        self.conclude()
        changed = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (2/6)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
        })
        importation = self.preview(changed)
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual((row.action, row.changes), ('update', {'space': ['1/13', '2/6']}))
        self.assertEqual(self.allocation().space.name, '1/13')
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertEqual(self.allocation().space.name, '2/6')
        self.assertEqual(Allocation.objects.count(), 4)

    def test_allocation_that_changed_teachers_is_updated(self):
        self.conclude()
        changed = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza/ Viviane) (1/13)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
        })
        importation = self.preview(changed)
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual((row.action, row.changes), ('update', {'teachers': [['Elza'], ['Elza', 'Viviane']]}))
        importation.confirm(self.definition, self.executor)
        self.assertEqual(
            sorted(teacher.name for teacher in self.allocation().teachers.all()), ['Elza', 'Viviane'],
        )

    def test_allocation_missing_from_the_new_file_is_preserved(self):
        self.conclude()
        without_calculus = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
        })
        importation = self.conclude(without_calculus)
        self.assertEqual(Allocation.objects.count(), 4)
        self.assertTrue(Allocation.objects.filter(subject__name='Cálculo III').exists())
        self.assertEqual([row.action for row in importation.rows.all() if row.action == 'delete'], [])

    def test_new_activity_is_added_to_a_semester_already_imported(self):
        self.conclude()
        with_more = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
            ('TERÇA', '07:20 - 08:10', 0): 'Biologia (Érica) (1/13)',
        })
        importation = self.conclude(with_more)
        self.assertEqual(importation.summary()['create'], 1)
        self.assertEqual(Allocation.objects.count(), 5)

    def test_manual_allocation_is_never_touched(self):
        self.conclude()
        semester = Semester.objects.get(code='2026/1')
        group = ClassGroup.objects.get(label='2º PERÍODO')
        subject, _ = Subject.objects.resolve('Reunião')
        slot = TimeSlot.objects.get(start_time='07:20')
        manual = Allocation.objects.create(
            semester=semester,
            class_group=group,
            subject=subject,
            weekday=Weekday.FRIDAY,
            time_slot=slot,
            origin=Origin.MANUAL,
        )
        self.conclude()
        manual.refresh_from_db()
        self.assertEqual(manual.origin, Origin.MANUAL)
        self.assertTrue(Allocation.objects.filter(pk=manual.pk).exists())

    def test_catalog_value_missing_from_the_new_file_is_preserved(self):
        self.conclude()
        fewer = workbook_file(spaces=['(1/13)', '(2/6)', '(HV 3)'])
        self.conclude(fewer)
        self.assertTrue(Space.objects.filter(name='Lab. de Madeira').exists())

    def test_another_semester_is_untouched(self):
        self.conclude()
        first = sorted(Allocation.objects.filter(semester__code='2026/1').values_list('pk', flat=True))
        self.conclude(semester='2026/2')
        self.assertEqual(
            sorted(Allocation.objects.filter(semester__code='2026/1').values_list('pk', flat=True)), first,
        )
        self.assertEqual(Allocation.objects.filter(semester__code='2026/2').count(), 4)
        self.assertEqual(TimeSlot.objects.filter(semester__code='2026/2').count(), 4)

    def test_the_same_activity_twice_is_a_duplicate_error(self):
        uploaded = workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13) / QUÍMICA ORGÂNICA (Elza) (2/6)',
        })
        importation = self.preview(uploaded)
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        errors = [row.errors for row in importation.rows.all() if row.errors]
        self.assertEqual(len(errors), 2)
        self.assertEqual({found[0]['code'] for found in errors}, {'duplicate'})
        self.assertIn(f'{UNDERGRADUATE_SHEET}!C3#1', errors[0][0]['message'])
        self.assertIn(f'{UNDERGRADUATE_SHEET}!C3#2', errors[0][0]['message'])
        self.assertEqual(Allocation.objects.count(), 0)


class DivergenceTests(ImportTestCase):
    def test_data_changed_after_the_preview_gives_a_new_plan(self):
        importation = self.preview()
        Space.objects.resolve('1/13')
        self.assertFalse(importation.confirm(self.definition, self.executor))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(importation.revalidation_count, 1)
        self.assertEqual(Allocation.objects.count(), 0)

    def test_confirmation_uses_the_recorded_semester(self):
        importation = self.preview(semester='2027/2')
        self.assertTrue(importation.confirm(self.definition, self.executor))
        self.assertEqual(list(Semester.objects.values_list('code', flat=True)), ['2027/2'])
        self.assertEqual(Allocation.objects.filter(semester__code='2027/2').count(), 4)


class AuditTests(ImportTestCase):
    def test_summary_of_the_confirmation(self):
        importation = self.conclude()
        record = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk')
        self.assertEqual(record.resource, catalog.SPACE_ALLOCATION_IMPORT)
        self.assertEqual(str(record.resource_id), str(importation.pk))
        self.assertEqual(
            record.metadata,
            {
                'arquivo': 'ensalamento.xlsx',
                'situacao': 'CONCLUIDA',
                'cadastrados': len(TEACHERS) + len(SPACES) + 4,
                'atualizados': 0,
                'sem_alteracao': 0,
                'com_erro': 0,
                'semestre': '2026/1',
            },
        )

    def test_no_record_for_each_entity(self):
        self.conclude()
        self.assertEqual(
            sorted(set(AuditLog.objects.values_list('resource', flat=True))),
            [catalog.SPACE_ALLOCATION_IMPORT],
        )

    def test_preview_records_only_the_preview(self):
        self.preview()
        self.assertEqual(
            list(AuditLog.objects.values_list('action', 'resource')),
            [(catalog.CREATE, catalog.SPACE_ALLOCATION_IMPORT)],
        )

    def test_summary_of_a_reimport_counts_the_unchanged(self):
        self.conclude()
        importation = self.conclude()
        record = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk')
        self.assertEqual(record.metadata['sem_alteracao'], importation.rows.count())
        self.assertEqual(record.metadata['cadastrados'], 0)


class RealSpreadsheetTests(ImportTestCase):
    def uploaded(self):
        return SimpleUploadedFile(
            'planilha_example.xlsx', SPREADSHEET.read_bytes(), content_type=CONTENT_TYPE,
        )

    def test_real_file_is_read_and_previewed(self):
        importation = self.preview(self.uploaded())
        self.assertEqual(importation.rows.count(), 1706)
        self.assertEqual(importation.file_name, 'planilha_example.xlsx')
        self.assertFalse(Allocation.objects.exists())

    def test_real_file_has_the_activities_that_the_campus_needs_to_fix(self):
        importation = self.preview(self.uploaded())
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        self.assertEqual(importation.summary()['errors'], 147)

    def test_real_file_plans_the_catalogs_and_most_activities(self):
        summary = self.preview(self.uploaded()).summary()
        self.assertEqual(summary['create'], 1706 - 147 - summary['unchanged'])
        self.assertEqual(summary['update'], 0)

    def test_real_file_cannot_be_confirmed_while_it_has_errors(self):
        importation = self.preview(self.uploaded())
        with self.assertRaises(Exception):
            importation.confirm(self.definition, self.executor)
        self.assertFalse(Allocation.objects.exists())
