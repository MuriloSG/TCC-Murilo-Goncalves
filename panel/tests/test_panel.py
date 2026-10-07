from datetime import date, datetime, time
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts import permissions
from accounts.models import Role, User
from bookings.models import Booking, BookingRequest
from bookings.tests.base import user_with
from imports.models import Import
from panel import indicators
from schedule.models import Allocation, AllocationException, ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.tests.test_timetable import allocate

MONDAY = date(2026, 10, 5)
EVERY_BLOCK = (
    permissions.PANEL_VIEW,
    permissions.BOOKING_REVIEW,
    permissions.BOOKING_VIEW,
    permissions.SPACE_ALLOCATION_VIEW,
    permissions.SPACE_ALLOCATION_IMPORT,
)


def at(day, hour=10, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class PanelTestCase(TestCase):
    """Relógio fixado na segunda-feira 05/10/2026 às 10:00 e o semestre 2026/2 com período."""

    moment = at(MONDAY)

    def setUp(self):
        patcher = mock.patch('django.utils.timezone.now', return_value=self.moment)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.semester, _ = Semester.objects.resolve('2026/2')
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('INFORMÁTICA', stage=Stage.SECONDARY)
        self.group_a, _ = ClassGroup.objects.resolve(course, '2º ANO A')
        self.group_b, _ = ClassGroup.objects.resolve(course, '2º ANO B')
        self.admin = user_with('gestor@ifnmg.edu.br', *EVERY_BLOCK)

    def lesson(self, space='Sala 1/3', start=time(10, 0), end=time(12, 0), group=None, subject='Redes', teachers=('Ana Souza',), weekday=Weekday.MONDAY):
        return allocate(self.semester, group or self.group_a, subject, weekday, start, end, space, list(teachers))

    def booking(self, space_name, day, start, end):
        space = Space.objects.filter(name=space_name).first() or Space.objects.register(space_name)
        request = BookingRequest.objects.create(
            requested_by=self.admin, space=space, date=day, start_time=start, end_time=end,
            description='Reunião do colegiado.', status=BookingRequest.Status.APPROVED,
        )
        return Booking.objects.create(
            request=request, space=space, starts_at=at(day, start.hour, start.minute),
            ends_at=at(day, end.hour, end.minute), description=request.description,
            requested_by=self.admin, approved_by=self.admin,
        )

    def request(self, day, start=time(14, 0), end=time(16, 0), status=BookingRequest.Status.PENDING, space='Auditório'):
        place = Space.objects.filter(name=space).first() or Space.objects.register(space)
        return BookingRequest.objects.create(
            requested_by=self.admin, space=place, date=day, start_time=start, end_time=end,
            description='Palestra.', status=status,
        )

    def load_of(self, occupancy, name):
        return next((load for load in occupancy.spaces if load.space.name == name), None)


class AccessTests(PanelTestCase):
    def test_with_every_permission_shows_every_block(self):
        self.client.force_login(self.admin)
        response = self.client.get('/painel/')
        self.assertEqual(response.status_code, 200)
        for title in ('Espaços mais ocupados', 'Para decidir', 'Pendências da grade', 'Importações abertas'):
            self.assertContains(response, title)

    def test_without_module_permissions_shows_the_notice(self):
        self.client.force_login(user_with('painel@ifnmg.edu.br', permissions.PANEL_VIEW))
        response = self.client.get('/painel/')
        self.assertContains(response, 'Nenhum indicador liberado para o seu perfil.')

    def test_without_review_hides_the_requests(self):
        self.request(date(2026, 10, 6))
        self.client.force_login(user_with('grade@ifnmg.edu.br', permissions.PANEL_VIEW, permissions.SPACE_ALLOCATION_VIEW))
        with mock.patch('panel.indicators.requests_summary') as summary:
            response = self.client.get('/painel/')
        summary.assert_not_called()
        self.assertNotContains(response, 'Para decidir')
        self.assertNotContains(response, 'Solicitações pendentes')

    def test_without_import_hides_the_imports(self):
        self.client.force_login(user_with('grade@ifnmg.edu.br', permissions.PANEL_VIEW, permissions.SPACE_ALLOCATION_VIEW))
        self.assertNotContains(self.client.get('/painel/'), 'Importações abertas')

    def test_superadmin_sees_every_block(self):
        superadmin = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
        self.client.force_login(superadmin)
        response = self.client.get('/painel/')
        self.assertContains(response, 'Para decidir')
        self.assertContains(response, 'Importações abertas')


class EntryTests(PanelTestCase):
    def test_holder_opens_the_panel_after_login(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get('/inicio/'), '/painel/', fetch_redirect_response=False)

    def test_teacher_keeps_opening_the_agenda(self):
        teacher = User.objects.register(email='docente@ifnmg.edu.br', name='Docente', role=Role.objects.get(code='DOCENTE'))
        self.client.force_login(teacher)
        self.assertRedirects(self.client.get('/inicio/'), '/agenda/', fetch_redirect_response=False)
        self.assertNotContains(self.client.get('/agenda/'), 'href="/painel/"')


class RequestTests(PanelTestCase):
    def test_counts_by_status(self):
        for day in (date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)):
            self.request(day)
        self.request(date(2026, 10, 9), status=BookingRequest.Status.SUGGESTED)
        self.request(date(2026, 10, 9), status=BookingRequest.Status.APPROVED, space='Sala 9')
        self.request(date(2026, 10, 9), status=BookingRequest.Status.REJECTED)
        summary = indicators.requests_summary(timezone.localtime())
        self.assertEqual((summary['pending'], summary['awaiting']), (3, 1))

    def test_passed_start_is_overdue_and_left_out_of_the_list(self):
        self.request(MONDAY, time(8, 0), time(9, 0))
        upcoming = self.request(date(2026, 10, 6), time(8, 0), time(9, 0))
        summary = indicators.requests_summary(timezone.localtime())
        self.assertEqual(summary['overdue'], 1)
        self.assertEqual(summary['upcoming'], [upcoming])

    def test_five_latest_requests_in_date_order(self):
        days = [date(2026, 10, day) for day in (12, 6, 7, 13, 8, 9, 14, 15)]
        for day in days:
            self.request(day)
        summary = indicators.requests_summary(timezone.localtime())
        self.assertEqual([item.date for item in summary['upcoming']], sorted(days[-5:]))
        self.assertEqual(summary['pending'], 8)

    def test_empty_state(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/painel/'), 'Nenhuma solicitação pendente.')


class OccupancyTests(PanelTestCase):
    def test_shared_lesson_counts_once(self):
        self.lesson()
        self.lesson(group=self.group_b)
        load = self.load_of(indicators.occupancy(indicators.TODAY, MONDAY), 'Sala 1/3')
        self.assertEqual((load.hours, load.lesson_count), (2, 1))

    def test_cancelled_occurrence_does_not_count(self):
        allocation = self.lesson()
        AllocationException.objects.create(allocation=allocation, date=MONDAY, created_by=self.admin)
        self.assertIsNone(self.load_of(indicators.occupancy(indicators.TODAY, MONDAY), 'Sala 1/3'))

    def test_booking_over_lesson_counts_once_and_segments_add_up(self):
        self.lesson()
        self.booking('Sala 1/3', MONDAY, time(11, 0), time(13, 0))
        load = self.load_of(indicators.occupancy(indicators.TODAY, MONDAY), 'Sala 1/3')
        self.assertEqual((load.hours, load.lesson_hours, load.booking_hours), (3, 2, 1))
        self.assertEqual((load.lesson_count, load.booking_count), (1, 1))
        self.assertEqual(load.lesson_width + load.booking_width, load.total_width)

    def test_ended_lesson_does_not_count_after_the_end(self):
        allocation = self.lesson()
        Allocation.objects.filter(pk=allocation.pk).update(valid_until=date(2026, 10, 4))
        self.assertIsNone(self.load_of(indicators.occupancy(indicators.WEEK, MONDAY), 'Sala 1/3'))

    def test_active_space_without_occupancy_is_idle(self):
        Space.objects.register('Sala 2/1')
        self.lesson()
        occupancy = indicators.occupancy(indicators.WEEK, MONDAY)
        self.assertIn('Sala 2/1', [space.name for space in occupancy.idle])
        self.assertIsNone(self.load_of(occupancy, 'Sala 2/1'))

    def test_inactive_space_without_occupancy_is_left_out(self):
        Space.objects.register('Sala 9/9').deactivate()
        occupancy = indicators.occupancy(indicators.WEEK, MONDAY)
        self.assertNotIn('Sala 9/9', [space.name for space in occupancy.idle])

    def test_weekend_counts_only_bookings(self):
        saturday = date(2026, 10, 10)
        self.lesson()
        self.booking('Auditório', saturday, time(9, 0), time(11, 0))
        occupancy = indicators.occupancy(indicators.TODAY, saturday)
        self.assertEqual([load.space.name for load in occupancy.spaces], ['Auditório'])

    def test_hours_by_day_in_the_week(self):
        self.lesson()
        self.booking('Auditório', MONDAY, time(14, 0), time(17, 0))
        days = indicators.occupancy(indicators.WEEK, MONDAY).days
        self.assertEqual(len(days), 7)
        self.assertEqual((days[0].hours, days[6].hours), (5, 0))
        self.assertTrue(days[0].is_today)

    def test_order_by_hours(self):
        self.lesson('Sala 1/3', time(10, 0), time(11, 0))
        self.lesson('Laboratório 2', time(10, 0), time(12, 0), group=self.group_b)
        names = [load.space.name for load in indicators.occupancy(indicators.TODAY, MONDAY).spaces]
        self.assertEqual(names, ['Laboratório 2', 'Sala 1/3'])

    def test_only_the_ten_busiest(self):
        for index in range(12):
            self.lesson(f'Sala {index}', time(7, 0), time(8 + index % 4, 0), subject=f'Disciplina {index}')
        self.assertEqual(len(indicators.occupancy(indicators.TODAY, MONDAY).spaces), 10)

    def test_semester_without_period_is_warned(self):
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/painel/'), 'O semestre 2026/2 não tem período definido.')

    def test_outside_every_semester(self):
        occupancy = indicators.occupancy(indicators.TODAY, date(2027, 1, 20))
        self.assertTrue(occupancy.without_semester)

    def test_fixed_number_of_queries(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                indicators.occupancy(indicators.WEEK, MONDAY)
            return len(queries)

        for index in range(5):
            self.lesson(f'Sala {index}', subject=f'Disciplina {index}')
        few = count()
        for index in range(5, 40):
            self.lesson(f'Sala {index}', subject=f'Disciplina {index}')
        self.assertEqual(count(), few)


class GridIssueTests(PanelTestCase):
    def groups(self):
        return {group.key: group for group in indicators.grid_issues(self.semester, timezone.localtime(), True)}

    def test_lesson_without_space(self):
        self.lesson(space=None, subject='Química Orgânica')
        group = self.groups()['sem-espaco']
        self.assertEqual(group.count, 1)
        self.assertIn('Química Orgânica', group.items[0].text)

    def test_ended_version_is_not_an_issue(self):
        allocation = self.lesson(space=None)
        Allocation.objects.filter(pk=allocation.pk).update(valid_until=date(2026, 9, 30))
        self.assertEqual(self.groups()['sem-espaco'].count, 0)

    def test_without_teacher_counts_each_day_and_slot(self):
        self.lesson(start=time(8, 0), end=time(9, 0), teachers=())
        self.lesson(start=time(9, 0), end=time(10, 0), teachers=())
        self.assertEqual(self.groups()['sem-docente'].count, 2)

    def test_teacher_in_two_spaces_at_once(self):
        self.lesson('Sala 1/3')
        self.lesson('Laboratório 2', group=self.group_b, subject='Banco de dados')
        self.assertEqual(self.groups()['conflito'].count, 1)

    def test_shared_lesson_is_not_a_conflict(self):
        self.lesson('Sala 1/3')
        self.lesson('Sala 1/3', group=self.group_b)
        self.assertEqual(self.groups()['conflito'].count, 0)

    def test_adjacent_slots_are_not_a_conflict(self):
        self.lesson('Sala 1/3', time(10, 0), time(11, 0))
        self.lesson('Laboratório 2', time(11, 0), time(12, 0), group=self.group_b)
        self.assertEqual(self.groups()['conflito'].count, 0)

    def test_validities_that_do_not_cross(self):
        first = self.lesson('Sala 1/3')
        second = self.lesson('Laboratório 2', group=self.group_b)
        Allocation.objects.filter(pk=first.pk).update(valid_from=date(2026, 8, 3), valid_until=date(2026, 10, 4))
        Allocation.objects.filter(pk=second.pk).update(valid_from=date(2026, 10, 5))
        self.assertEqual(self.groups()['conflito'].count, 0)

    def test_booking_clash_with_a_later_lesson(self):
        self.booking('Sala 1/3', date(2026, 10, 12), time(10, 0), time(11, 0))
        self.lesson('Sala 1/3')
        items = self.groups()['choque'].items
        self.assertEqual(len(items), 1)
        self.assertIn('12/10/2026', items[0].text)

    def test_without_agenda_view_there_is_no_clash_item(self):
        groups = indicators.grid_issues(self.semester, timezone.localtime(), False)
        self.assertNotIn('choque', [group.key for group in groups])


class ImportTests(PanelTestCase):
    def importation(self, kind, status):
        return Import.objects.create(kind=kind, status=status, file_name=f'{kind}.xlsx', created_by=self.admin)

    def test_open_space_allocation_imports(self):
        pending = self.importation('ENSALAMENTO', Import.Status.PENDING)
        self.importation('ENSALAMENTO', Import.Status.CONCLUDED)
        self.importation('USUARIO', Import.Status.WITH_ERRORS)
        self.assertEqual(indicators.open_imports(), (1, [pending]))


class FilterTests(PanelTestCase):
    def test_semester_of_the_day_by_default(self):
        first, _ = Semester.objects.resolve('2026/1')
        allocate(first, self.group_a, 'Redes', Weekday.MONDAY, time(8, 0), time(9, 0), 'Sala 1/3', [])
        self.lesson()
        self.assertEqual(indicators.chosen_semester(None, MONDAY)[1].code, '2026/2')

    def test_most_recent_when_the_day_is_not_imported(self):
        self.lesson()
        self.assertEqual(indicators.chosen_semester(None, date(2027, 3, 1))[1].code, '2026/2')

    def test_invalid_value_falls_back(self):
        self.lesson()
        self.client.force_login(self.admin)
        response = self.client.get('/painel/?semestre=1999/9&ocupacao=mes')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['semester'].code, '2026/2')
        self.assertEqual(response.context['filters'].period, indicators.TODAY)

    def test_filter_does_not_change_today(self):
        self.lesson()
        first, _ = Semester.objects.resolve('2026/1')
        allocate(first, self.group_a, 'Redes', Weekday.MONDAY, time(8, 0), time(9, 0), 'Sala 1/3', [])
        self.client.force_login(self.admin)
        response = self.client.get('/painel/?semestre=2026/1')
        self.assertEqual(response.context['occupancy'].start, MONDAY)
        self.assertEqual(response.context['semester'].code, '2026/1')


class IssueModalTests(PanelTestCase):
    def url(self, key, query=''):
        return f"{reverse('panel_issue', args=[key])}{query}"

    def test_without_the_grid_is_403(self):
        self.client.force_login(user_with('painel@ifnmg.edu.br', permissions.PANEL_VIEW))
        self.assertEqual(self.client.get(self.url('sem-ocupacao')).status_code, 403)

    def test_clash_requires_the_agenda(self):
        self.lesson()
        self.client.force_login(user_with('grade@ifnmg.edu.br', permissions.PANEL_VIEW, permissions.SPACE_ALLOCATION_VIEW))
        self.assertEqual(self.client.get(self.url('choque')).status_code, 403)

    def test_unknown_key_is_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url('outra')).status_code, 404)

    def test_htmx_answers_the_modal(self):
        self.lesson(space=None, subject='Química Orgânica')
        self.client.force_login(self.admin)
        response = self.client.get(self.url('sem-espaco'), headers={'HX-Request': 'true'})
        self.assertTemplateUsed(response, 'panel/issue_modal.html')
        self.assertTemplateNotUsed(response, 'panel/issue_page.html')
        self.assertContains(response, '<dialog')
        self.assertContains(response, 'Química Orgânica')

    def test_without_htmx_answers_the_page(self):
        self.lesson()
        self.client.force_login(self.admin)
        response = self.client.get(self.url('sem-ocupacao'))
        self.assertTemplateUsed(response, 'panel/issue_page.html')

    def test_idle_spaces_are_paginated(self):
        for index in range(12):
            Space.objects.register(f'Sala livre {index:02d}')
        self.lesson()
        self.client.force_login(self.admin)
        first = self.client.get(self.url('sem-ocupacao'), headers={'HX-Request': 'true'})
        self.assertEqual(len(first.context['page'].object_list), 5)
        self.assertContains(first, 'pagina=2')
        second = self.client.get(self.url('sem-ocupacao', '?pagina=2'), headers={'HX-Request': 'true'})
        self.assertEqual(len(second.context['page'].object_list), 5)


class WithoutSpaceTileTests(PanelTestCase):
    def test_only_the_top_card_shows_lessons_without_space(self):
        self.lesson(space=None)
        self.client.force_login(self.admin)
        response = self.client.get('/painel/')
        self.assertNotIn('sem-espaco', [group.key for group in response.context['issues']])
        self.assertEqual(response.context['without_space'], 1)
        self.assertContains(response, 'hx-get="/painel/pendencias/sem-espaco/', count=1)


class IssueTableTests(PanelTestCase):
    def test_lesson_without_space_has_no_button(self):
        self.lesson(space=None, teachers=())
        self.client.force_login(self.admin)
        response = self.client.get(reverse('panel_issue', args=['sem-docente']), headers={'HX-Request': 'true'})
        self.assertNotContains(response, 'Abrir na Grade')
        self.assertContains(response, 'Sem espaço')

    def test_clash_opens_the_agenda(self):
        self.booking('Sala 1/3', date(2026, 10, 12), time(10, 0), time(11, 0))
        self.lesson('Sala 1/3')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('panel_issue', args=['choque']), headers={'HX-Request': 'true'})
        self.assertContains(response, 'aria-label="Abrir na Agenda"')
