"""Solicitação, conflitos e máquina de estados da Agenda."""

import threading
from datetime import date, datetime, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from config.testing import IsolatedCasesMixin
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from bookings.models import CANCEL_DEADLINE_MESSAGE, WEEKEND_MESSAGE, Booking, BookingRequest, InvalidTransition, SlotUnavailable, moment
from bookings.occupancy import find_conflict
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, THURSDAY, frozen_clock, semester_with_lesson, space, submit, user_with
from schedule.models import Allocation

Status = BookingRequest.Status


class BookingTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        frozen_clock(self)
        self.lab = space('Laboratório de Informática 2')
        self.other_lab = space('Laboratório de Informática 3')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.bruno = user_with('bruno@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        semester_with_lesson()

    def approved(self, start, end, day=THURSDAY, target=None):
        request = submit(self.bruno, target or self.lab, day, start, end)
        request.approve(self.reviewer)
        return request

    def assert_refused(self, error_class=ValidationError):
        return self.assertRaises(error_class)


class SubmitTests(BookingTestCase):
    def test_submit_creates_a_pending_request_that_does_not_occupy(self):
        with self.case('pendente sem agendamento'):
            request = submit(self.ana, self.lab, THURSDAY, time(16, 0), time(18, 0))
            self.assertEqual(request.status, Status.PENDING)
            self.assertEqual((request.date, request.start_time, request.end_time), (THURSDAY, time(16, 0), time(18, 0)))
            self.assertEqual(request.requested_by, self.ana)
            self.assertFalse(Booking.objects.exists())
        with self.case('não ocupa o horário'):
            submit(self.ana, self.lab)
            self.assertEqual(submit(self.bruno, self.lab).status, Status.PENDING)

    def test_invalid_data_is_refused(self):
        with self.case('descrição'):
            for description in ('', '   '):
                with self.subTest(description=description), self.assert_refused() as caught:
                    submit(self.ana, self.lab, description=description)
                self.assertIn('description', caught.exception.message_dict)
            self.assertEqual(submit(self.ana, self.lab, description='  Reunião  ').description, 'Reunião')
            self.assertEqual(BookingRequest.objects.count(), 1)
        with self.case('quantidade de estudantes'):
            for count in (None, 0, 1000):
                with self.subTest(count=count), self.assert_refused() as caught:
                    submit(self.ana, self.lab, student_count=count)
                self.assertIn('student_count', caught.exception.message_dict)
            self.assertEqual(submit(self.ana, self.lab, student_count=35).student_count, 35)
            self.assertEqual(BookingRequest.objects.count(), 1)
        with self.case('fim depois do início'):
            for start, end in ((time(16, 0), time(14, 0)), (time(16, 0), time(16, 0))):
                with self.subTest(start=start, end=end), self.assert_refused() as caught:
                    submit(self.ana, self.lab, start=start, end=end)
                self.assertIn('end_time', caught.exception.message_dict)
            self.assertFalse(BookingRequest.objects.exists())

    def test_context_is_refused(self):
        with self.case('início passado'):
            with self.assert_refused() as caught:
                submit(self.ana, self.lab, date(2026, 10, 1), time(9, 0), time(11, 0))
            self.assertIn('start_time', caught.exception.message_dict)
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('espaço desativado'):
            self.other_lab.deactivate()
            with self.assert_refused() as caught:
                submit(self.ana, self.other_lab)
            self.assertIn('space', caught.exception.message_dict)
        with self.case('fora do semestre'):
            with self.assertRaises(ValidationError) as caught:
                submit(self.ana, self.lab, date(2027, 1, 7), time(14, 0), time(16, 0))
            self.assertEqual(
                caught.exception.message_dict['date'],
                ['A data 07/01/2027 está fora do período do semestre 2026/2. Escolha outra data.'],
            )
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('sem a permissão'):
            viewer = user_with('consulta@ifnmg.edu.br', 'AGENDA.VISUALIZAR')
            with self.assert_refused():
                submit(viewer, self.lab)
            self.assertFalse(BookingRequest.objects.exists())

    def test_conflict_with_a_booking_or_a_lesson(self):
        with self.case('agendamento aprovado'):
            self.approved(time(14, 0), time(15, 0), target=self.other_lab)
            with self.assert_refused(SlotUnavailable) as caught:
                submit(self.ana, self.other_lab, start=time(14, 30), end=time(16, 0))
            self.assertEqual(caught.exception.messages, ['Este espaço está ocupado das 14:00 às 15:00. Escolha outro horário.'])
            self.assertEqual(BookingRequest.objects.filter(requested_by=self.ana).count(), 0)
        with self.case('aula do ensalamento'):
            with self.assert_refused(SlotUnavailable) as caught:
                submit(self.ana, self.lab, start=time(14, 0), end=time(16, 0))
            self.assertIn('ensalamento das 14:10 às 15:00', caught.exception.messages[0])


class WeekendTests(BookingTestCase):
    SATURDAY = date(2026, 10, 17)
    SUNDAY = date(2026, 10, 18)

    def test_only_weekdays_are_booked(self):
        with self.case('sábado e domingo'):
            for day in (self.SATURDAY, self.SUNDAY):
                with self.subTest(day=day), self.assert_refused() as caught:
                    submit(self.ana, self.lab, day)
                self.assertEqual(caught.exception.message_dict['date'], [WEEKEND_MESSAGE])
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('dias úteis'):
            for offset in range(5):
                day = date(2026, 10, 19 + offset)
                with self.subTest(day=day):
                    self.assertEqual(submit(self.ana, self.lab, day).status, Status.PENDING)
            self.assertEqual(BookingRequest.objects.count(), 5)
        with self.case('fora do semestre informa o período'):
            with self.assert_refused() as caught:
                submit(self.ana, self.lab, date(2027, 1, 9))
            self.assertEqual(
                caught.exception.message_dict['date'],
                ['A data 09/01/2027 está fora do período do semestre 2026/2. Escolha outra data.'],
            )
        with self.case('sugestão no fim de semana'):
            request = submit(self.ana, self.lab)
            with self.assert_refused() as caught:
                request.suggest(self.reviewer, self.other_lab, self.SATURDAY, time(14, 0), time(16, 0))
            self.assertEqual(caught.exception.message_dict['suggested_date'], [WEEKEND_MESSAGE])
            request.refresh_from_db()
            self.assertEqual(request.status, Status.PENDING)

    def test_requests_from_before_the_rule_are_still_decided(self):
        with self.case('aprovação'):
            request = BookingRequest.objects.create(
                requested_by=self.ana, space=self.lab, date=self.SATURDAY, start_time=time(8, 0), end_time=time(10, 0),
                description='Solicitação anterior à regra.', student_count=30, status=Status.PENDING,
            )
            request.approve(self.reviewer)
            self.assertEqual(request.status, Status.APPROVED)
            self.assertEqual(timezone.localtime(request.booking.starts_at).date(), self.SATURDAY)
        with self.case('aceite da sugestão'):
            request = submit(self.ana, self.lab)
            BookingRequest.objects.filter(pk=request.pk).update(
                status=Status.SUGGESTED, suggested_space=self.other_lab, suggested_date=self.SUNDAY,
                suggested_start_time=time(8, 0), suggested_end_time=time(10, 0), decided_by=self.reviewer,
            )
            request.refresh_from_db()
            request.accept_suggestion(self.ana)
            self.assertEqual(request.status, Status.APPROVED)
            self.assertEqual(timezone.localtime(request.booking.starts_at).date(), self.SUNDAY)


class ConflictTests(BookingTestCase):
    def test_slots_that_do_not_overlap_do_not_conflict(self):
        with self.case('intervalos encostados'):
            self.approved(time(14, 0), time(15, 0), target=self.other_lab)
            request = self.approved(time(15, 0), time(16, 0), target=self.other_lab)
            self.assertEqual(request.status, Status.APPROVED)
            self.assertEqual(Booking.objects.count(), 2)
            self.assertIsNone(find_conflict(self.other_lab, THURSDAY, time(13, 0), time(14, 0)))
        with self.case('encostado na aula'):
            self.assertIsNone(find_conflict(self.lab, THURSDAY, time(15, 0), time(16, 0)))
            self.assertIsNone(find_conflict(self.lab, THURSDAY, time(13, 0), time(14, 10)))
            self.assertIsNotNone(find_conflict(self.lab, THURSDAY, time(14, 59), time(16, 0)))
        with self.case('outro espaço e outro dia'):
            self.approved(time(14, 0), time(16, 0), target=self.other_lab)
            self.assertIsNone(find_conflict(self.lab, THURSDAY, time(16, 0), time(17, 0)))
            self.assertIsNone(find_conflict(self.other_lab, FRIDAY, time(14, 0), time(16, 0)))

    def test_extended_interval_conflicts(self):
        with self.case('fim estendido'):
            self.approved(time(15, 0), time(17, 0), target=self.other_lab)
            self.assertEqual(submit(self.ana, self.other_lab, start=time(13, 0), end=time(15, 0)).status, Status.PENDING)
            for end in (time(15, 1), time(16, 0), time(17, 0), time(18, 0)):
                with self.subTest(end=end), self.assert_refused(SlotUnavailable) as caught:
                    submit(self.ana, self.other_lab, start=time(13, 0), end=end)
                self.assertEqual(caught.exception.messages, ['Este espaço está ocupado das 15:00 às 17:00. Escolha outro horário.'])
        with self.case('aprovação de pedido estendido'):
            longer = submit(self.ana, self.other_lab, start=time(13, 0), end=time(16, 0))
            self.approved(time(15, 0), time(17, 0), target=self.other_lab)
            with self.assert_refused(SlotUnavailable):
                longer.approve(self.reviewer)
            longer.refresh_from_db()
            self.assertEqual(longer.status, Status.PENDING)
            self.assertEqual(Booking.objects.count(), 1)

    def test_database_refuses_overlapping_bookings(self):
        first = self.approved(time(14, 0), time(16, 0), target=self.other_lab)
        second = submit(self.bruno, self.lab, FRIDAY)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                request=second, space=self.other_lab, starts_at=moment(THURSDAY, time(15, 30)), ends_at=moment(THURSDAY, time(17, 0)),
                description='x', requested_by=self.bruno, approved_by=self.reviewer,
            )
        self.assertEqual(Booking.objects.get().request, first)


class ApproveTests(BookingTestCase):
    def test_approve_creates_the_booking_with_the_original_slot(self):
        allocations = Allocation.objects.count()
        request = submit(self.ana, self.lab)
        request.approve(self.reviewer)
        self.assertEqual(request.status, Status.APPROVED)
        self.assertEqual(request.decided_by, self.reviewer)
        booking = request.booking
        self.assertEqual(booking.space, self.lab)
        self.assertEqual(timezone.localtime(booking.starts_at).replace(tzinfo=None).isoformat(), '2026-10-15T16:00:00')
        self.assertEqual(timezone.localtime(booking.ends_at).time(), time(18, 0))
        self.assertEqual(booking.description, request.description)
        self.assertEqual(Allocation.objects.count(), allocations)

    def test_approval_refusals(self):
        with self.case('horário ocupado depois do pedido'):
            first = submit(self.ana, self.lab)
            second = submit(self.bruno, self.lab)
            first.approve(self.reviewer)
            with self.assert_refused(SlotUnavailable):
                second.approve(self.reviewer)
            second.refresh_from_db()
            self.assertEqual(second.status, Status.PENDING)
            self.assertEqual(Booking.objects.count(), 1)
        with self.case('depois do início'):
            request = submit(self.ana, self.lab)
            later = timezone.make_aware(datetime(2026, 10, 15, 17, 0))
            with mock.patch('django.utils.timezone.now', return_value=later), self.assert_refused():
                request.approve(self.reviewer)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.PENDING)
        with self.case('sem a permissão de analisar'):
            request = submit(self.ana, self.lab)
            with self.assert_refused():
                request.approve(self.bruno)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.PENDING)


class RejectTests(BookingTestCase):
    def test_reject_records_the_required_reason(self):
        with self.case('registra o motivo'):
            request = submit(self.ana, self.lab)
            request.reject(self.reviewer, 'Laboratório em manutenção nessa data.')
            self.assertEqual(request.status, Status.REJECTED)
            self.assertEqual(request.rejection_reason, 'Laboratório em manutenção nessa data.')
            self.assertFalse(Booking.objects.exists())
        with self.case('motivo obrigatório'):
            request = submit(self.ana, self.lab)
            with self.assert_refused() as caught:
                request.reject(self.reviewer, '  ')
            self.assertIn('rejection_reason', caught.exception.message_dict)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.PENDING)
        with self.case('depois de uma sugestão'):
            request = submit(self.ana, self.lab)
            request.suggest(self.reviewer, self.other_lab, FRIDAY, time(14, 0), time(16, 0))
            request.reject(self.reviewer, 'Nenhum laboratório disponível.')
            self.assertEqual(request.status, Status.REJECTED)


class SuggestTests(BookingTestCase):
    def suggested(self, message='O laboratório 2 recebe manutenção no dia 15.'):
        request = submit(self.ana, self.lab)
        request.suggest(self.reviewer, self.other_lab, FRIDAY, time(14, 0), time(16, 0), message)
        return request

    def test_suggest_keeps_the_original_data(self):
        with self.case('mantém o original'):
            request = self.suggested()
            self.assertEqual(request.status, Status.SUGGESTED)
            self.assertEqual((request.space, request.date, request.start_time, request.end_time), (self.lab, THURSDAY, time(16, 0), time(18, 0)))
            self.assertEqual(
                (request.suggested_space, request.suggested_date, request.suggested_start_time, request.suggested_end_time),
                (self.other_lab, FRIDAY, time(14, 0), time(16, 0)),
            )
            self.assertEqual(request.suggestion_message, 'O laboratório 2 recebe manutenção no dia 15.')
            self.assertFalse(Booking.objects.exists())
        with self.case('mensagem opcional'):
            self.assertEqual(self.suggested(message='').status, Status.SUGGESTED)
        with self.case('nova sugestão substitui'):
            request = self.suggested()
            request.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0), 'Outro horário.')
            self.assertEqual((request.suggested_start_time, request.suggestion_message), (time(8, 0), 'Outro horário.'))
            self.assertEqual(request.status, Status.SUGGESTED)

    def test_invalid_suggestions_are_refused(self):
        with self.case('igual ao original'):
            request = submit(self.ana, self.lab)
            with self.assert_refused():
                request.suggest(self.reviewer, self.lab, THURSDAY, time(16, 0), time(18, 0))
            request.refresh_from_db()
            self.assertEqual(request.status, Status.PENDING)
        with self.case('horário ocupado'):
            self.approved(time(14, 0), time(16, 0), day=FRIDAY, target=self.other_lab)
            request = submit(self.ana, self.lab)
            with self.assert_refused(SlotUnavailable):
                request.suggest(self.reviewer, self.other_lab, FRIDAY, time(15, 0), time(17, 0))
        with self.case('dados inválidos'):
            request = submit(self.ana, self.lab)
            with self.assert_refused() as caught:
                request.suggest(self.reviewer, self.other_lab, FRIDAY, time(16, 0), time(14, 0))
            self.assertIn('suggested_end_time', caught.exception.message_dict)

    def test_accept_creates_the_booking_unless_occupied(self):
        with self.case('aceite'):
            request = self.suggested()
            request.accept_suggestion(self.ana)
            self.assertEqual(request.status, Status.APPROVED)
            self.assertIsNotNone(request.responded_at)
            booking = request.booking
            self.assertEqual(booking.space, self.other_lab)
            self.assertEqual(timezone.localtime(booking.starts_at).date(), FRIDAY)
            self.assertEqual(booking.approved_by, self.reviewer)
            self.assertEqual((request.space, request.date), (self.lab, THURSDAY))
        with self.case('aceite de horário ocupado'):
            request = self.suggested()
            self.approved(time(15, 0), time(17, 0), day=FRIDAY, target=self.other_lab)
            with self.assert_refused(SlotUnavailable):
                request.accept_suggestion(self.ana)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.SUGGESTED)
            self.assertFalse(Booking.objects.filter(request=request).exists())

    def test_decline_by_the_requester_only(self):
        with self.case('recusa'):
            request = self.suggested()
            request.decline_suggestion(self.ana)
            self.assertEqual(request.status, Status.DECLINED)
            self.assertIsNotNone(request.responded_at)
            self.assertFalse(Booking.objects.exists())
        with self.case('só o solicitante responde'):
            request = self.suggested()
            for answer in (request.accept_suggestion, request.decline_suggestion):
                with self.subTest(answer=answer.__name__), self.assert_refused():
                    answer(self.reviewer)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.SUGGESTED)


class TransitionTests(BookingTestCase):
    def states(self):
        pending = submit(self.ana, self.lab, start=time(8, 0), end=time(9, 0))
        approved = submit(self.ana, self.lab, start=time(9, 0), end=time(10, 0))
        approved.approve(self.reviewer)
        rejected = submit(self.ana, self.lab, start=time(10, 0), end=time(11, 0))
        rejected.reject(self.reviewer, 'Motivo.')
        suggested = submit(self.ana, self.lab, start=time(11, 0), end=time(12, 0))
        suggested.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0))
        declined = submit(self.ana, self.lab, start=time(12, 0), end=time(13, 0))
        declined.suggest(self.reviewer, self.other_lab, FRIDAY, time(9, 0), time(10, 0))
        declined.decline_suggestion(self.ana)
        return {Status.PENDING: pending, Status.APPROVED: approved, Status.REJECTED: rejected, Status.SUGGESTED: suggested, Status.DECLINED: declined}

    def test_only_the_table_transitions_are_accepted(self):
        allowed = {
            'approve': {Status.PENDING},
            'reject': {Status.PENDING, Status.SUGGESTED},
            'suggest': {Status.PENDING, Status.SUGGESTED},
            'accept_suggestion': {Status.SUGGESTED},
            'decline_suggestion': {Status.SUGGESTED},
        }
        actions = {
            'approve': lambda request: request.approve(self.reviewer),
            'reject': lambda request: request.reject(self.reviewer, 'Motivo.'),
            'suggest': lambda request: request.suggest(self.reviewer, self.other_lab, date(2026, 10, 20), time(8, 0), time(9, 0)),
            'accept_suggestion': lambda request: request.accept_suggestion(self.ana),
            'decline_suggestion': lambda request: request.decline_suggestion(self.ana),
        }
        for name, action in actions.items():
            for status, request in self.states().items():
                if status in allowed[name]:
                    continue
                with self.subTest(action=name, status=status):
                    bookings = Booking.objects.count()
                    with self.assertRaises(InvalidTransition):
                        action(request)
                    request.refresh_from_db()
                    self.assertEqual(request.status, status)
                    self.assertEqual(Booking.objects.count(), bookings)
            Booking.objects.all().delete()
            BookingRequest.objects.all().delete()

    def test_double_decision(self):
        request = submit(self.ana, self.lab)
        stale = BookingRequest.objects.get(pk=request.pk)
        request.reject(self.reviewer, 'Motivo.')
        with self.assertRaises(InvalidTransition):
            stale.approve(self.reviewer)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.REJECTED)


class CancelTests(BookingTestCase):
    def approved_for_ana(self, day=THURSDAY, start=time(16, 0), end=time(18, 0)):
        request = submit(self.ana, self.lab, day, start, end)
        request.approve(self.reviewer)
        return request

    def at(self, hour, minute, day=THURSDAY):
        patcher = mock.patch('django.utils.timezone.now', return_value=timezone.make_aware(datetime.combine(day, time(hour, minute))))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_requester_and_reviewer_cancel_and_free_the_slot(self):
        for user, reason in ((self.ana, ''), (self.reviewer, '  Turma em visita técnica.  ')):
            with self.subTest(user=user.email):
                request = self.approved_for_ana()
                request.cancel(user, reason)
                self.assertEqual(request.status, Status.CANCELLED)
                self.assertEqual((request.cancelled_by, request.cancellation_reason), (user, reason.strip()))
                self.assertIsNotNone(request.cancelled_at)
                self.assertFalse(Booking.objects.exists())
                self.assertIsNone(find_conflict(self.lab, THURSDAY, time(16, 0), time(18, 0)))
                BookingRequest.objects.all().delete()

    def test_deadline_is_one_hour_before_the_start(self):
        request = self.approved_for_ana()
        for hour, minute in ((15, 1), (15, 0)):
            self.at(hour, minute)
            with self.subTest(at=f'{hour}:{minute:02}'):
                self.assertFalse(request.can_cancel(self.ana))
                with self.assert_refused() as caught:
                    request.cancel(self.ana)
                self.assertEqual(caught.exception.messages, [CANCEL_DEADLINE_MESSAGE])
                request.refresh_from_db()
                self.assertEqual(request.status, Status.APPROVED)
                self.assertTrue(Booking.objects.exists())
        self.at(14, 59)
        self.assertTrue(request.can_cancel(self.ana))
        request.cancel(self.ana)
        self.assertEqual(request.status, Status.CANCELLED)

    def test_deadline_uses_the_accepted_suggestion(self):
        request = submit(self.ana, self.lab, THURSDAY, time(16, 0), time(18, 0))
        request.suggest(self.reviewer, self.other_lab, THURSDAY, time(10, 0), time(11, 0))
        request.accept_suggestion(self.ana)
        self.at(9, 30)
        with self.assert_refused():
            request.cancel(self.ana)
        self.at(8, 59)
        request.cancel(self.ana)
        self.assertEqual(request.status, Status.CANCELLED)
        self.assertIsNone(find_conflict(self.other_lab, THURSDAY, time(10, 0), time(11, 0)))

    def test_cancel_refusals(self):
        with self.case('outro usuário'):
            request = self.approved_for_ana()
            self.assertFalse(request.can_cancel(self.bruno))
            with self.assert_refused():
                request.cancel(self.bruno)
            request.refresh_from_db()
            self.assertEqual(request.status, Status.APPROVED)
            self.assertTrue(Booking.objects.exists())
        with self.case('só aprovadas'):
            pending = submit(self.ana, self.lab, start=time(8, 0), end=time(9, 0))
            rejected = submit(self.ana, self.lab, start=time(10, 0), end=time(11, 0))
            rejected.reject(self.reviewer, 'Motivo.')
            cancelled = self.approved_for_ana()
            cancelled.cancel(self.ana)
            for request in (pending, rejected, cancelled):
                with self.subTest(status=request.status):
                    status = request.status
                    self.assertFalse(request.can_cancel(self.reviewer))
                    with self.assertRaises(InvalidTransition):
                        request.cancel(self.reviewer)
                    request.refresh_from_db()
                    self.assertEqual(request.status, status)


class ConcurrentApprovalTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        frozen_clock(self)
        self.lab = space('Laboratório de Informática 4')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)

    def test_simultaneous_approvals_create_one_booking(self):
        first = submit(self.ana, self.lab, start=time(14, 0), end=time(16, 0))
        second = submit(self.ana, self.lab, start=time(15, 0), end=time(17, 0))
        barrier = threading.Barrier(2)
        errors = []

        def approve(request):
            try:
                barrier.wait()
                request.approve(self.reviewer)
            except ValidationError as error:
                errors.append(error)
            finally:
                connection.close()

        threads = [threading.Thread(target=approve, args=(request,)) for request in (first, second)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            sorted(BookingRequest.objects.values_list('status', flat=True)),
            sorted([Status.APPROVED, Status.PENDING]),
        )


class SpaceDeletionTests(BookingTestCase):
    def test_space_with_requests_is_not_deleted(self):
        submit(self.ana, self.other_lab)
        with self.assertRaises(ValidationError) as caught:
            self.other_lab.delete_space()
        self.assertIn('solicitações de agendamento', caught.exception.messages[0])
        self.assertTrue(type(self.other_lab).objects.filter(pk=self.other_lab.pk).exists())
