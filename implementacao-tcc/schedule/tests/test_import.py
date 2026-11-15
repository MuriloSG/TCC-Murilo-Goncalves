"""Fluxo da importação de ensalamento, com planilhas montadas na estrutura da planilha real."""

import io
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from accounts import permissions
from accounts.models import Role, User
from accounts.tests.roles import requester_role
from audit import catalog
from audit.models import AuditLog
from bookings.models import Booking, BookingRequest
from config.testing import IsolatedCasesMixin
from imports.forms import ImportUploadForm
from imports.models import Import
from imports.tests.worker import confirm, preview, refresh
from outbox.models import OutboxEntry
from schedule.imports import COURSE_STAGE_KEPT, RECURRENCE_CHANGED, SpaceAllocationImport, concluded_message
from schedule.models import (
    Allocation,
    ClassGroup,
    ClassOffering,
    Course,
    Origin,
    Semester,
    Space,
    SpaceName,
    Stage,
    Subject,
    Teacher,
    TeachingAssignment,
    TimeSlot,
    Weekday,
    teacher_of,
)
from schedule.sheets import CATALOG_SHEET, SECONDARY_SHEET, UNDERGRADUATE_SHEET, USER_COLUMNS, USERS_SHEET

FIXTURES = Path(__file__).parent / 'fixtures'
SPREADSHEET = FIXTURES / 'planilha_example.xlsx'
SUGGESTED_SPREADSHEET = FIXTURES / 'planilha_example_sugerida.xlsx'
CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

TEACHERS = ['Viviane', 'Elza', 'Eduardo Garrido', 'Thaís Rios', 'Gera Jr.', 'Érica']
SPACES = ['(1/13)', '(2/6)', '(HV 3)', 'Lab. de Madeira']
UNDERGRADUATE_SLOTS = ['07:20 - 08:10', '08:10 - 09:00', 'INTERVALO', '09:20 - 10:10']
SECONDARY_SLOTS = ['07:20 - 08:10', 'ALMOÇO', '13:20 - 14:10']
SPACE_NAMES = ['1/13', '2/6', 'HV 3', 'Lab. de Madeira']


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


def workbook_file(
    undergraduate=None, secondary=None, teachers=None, spaces=None, name='ensalamento.xlsx',
    users=None, users_title=USERS_SHEET, users_header=USER_COLUMNS,
):
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
    if users is not None:
        users_sheet = book.create_sheet(users_title)
        users_sheet.append(list(users_header))
        for user in users:
            users_sheet.append(list(user))
    stream = io.BytesIO()
    book.save(stream)
    return SimpleUploadedFile(name, stream.getvalue(), content_type=CONTENT_TYPE)


PERIOD = {'own_início': '2026-08-03', 'own_fim': '2026-12-18'}


def space_manager(email='admin@ifnmg.edu.br', extra_permissions=()):
    """Usuário que importa o ensalamento e pode alterar o cadastro de espaços."""
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(
        code=code,
        name=code,
        permissions=[permissions.SPACE_ALLOCATION_IMPORT, *permissions.SPACE_PERMISSIONS, *extra_permissions],
    )
    return User.objects.register(email=email, name=code.capitalize(), role=role)


class ImportTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.executor = space_manager()
        self.definition = SpaceAllocationImport()

    def preview(self, uploaded=None, semester='2026/1', period=None):
        form = ImportUploadForm(
            data={'own_semestre': semester, **(PERIOD if period is None else period)},
            files={'file': uploaded if uploaded is not None else workbook_file()},
            definition=self.definition,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return preview(
            self.definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, self.executor,
        )

    def conclude(self, uploaded=None, semester='2026/1', period=None):
        importation = self.preview(uploaded, semester, period)
        self.assertEqual(importation.status, Import.Status.VALIDATED, self.errors_of(importation))
        self.assertTrue(confirm(importation, self.definition, self.executor))
        return importation

    def errors_of(self, importation):
        return [
            (row.line_number, row.values.get('Célula'), row.errors)
            for row in importation.rows.all()
            if row.errors
        ]

    def allocation(self):
        return Allocation.objects.get(subject__name='QUÍMICA ORGÂNICA', time_slot__start_time='07:20')


BLANK = {'own_início': '', 'own_fim': ''}
LATER = {'own_início': '2026-08-10', 'own_fim': '2026-12-18'}


def without_catalog():
    book = Workbook()
    book.remove(book.active)
    grid(book.create_sheet(UNDERGRADUATE_SHEET), 'CURSO', ['2º PERÍODO\nX'], [('SEGUNDA', ['07:20 - 08:10'])], {})
    grid(book.create_sheet(SECONDARY_SHEET), 'CURSO', ['1º ANO A\nX'], [('SEGUNDA', ['07:20 - 08:10'])], {})
    stream = io.BytesIO()
    book.save(stream)
    return SimpleUploadedFile('sem_catalogo.xlsx', stream.getvalue(), content_type=CONTENT_TYPE)


class PreviewTests(ImportTestCase):
    def test_preview_plans_everything_and_changes_nothing(self):
        importation = self.preview()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(importation.rows.count(), len(TEACHERS) + len(SPACES) + 4)
        self.assertEqual(importation.summary()['create'], len(TEACHERS) + len(SPACE_NAMES) + 4)
        unused = importation.rows.get(values__Nome='Lab. de Madeira')
        self.assertEqual((unused.action, unused.warnings), ('create', []))
        for model in (Semester, Space, Teacher, Course, Subject, ClassGroup, TimeSlot, Allocation, ClassOffering, TeachingAssignment):
            self.assertFalse(model.objects.exists(), model.__name__)

        rows = list(importation.rows.order_by('line_number'))
        space_row = rows[0]
        self.assertEqual(space_row.values['Nome'], '(1/13)')
        self.assertEqual(space_row.values['Célula'], f'{CATALOG_SHEET}!B2')
        self.assertEqual(space_row.changes['name'], [None, '1/13'])
        teacher_row = next(row for row in rows if row.values['Tipo'] == 'DOCENTE')
        self.assertEqual((teacher_row.values['Nome'], teacher_row.values['Célula']), ('Viviane', f'{CATALOG_SHEET}!A2'))
        activity = next(row for row in rows if row.values['Célula'] == f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(
            {key: activity.values[key] for key in ('Dia', 'Horário', 'Turma', 'Curso', 'Atividade')},
            {
                'Dia': 'SEGUNDA ',
                'Horário': '07:20 - 08:10',
                'Turma': '2º PERÍODO\nEng. Teste',
                'Curso': 'BACHARELADO EM ENGENHARIA DE TESTE',
                'Atividade': 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            },
        )
        self.assertEqual(activity.changes, {'space': [None, '1/13'], 'teachers': [None, ['Elza']]})

    def test_upload_form_refusals(self):
        cases = [
            ('sem a aba do catálogo', {'own_semestre': '2026/1', **PERIOD}, without_catalog(), 'file', CATALOG_SHEET),
            ('catálogo vazio', {'own_semestre': '2026/1', **PERIOD}, workbook_file(teachers=[], spaces=[]), 'file', 'está vazia'),
            ('sem semestre', {}, workbook_file(), 'own_semestre', 'Informe o semestre da planilha.'),
            ('semestre fora do formato', {'own_semestre': '2026'}, workbook_file(), 'own_semestre', 'Informe o semestre no formato 2026/1.'),
            (
                'primeira importação sem datas', {'own_semestre': '2026/1', **BLANK}, workbook_file(), 'own_início',
                'Informe o início e o fim do semestre, que ainda não tem período.',
            ),
        ]
        for label, data, uploaded, field, message in cases:
            with self.subTest(label):
                form = ImportUploadForm(data=data, files={'file': uploaded}, definition=self.definition)
                self.assertFalse(form.is_valid())
                self.assertIn(message, ' '.join(form.errors[field]))
        self.assertFalse(Import.objects.exists())
        self.assertFalse(Semester.objects.exists())

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


class ConfirmationTests(ImportTestCase):
    def test_confirmation_creates_the_semester_and_the_entities(self):
        self.conclude()
        self.assertEqual(list(Semester.objects.values_list('code', flat=True)), ['2026/1'])
        self.assertEqual(Teacher.objects.count(), len(TEACHERS))
        self.assertEqual(sorted(Space.objects.values_list('name', flat=True)), SPACE_NAMES)
        self.assertEqual(set(Space.objects.values_list('origin', flat=True)), {'PLANILHA'})
        self.assertEqual(
            (Course.objects.count(), Subject.objects.count(), ClassGroup.objects.count(), Allocation.objects.count()),
            (2, 3, 3, 4),
        )
        space = Space.objects.get(name='Lab. de Madeira')
        self.assertEqual((space.is_active, space.allocations.count()), (True, 0))
        self.assertTrue(Teacher.objects.filter(name='Gera Jr.').exists())

        allocation = self.allocation()
        self.assertEqual(allocation.semester.code, '2026/1')
        self.assertEqual(allocation.class_group.label, '2º PERÍODO')
        self.assertEqual(allocation.class_group.course.name, 'BACHARELADO EM ENGENHARIA DE TESTE')
        self.assertEqual(allocation.class_group.course.stage, Stage.UNDERGRADUATE)
        self.assertEqual(allocation.weekday, Weekday.MONDAY)
        self.assertEqual(allocation.space.name, '1/13')
        self.assertEqual([teacher.name for teacher in allocation.teachers.all()], ['Elza'])
        self.assertEqual(allocation.origin, Origin.IMPORTED)

        chemistry = Allocation.objects.filter(subject__name='QUÍMICA ORGÂNICA').order_by('time_slot__start_time')
        self.assertEqual(
            [(str(item.time_slot), item.space.name) for item in chemistry],
            [('07:20 - 08:10', '1/13'), ('08:10 - 09:00', '1/13')],
        )
        group = ClassGroup.objects.get(label='1º ANO A')
        self.assertEqual((group.course.name, group.course.stage), ('AGROINDÚSTRIA', Stage.SECONDARY))
        self.assertEqual(group.allocations.count(), 1)

    def test_repeated_catalog_value_becomes_one_record(self):
        uploaded = workbook_file(teachers=['Viviane', 'Elza', 'Érica', 'viviane'], spaces=['(1/13)', '(2/6)', '(HV 3)'])
        importation = self.conclude(uploaded)
        self.assertEqual(Teacher.objects.filter(name__iexact='viviane').count(), 1)
        self.assertEqual(Teacher.objects.count(), 3)
        repeated = importation.rows.get(values__Nome='viviane')
        first = importation.rows.get(values__Nome='Viviane')
        self.assertEqual((first.action, repeated.action), ('create', 'unchanged'))
        self.assertIsNone(repeated.target)


class ReimportTests(ImportTestCase):
    def test_reimport_keeps_what_left_the_file_and_adds_what_is_new(self):
        self.conclude()
        with self.case('aula fora do novo arquivo é mantida'):
            importation = self.conclude(workbook_file(undergraduate={
                ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
                ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            }))
            self.assertEqual(Allocation.objects.count(), 4)
            self.assertTrue(Allocation.objects.filter(subject__name='Cálculo III').exists())
            self.assertFalse(importation.rows.filter(action='delete').exists())
        with self.case('espaço fora do catálogo continua ativo e é reconhecido nas células'):
            importation = self.conclude(workbook_file(
                spaces=['(1/13)', '(2/6)'],
                secondary={('SEGUNDA-FEIRA', '13:20 - 14:10', 0): 'Biologia (Érica) (HV 3)'},
            ))
            row = importation.rows.get(values__Célula=f'{SECONDARY_SHEET}!C5')
            self.assertEqual((row.errors, row.pending, row.action), ([], [], 'unchanged'))
            self.assertTrue(Space.objects.get(name='HV 3').is_active)
        with self.case('aula nova entra no semestre já importado'):
            importation = self.conclude(workbook_file(undergraduate={
                ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
                ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
                ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
                ('TERÇA', '07:20 - 08:10', 0): 'Biologia (Érica) (1/13)',
            }))
            self.assertEqual(importation.summary()['create'], 1)
            self.assertEqual(Allocation.objects.count(), 5)

    def test_manual_allocation_is_never_touched(self):
        self.conclude()
        subject, _ = Subject.objects.resolve('Reunião')
        manual = Allocation.objects.create(
            semester=Semester.objects.get(code='2026/1'),
            class_group=ClassGroup.objects.get(label='2º PERÍODO'),
            subject=subject,
            weekday=Weekday.FRIDAY,
            time_slot=TimeSlot.objects.get(start_time='07:20'),
            origin=Origin.MANUAL,
        )
        self.conclude()
        manual.refresh_from_db()
        self.assertEqual(manual.origin, Origin.MANUAL)

    def test_another_semester_is_untouched(self):
        self.conclude()
        first = sorted(Allocation.objects.filter(semester__code='2026/1').values_list('pk', flat=True))
        self.conclude(semester='2026/2')
        self.assertEqual(
            sorted(Allocation.objects.filter(semester__code='2026/1').values_list('pk', flat=True)), first,
        )
        self.assertEqual(Allocation.objects.filter(semester__code='2026/2').count(), 4)
        self.assertEqual(TimeSlot.objects.filter(semester__code='2026/2').count(), 4)

    def test_lesson_changed_in_the_system_is_kept_and_its_row_warns(self):
        self.conclude()
        chemistry = Allocation.objects.filter(subject__name='QUÍMICA ORGÂNICA').order_by('time_slot__start_time')
        superadmin = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
        with patch('django.utils.timezone.localdate', return_value=date(2026, 9, 1)):
            Allocation.objects.change_recurrence(
                [allocation.pk for allocation in chemistry], date(2026, 10, 5), superadmin,
                Weekday.MONDAY, time(7, 20), Space.objects.get(name='2/6'), [Teacher.objects.get(name='Elza')],
            )
        versions = list(Allocation.objects.order_by('pk').values())
        importation = self.preview()
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(row.action, 'unchanged')
        self.assertEqual(row.warnings, [RECURRENCE_CHANGED])
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(list(Allocation.objects.order_by('pk').values()), versions)

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


class IdempotentReimportTests(ImportTestCase):
    """Reimportar reaproveita os registros pela identidade e não regrava o que não mudou."""

    MODELS = (Semester, Space, SpaceName, Teacher, Course, Subject, ClassGroup, TimeSlot, Allocation, ClassOffering, TeachingAssignment)

    def snapshot(self):
        """Linhas gravadas de cada modelo, com chaves e relacionamentos, e os docentes de cada aula."""
        rows = {model.__name__: list(model.objects.order_by('pk').values()) for model in self.MODELS}
        rows['Allocation.teachers'] = list(Allocation.teachers.through.objects.order_by('allocation_id', 'teacher_id').values_list('allocation_id', 'teacher_id'))
        return rows

    def changed(self):
        return workbook_file(undergraduate={
            ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Elza/ Viviane) (2/6)',
            ('SEGUNDA ', '08:10 - 09:00', 0): 'QUÍMICA ORGÂNICA (Elza) (1/13)',
            ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
        })

    def test_the_same_file_three_times_keeps_the_persisted_rows(self):
        self.conclude()
        first = self.snapshot()
        self.assertEqual(len(first['Allocation']), 4)
        for attempt in (2, 3):
            with self.subTest(attempt=attempt):
                summary = self.conclude().summary()
                self.assertEqual((summary['create'], summary['update']), (0, 0))
                self.assertEqual(self.snapshot(), first)

    def test_changed_space_and_teachers_update_the_same_lesson(self):
        self.conclude()
        before = self.snapshot()
        lesson = self.allocation()
        importation = self.preview(self.changed())
        row = importation.rows.get(values__Célula=f'{UNDERGRADUATE_SHEET}!C3')
        self.assertEqual(
            (row.action, row.changes),
            ('update', {'space': ['1/13', '2/6'], 'teachers': [['Elza'], ['Elza', 'Viviane']]}),
        )
        self.assertEqual(self.allocation().space.name, '1/13')
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual((importation.summary()['create'], importation.summary()['update']), (0, 1))
        after = self.snapshot()
        updated = self.allocation()
        self.assertEqual(updated.pk, lesson.pk)
        self.assertEqual(updated.space.name, '2/6')
        self.assertEqual(sorted(teacher.name for teacher in updated.teachers.all()), ['Elza', 'Viviane'])
        expected = [
            row | {'space_id': updated.space_id} if row['id'] == lesson.pk else row for row in before['Allocation']
        ]
        self.assertEqual(after['Allocation'], expected)
        viviane = Teacher.objects.get(name='Viviane').pk
        self.assertEqual(
            sorted(after['Allocation.teachers']), sorted(before['Allocation.teachers'] + [(lesson.pk, viviane)]),
        )
        for model in self.MODELS:
            if model not in (Allocation, ClassOffering, TeachingAssignment):
                with self.subTest(model=model.__name__):
                    self.assertEqual(after[model.__name__], before[model.__name__])
        self.assertEqual(self.conclude(self.changed()).summary()['update'], 0)
        self.assertEqual(self.snapshot(), after)

    def test_approved_booking_is_untouched_by_the_reimport(self):
        self.conclude()
        monday = date(2026, 8, 10)
        lesson = self.allocation()
        owner = User.objects.create_superadmin('agenda@ifnmg.edu.br', 'Agenda', 'Senha-forte-123')
        request = BookingRequest.objects.create(
            requested_by=owner, space=lesson.space, date=monday, start_time=time(7, 30), end_time=time(8, 0),
            description='Reunião aprovada antes da reimportação.', student_count=10,
            status=BookingRequest.Status.APPROVED, decided_by=owner,
        )
        booking = Booking.objects.book(request, lesson.space, monday, time(7, 30), time(8, 0), owner)
        requests = list(BookingRequest.objects.values())
        bookings = list(Booking.objects.values())
        for uploaded in (None, self.changed()):
            self.conclude(uploaded)
            with self.subTest(changed=uploaded is not None):
                self.assertEqual(list(BookingRequest.objects.values()), requests)
                self.assertEqual(list(Booking.objects.values()), bookings)
        booking.refresh_from_db()
        self.assertEqual((booking.request.status, booking.space_id), (BookingRequest.Status.APPROVED, lesson.space_id))


class DivergenceTests(ImportTestCase):
    def test_data_changed_after_the_preview_gives_a_new_plan(self):
        importation = self.preview()
        Space.objects.register('1/13')
        self.assertFalse(confirm(importation, self.definition, self.executor))
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(importation.revalidation_count, 1)
        self.assertEqual(Allocation.objects.count(), 0)
        self.assertEqual((ClassOffering.objects.count(), TeachingAssignment.objects.count()), (0, 0))

    def test_confirmation_uses_the_recorded_semester(self):
        importation = self.preview(semester='2027/2')
        self.assertTrue(confirm(importation, self.definition, self.executor))
        self.assertEqual(list(Semester.objects.values_list('code', flat=True)), ['2027/2'])
        self.assertEqual(Allocation.objects.filter(semester__code='2027/2').count(), 4)


UNDERGRADUATE_COURSE = 'BACHARELADO EM ENGENHARIA DE TESTE'


class RegisteredCourseTests(ImportTestCase):
    """Curso cadastrado pela tela antes da importação, reaproveitado pelo nome (`NamedManager.resolve`)."""

    def course_rows(self, importation):
        return list(importation.rows.filter(values__Curso=UNDERGRADUATE_COURSE))

    def test_registered_course_is_reused_by_the_normalized_name(self):
        with self.case('caixa e espaços diferentes reaproveitam o curso'):
            course = Course.objects.register('  bacharelado   em engenharia de teste ', Stage.UNDERGRADUATE)
            self.conclude()
            self.assertEqual(Course.objects.count(), 2)
            self.assertEqual(ClassGroup.objects.get(label='2º PERÍODO').course, course)
            course.refresh_from_db()
            self.assertEqual(course.name, 'bacharelado em engenharia de teste')
        with self.case('acentos diferentes dão outro curso'):
            Course.objects.register('AGROINDUSTRIA', Stage.SECONDARY)
            self.conclude()
            self.assertEqual(Course.objects.count(), 3)
            self.assertEqual(ClassGroup.objects.get(label='1º ANO A').course.name, 'AGROINDÚSTRIA')

    def test_registered_stage_is_kept_and_a_divergent_one_warns(self):
        with self.case('mesma etapa, sem aviso'):
            Course.objects.register(UNDERGRADUATE_COURSE, Stage.UNDERGRADUATE)
            importation = self.conclude()
            self.assertEqual([row.warnings for row in self.course_rows(importation)], [[]] * 3)
        with self.case('etapa divergente'):
            course = Course.objects.register(UNDERGRADUATE_COURSE, Stage.SECONDARY)
            importation = self.preview()
            self.assertEqual(importation.status, Import.Status.VALIDATED)
            rows = self.course_rows(importation)
            self.assertEqual([(row.warnings, row.action) for row in rows], [([COURSE_STAGE_KEPT[Stage.SECONDARY]], 'create')] * 3)
            self.assertTrue(confirm(importation, self.definition, self.executor))
            self.assertEqual(importation.revalidation_count, 0)
            self.assertEqual([row.warnings for row in self.course_rows(importation)], [[COURSE_STAGE_KEPT[Stage.SECONDARY]]] * 3)
            course.refresh_from_db()
            self.assertEqual(course.stage, Stage.SECONDARY)
            self.assertEqual(Allocation.objects.filter(class_group__course=course).count(), 3)
            self.assertEqual(
                self.definition.warning_labels[COURSE_STAGE_KEPT[Stage.SECONDARY]],
                'O curso está cadastrado como Ensino médio e a aba da planilha indica Graduação. A etapa cadastrada foi mantida.',
            )


class PeriodImportTests(ImportTestCase):
    def period(self, code='2026/1'):
        semester = Semester.objects.get(code=code)
        return semester.start_date, semester.end_date

    def last_summary(self):
        return AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata

    def test_first_import_sets_the_period_only_on_the_confirmation(self):
        self.preview()
        self.assertFalse(Semester.objects.filter(code='2026/1').exists())
        self.conclude()
        self.assertEqual(self.period(), (date(2026, 8, 3), date(2026, 12, 18)))
        summary = self.last_summary()
        self.assertEqual((summary['inicio'], summary['fim']), ('2026-08-03', '2026-12-18'))
        self.assertNotIn('inicio_anterior', summary)

    def test_reimport_changes_the_period_only_with_new_dates(self):
        self.conclude()
        original = (date(2026, 8, 3), date(2026, 12, 18))
        with self.case('prévia descartada'):
            self.preview(period=LATER).discard(self.definition, self.executor)
            self.assertEqual(self.period(), original)
        with self.case('confirmação divergente'):
            importation = self.preview(period=LATER, uploaded=workbook_file(spaces=[*SPACES, 'Zoo II']))
            Space.objects.register('Zoo II')
            self.assertFalse(confirm(importation, self.definition, self.executor))
            self.assertEqual(self.period(), original)
        with self.case('datas em branco mantêm o período'):
            self.conclude(period=BLANK)
            self.assertEqual(self.period(), original)
            summary = self.last_summary()
            self.assertEqual((summary['inicio'], summary['fim']), (None, None))
            self.assertNotIn('inicio_anterior', summary)
        with self.case('datas novas atualizam e auditam o anterior'):
            self.conclude(period=LATER)
            self.assertEqual(self.period(), (date(2026, 8, 10), date(2026, 12, 18)))
            summary = self.last_summary()
            self.assertEqual(
                {key: summary[key] for key in ('inicio', 'fim', 'inicio_anterior', 'fim_anterior')},
                {'inicio': '2026-08-10', 'fim': '2026-12-18', 'inicio_anterior': '2026-08-03', 'fim_anterior': '2026-12-18'},
            )


class AuditTests(ImportTestCase):
    def test_import_is_audited_by_its_summary(self):
        before = AuditLog.objects.latest('pk').pk
        with self.case('a prévia registra só a prévia'):
            self.preview()
            self.assertEqual(
                list(AuditLog.objects.filter(pk__gt=before).values_list('action', 'resource')),
                [(catalog.CREATE, catalog.SPACE_ALLOCATION_IMPORT)],
            )
        importation = self.conclude()
        record = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk')
        self.assertEqual((record.resource, str(record.resource_id)), (catalog.SPACE_ALLOCATION_IMPORT, str(importation.pk)))
        self.assertEqual(
            record.metadata,
            {
                'arquivo': 'ensalamento.xlsx',
                'situacao': 'CONCLUIDA',
                'cadastrados': len(TEACHERS) + len(SPACE_NAMES) + 4,
                'atualizados': 0,
                'sem_alteracao': 0,
                'com_erro': 0,
                'semestre': '2026/1',
                'inicio': '2026-08-03',
                'fim': '2026-12-18',
                'espacos_cadastrados': 4,
                'outros_nomes_associados': 0,
                'espacos_reativados': 0,
            },
        )
        self.assertEqual(
            sorted(set(AuditLog.objects.filter(pk__gt=before).values_list('resource', flat=True))),
            sorted([catalog.SPACE_ALLOCATION_IMPORT, catalog.SPACE]),
        )
        self.assertEqual(
            AuditLog.objects.filter(resource=catalog.SPACE, action=catalog.CREATE).count(), Space.objects.count(),
        )
        importation = self.conclude()
        metadata = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk').metadata
        self.assertEqual(
            (metadata['sem_alteracao'], metadata['cadastrados'], metadata['espacos_cadastrados']),
            (importation.rows.count(), 0, 0),
        )


class RealSpreadsheetTests(ImportTestCase):
    def uploaded(self):
        return SimpleUploadedFile(
            'planilha_example.xlsx', SPREADSHEET.read_bytes(), content_type=CONTENT_TYPE,
        )

    def test_real_file_is_previewed_with_the_activities_that_the_campus_needs_to_fix(self):
        importation = self.preview(self.uploaded())
        self.assertEqual(importation.rows.count(), 1706)
        self.assertEqual(importation.file_name, 'planilha_example.xlsx')
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        summary = importation.summary()
        self.assertEqual(summary['errors'], 121)
        without_action = importation.rows.filter(action=None, errors=[], pending=[]).count()
        self.assertEqual(summary['create'], 1706 - 121 - summary['pending'] - summary['unchanged'] - without_action)
        self.assertEqual(summary['update'], 0)
        with self.assertRaises(Exception):
            confirm(importation, self.definition, self.executor)
        self.assertFalse(Allocation.objects.exists())


def offering_teachers(subject='QUÍMICA ORGÂNICA', label='2º PERÍODO', semester='2026/1'):
    offering = ClassOffering.objects.get(semester__code=semester, subject__name=subject, class_group__label=label)
    return {assignment.teacher.name: assignment.is_current for assignment in offering.assignments.select_related('teacher')}


def chemistry_by(teacher):
    return workbook_file(undergraduate={
        ('SEGUNDA ', '07:20 - 08:10', 0): f'QUÍMICA ORGÂNICA ({teacher}) (1/13)',
        ('SEGUNDA ', '08:10 - 09:00', 0): f'QUÍMICA ORGÂNICA ({teacher}) (1/13)',
        ('SEGUNDA ', '09:20 - 10:10', 1): 'Cálculo III (Viviane) (2/6)',
    })


class AcademicLinkTests(ImportTestCase):
    """Ofertas e docentes das ofertas estabelecidos pela importação."""

    def test_offerings_and_teachers_follow_the_confirmed_imports(self):
        with self.case('linha recusada não deixa vínculo'):
            importation = self.preview(workbook_file(undergraduate={
                ('SEGUNDA ', '07:20 - 08:10', 0): 'QUÍMICA ORGÂNICA (Desconhecido) (1/13)',
            }))
            self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
            self.assertFalse(ClassOffering.objects.filter(subject__name='QUÍMICA ORGÂNICA').exists())
        self.conclude()
        self.assertEqual(ClassOffering.objects.count(), 3)
        self.assertEqual(offering_teachers(), {'Elza': True})
        self.assertEqual(offering_teachers('Cálculo III', '4º PERÍODO'), {'Viviane': True})
        self.conclude(chemistry_by('Viviane'))
        self.assertEqual(offering_teachers(), {'Elza': False, 'Viviane': True})
        self.conclude()
        self.assertEqual(offering_teachers(), {'Elza': True, 'Viviane': False})
        self.assertEqual(ClassOffering.objects.count(), 3)


ELZA = ('elza@ifnmg.edu.br', 'Elza Souza', 'SOLICITACAO', 'Elza')
VIVIANE = ('viviane@ifnmg.edu.br', 'Viviane Lima', 'SOLICITACAO', 'Viviane')


class UserSheetTests(ImportTestCase):
    """Aba opcional `usuários - sistema`."""

    def setUp(self):
        self.executor = space_manager(extra_permissions=[permissions.USER_CREATE, permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST])
        self.definition = SpaceAllocationImport()
        self.teacher_role = requester_role()

    def with_users(self, *users, **options):
        return workbook_file(users=list(users), **options)

    def user_rows(self, importation):
        return list(importation.rows.filter(values__Tipo='USUARIO').order_by('line_number'))

    def imported_users(self):
        return User.objects.exclude(pk=self.executor.pk)

    def password_links(self):
        return OutboxEntry.objects.filter(kind='LINK_SENHA').exclude(reference=str(self.executor.pk))

    def user_audit(self):
        return AuditLog.objects.filter(resource=catalog.USER, action=catalog.CREATE).exclude(
            resource_id=str(self.executor.pk),
        )

    def error_codes(self, row):
        return [(error['column'], error['code']) for error in row.errors]

    def register_elza(self):
        return User.objects.register(email='elza@ifnmg.edu.br', name='Elza Souza', role=self.teacher_role, username='Elza')

    def test_valid_users_are_planned_and_created(self):
        Role.objects.create_role(code='SECRETARIA', name='Secretaria')
        importation = self.preview(self.with_users(ELZA, ('ana@ifnmg.edu.br', 'Ana', 'secretaria', '')))
        self.assertEqual(importation.status, Import.Status.VALIDATED, self.errors_of(importation))
        rows = self.user_rows(importation)
        self.assertEqual([row.line_number for row in rows], [1, 2])
        self.assertEqual((rows[0].values['Célula'], rows[0].values['E-mail']), ('usuários - sistema!A2', 'elza@ifnmg.edu.br'))
        self.assertIn('usuarios', [item.slug for item in self.definition.row_filters])
        self.assertEqual(rows[0].action, 'create')
        self.assertEqual(rows[0].changes, {
            'email': [None, 'elza@ifnmg.edu.br'],
            'name': [None, 'Elza Souza'],
            'role': [None, 'SOLICITACAO'],
            'username': [None, 'Elza'],
        })

        self.assertTrue(confirm(importation, self.definition, self.executor))
        user = User.objects.get(email='elza@ifnmg.edu.br')
        self.assertEqual((user.is_active, user.is_superadmin, user.role, user.username), (True, False, self.teacher_role, 'Elza'))
        self.assertFalse(user.has_usable_password())
        self.assertTrue(OutboxEntry.objects.filter(kind='LINK_SENHA', reference=str(user.pk)).exists())
        self.assertEqual(self.user_rows(importation)[0].created_object, str(user.pk))
        self.assertEqual(set(self.user_audit().values_list('origin', flat=True)), {catalog.IMPORTED})
        self.assertEqual(teacher_of(user), Teacher.objects.get(name='Elza'))
        ana = User.objects.get(email='ana@ifnmg.edu.br')
        self.assertEqual((ana.role.code, ana.username), ('SECRETARIA', None))
        message = concluded_message(importation.summary(), importation)
        self.assertIn('2 usuários cadastrados', message)
        self.assertTrue(message.endswith('O link para definir a senha será enviado aos usuários cadastrados.'))
        record = AuditLog.objects.get(resource=catalog.SPACE_ALLOCATION_IMPORT, action=catalog.IMPORT)
        self.assertEqual(record.metadata['usuarios_cadastrados'], 2)

    def test_existing_user_is_kept_as_it_is(self):
        Role.objects.create_role(code='SECRETARIA', name='Secretaria')
        cases = [
            ('mesmo e-mail com outra caixa', ('ELZA@ifnmg.edu.br', 'Elza Souza', 'SOLICITACAO', 'Elza'), False, []),
            ('outros dados', ('elza@ifnmg.edu.br', 'Elza', 'SECRETARIA', 'Elza'), False, ['usuario_com_outros_dados']),
            ('inativo', ELZA, True, ['usuario_inativo']),
        ]
        for label, line, inactive, warnings in cases:
            with self.case(label):
                existing = self.register_elza()
                if inactive:
                    User.objects.filter(pk=existing.pk).update(is_active=False)
                links = self.password_links().count()
                row = self.user_rows(self.conclude(self.with_users(line)))[0]
                self.assertEqual((row.action, row.target, row.warnings), ('unchanged', str(existing.pk), warnings))
                self.assertEqual(User.objects.filter(email__iexact='elza@ifnmg.edu.br').count(), 1)
                self.assertEqual(self.password_links().count(), links)
                existing.refresh_from_db()
                self.assertEqual(
                    (existing.name, existing.role.code, existing.is_active), ('Elza Souza', 'SOLICITACAO', not inactive),
                )

    def test_invalid_user_rows_are_errors(self):
        cases = [
            ('e-mail inválido', [('elza', 'Elza', 'SOLICITACAO', 'Elza')], [[('E-mail', 'invalid')]]),
            (
                'e-mail repetido na aba', [ELZA, ('ELZA@ifnmg.edu.br', 'Outra', 'SOLICITACAO', 'Outra')],
                [[('E-mail', 'duplicate')], [('E-mail', 'duplicate')]],
            ),
            (
                'nome de usuário repetido na aba', [ELZA, ('outra@ifnmg.edu.br', 'Outra', 'SOLICITACAO', 'ELZA')],
                [[('Nome de usuário', 'duplicate')], [('Nome de usuário', 'duplicate')]],
            ),
            (
                'células obrigatórias',
                [
                    ('', 'Elza', 'SOLICITACAO', 'Elza'),
                    ('viviane@ifnmg.edu.br', '', 'SOLICITACAO', 'Viviane'),
                    ('erica@ifnmg.edu.br', 'Érica', '', 'Érica'),
                    ('ana@ifnmg.edu.br', 'Ana', 'SOLICITACAO', ''),
                ],
                [[('E-mail', 'required')], [('Nome', 'required')], [('Perfil', 'required')], []],
            ),
        ]
        for label, users, expected in cases:
            with self.case(label):
                importation = self.preview(self.with_users(*users))
                self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
                found = [self.error_codes(row) for row in self.user_rows(importation)]
                for codes, wanted in zip(found, expected):
                    for code in wanted:
                        self.assertIn(code, codes)
                    if not wanted:
                        self.assertEqual(codes, [])
        with self.case('nome de usuário de outro usuário'):
            User.objects.register(email='outra@ifnmg.edu.br', name='Outra', role=self.teacher_role, username='Elza')
            row = self.user_rows(self.preview(self.with_users(ELZA)))[0]
            self.assertIn(('Nome de usuário', 'username_taken'), self.error_codes(row))
        with self.case('sem a permissão de cadastrar usuários'):
            executor, self.executor = self.executor, space_manager('semcadastro@ifnmg.edu.br')
            try:
                row = self.user_rows(self.preview(self.with_users(ELZA)))[0]
            finally:
                self.executor = executor
            self.assertIn((None, 'permission_denied'), self.error_codes(row))
        with self.case('erro do banco'):
            with patch.object(User.objects, 'register', side_effect=DatabaseError):
                row = self.user_rows(self.preview(self.with_users(ELZA)))[0]
            self.assertEqual(self.error_codes(row), [(None, 'database')])
            self.assertFalse(self.imported_users().exists())

    def test_user_error_blocks_whole_import(self):
        importation = self.preview(self.with_users(ELZA, ('viviane', 'Viviane', 'SOLICITACAO', 'Viviane')))
        self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
        with self.assertRaises(Exception):
            confirm(importation, self.definition, self.executor)
        self.assertFalse(self.imported_users().exists())
        self.assertFalse(Allocation.objects.exists())

    def test_users_are_created_only_by_a_complete_confirmation(self):
        with self.case('prévia e atualização'):
            importation = self.preview(self.with_users(ELZA, VIVIANE))
            refresh(importation, self.definition, self.executor)
            self.assertFalse(self.imported_users().exists())
            self.assertFalse(self.password_links().exists())
            self.assertFalse(self.user_audit().exists())
        with self.case('divergência'):
            importation = self.preview(self.with_users(ELZA, VIVIANE))
            self.register_elza()
            self.assertFalse(confirm(importation, self.definition, self.executor))
            self.assertEqual((importation.revalidation_count, importation.status), (1, Import.Status.VALIDATED))
            self.assertFalse(User.objects.filter(email='viviane@ifnmg.edu.br').exists())
            self.assertFalse(Allocation.objects.exists())
        with self.case('erro inesperado depois dos usuários'):
            importation = self.preview(self.with_users(ELZA))
            with patch.object(Allocation.objects, 'apply', side_effect=RuntimeError):
                self.assertFalse(confirm(importation, self.definition, self.executor))
            self.assertEqual((importation.status, importation.operation), (Import.Status.VALIDATED, Import.Operation.CONFIRMATION))
            self.assertFalse(self.imported_users().exists())
            self.assertFalse(self.password_links().exists())
            self.assertFalse(Space.objects.exists())
            self.assertFalse(AuditLog.objects.filter(resource=catalog.SPACE).exists())
        with self.case('quem confirma não tem a permissão'):
            importation = self.preview(self.with_users(ELZA))
            self.assertFalse(confirm(importation, self.definition, space_manager('semcadastro@ifnmg.edu.br')))
            self.assertEqual(importation.status, Import.Status.WITH_ERRORS)
            self.assertFalse(User.objects.filter(email='elza@ifnmg.edu.br').exists())
            self.assertFalse(Allocation.objects.exists())


class SuggestedSpreadsheetTests(ImportTestCase):
    """Planilha sugerida, com a aba `usuários - sistema`."""

    def setUp(self):
        self.executor = space_manager(extra_permissions=[permissions.USER_CREATE, permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST])
        self.definition = SpaceAllocationImport()

    def test_users_sheet_is_read_and_every_user_is_planned(self):
        uploaded = SimpleUploadedFile(
            'planilha_example_sugerida.xlsx', SUGGESTED_SPREADSHEET.read_bytes(), content_type=CONTENT_TYPE,
        )
        importation = self.preview(uploaded)
        rows = list(importation.rows.filter(values__Tipo='USUARIO'))
        self.assertEqual(len(rows), 129)
        self.assertEqual([row.errors for row in rows if row.errors], [])
        self.assertEqual({row.action for row in rows}, {'create'})
        self.assertEqual(User.objects.count(), 1)
