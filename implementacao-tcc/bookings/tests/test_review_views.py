"""Análise das solicitações: lista, detalhe, aprovação, rejeição e alternativa."""

from datetime import time

from django.db import connection
from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from bookings.models import Booking, BookingRequest
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, frozen_clock, semester_with_lesson, space, submit, user_with
from schedule.models import Space

Status = BookingRequest.Status
LIST = reverse('agenda_review_list')


def url(name, request):
    return reverse(name, args=[request.pk])


class ReviewTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        frozen_clock(self)
        semester_with_lesson()
        self.lab = Space.objects.get(name='Laboratório de Informática 2')
        self.other_lab = space('Laboratório de Informática 3')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.bruno = user_with('bruno@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        self.request = submit(self.ana, self.lab)
        self.client.force_login(self.reviewer)

    def suggestion(self, **values):
        return {
            'suggested_space': self.other_lab.pk, 'suggested_date': '2026-10-16', 'suggested_start_time': '14:00',
            'suggested_end_time': '16:00', 'suggestion_message': 'O laboratório 2 recebe manutenção no dia 15.',
        } | values


class ListTests(ReviewTestCase):
    def test_lists_only_what_needs_a_decision_by_default(self):
        suggested = submit(self.bruno, self.lab, start=time(8, 0), end=time(9, 0), description='Com alternativa.')
        suggested.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0))
        approved = submit(self.bruno, self.lab, start=time(9, 0), end=time(10, 0), description='Já aprovada.')
        approved.approve(self.reviewer)
        content = self.client.get(LIST).content.decode()
        self.assertIn('Reunião do projeto de extensão com os alunos.', content)
        self.assertIn('Com alternativa.', content)
        self.assertNotIn('Já aprovada.', content)
        self.assertIn('ana@ifnmg.edu.br', content)
        self.assertLess(content.index('Reunião do projeto'), content.index('Com alternativa.'))
        self.assertIn('Já aprovada.', self.client.get(LIST, {'situacao': 'todas'}).content.decode())


class DetailTests(ReviewTestCase):
    def test_detail_has_what_is_needed_to_decide(self):
        with self.case('dados para decidir'):
            content = self.client.get(url('agenda_review_detail', self.request)).content.decode()
            for text in (
                self.ana.name, 'ana@ifnmg.edu.br', 'Laboratório de Informática 2', '15/10/2026, das 16:00 às 18:00',
                'Reunião do projeto de extensão com os alunos.', 'Quantidade de alunos', 'Pendente', 'Solicitação criada', 'Aprovar', 'Rejeitar', 'Sugerir alternativa',
            ):
                with self.subTest(text=text):
                    self.assertIn(text, content)
        with self.case('sem dados pessoais desnecessários'):
            content = self.client.get(url('agenda_review_detail', self.request)).content.decode()
            self.assertNotIn('Perfil', content)
            self.assertNotIn('AGENDA.SOLICITAR', content)
        with self.case('encerrada sem ações'):
            self.request.reject(self.reviewer, 'Motivo.')
            content = self.client.get(url('agenda_review_detail', self.request)).content.decode()
            self.assertNotIn(url('agenda_review_approve', self.request), content)
            self.assertIn('Rejeitada', content)
            self.assertIn(f'por {self.reviewer.name}', content)


class DecisionTests(ReviewTestCase):
    def test_decisions(self):
        with self.case('aprovar'):
            response = self.client.post(url('agenda_review_approve', self.request))
            self.assertRedirects(response, url('agenda_review_detail', self.request), fetch_redirect_response=False)
            self.request.refresh_from_db()
            self.assertEqual(self.request.status, Status.APPROVED)
            self.assertEqual(Booking.objects.get(request=self.request).student_count, 30)
        with self.case('rejeitar'):
            self.client.post(url('agenda_review_reject', self.request), {'rejection_reason': 'Laboratório em manutenção nessa data.'})
            self.request.refresh_from_db()
            self.assertEqual((self.request.status, self.request.rejection_reason), (Status.REJECTED, 'Laboratório em manutenção nessa data.'))
        with self.case('formulário da sugestão'):
            content = self.client.get(url('agenda_review_suggest', self.request)).content.decode()
            self.assertRegex(content, rf'<option value="{self.lab.pk}" selected>')
            self.assertIn('name="suggested_date" value="2026-10-15"', content)
        with self.case('sugerir'):
            self.client.post(url('agenda_review_suggest', self.request), self.suggestion())
            self.request.refresh_from_db()
            self.assertEqual(self.request.status, Status.SUGGESTED)
            self.assertEqual((self.request.suggested_space, self.request.suggested_date), (self.other_lab, FRIDAY))
            self.assertEqual(self.request.space, self.lab)

    def test_refusals_appear_on_the_form(self):
        with self.case('rejeitar sem motivo'):
            response = self.client.post(url('agenda_review_reject', self.request), {'rejection_reason': '  '})
            self.assertContains(response, 'Informe o motivo da rejeição.')
            self.request.refresh_from_db()
            self.assertEqual(self.request.status, Status.PENDING)
        with self.case('sugestão igual ao original'):
            response = self.client.post(url('agenda_review_suggest', self.request), self.suggestion(
                suggested_space=self.lab.pk, suggested_date='2026-10-15', suggested_start_time='16:00', suggested_end_time='18:00',
            ))
            self.assertContains(response, 'A alternativa deve mudar o espaço, a data ou o horário da solicitação.')


class CancelTests(ReviewTestCase):
    def test_cancel_only_approved_requests(self):
        with self.case('aprovada'):
            self.request.approve(self.reviewer)
            detail = url('agenda_review_detail', self.request)
            self.assertTrue(self.client.get(detail).context['can_cancel'])
            response = self.client.post(url('agenda_review_cancel', self.request), {'cancellation_reason': ''})
            self.assertRedirects(response, detail, fetch_redirect_response=False)
            self.request.refresh_from_db()
            self.assertEqual((self.request.status, self.request.cancelled_by), (Status.CANCELLED, self.reviewer))
            self.assertFalse(Booking.objects.exists())
            self.assertContains(self.client.get(detail), 'Agendamento cancelado')
        with self.case('pendente'):
            self.assertFalse(self.client.get(url('agenda_review_detail', self.request)).context['can_cancel'])
            response = self.client.post(url('agenda_review_cancel', self.request), {'cancellation_reason': ''})
            self.assertContains(response, 'Esta solicitação está pendente e não aceita esta ação.')
