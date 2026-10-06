"""Solicitação, conflitos e máquina de estados da Agenda (D3 a D6)."""

import threading
from datetime import date, datetime, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from bookings.models import Booking, BookingRequest, InvalidTransition, SlotUnavailable, moment
from bookings.occupancy import find_conflict
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, THURSDAY, frozen_clock, semester_with_lesson, space, submit, user_with
from schedule.models import Allocation

Status = BookingRequest.Status


class BookingTestCase(TestCase):
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
    def test_submit_creates_a_pending_request_without_booking(self):
        request = submit(self.ana, self.lab, THURSDAY, time(16, 0), time(18, 0))
        self.assertEqual(request.status, Status.PENDING)
        self.assertEqual((request.date, request.start_time, request.end_time), (THURSDAY, time(16, 0), time(18, 0)))
        self.assertEqual(request.requested_by, self.ana)
        self.assertFalse(Booking.objects.exists())

    def test_description_is_required_and_trimmed(self):
        for description in ('', '   '):
            with self.subTest(description=description), self.assert_refused() as caught:
                submit(self.ana, self.lab, description=description)
            self.assertIn('description', caught.exception.message_dict)
        self.assertEqual(submit(self.ana, self.lab, description='  Reunião  ').description, 'Reunião')
        self.assertEqual(BookingRequest.objects.count(), 1)

    def test_student_count_is_required_and_positive(self):
        for count in (None, 0, 1000):
            with self.subTest(count=count), self.assert_refused() as caught:
                submit(self.ana, self.lab, student_count=count)
            self.assertIn('student_count', caught.exception.message_dict)
        self.assertEqual(submit(self.ana, self.lab, student_count=35).student_count, 35)
        self.assertEqual(BookingRequest.objects.count(), 1)

    def test_end_must_follow_start(self):
        for start, end in ((time(16, 0), time(14, 0)), (time(16, 0), time(16, 0))):
            with self.subTest(start=start, end=end), self.assert_refused() as caught:
                submit(self.ana, self.lab, start=start, end=end)
            self.assertIn('end_time', caught.exception.message_dict)
        self.assertFalse(BookingRequest.objects.exists())

    def test_past_start_is_refused(self):
        with self.assert_refused() as caught:
            submit(self.ana, self.lab, date(2026, 10, 1), time(9, 0), time(11, 0))
        self.assertIn('start_time', caught.exception.message_dict)
        self.assertFalse(BookingRequest.objects.exists())

    def test_inactive_space_is_refused(self):
        self.other_lab.deactivate()
        with self.assert_refused() as caught:
            submit(self.ana, self.other_lab)
        self.assertIn('space', caught.exception.message_dict)

    def test_conflict_with_an_approved_booking(self):
        self.approved(time(14, 0), time(15, 0), target=self.other_lab)
        with self.assert_refused(SlotUnavailable) as caught:
            submit(self.ana, self.other_lab, start=time(14, 30), end=time(16, 0))
        self.assertEqual(caught.exception.messages, ['Este espaço está ocupado das 14:00 às 15:00. Escolha outro horário.'])
        self.assertEqual(BookingRequest.objects.filter(requested_by=self.ana).count(), 0)

    def test_conflict_with_the_space_allocation(self):
        with self.assert_refused(SlotUnavailable) as caught:
            submit(self.ana, self.lab, start=time(14, 0), end=time(16, 0))
        self.assertIn('ensalamento das 14:10 às 15:00', caught.exception.messages[0])

    def test_date_outside_the_semester_period_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            submit(self.ana, self.lab, date(2027, 1, 7), time(14, 0), time(16, 0))
        self.assertEqual(
            caught.exception.message_dict['date'],
            ['A data 07/01/2027 está fora do período do semestre 2026/2. Escolha outra data.'],
        )
        self.assertFalse(BookingRequest.objects.exists())

    def test_pending_request_does_not_occupy_the_slot(self):
        submit(self.ana, self.lab)
        self.assertEqual(submit(self.bruno, self.lab).status, Status.PENDING)

    def test_requires_the_request_permission(self):
        viewer = user_with('consulta@ifnmg.edu.br', 'AGENDA.VISUALIZAR')
        with self.assert_refused():
            submit(viewer, self.lab)
        self.assertFalse(BookingRequest.objects.exists())


class ConflictTests(BookingTestCase):
    def test_touching_intervals_do_not_conflict(self):
        self.approved(time(14, 0), time(15, 0), target=self.other_lab)
        request = self.approved(time(15, 0), time(16, 0), target=self.other_lab)
        self.assertEqual(request.status, Status.APPROVED)
        self.assertEqual(Booking.objects.count(), 2)
        self.assertIsNone(find_conflict(self.other_lab, THURSDAY, time(13, 0), time(14, 0)))

    def test_touching_the_space_allocation_does_not_conflict(self):
        self.assertIsNone(find_conflict(self.lab, THURSDAY, time(15, 0), time(16, 0)))
        self.assertIsNone(find_conflict(self.lab, THURSDAY, time(13, 0), time(14, 10)))
        self.assertIsNotNone(find_conflict(self.lab, THURSDAY, time(14, 59), time(16, 0)))

    def test_other_space_and_other_day_do_not_conflict(self):
        self.approved(time(14, 0), time(16, 0), target=self.other_lab)
        self.assertIsNone(find_conflict(self.lab, THURSDAY, time(16, 0), time(17, 0)))
        self.assertIsNone(find_conflict(self.other_lab, FRIDAY, time(14, 0), time(16, 0)))

    def test_conflict_uses_two_queries(self):
        with CaptureQueriesContext(connection) as queries:
            find_conflict(self.lab, THURSDAY, time(16, 0), time(18, 0))
        self.assertEqual(len(queries), 2)

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

    def test_slot_taken_after_the_request(self):
        first = submit(self.ana, self.lab)
        second = submit(self.bruno, self.lab)
        first.approve(self.reviewer)
        with self.assert_refused(SlotUnavailable):
            second.approve(self.reviewer)
        second.refresh_from_db()
        self.assertEqual(second.status, Status.PENDING)
        self.assertEqual(Booking.objects.count(), 1)

    def test_approve_after_the_start_passed(self):
        request = submit(self.ana, self.lab)
        later = timezone.make_aware(datetime(2026, 10, 15, 17, 0))
        with mock.patch('django.utils.timezone.now', return_value=later), self.assert_refused():
            request.approve(self.reviewer)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.PENDING)

    def test_approve_requires_the_review_permission(self):
        request = submit(self.ana, self.lab)
        with self.assert_refused():
            request.approve(self.bruno)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.PENDING)


class RejectTests(BookingTestCase):
    def test_reject_records_the_reason(self):
        request = submit(self.ana, self.lab)
        request.reject(self.reviewer, 'Laboratório em manutenção nessa data.')
        self.assertEqual(request.status, Status.REJECTED)
        self.assertEqual(request.rejection_reason, 'Laboratório em manutenção nessa data.')
        self.assertFalse(Booking.objects.exists())

    def test_reason_is_required(self):
        request = submit(self.ana, self.lab)
        with self.assert_refused() as caught:
            request.reject(self.reviewer, '  ')
        self.assertIn('rejection_reason', caught.exception.message_dict)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.PENDING)

    def test_reject_after_a_suggestion(self):
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
        request = self.suggested()
        self.assertEqual(request.status, Status.SUGGESTED)
        self.assertEqual((request.space, request.date, request.start_time, request.end_time), (self.lab, THURSDAY, time(16, 0), time(18, 0)))
        self.assertEqual(
            (request.suggested_space, request.suggested_date, request.suggested_start_time, request.suggested_end_time),
            (self.other_lab, FRIDAY, time(14, 0), time(16, 0)),
        )
        self.assertEqual(request.suggestion_message, 'O laboratório 2 recebe manutenção no dia 15.')
        self.assertFalse(Booking.objects.exists())

    def test_message_is_optional(self):
        self.assertEqual(self.suggested(message='').status, Status.SUGGESTED)

    def test_same_as_the_original_is_refused(self):
        request = submit(self.ana, self.lab)
        with self.assert_refused():
            request.suggest(self.reviewer, self.lab, THURSDAY, time(16, 0), time(18, 0))
        request.refresh_from_db()
        self.assertEqual(request.status, Status.PENDING)

    def test_occupied_suggestion_is_refused(self):
        self.approved(time(14, 0), time(16, 0), day=FRIDAY, target=self.other_lab)
        request = submit(self.ana, self.lab)
        with self.assert_refused(SlotUnavailable):
            request.suggest(self.reviewer, self.other_lab, FRIDAY, time(15, 0), time(17, 0))

    def test_invalid_suggestion_is_refused(self):
        request = submit(self.ana, self.lab)
        with self.assert_refused() as caught:
            request.suggest(self.reviewer, self.other_lab, FRIDAY, time(16, 0), time(14, 0))
        self.assertIn('suggested_end_time', caught.exception.message_dict)

    def test_new_suggestion_replaces_the_previous(self):
        request = self.suggested()
        request.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0), 'Outro horário.')
        self.assertEqual((request.suggested_start_time, request.suggestion_message), (time(8, 0), 'Outro horário.'))
        self.assertEqual(request.status, Status.SUGGESTED)

    def test_accept_creates_the_booking_with_the_suggestion(self):
        request = self.suggested()
        request.accept_suggestion(self.ana)
        self.assertEqual(request.status, Status.APPROVED)
        self.assertIsNotNone(request.responded_at)
        booking = request.booking
        self.assertEqual(booking.space, self.other_lab)
        self.assertEqual(timezone.localtime(booking.starts_at).date(), FRIDAY)
        self.assertEqual(booking.approved_by, self.reviewer)
        self.assertEqual((request.space, request.date), (self.lab, THURSDAY))

    def test_accept_an_occupied_suggestion(self):
        request = self.suggested()
        self.approved(time(15, 0), time(17, 0), day=FRIDAY, target=self.other_lab)
        with self.assert_refused(SlotUnavailable):
            request.accept_suggestion(self.ana)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.SUGGESTED)
        self.assertFalse(Booking.objects.filter(request=request).exists())

    def test_decline_closes_without_booking(self):
        request = self.suggested()
        request.decline_suggestion(self.ana)
        self.assertEqual(request.status, Status.DECLINED)
        self.assertIsNotNone(request.responded_at)
        self.assertFalse(Booking.objects.exists())

    def test_only_the_requester_answers(self):
        request = self.suggested()
        for answer in (request.accept_suggestion, request.decline_suggestion):
            with self.subTest(answer=answer.__name__), self.assert_refused():
                answer(self.reviewer)
        request.refresh_from_db()
        self.assertEqual(request.status, Status.SUGGESTED)


class TransitionTests(BookingTestCase):
    def states(self):
        """Uma solicitação em cada estado."""
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
