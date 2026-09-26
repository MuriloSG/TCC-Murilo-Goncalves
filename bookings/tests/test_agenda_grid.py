"""Grade da Agenda: acesso, ensalamento e agendamentos aprovados, isolamento e consultas (D7)."""

from datetime import date, time, timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts import permissions
from bookings.models import Booking, BookingRequest
from schedule.models import Space
from bookings.tests.base import REQUESTER, REVIEWER, THURSDAY, frozen_clock, semester_with_lesson, space, submit, user_with

URL = reverse('agenda_grid')
WEEK = {'sala': 'Laboratório de Informática 2', 'semana': '2026-10-12'}


class AgendaTestCase(TestCase):
    def setUp(self):
        frozen_clock(self)
        semester_with_lesson()
        self.lab = Space.objects.get(name='Laboratório de Informática 2')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        self.viewer = user_with('consulta@ifnmg.edu.br', permissions.BOOKING_VIEW)
        self.outsider = user_with('fora@ifnmg.edu.br', permissions.SPACE_ALLOCATION_VIEW)

    def book(self, day=THURSDAY, start=time(16, 0), end=time(18, 0), description='Reunião do projeto de extensão com os alunos.'):
        request = submit(self.ana, self.lab, day, start, end, description)
        request.approve(self.reviewer)
        return request

    def grid(self, user, **query):
        self.client.force_login(user)
        return self.client.get(URL, query or WEEK)


class AccessTests(AgendaTestCase):
    def test_anonymous_is_sent_to_the_login_with_next(self):
        self.assertRedirects(self.client.get(URL), f"{reverse('account_login')}?next={URL}", fetch_redirect_response=False)

    def test_without_the_view_permission(self):
        response = self.grid(self.outsider)
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(self.client.get(reverse('home')), URL)

    def test_with_the_view_permission(self):
        response = self.grid(self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1 class="page-title">Agenda</h1>', html=True)

    def test_menu_has_agenda_apart_from_the_space_allocation(self):
        both = user_with('ambos@ifnmg.edu.br', permissions.BOOKING_VIEW, permissions.SPACE_ALLOCATION_VIEW)
        self.client.force_login(both)
        content = self.client.get(reverse('home')).content.decode()
        self.assertIn(f'href="{URL}"', content)
        self.assertIn(f'href="{reverse("space_allocation_grid")}"', content)


class GridTests(AgendaTestCase):
    def test_week_shows_lessons_and_approved_bookings(self):
        self.book()
        response = self.grid(self.viewer)
        content = response.content.decode()
        self.assertContains(response, 'Semana da sala Laboratório de Informática 2')
        self.assertIn('Reunião do projeto de extensão com os alunos.', content)
        self.assertIn('Agendamento</p>', content)
        self.assertIn('Ensalamento</p>', content)
        self.assertIn('Redes', content)
        self.assertIn('Das 16:00 às 18:00', content)

    def test_booking_fills_every_slot_it_crosses(self):
        request = submit(self.ana, self.lab, date(2026, 10, 14), time(14, 30), time(15, 30), 'Banca de defesa.')
        request.approve(self.reviewer)
        week = self.grid(self.viewer).context['week']
        wednesday = week.days[2]
        [cell] = [cell for cell in wednesday.cells if cell and not cell.is_continued]
        self.assertEqual(cell.entries[0].description, 'Banca de defesa.')
        self.assertEqual(week.days[2].available, 0)

    def test_pending_request_is_not_in_the_grid(self):
        submit(self.ana, self.lab, description='Solicitação ainda pendente.')
        self.assertNotContains(self.grid(self.viewer), 'Solicitação ainda pendente.')

    def test_requester_name_only_for_the_reviewer(self):
        self.book()
        self.assertNotContains(self.grid(self.viewer), self.ana.name)
        self.assertContains(self.grid(self.reviewer), self.ana.name)

    def test_month_view(self):
        self.book()
        response = self.grid(self.viewer, sala='Laboratório de Informática 2', visao='mes', mes='2026-10')
        self.assertTrue(response.context['is_month'])
        self.assertContains(response, 'Mês da sala Laboratório de Informática 2')
        self.assertContains(response, 'Reunião do projeto de extensão com os alunos.')

    def test_inactive_space_is_not_offered(self):
        other = space('Sala 101')
        other.deactivate()
        self.assertNotIn(other, self.grid(self.viewer).context['filter_form'].fields['sala'].choices)
        self.assertNotContains(self.grid(self.viewer), '<option value="Sala 101"')


class IsolationTests(AgendaTestCase):
    def test_space_allocation_grid_does_not_show_bookings(self):
        self.book()
        self.client.force_login(user_with('ensalamento@ifnmg.edu.br', permissions.SPACE_ALLOCATION_VIEW, *REQUESTER))
        response = self.client.get(reverse('space_allocation_grid'), WEEK)
        self.assertContains(response, 'Redes')
        self.assertNotContains(response, 'Reunião do projeto de extensão')
        self.assertNotContains(response, 'Agendamento')
        self.assertNotContains(response, 'agenda/solicitar')

    def test_public_calendar_does_not_show_bookings(self):
        self.book()
        response = self.client.get(reverse('public_calendar'), {'sala': 'Laboratório de Informática 2', 'inicio': '2026-10-12', 'fim': '2026-10-16'})
        self.assertContains(response, 'Redes')
        self.assertNotContains(response, 'Reunião do projeto de extensão')


class QueryTests(AgendaTestCase):
    def queries(self, **query):
        self.client.force_login(self.reviewer)
        with CaptureQueriesContext(connection) as captured:
            self.assertEqual(self.client.get(URL, query).status_code, 200)
        return len(captured)

    def test_fixed_queries_for_a_week_and_a_month(self):
        self.book()
        week = self.queries(**WEEK)
        for offset in range(30):
            day = date(2026, 10, 1) + timedelta(days=offset)
            if day.weekday() < 5 and day != THURSDAY:
                self.book(day=day, start=time(19, 0), end=time(19, 30), description=f'Uso {offset}')
        self.assertGreaterEqual(Booking.objects.count(), 20)
        month = self.queries(sala='Laboratório de Informática 2', visao='mes', mes='2026-10')
        self.assertEqual(week, month)
        self.assertEqual(BookingRequest.objects.filter(status=BookingRequest.Status.APPROVED).count(), Booking.objects.count())


class WeekendTests(AgendaTestCase):
    def test_weekend_opens_the_following_week(self):
        from unittest import mock
        from django.utils import timezone
        from datetime import datetime
        saturday = timezone.make_aware(datetime(2026, 10, 3, 10, 0))
        with mock.patch('django.utils.timezone.now', return_value=saturday):
            self.client.force_login(self.ana)
            response = self.client.get(URL, {'sala': 'Laboratório de Informática 2'})
        self.assertEqual(response.context['week'].start, date(2026, 10, 5))
        self.assertContains(response, 'timetable-request')

    def test_weekday_opens_the_current_week(self):
        self.client.force_login(self.ana)
        response = self.client.get(URL, {'sala': 'Laboratório de Informática 2'})
        self.assertEqual(response.context['week'].start, date(2026, 9, 28))
