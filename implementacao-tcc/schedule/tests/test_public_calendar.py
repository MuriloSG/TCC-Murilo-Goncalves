"""Calendário público do ensalamento: acesso, isolamento, dados expostos, filtros, datas e consultas."""

import re
from datetime import date, time
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from accounts.permissions import USER_VIEW
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin
from schedule import occupancy, public
from schedule.models import Allocation, AllocationException, ClassGroup, Course, Origin, Semester, Space, Stage, Weekday
from schedule.occupancy import Occurrence
from schedule.tests.test_timetable import allocate
from schedule.timetable import Entry

TODAY = date(2026, 9, 23)
URL = reverse('public_calendar')


class PublicCalendarTestCase(IsolatedCasesMixin, TestCase):
    """Semestre 2026/2 com período, dois cursos e aulas em salas diferentes no mesmo horário."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 6, 1), date(2026, 12, 23))
        info = Course.objects.resolve('INFORMÁTICA', stage=Stage.SECONDARY)[0]
        physics = Course.objects.resolve('LICENCIATURA EM FÍSICA', stage=Stage.UNDERGRADUATE)[0]
        cls.group_a = ClassGroup.objects.resolve(info, '2º ANO A')[0]
        cls.group_b = ClassGroup.objects.resolve(info, '2º ANO B')[0]
        second = ClassGroup.objects.resolve(physics, '2º PERÍODO')[0]
        fourth = ClassGroup.objects.resolve(physics, '4º PERÍODO')[0]
        first_slot, second_slot = (time(7, 0), time(7, 50)), (time(7, 50), time(8, 40))
        allocate(cls.semester, cls.group_a, 'Banco de Dados', Weekday.MONDAY, *first_slot, space='10', teachers=['Aldo Gomes'])
        allocate(cls.semester, cls.group_a, 'Redes', Weekday.TUESDAY, *first_slot, space='12', teachers=['Aldo Gomes'])
        allocate(cls.semester, cls.group_b, 'Matemática', Weekday.MONDAY, *first_slot, space='11', teachers=['Érica'])
        allocate(cls.semester, cls.group_a, 'Estudo Orientado', Weekday.THURSDAY, *first_slot, teachers=['Aldo Gomes'])
        allocate(cls.semester, second, 'Física I', Weekday.WEDNESDAY, *first_slot, space='20', teachers=['Adailton'])
        allocate(cls.semester, fourth, 'Física I', Weekday.WEDNESDAY, *first_slot, space='20', teachers=['Adailton'])
        allocate(cls.semester, cls.group_b, 'Artes', Weekday.FRIDAY, *second_slot, space='7', teachers=['Érica'])
        Space.objects.named('7').deactivate()
        Space.objects.register('8').deactivate()
        Space.objects.named('10').add_name('Sala Dez')
        role = Role.objects.create_role(code='GESTOR', name='Gestor', permissions=[USER_VIEW])
        cls.aldo = User.objects.register(
            email='aldo.gomes@ifnmg.edu.br', name='Aldo Gomes da Silva', role=role, username='aldo gomes',
        )
        adailton = User.objects.register(email='adailton@ifnmg.edu.br', name='Adailton Pereira', role=role, username='Adailton')
        User.objects.filter(pk=adailton.pk).update(is_active=False)
        User.objects.create_superadmin('super@ifnmg.edu.br', 'Superadmin Geral', 'senha-forte-123')
        User.objects.register(email='admin@ifnmg.edu.br', name='Administradora', role=role, username='Administradora')

    def setUp(self):
        patcher = mock.patch('schedule.public_views.timezone.localdate', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get(self, **params):
        return self.client.get(URL, params)

    def text(self, response):
        return re.sub(r'\s+', ' ', response.content.decode())

    def calendar(self, **params):
        return public.public_calendar(params, TODAY)


class AccessTests(PublicCalendarTestCase):
    def test_visitor_and_user_see_the_same_page_without_audit_cookie_or_layout(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escolha uma sala, um docente ou um curso.')
        before = AuditLog.objects.count()
        response = self.get(sala='10')
        anonymous = response.content
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertFalse(response.cookies)
        self.client.force_login(self.aldo)
        self.assertEqual(self.get(sala='10').content, anonymous)
        html = self.text(self.get(sala='10'))
        self.assertIn('<meta name="robots" content="noindex">', html)
        for text in (
            'csrfmiddlewaretoken', 'X-CSRFToken', 'menu-lateral', 'data-notifications', 'Aldo Gomes da Silva', 'Gestor',
            reverse('account_logout'),
        ):
            self.assertNotIn(text, html)


class FutureSourceTests(PublicCalendarTestCase):
    def test_extra_occupancy_source_never_reaches_the_public_calendar(self):
        class ReservationSource:
            kind = 'RESERVA'

            def occurrences(self, space, start_date, end_date):
                return [Occurrence(
                    date=date(2026, 9, 21), start=time(7, 50), end=time(8, 40), space_id=space.pk, kind=self.kind,
                    entry=Entry(subject='Reserva secreta', group_label='Evento interno', teachers=('Fulano',), stage=Stage.UNDERGRADUATE),
                )]

        with mock.patch.object(occupancy, 'grid_sources', lambda: [occupancy.AllocationSource(), ReservationSource()]):
            self.assertEqual(len(occupancy.occupancy(Space.objects.named('10'), date(2026, 9, 21), date(2026, 9, 25))), 2)
            html = self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn('Banco de Dados', html)
        self.assertNotIn('Reserva secreta', html)
        self.assertNotIn('Evento interno', html)


class ExposedDataTests(PublicCalendarTestCase):
    def test_lessons_show_only_public_data(self):
        space = Space.objects.named('10')
        html = self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25'))
        for text in ('Banco de Dados', 'Informática', '2º ano A', '10', 'Aldo Gomes'):
            self.assertIn(text, html)
        for text in (
            'aldo.gomes@ifnmg.edu.br', 'Sala Dez', 'Manual', 'Planilha', 'Choque', 'Aldo Gomes da Silva', 'Gestor',
            'super@ifnmg.edu.br', 'admin@ifnmg.edu.br', 'importacoes', 'auditoria',
        ):
            self.assertNotIn(text, html)
        self.assertNotRegex(html, rf'[?&=/]{space.pk}\b')
        self.assertContains(self.get(docente='Aldo Gomes', inicio='2026-09-24', fim='2026-09-24'), 'Sem sala definida')
        for teacher, day, email in (
            ('Érica', '2026-09-21', 'mailto:'),
            ('Adailton', '2026-09-23', 'adailton@ifnmg.edu.br'),
            ('Aldo Gomes', '2026-09-21', 'aldo.gomes@ifnmg.edu.br'),
        ):
            with self.subTest(teacher):
                html = self.text(self.get(docente=teacher, inicio=day, fim=day))
                self.assertIn(teacher, html)
                self.assertNotIn(email, html)
                self.assertNotIn('mailto:', html)

    def test_ids_never_appear_in_the_filters(self):
        html = self.text(self.get(docente='Aldo Gomes'))
        values = set(re.findall(r'<option value="([^"]*)"', html))
        calendar = self.calendar()
        names = {record.name for record in (*calendar.options.spaces, *calendar.options.teachers, *calendar.options.courses)}
        self.assertIn('Aldo Gomes', values)
        self.assertLessEqual(values, names | set(calendar.options.semesters) | set(public.STAGES) | {''})


class FilterTests(PublicCalendarTestCase):
    def test_filter_options_come_from_the_semester(self):
        Space.objects.register('9')
        Course.objects.resolve('AGROPECUÁRIA', stage=Stage.SECONDARY)
        options = self.calendar().options
        self.assertEqual([teacher.name for teacher in options.teachers], ['Adailton', 'Aldo Gomes', 'Érica'])
        self.assertEqual([space.name for space in options.spaces], ['7', '9', '10', '11', '12', '20'])
        self.assertEqual([course.name for course in options.courses], ['INFORMÁTICA', 'LICENCIATURA EM FÍSICA'])
        self.assertEqual(options.groups, [])
        self.assertNotContains(self.get(sala='10'), 'name="turma"')
        self.assertEqual([group.label for group in self.calendar(curso='INFORMÁTICA').options.groups], ['2º ANO A', '2º ANO B'])
        self.assertContains(self.get(curso='INFORMÁTICA'), 'name="turma"')

    def test_filters_limit_the_lessons(self):
        html = self.text(self.get(docente='Aldo Gomes', sala='10', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn('Banco de Dados', html)
        self.assertNotIn('Redes', html)
        html = self.text(self.get(curso='INFORMÁTICA', turma='2º ano b', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn('Matemática', html)
        self.assertNotIn('Banco de Dados', html)
        self.assertEqual(self.calendar(curso='INFORMÁTICA', nivel='graduacao').week.occupied, 0)
        self.assertNotIn('timetable-card', self.text(self.get(docente='Érica', nivel='graduacao')))

    def test_unknown_or_invalid_values_are_discarded(self):
        calendar = self.calendar(sala='Inexistente', docente='Aldo Gomes')
        self.assertIsNone(calendar.space)
        self.assertEqual(calendar.teacher.name, 'Aldo Gomes')
        self.assertEqual(self.calendar(docente='aldo gomes').teacher.name, 'Aldo Gomes')
        self.assertIsNone(self.calendar(docente='A' * 201).teacher)
        calendar = self.calendar(curso='INFORMÁTICA', turma='2º PERÍODO')
        self.assertEqual((calendar.group, calendar.course.name), (None, 'INFORMÁTICA'))
        self.assertIsNone(self.calendar(sala='10', turma='2º ANO A').group)


class SemesterTests(PublicCalendarTestCase):
    def test_current_semester_is_the_default_and_an_empty_one_explains(self):
        self.assertEqual(self.calendar().semester_code, '2026/2')
        calendar = public.public_calendar({'semestre': '2026/2', 'sala': '10'}, date(2027, 3, 1))
        self.assertEqual(calendar.semester_code, '2026/2')
        calendar = public.public_calendar({'semestre': '2025/1', 'sala': '10'}, date(2027, 3, 1))
        self.assertEqual(calendar.message, 'Nenhum horário publicado no semestre 2027/1.')
        self.assertIsNone(calendar.week)

    def test_semester_without_period_shows_the_typical_week(self):
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)
        html = self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn('Datas do semestre 2026/2 ainda não definidas. O calendário mostra a semana típica.', html)
        self.assertIn('Banco de Dados', html)
        self.assertNotIn('21/09/2026', html)
        self.assertRegex(html, r'name="inicio"[^>]*disabled')


def queries_allocations(queries):
    return any('"schedule_allocation"."weekday"' in query['sql'] for query in queries)


class DateTests(PublicCalendarTestCase):
    def test_default_and_accepted_ranges(self):
        calendar = self.calendar(sala='10')
        self.assertEqual((calendar.start, calendar.end), (date(2026, 9, 21), date(2026, 9, 25)))
        html = self.text(self.get(sala='10'))
        self.assertIn('value="2026-09-21"', html)
        self.assertIn('value="2026-09-25"', html)
        calendar = self.calendar(sala='10', inicio='2026-09-01', fim='2026-10-01')
        self.assertEqual((calendar.date_error, len(calendar.week.days)), ('', 23))
        calendar = self.calendar(sala='10', inicio='2026-09-21', fim='2026-09-27')
        self.assertEqual([day.date for day in calendar.week.days][-1], date(2026, 9, 25))
        self.assertEqual(len(calendar.week.days), 5)

    def test_refused_ranges_explain_why_and_query_nothing(self):
        cases = [
            ('Informe a data inicial e a data final.', {'inicio': '2026-09-21'}),
            ('Informe uma data válida.', {'inicio': '2026-02-30', 'fim': '2026-03-05'}),
            ('A data final deve ser igual ou posterior à data inicial.', {'inicio': '2026-09-25', 'fim': '2026-09-21'}),
            ('Escolha um intervalo de até 31 dias.', {'inicio': '2026-09-01', 'fim': '2026-10-15'}),
            (
                'O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026.',
                {'inicio': '2027-02-01', 'fim': '2027-02-05'},
            ),
        ]
        for message, params in cases:
            with self.subTest(message):
                with CaptureQueriesContext(connection) as queries:
                    response = self.get(sala='10', **params)
                self.assertContains(response, message)
                self.assertNotContains(response, 'data-public-scroll')
                self.assertFalse(queries_allocations(queries))


class GridTests(PublicCalendarTestCase):
    def test_cells_show_joint_groups_and_free_slots(self):
        html = self.text(self.get(curso='INFORMÁTICA', inicio='2026-09-21', fim='2026-09-21'))
        self.assertIn('Banco de Dados', html)
        self.assertIn('Matemática', html)
        self.assertNotIn('Choque', html)
        self.assertNotIn('turmas juntas', html)
        self.assertContains(self.get(curso='LICENCIATURA EM FÍSICA', inicio='2026-09-23', fim='2026-09-23'), '2 turmas juntas')
        self.assertIn(', disponível</span>', self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25')))
        html = self.text(self.get(docente='Aldo Gomes', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn(', sem aula</span>', html)
        self.assertNotIn(', disponível</span>', html)

    def test_grid_always_has_every_slot_of_the_semester(self):
        physics = ClassGroup.objects.get(label='4º PERÍODO')
        allocate(self.semester, physics, 'Física Noturna', Weekday.MONDAY, time(19, 0), time(19, 50), space='20', teachers=['Adailton'])
        allocate(self.semester, physics, 'Física da Tarde', Weekday.TUESDAY, time(13, 0), time(13, 50), space='20', teachers=['Adailton'])
        every = [row.start for row in self.calendar(sala='20').week.rows]
        self.assertIn(time(19, 0), every)
        for course in ('INFORMÁTICA', 'LICENCIATURA EM FÍSICA'):
            with self.subTest(course=course):
                self.assertEqual([row.start for row in self.calendar(curso=course).week.rows], every)

    def test_empty_states(self):
        for label, params, expected in (
            ('docente sem aulas', {'docente': 'Aldo Gomes', 'inicio': '2026-09-25', 'fim': '2026-09-25'}, 'Sexta-feira, 25/09/2026, das 07:00 às 07:50, sem aula'),
            ('curso sem aulas', {'curso': 'LICENCIATURA EM FÍSICA', 'inicio': '2026-09-25', 'fim': '2026-09-25'}, 'sem aula'),
            ('sala sem aulas', {'sala': '7', 'inicio': '2026-09-21', 'fim': '2026-09-24'}, 'disponível'),
        ):
            with self.subTest(label):
                html = self.text(self.get(**params))
                self.assertIn('data-public-scroll', html)
                self.assertNotIn('timetable-card', html)
                self.assertNotIn('timetable-empty', html)
                self.assertIn(expected, html)
        self.assertNotContains(self.get(), 'data-public-scroll')
        with CaptureQueriesContext(connection) as queries:
            response = self.get(nivel='ensino-medio', inicio='2026-09-21', fim='2026-09-25')
        self.assertContains(response, 'Escolha uma sala, um docente ou um curso.')
        self.assertFalse(queries_allocations(queries))


class QueryTests(PublicCalendarTestCase):
    def count(self, **params):
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.get(**params).status_code, 200)
        return len(queries)

    def test_queries_do_not_grow_with_the_range_or_the_lessons(self):
        for principal in ({'sala': '10'}, {'docente': 'Aldo Gomes'}, {'curso': 'INFORMÁTICA'}):
            week = self.count(**principal, inicio='2026-09-21', fim='2026-09-25')
            month = self.count(**principal, inicio='2026-09-01', fim='2026-10-01')
            self.assertEqual(week, month, principal)
            self.assertLessEqual(week, 10, principal)
        before = self.count(docente='Aldo Gomes', inicio='2026-09-01', fim='2026-10-01')
        group = ClassGroup.objects.get(label='2º ANO B')
        for index, weekday in enumerate([Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY]):
            allocate(self.semester, group, f'Disciplina {index}', weekday, time(9, 0), time(9, 50), space=f'3{index}', teachers=['Aldo Gomes', f'Docente {index}'])
        self.assertEqual(self.count(docente='Aldo Gomes', inicio='2026-09-01', fim='2026-10-01'), before)


ORIGINAL_URL = reverse('public_original_timetable')


class OriginalTimetableTests(PublicCalendarTestCase):
    """Horário original: semana típica importada, com os mesmos filtros e sem datas."""

    def original(self, **params):
        return public.original_timetable(params, TODAY)

    def subjects(self, calendar):
        return [
            (day.label, entry.subject)
            for day in calendar.week.days
            for cell in day.cells
            if cell and not cell.is_continued and not cell.is_outside
            for cluster in cell.clusters
            for entry in cluster.entries
        ]

    def test_original_keeps_the_imported_week(self):
        mathematics = self.group_b.allocations.get(subject__name='Matemática')
        with self.case('ocorrência cancelada continua no original'):
            superadmin = User.objects.get(email='super@ifnmg.edu.br')
            AllocationException.objects.cancel([mathematics.pk], date(2026, 9, 21), superadmin)
            self.assertNotIn('Matemática', self.text(self.get(sala='11', inicio='2026-09-21', fim='2026-09-25')))
            self.assertIn(('Segunda', 'Matemática'), self.subjects(self.original(sala='11')))
        with self.case('recorrência alterada mantém a versão importada'):
            Allocation.objects.filter(pk=mathematics.pk).update(valid_until=date(2026, 8, 31))
            changed = allocate(self.semester, self.group_b, 'Matemática', Weekday.TUESDAY, time(7, 0), time(7, 50), space='11', teachers=['Érica'])
            Allocation.objects.filter(pk=changed.pk).update(origin=Origin.MANUAL, valid_from=date(2026, 9, 1))
            self.assertEqual(self.subjects(self.original(sala='11')), [('Segunda', 'Matemática')])
        with mock.patch.object(public, 'public_bookings') as bookings:
            self.original(sala='10')
        bookings.assert_not_called()

    def test_original_uses_the_same_filters_without_dates(self):
        self.assertEqual(self.client.get(ORIGINAL_URL).status_code, 200)
        self.assertEqual(self.original().message, public.CHOOSE_MESSAGE)
        calendar = self.original(curso='INFORMÁTICA', turma='2º ANO A', inicio='x', fim='2026-01-01')
        self.assertEqual(calendar.date_error, '')
        self.assertEqual(
            sorted(subject for _, subject in self.subjects(calendar)),
            ['Banco de Dados', 'Estudo Orientado', 'Redes'],
        )
        self.assertEqual(self.subjects(self.original(docente='Érica', sala='7')), [('Sexta', 'Artes')])
        response = self.client.get(ORIGINAL_URL, {'sala': '10', 'inicio': '2026-09-21', 'fim': '2026-09-25'})
        self.assertNotIn('inicio', response.context['filter_form'].fields)
        self.assertEqual(response.context['other_url'], f'{URL}?sala=10')
        self.assertEqual(response.context['calendar'].notice, '')
        response = self.get(sala='10', inicio='2026-09-21', fim='2026-09-25')
        self.assertEqual(response.context['other_url'], f'{ORIGINAL_URL}?sala=10')
