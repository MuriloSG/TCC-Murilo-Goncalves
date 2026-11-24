"""Grade da Agenda: acesso, ensalamento, agendamentos, isolamento e consultas."""

from datetime import date, time, timedelta

from django.db import connection
from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts import permissions
from bookings.models import Booking, BookingRequest
from accounts.models import User
from schedule.models import Space
from bookings.tests.base import REQUESTER, REVIEWER, THURSDAY, frozen_clock, semester_with_lesson, space, submit, user_with

URL = reverse('agenda_grid')
WEEK = {'sala': 'Laboratório de Informática 2', 'semana': '2026-10-12'}


class AgendaTestCase(IsolatedCasesMixin, TestCase):
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


class GridTests(AgendaTestCase):
    def test_week_and_month_show_lessons_and_approved_bookings(self):
        with self.case('semana'):
            self.book()
            response = self.grid(self.viewer)
            content = response.content.decode()
            self.assertContains(response, 'Semana da sala Laboratório de Informática 2')
            self.assertNotIn('Reunião do projeto de extensão com os alunos.', content)
            self.assertIn('Agendamento</p>', content)
            self.assertIn('Ensalamento</p>', content)
            self.assertIn('Redes', content)
            self.assertNotIn('Das 16:00 às 18:00', content)
        with self.case('pedido pendente fora'):
            submit(self.ana, self.lab, description='Solicitação ainda pendente.')
            self.assertNotContains(self.grid(self.viewer), 'Solicitação ainda pendente.')
        with self.case('mês'):
            self.book()
            response = self.grid(self.viewer, sala='Laboratório de Informática 2', visao='mes', mes='2026-10')
            self.assertTrue(response.context['is_month'])
            self.assertContains(response, 'Mês da sala Laboratório de Informática 2')
            self.assertContains(response, 'Agendamento</p>')

    def test_booking_fills_every_slot_it_crosses(self):
        request = submit(self.ana, self.lab, date(2026, 10, 14), time(14, 30), time(15, 30), 'Banca de defesa.')
        request.approve(self.reviewer)
        week = self.grid(self.viewer).context['week']
        wednesday = week.days[2]
        [cell] = [cell for cell in wednesday.cells if cell and not cell.is_continued]
        self.assertEqual(cell.entries[0].description, 'Banca de defesa.')
        self.assertEqual(week.days[2].available, 0)

    def test_requester_name_only_for_the_reviewer(self):
        self.book()
        self.assertNotContains(self.grid(self.viewer), self.ana.name)
        self.assertContains(self.grid(self.reviewer), self.ana.name)


class OtherCalendarsTests(AgendaTestCase):
    """Os agendamentos aprovados aparecem também na Grade do Ensalamento e no calendário público."""

    PUBLIC = {'sala': 'Laboratório de Informática 2', 'inicio': '2026-10-12', 'fim': '2026-10-16'}

    def space_allocation_grid(self, *codes):
        self.client.force_login(user_with(f'ensalamento{"abcd"[len(codes)]}@ifnmg.edu.br', permissions.SPACE_ALLOCATION_VIEW, *codes))
        return self.client.get(reverse('space_allocation_grid'), WEEK)

    def test_space_allocation_grid_shows_only_the_approved_booking(self):
        with self.case('mostra o aprovado'):
            self.book()
            response = self.space_allocation_grid(*REQUESTER)
            self.assertContains(response, 'Redes')
            self.assertContains(response, 'Agendamento</p>')
            self.assertNotContains(response, 'agenda/solicitar')
            self.assertNotContains(response, self.ana.name)
            self.assertEqual(response.context['week'].days[3].available, 0)
        with self.case('sem a linha do solicitante'):
            self.book()
            self.assertNotContains(self.space_allocation_grid(permissions.BOOKING_REVIEW), 'aria-label="Solicitante"')
        with self.case('pendente fora'):
            submit(self.ana, self.lab, description='Solicitação ainda pendente.')
            self.assertNotContains(self.space_allocation_grid(), 'Solicitação ainda pendente.')
            self.client.logout()
            self.assertNotContains(self.client.get(reverse('public_calendar'), self.PUBLIC), 'Solicitação ainda pendente.')

    def test_public_calendar_shows_the_class_without_private_data(self):
        with self.case('turma sem horário nem descrição'):
            self.book()
            self.client.logout()
            response = self.client.get(reverse('public_calendar'), self.PUBLIC)
            self.assertContains(response, 'Redes')
            self.assertContains(response, 'Agendamento</p>')
            self.assertContains(response, 'aria-label="Curso"')
            self.assertContains(response, 'aria-label="Turma"')
            self.assertContains(response, 'Laboratório de Informática 2')
            self.assertContains(response, self.ana.username)
            self.assertNotContains(response, 'Das 16:00 às 18:00')
            self.assertNotContains(response, self.ana.email)
            self.assertContains(response, '16:00 às 18:00')
            self.assertNotContains(response, 'Reunião do projeto de extensão')
            self.assertNotContains(response, self.reviewer.name)
        with self.case('sem vínculo mostra só o que existe'):
            request = self.book()
            BookingRequest.objects.filter(pk=request.pk).update(teaching_assignment=None)
            self.client.logout()
            response = self.client.get(reverse('public_calendar'), self.PUBLIC)
            card = response.content.decode().split('timetable-card is-booking')[1].partition('</div>')[0]
            self.assertIn('16:00 às 18:00', card)
            self.assertIn('Laboratório de Informática 2', card)
            self.assertIn(self.ana.name, card)
            self.assertNotIn('aria-label="Curso"', card)
            self.assertNotIn('aria-label="Turma"', card)
        with self.case('pelo docente'):
            User.objects.filter(pk=self.ana.pk).update(username='Viviane')
            self.book()
            self.client.logout()
            response = self.client.get(reverse('public_calendar'), {'docente': 'Viviane', 'inicio': '2026-10-12', 'fim': '2026-10-16'})
            self.assertContains(response, 'Redes')
            self.assertContains(response, 'Agendamento</p>')
            self.assertContains(response, 'Laboratório de Informática 2')
            self.assertContains(response, 'Viviane')
            self.assertNotContains(response, 'Reunião do projeto de extensão')
        with self.case('outro docente ou curso'):
            User.objects.filter(pk=self.ana.pk).update(username='Outra Pessoa')
            self.book()
            self.client.logout()
            for query in ({'docente': 'Viviane'}, {'curso': 'INFORMÁTICA'}):
                with self.subTest(query=query):
                    response = self.client.get(reverse('public_calendar'), query | {'inicio': '2026-10-12', 'fim': '2026-10-16'})
                    self.assertContains(response, 'Redes')
                    self.assertNotContains(response, 'Agendamento</p>')


class WeekendTests(AgendaTestCase):
    def test_default_week_skips_the_weekend(self):
        with self.case('fim de semana abre a próxima'):
            from unittest import mock
            from django.utils import timezone
            from datetime import datetime
            saturday = timezone.make_aware(datetime(2026, 10, 3, 10, 0))
            with mock.patch('django.utils.timezone.now', return_value=saturday):
                self.client.force_login(self.ana)
                response = self.client.get(URL, {'sala': 'Laboratório de Informática 2'})
            self.assertEqual(response.context['week'].start, date(2026, 10, 5))
            self.assertContains(response, 'timetable-request')
        with self.case('dia útil abre a atual'):
            self.client.force_login(self.ana)
            response = self.client.get(URL, {'sala': 'Laboratório de Informática 2'})
            self.assertEqual(response.context['week'].start, date(2026, 9, 28))


class OwnAgendaTests(AgendaTestCase):
    def test_all_or_own_agenda(self):
        with self.case('todas'):
            self.book()
            response = self.grid(self.viewer)
            self.assertContains(response, '<option value="todas" selected>Todas as agendas</option>', html=True)
            self.assertContains(response, 'Agendamento</p>')
        with self.case('a própria'):
            self.book()
            other = user_with('outra@ifnmg.edu.br', *REQUESTER)
            response = self.grid(other, agenda='minha', **WEEK)
            self.assertContains(response, '<option value="minha" selected>Minha agenda</option>', html=True)
            self.assertNotContains(response, 'Agendamento</p>')
            self.assertNotContains(response, 'data=2026-10-15&amp;inicio=16')
            self.assertContains(response, 'ocupado</span>')
            self.assertContains(response, 'agenda=minha')
