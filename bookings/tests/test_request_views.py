"""Solicitação pela tela, "Minhas solicitações" e a resposta à alternativa (D1, D8)."""

from datetime import time

from django.test import Client, TestCase
from django.urls import reverse

from accounts import permissions
from bookings.models import Booking, BookingRequest
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, THURSDAY, frozen_clock, semester_with_lesson, space, submit, user_with
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

    def data(self, **values):
        return {
            'space': self.lab.pk, 'date': '2026-10-15', 'start_time': '16:00', 'end_time': '18:00',
            'description': 'Reunião do projeto de extensão com os alunos.',
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

    def test_anonymous_is_sent_to_the_login_with_next(self):
        for url in self.routes():
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"{reverse('account_login')}?next={url}", fetch_redirect_response=False)

    def test_without_the_request_permission(self):
        self.client.force_login(self.viewer)
        for url in self.routes():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_with_the_request_permission(self):
        self.client.force_login(self.ana)
        for url in self.routes():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_post_without_the_permission_creates_nothing(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.post(CREATE, self.data()).status_code, 403)
        self.assertFalse(BookingRequest.objects.exists())

    def test_post_without_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.ana)
        self.assertEqual(client.post(CREATE, self.data()).status_code, 403)
        request = self.suggested()
        self.assertEqual(client.post(reverse('agenda_my_request_accept', args=[request.pk])).status_code, 403)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.SUGGESTED)


class CreateTests(RequestScreenTestCase):
    def test_modal_is_filled_from_the_slot(self):
        self.client.force_login(self.ana)
        response = self.client.get(CREATE, {'espaco': self.lab.pk, 'data': '2026-10-15', 'inicio': '14:00', 'fim': '16:00'}, headers={'HX-Request': 'true'})
        content = response.content.decode()
        self.assertIn('<dialog class="modal"', content)
        self.assertIn('Laboratório de Informática 2.', content)
        self.assertIn(f'name="space" value="{self.lab.pk}"', content)
        self.assertRegex(content, r'name="date" value="2026-10-15"[^>]*readonly')
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

    def test_occupied_slot(self):
        approved = submit(self.bruno, self.lab, start=time(16, 0), end=time(17, 0))
        approved.approve(self.reviewer)
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(start_time='16:30'))
        self.assertContains(response, 'Este espaço está ocupado das 16:00 às 17:00. Escolha outro horário.')
        self.assertEqual(BookingRequest.objects.filter(requested_by=self.ana).count(), 0)

    def test_conflict_with_the_space_allocation(self):
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(start_time='14:00', end_time='16:00'))
        self.assertContains(response, 'Este espaço está ocupado pelo ensalamento das 14:10 às 15:00. Escolha outro horário.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_end_before_start(self):
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(start_time='16:00', end_time='14:00'))
        self.assertContains(response, 'O fim deve ser posterior ao início.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_forged_inactive_space(self):
        self.other_lab.deactivate()
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(space=self.other_lab.pk))
        self.assertContains(response, 'O espaço Laboratório de Informática 3 está desativado. Escolha outro espaço.')
        self.assertFalse(BookingRequest.objects.exists())

    def test_forged_unknown_space(self):
        self.client.force_login(self.ana)
        response = self.client.post(CREATE, self.data(space=999999))
        self.assertContains(response, 'Escolha o espaço na Grade da Agenda.')
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

    def test_without_the_request_permission(self):
        self.assertNotIn(CREATE, self.grid(self.viewer))

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
