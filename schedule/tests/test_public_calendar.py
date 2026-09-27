"""Calendário público do ensalamento: acesso, isolamento, dados expostos, filtros, datas e consultas."""

import re
from datetime import date, time
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from accounts.permissions import SPACE_ALLOCATION_VIEW, USER_VIEW
from audit.models import AuditLog
from schedule import occupancy, public
from schedule.models import ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.occupancy import Occurrence
from schedule.tests.test_timetable import allocate
from schedule.timetable import Entry

TODAY = date(2026, 9, 23)
URL = reverse('public_calendar')


class PublicCalendarTestCase(TestCase):
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
    def test_visitor_opens_the_public_route(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escolha uma sala, um docente ou um curso.')

    def test_visitor_cannot_open_the_authenticated_grid(self):
        grid = reverse('space_allocation_grid')
        response = self.client.get(grid)
        self.assertRedirects(response, f"{reverse('account_login')}?next={grid}", fetch_redirect_response=False)

    def test_authenticated_grid_still_requires_the_permission(self):
        self.client.force_login(self.aldo)
        self.assertEqual(self.client.get(reverse('space_allocation_grid')).status_code, 403)

    def test_authenticated_user_sees_the_same_calendar(self):
        anonymous = self.get(sala='10').content
        self.client.force_login(self.aldo)
        self.assertEqual(self.get(sala='10').content, anonymous)

    def test_only_get_and_head_are_accepted(self):
        self.assertEqual(self.client.head(URL).status_code, 200)
        for method in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(method(URL).status_code, 405)

    def test_post_without_csrf_is_405_and_writes_nothing(self):
        client = self.client_class(enforce_csrf_checks=True)
        before = AuditLog.objects.count()
        self.assertEqual(client.post(URL, {'sala': '10'}).status_code, 405)
        self.assertEqual(AuditLog.objects.count(), before)

    def test_view_declares_no_permission_nor_audit(self):
        from schedule.public_views import PublicCalendarView
        from schedule.views import SpaceAllocationGridView

        self.assertFalse(hasattr(PublicCalendarView, 'permission_required'))
        self.assertFalse(hasattr(PublicCalendarView, 'audit_resource'))
        self.assertFalse(issubclass(PublicCalendarView, SpaceAllocationGridView))
        self.assertEqual(SpaceAllocationGridView.permission_required, SPACE_ALLOCATION_VIEW)

    def test_access_writes_no_audit_and_sets_no_cookie(self):
        before = AuditLog.objects.count()
        response = self.get(sala='10')
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertFalse(response.cookies)

    def test_page_is_noindex_without_csrf_nor_authenticated_layout(self):
        self.client.force_login(self.aldo)
        html = self.text(self.get(sala='10'))
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertNotIn('csrfmiddlewaretoken', html)
        self.assertNotIn('X-CSRFToken', html)
        self.assertNotIn('menu-lateral', html)
        self.assertNotIn('data-notifications', html)
        self.assertNotIn('Aldo Gomes da Silva', html)
        self.assertNotIn('Gestor', html)
        self.assertNotIn(reverse('account_logout'), html)
        self.assertIn(reverse('account_login'), html)


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
    def test_card_shows_subject_group_space_and_teacher_without_email(self):
        html = self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25'))
        for text in ('Banco de Dados', 'Informática', '2º ano A', '10', 'Aldo Gomes'):
            self.assertIn(text, html)
        self.assertNotIn('aldo.gomes@ifnmg.edu.br', html)

    def test_allocation_without_space(self):
        self.assertContains(self.get(docente='Aldo Gomes', inicio='2026-09-24', fim='2026-09-24'), 'Sem sala definida')

    def test_no_administrative_or_personal_data(self):
        space = Space.objects.named('10')
        html = self.text(self.get(sala='10', inicio='2026-09-21', fim='2026-09-25'))
        for text in ('Sala Dez', 'Manual', 'Planilha', 'Choque', 'Aldo Gomes da Silva', 'Gestor', 'super@ifnmg.edu.br', 'admin@ifnmg.edu.br'):
            self.assertNotIn(text, html)
        self.assertNotRegex(html, rf'[?&=/]{space.pk}\b')
        self.assertNotIn('importacoes', html)
        self.assertNotIn('auditoria', html)

    def test_ids_never_appear_in_the_filters(self):
        html = self.text(self.get(docente='Aldo Gomes'))
        values = set(re.findall(r'<option value="([^"]*)"', html))
        calendar = self.calendar()
        names = {record.name for record in (*calendar.options.spaces, *calendar.options.teachers, *calendar.options.courses)}
        self.assertIn('Aldo Gomes', values)
        self.assertLessEqual(values, names | set(calendar.options.semesters) | set(public.STAGES) | {''})


class TeacherTests(PublicCalendarTestCase):
    def test_options_come_only_from_teachers_of_the_semester(self):
        names = [teacher.name for teacher in self.calendar().options.teachers]
        self.assertEqual(names, ['Adailton', 'Aldo Gomes', 'Érica'])
        self.assertNotIn('Administradora', names)
        self.assertNotIn('Superadmin Geral', names)

    def test_teacher_without_user_shows_only_the_name(self):
        html = self.text(self.get(docente='Érica', inicio='2026-09-21', fim='2026-09-21'))
        self.assertIn('Érica', html)
        self.assertNotIn('mailto:', html)

    def test_inactive_user_has_no_email(self):
        html = self.text(self.get(docente='Adailton', inicio='2026-09-23', fim='2026-09-23'))
        self.assertIn('Adailton', html)
        self.assertNotIn('adailton@ifnmg.edu.br', html)

    def test_match_ignores_case_but_is_exact(self):
        self.assertEqual(public.teacher_emails({'Aldo Gomes'}), {'aldo gomes': 'aldo.gomes@ifnmg.edu.br'})
        self.assertEqual(public.teacher_emails({'Aldo'}), {})
        self.assertEqual(public.teacher_emails({'Aldo Gomes '}), {})


class FilterTests(PublicCalendarTestCase):
    def test_teacher_and_space_combined(self):
        html = self.text(self.get(docente='Aldo Gomes', sala='10', inicio='2026-09-21', fim='2026-09-25'))
        self.assertIn('Banco de Dados', html)
        self.assertNotIn('Redes', html)

    def test_course_and_incompatible_stage(self):
        self.assertEqual(self.calendar(curso='INFORMÁTICA', nivel='graduacao').week.occupied, 0)

    def test_unknown_value_is_discarded(self):
        calendar = self.calendar(sala='Inexistente', docente='Aldo Gomes')
        self.assertIsNone(calendar.space)
        self.assertEqual(calendar.teacher.name, 'Aldo Gomes')

    def test_name_ignores_case(self):
        self.assertEqual(self.calendar(docente='aldo gomes').teacher.name, 'Aldo Gomes')

    def test_too_long_value_is_discarded(self):
        self.assertIsNone(self.calendar(docente='A' * 201).teacher)

    def test_inactive_space_with_lessons_is_an_option(self):
        names = [space.name for space in self.calendar().options.spaces]
        self.assertIn('7', names)
        self.assertNotIn('8', names)
        self.assertEqual(names, ['7', '10', '11', '12', '20'])

    def test_courses_are_only_the_allocated_ones(self):
        Course.objects.resolve('AGROPECUÁRIA', stage=Stage.SECONDARY)
        self.assertEqual([course.name for course in self.calendar().options.courses], ['INFORMÁTICA', 'LICENCIATURA EM FÍSICA'])

    def test_stage_options_are_the_existing_ones(self):
        html = self.text(self.get())
        self.assertIn('>Graduação<', html)
        self.assertIn('>Ensino médio<', html)

    def test_stage_filter(self):
        html = self.text(self.get(docente='Érica', nivel='graduacao'))
        self.assertNotIn('timetable-card', html)


class PrincipalFilterTests(PublicCalendarTestCase):
    def test_stage_alone_does_not_query_allocations(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.get(nivel='ensino-medio', inicio='2026-09-21', fim='2026-09-25')
        self.assertContains(response, 'Escolha uma sala, um docente ou um curso.')
        self.assertFalse(any('"schedule_allocation"."weekday"' in query['sql'] for query in queries))
        self.assertLessEqual(len(queries), 4)


class SemesterTests(PublicCalendarTestCase):
    def test_current_semester_is_the_default(self):
        self.assertEqual(self.calendar().semester_code, '2026/2')

    def test_semester_without_allocations(self):
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


class DateTests(PublicCalendarTestCase):
    def assertRefused(self, message, **params):
        with CaptureQueriesContext(connection) as queries:
            response = self.get(sala='10', **params)
        self.assertContains(response, message)
        self.assertFalse(any('"schedule_allocation"."weekday"' in query['sql'] for query in queries))

    def test_default_range_is_the_week_of_today(self):
        calendar = self.calendar(sala='10')
        self.assertEqual((calendar.start, calendar.end), (date(2026, 9, 21), date(2026, 9, 25)))
        html = self.text(self.get(sala='10'))
        self.assertIn('value="2026-09-21"', html)
        self.assertIn('value="2026-09-25"', html)

    def test_only_one_date(self):
        self.assertRefused('Informe a data inicial e a data final.', inicio='2026-09-21')

    def test_invalid_date(self):
        self.assertRefused('Informe uma data válida.', inicio='2026-02-30', fim='2026-03-05')

    def test_end_before_start(self):
        self.assertRefused('A data final deve ser igual ou posterior à data inicial.', inicio='2026-09-25', fim='2026-09-21')

    def test_more_than_31_days(self):
        self.assertRefused('Escolha um intervalo de até 31 dias.', inicio='2026-09-01', fim='2026-10-15')

    def test_31_days_are_accepted(self):
        calendar = self.calendar(sala='10', inicio='2026-09-01', fim='2026-10-01')
        self.assertEqual(calendar.date_error, '')
        self.assertEqual(len(calendar.week.days), 23)

    def test_range_outside_the_semester(self):
        self.assertRefused(
            'O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026.',
            inicio='2027-02-01', fim='2027-02-05',
        )

    def test_weekend_is_not_a_column(self):
        calendar = self.calendar(sala='10', inicio='2026-09-21', fim='2026-09-27')
        self.assertEqual([day.date for day in calendar.week.days][-1], date(2026, 9, 25))
        self.assertEqual(len(calendar.week.days), 5)

    def test_days_outside_the_period(self):
        html = self.text(self.get(sala='10', inicio='2026-12-21', fim='2026-12-25'))
        self.assertIn('Fora do semestre', html)

    def test_there_is_no_interval_navigation(self):
        html = self.text(self.get(sala='10', inicio='2026-09-14', fim='2026-09-25'))
        for text in ('Anterior', 'Próximo', '>Hoje</a>'):
            self.assertNotIn(text, html)


class GridTests(PublicCalendarTestCase):
    def test_groups_in_different_spaces_are_not_a_clash(self):
        html = self.text(self.get(curso='INFORMÁTICA', inicio='2026-09-21', fim='2026-09-21'))
        self.assertIn('Banco de Dados', html)
        self.assertIn('Matemática', html)
        self.assertNotIn('Choque', html)
        self.assertNotIn('turmas juntas', html)

    def test_joint_groups_in_the_same_space(self):
        self.assertContains(self.get(curso='LICENCIATURA EM FÍSICA', inicio='2026-09-23', fim='2026-09-23'), '2 turmas juntas')

    def test_empty_slot_is_available_only_for_a_space(self):
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

    def test_today_is_marked(self):
        self.assertContains(self.get(sala='10'), 'id="hoje"')


class EmptyStateTests(PublicCalendarTestCase):
    def assertEmptyGrid(self, **params):
        html = self.text(self.get(**params))
        self.assertIn('data-public-scroll', html)
        self.assertNotIn('timetable-card', html)
        self.assertNotIn('timetable-empty', html)
        return html

    def test_teacher_without_lessons_shows_only_the_empty_grid(self):
        html = self.assertEmptyGrid(docente='Aldo Gomes', inicio='2026-09-25', fim='2026-09-25')
        self.assertIn('Sexta-feira, 25/09/2026, das 07:00 às 07:50, sem aula', html)
        self.assertIn('das 07:50 às 08:40, sem aula', html)

    def test_course_without_lessons_shows_only_the_empty_grid(self):
        self.assertEmptyGrid(curso='LICENCIATURA EM FÍSICA', inicio='2026-09-25', fim='2026-09-25')

    def test_space_without_lessons_shows_only_the_empty_grid(self):
        html = self.assertEmptyGrid(sala='7', inicio='2026-09-21', fim='2026-09-24')
        self.assertIn('disponível', html)

    def test_no_grid_without_principal_filter_or_with_refused_dates(self):
        self.assertNotContains(self.get(), 'data-public-scroll')
        self.assertNotContains(self.get(sala='10', inicio='2026-09-01', fim='2026-10-15'), 'data-public-scroll')
        self.assertNotContains(self.get(sala='10', inicio='2027-02-01', fim='2027-02-05'), 'data-public-scroll')


class QueryTests(PublicCalendarTestCase):
    def count(self, **params):
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.get(**params).status_code, 200)
        return len(queries)

    def test_fixed_number_of_queries(self):
        for principal in ({'sala': '10'}, {'docente': 'Aldo Gomes'}, {'curso': 'INFORMÁTICA'}):
            week = self.count(**principal, inicio='2026-09-21', fim='2026-09-25')
            month = self.count(**principal, inicio='2026-09-01', fim='2026-10-01')
            self.assertEqual(week, month, principal)
            self.assertLessEqual(week, 9 if 'curso' in principal else 10, principal)

    def test_more_lessons_do_not_add_queries(self):
        before = self.count(docente='Aldo Gomes', inicio='2026-09-01', fim='2026-10-01')
        group = ClassGroup.objects.get(label='2º ANO B')
        for index, weekday in enumerate([Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY]):
            allocate(self.semester, group, f'Disciplina {index}', weekday, time(9, 0), time(9, 50), space=f'3{index}', teachers=['Aldo Gomes', f'Docente {index}'])
        self.assertEqual(self.count(docente='Aldo Gomes', inicio='2026-09-01', fim='2026-10-01'), before)
