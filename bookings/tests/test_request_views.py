"""Solicitação pela tela, "Minhas solicitações", a resposta à alternativa e o cancelamento (D1, D8)."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from bookings.models import Booking, BookingRequest
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, academic, frozen_clock, semester_with_lesson, space, submit, user_with
from schedule.models import Space

Status = BookingRequest.Status
CREATE = reverse('agenda_request_create')
MINE = reverse('agenda_my_requests')


class RequestScreenTestCase(TestCase):
    def setUp(self):
        frozen_clock(self)
        semester_with_lesson()
        self.lab = Space.objects.get(name='Laboratório de Informática 2')
        self.other_lab = space('Laboratório de Informática 3')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.bruno = user_with('bruno@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        self.viewer = user_with('consulta@ifnmg.edu.br', permissions.BOOKING_VIEW)
        self.assignment = academic(teacher='ana')
        self.offering = self.assignment.offering

    def data(self, **values):
        return {
            'subject': self.offering.subject_id,
            'teaching_assignment': self.assignment.pk,
            'space': self.lab.pk, 'date': '2026-10-15', 'start_time': '16:00', 'end_time': '18:00',
            'description': 'Reunião do projeto de extensão com os alunos.', 'student_count': '30', 'confirmar': '1',
        } | values

    def suggested(self, owner=None):
        request = submit(owner or self.ana, self.lab)
        request.suggest(self.reviewer, self.other_lab, FRIDAY, time(14, 0), time(16, 0), 'O laboratório 2 recebe manutenção no dia 15.')
        return request


class AccessTests(RequestScreenTestCase):
    def routes(self):
        request = self.suggested()
        return [
            CREATE,
            MINE,
            reverse('agenda_my_request', args=[request.pk]),
            reverse('agenda_my_request_accept', args=[request.pk]),
            reverse('agenda_my_request_decline', args=[request.pk]),
        ]

    def test_with_the_request_permission(self):
        self.client.force_login(self.ana)
        for url in self.routes():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class CreateTests(RequestScreenTestCase):
    def test_modal_is_filled_from_the_slot(self):
        self.client.force_login(self.ana)
        response = self.client.get(CREATE, {'espaco': self.lab.pk, 'data': '2026-10-15', 'inicio': '14:00', 'fim': '16:00'}, headers={'HX-Request': 'true'})
        content = response.content.decode()
        self.assertIn('<dialog class="modal"', content)
        self.assertIn(f'<option value="{self.lab.pk}" selected>Laboratório de Informática 2</option>', content)
        self.assertIn('Semestre 2026/2.', content)
        self.assertNotIn('name="semester"', content)
        self.assertIn('name="date" value="2026-10-15"', content)
        self.assertNotRegex(content, r'name="date"[^>]*readonly')
        self.assertIn('name="start_time" value="14:00"', content)
        self.assertIn('name="end_time" value="16:00"', content)
        self.assertRegex(content, r'<textarea name="description"[^>]*>\s*</textarea>')

    def test_submit_creates_a_pending_request(self):
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data())
        request = BookingRequest.objects.get()
        self.assertEqual((request.status, request.requested_by, request.space), (Status.PENDING, self.ana, self.lab))
        self.assertRedirects(response, f"{reverse('agenda_grid')}?sala=Laborat%C3%B3rio+de+Inform%C3%A1tica+2&semana=2026-10-15", fetch_redirect_response=False)
        self.assertFalse(Booking.objects.exists())
        messages = [str(message) for message in response.wsgi_request._messages]
        self.assertEqual(messages, ['Solicitação de agendamento de Laboratório de Informática 2 em 15/10/2026, das 16:00 às 18:00 enviada.'])

    def test_description_is_required(self):
        self.client.force_login(self.ana)
        for description in ('', '   '):
            with self.subTest(description=description):
                response = self.client.post(CREATE, self.data(description=description))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Informe a descrição do uso do espaço.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_student_count_is_required(self):
        self.client.force_login(self.ana)
        for count, message in (('', 'Informe a quantidade de alunos.'), ('0', 'Informe uma quantidade de alunos entre 1 e 999.')):
            with self.subTest(count=count):
                response = self.client.post(CREATE, self.data(student_count=count))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
        self.assertFalse(BookingRequest.objects.exists())

    def test_conflict_with_the_space_allocation(self):
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(start_time='14:00', end_time='16:00'))
        self.assertContains(response, 'Este espaço está ocupado pelo ensalamento das 14:10 às 15:00. Escolha outro horário.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_weekend_is_refused_by_the_server(self):
        self.client.force_login(self.ana)
        for day in ('2026-10-17', '2026-10-18'):
            with self.subTest(day=day):
                response = self.client.post(CREATE, self.data(date=day))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Agendamentos só podem ser feitos de segunda a sexta. Escolha outra data.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_date_field_asks_the_calendar_for_weekdays_only(self):
        self.client.force_login(self.ana)
        content = self.client.get(CREATE, {'data': '2026-10-15'}, headers={'HX-Request': 'true'}).content.decode()
        self.assertRegex(content, r'<input type="date" name="date"[^>]*data-weekdays-only')

    def test_forged_inactive_space(self):
        self.other_lab.deactivate()
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(space=self.other_lab.pk))
        self.assertContains(response, 'Escolha um espaço ativo.')
        self.assertFalse(BookingRequest.objects.exists())


class GridActionTests(RequestScreenTestCase):
    def grid(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('agenda_grid'), {'sala': 'Laboratório de Informática 2', 'semana': '2026-10-12'}).content.decode()

    def test_available_future_slot_offers_the_request(self):
        content = self.grid(self.ana)
        self.assertIn(f'{CREATE}?espaco={self.lab.pk}&amp;data=2026-10-14&amp;inicio=14%3A10&amp;fim=15%3A00', content)
        self.assertIn('aria-label="Solicitar agendamento: Quarta-feira, 14/10/2026, das 14:10 às 15:00, disponível"', content)

    def test_occupied_slot_does_not_offer_the_request(self):
        content = self.grid(self.ana)
        self.assertNotIn('data=2026-10-15&amp;inicio=14%3A10', content)
        self.assertIn('data=2026-10-14&amp;inicio=14%3A10', content)

    def test_past_slot_does_not_offer_the_request(self):
        self.client.force_login(self.ana)
        content = self.client.get(reverse('agenda_grid'), {'sala': 'Laboratório de Informática 2', 'semana': '2026-09-28'}).content.decode()
        self.assertNotIn('data=2026-09-29', content)
        self.assertIn('data=2026-10-02', content)


class MyRequestsTests(RequestScreenTestCase):
    def test_list_shows_only_the_own_requests(self):
        submit(self.ana, self.lab, description='Solicitação de Ana.')
        submit(self.bruno, self.lab, description='Solicitação de Bruno.')
        self.client.force_login(self.ana)
        response = self.client.get(MINE)
        self.assertContains(response, 'Solicitação de Ana.')
        self.assertNotContains(response, 'Solicitação de Bruno.')
        self.assertContains(response, 'Pendente')

    def test_each_state_is_identified(self):
        approved = submit(self.ana, self.lab, start=time(8, 0), end=time(9, 0))
        approved.approve(self.reviewer)
        rejected = submit(self.ana, self.lab, start=time(9, 0), end=time(10, 0))
        rejected.reject(self.reviewer, 'Motivo.')
        self.suggested()
        declined = submit(self.ana, self.lab, start=time(10, 0), end=time(11, 0))
        declined.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0))
        declined.decline_suggestion(self.ana)
        submit(self.ana, self.lab, start=time(11, 0), end=time(12, 0))
        self.client.force_login(self.ana)
        content = self.client.get(MINE).content.decode()
        for label in ('Pendente', 'Aprovada', 'Rejeitada', 'Alternativa sugerida', 'Alternativa recusada', 'Resposta pendente'):
            with self.subTest(label=label):
                self.assertIn(label, content)

    def test_list_queries_do_not_grow_with_the_rows(self):
        self.client.force_login(self.ana)
        submit(self.ana, self.lab)
        self.client.get(MINE)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as one:
            self.client.get(MINE)
        for hour in range(7, 12):
            request = submit(self.ana, self.lab, start=time(hour, 0), end=time(hour, 30))
            request.suggest(self.reviewer, self.other_lab, FRIDAY, time(hour, 0), time(hour, 30))
        with CaptureQueriesContext(connection) as many:
            self.client.get(MINE)
        self.assertEqual(len(one), len(many))

    def test_detail_shows_the_original_and_the_suggestion(self):
        request = self.suggested()
        self.client.force_login(self.ana)
        content = self.client.get(reverse('agenda_my_request', args=[request.pk])).content.decode()
        for text in (
            'Laboratório de Informática 2', '15/10/2026, das 16:00 às 18:00',
            'Laboratório de Informática 3', '16/10/2026, das 14:00 às 16:00',
            'O laboratório 2 recebe manutenção no dia 15.', 'Aceitar alternativa', 'Recusar alternativa',
        ):
            with self.subTest(text=text):
                self.assertIn(text, content)

    def test_detail_shows_the_rejection_reason(self):
        request = submit(self.ana, self.lab)
        request.reject(self.reviewer, 'Laboratório em manutenção nessa data.')
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse('agenda_my_request', args=[request.pk])), 'Laboratório em manutenção nessa data.')

    def test_other_user_request_by_id_is_not_found(self):
        request = submit(self.bruno, self.lab)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('agenda_my_request', args=[request.pk])).status_code, 404)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(reverse('agenda_my_request', args=[request.pk])).status_code, 404)


class AnswerTests(RequestScreenTestCase):
    def test_accept_suggestion(self):
        request = self.suggested()
        self.client.force_login(self.ana)
        response = self.client.post(reverse('agenda_my_request_accept', args=[request.pk]))
        self.assertRedirects(response, reverse('agenda_my_request', args=[request.pk]), fetch_redirect_response=False)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.APPROVED)
        self.assertEqual(request.booking.space, self.other_lab)

    def test_accept_an_occupied_suggestion(self):
        request = self.suggested()
        other = submit(self.bruno, self.other_lab, FRIDAY, time(15, 0), time(17, 0))
        other.approve(self.reviewer)
        self.client.force_login(self.ana)
        response = self.client.post(reverse('agenda_my_request_accept', args=[request.pk]), follow=True)
        self.assertContains(response, 'Este espaço está ocupado das 15:00 às 17:00. Escolha outro horário.')
        request.refresh_from_db()
        self.assertEqual(request.status, Status.SUGGESTED)

    def test_decline_suggestion(self):
        request = self.suggested()
        self.client.force_login(self.ana)
        self.client.post(reverse('agenda_my_request_decline', args=[request.pk]))
        request.refresh_from_db()
        self.assertEqual(request.status, Status.DECLINED)
        self.assertFalse(Booking.objects.exists())

    def test_answer_by_another_user(self):
        request = self.suggested()
        for user in (self.bruno, self.reviewer):
            self.client.force_login(user)
            for name in ('agenda_my_request_accept', 'agenda_my_request_decline'):
                with self.subTest(user=user.email, route=name):
                    self.assertEqual(self.client.post(reverse(name, args=[request.pk])).status_code, 404)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.SUGGESTED)

    def test_answer_without_a_suggestion(self):
        request = submit(self.ana, self.lab)
        self.client.force_login(self.ana)
        response = self.client.post(reverse('agenda_my_request_accept', args=[request.pk]), follow=True)
        self.assertContains(response, 'Esta solicitação está pendente e não aceita esta ação.')
        request.refresh_from_db()
        self.assertEqual(request.status, Status.PENDING)


class CancelTests(RequestScreenTestCase):
    def setUp(self):
        super().setUp()
        self.request = submit(self.ana, self.lab)
        self.request.approve(self.reviewer)
        self.detail = reverse('agenda_my_request', args=[self.request.pk])
        self.cancel = reverse('agenda_my_request_cancel', args=[self.request.pk])

    def test_cancel_from_the_own_request(self):
        self.client.force_login(self.ana)
        self.assertTrue(self.client.get(self.detail).context['can_cancel'])
        self.assertEqual(self.client.get(self.cancel).status_code, 200)
        response = self.client.post(self.cancel, {'cancellation_reason': 'Turma em visita técnica.'})
        self.assertRedirects(response, self.detail, fetch_redirect_response=False)
        self.request.refresh_from_db()
        self.assertEqual((self.request.status, self.request.cancellation_reason), (Status.CANCELLED, 'Turma em visita técnica.'))
        self.assertFalse(Booking.objects.exists())
        detail = self.client.get(self.detail)
        self.assertFalse(detail.context['can_cancel'])
        self.assertContains(detail, 'Turma em visita técnica.')

    def test_cancel_after_the_deadline(self):
        soon = submit(self.ana, self.lab, date(2026, 10, 1), time(10, 30), time(11, 30))
        soon.approve(self.reviewer)
        self.client.force_login(self.ana)
        self.assertFalse(self.client.get(reverse('agenda_my_request', args=[soon.pk])).context['can_cancel'])
        response = self.client.post(reverse('agenda_my_request_cancel', args=[soon.pk]), {'cancellation_reason': ''})
        self.assertContains(response, 'O agendamento só pode ser cancelado até 1 hora antes do início.')
        soon.refresh_from_db()
        self.assertEqual(soon.status, Status.APPROVED)

    def test_cancel_by_another_user(self):
        for user in (self.bruno, self.reviewer):
            self.client.force_login(user)
            with self.subTest(user=user.email):
                self.assertEqual(self.client.post(self.cancel).status_code, 404)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, Status.APPROVED)
