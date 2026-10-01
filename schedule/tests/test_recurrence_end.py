"""Encerramento de uma aula a partir de uma data (Change encerrar-recorrencia-do-ensalamento)."""

import re
from datetime import date, time, timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from schedule.models import Allocation, AllocationException, ClassGroup, Course, Semester, Space, Stage, Subject, Teacher, Weekday
from schedule.occupancy import occupancy
from schedule.tests.test_occurrence_cancel import user_with
from schedule.tests.test_timetable import allocate

TODAY = date(2026, 9, 1)
BEFORE = date(2026, 9, 28)
PAST = date(2026, 8, 24)
CUT = date(2026, 10, 5)
AFTER = date(2026, 10, 12)
GRID = reverse('space_allocation_grid')
END = reverse('space_allocation_recurrence_end')
PUBLIC = reverse('public_calendar')


class EndingTestCase(TestCase):
    """Cálculo III às segundas, das 10:00 às 12:00 em duas faixas, na Sala 5."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        cls.first = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(10, 0), time(11, 0), 'Sala 5', ['Viviane'])
        cls.second = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(11, 0), time(12, 0), 'Sala 5', ['Viviane'])
        cls.room = Space.objects.get(name='Sala 5')
        view = permissions.SPACE_ALLOCATION_VIEW
        cls.ender = user_with('coord@ifnmg.edu.br', 'coord', view, permissions.SPACE_ALLOCATION_END_RECURRENCE)
        cls.canceller = user_with('gestor@ifnmg.edu.br', 'gestor', view, permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE)
        cls.viviane = user_with('viviane@ifnmg.edu.br', 'VIVIANE', view)
        cls.superadmin = user_with('super@ifnmg.edu.br', 'super')
        User.objects.filter(pk=cls.superadmin.pk).update(is_superadmin=True)
        cls.superadmin.refresh_from_db()

    def setUp(self):
        patcher = mock.patch('django.utils.timezone.localdate', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def end(self, user=None, cut=CUT, allocations=None):
        allocations = allocations or (self.first, self.second)
        return Allocation.objects.end_recurrence(
            [allocation.pk for allocation in allocations], cut, user or self.superadmin,
        )

    def lessons(self, start, end):
        return sorted({item.date for item in occupancy(self.room, start, end) if item.entry.subject == 'Cálculo III'})

    def url(self, day=CUT):
        return f'{END}?data={day.isoformat()}&alocacao={self.first.pk}&alocacao={self.second.pk}'

    def text(self, response):
        return re.sub(r'\s+', ' ', response.content.decode())


class EndingTests(EndingTestCase):
    def test_each_allocation_ends_the_day_before(self):
        self.end()
        for allocation in (self.first, self.second):
            allocation.refresh_from_db()
            self.assertEqual(allocation.valid_until, CUT - timedelta(days=1))

    def test_following_occurrences_are_gone(self):
        self.end()
        self.assertEqual(self.lessons(CUT, AFTER), [])

    def test_earlier_occurrences_remain(self):
        self.end()
        self.assertEqual(self.lessons(BEFORE, BEFORE), [BEFORE])

    def test_nothing_is_deleted(self):
        count = Allocation.objects.count()
        self.end()
        self.assertEqual(Allocation.objects.count(), count)

    def test_lesson_that_has_not_started_yet(self):
        for allocation in (self.first, self.second):
            allocation.valid_from = CUT
            allocation.save(update_fields=['valid_from'])
        self.end()
        self.first.refresh_from_db()
        self.assertEqual(self.first.valid_until, CUT - timedelta(days=1))
        self.assertEqual(self.lessons(self.semester.start_date, self.semester.end_date), [])

    def test_refuses_a_date_without_the_lesson(self):
        with self.assertRaises(ValidationError):
            self.end(cut=date(2026, 10, 6))
        self.first.refresh_from_db()
        self.assertIsNone(self.first.valid_until)

    def test_refuses_a_date_in_the_past(self):
        with self.assertRaises(ValidationError):
            self.end(cut=date(2026, 8, 24))
        self.first.refresh_from_db()
        self.assertIsNone(self.first.valid_until)

    def test_refuses_a_date_outside_the_semester(self):
        with self.assertRaises(ValidationError):
            self.end(cut=date(2027, 1, 4))
        self.first.refresh_from_db()
        self.assertIsNone(self.first.valid_until)

    def test_cancelled_occurrences_are_kept(self):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], BEFORE, self.canceller)
        self.end()
        self.assertTrue(AllocationException.objects.filter(allocation=self.first, date=BEFORE).exists())

    def test_cancelled_occurrences_do_not_count(self):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], CUT, self.canceller)
        plan = Allocation.objects.plan_ending([self.first.pk, self.second.pk], CUT, self.superadmin)
        dates = [day for day in self.lessons(CUT, self.semester.end_date)]
        self.assertEqual(plan.removed, len(dates))

    def test_records_the_audit_entry(self):
        self.end()
        logs = AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION, action=catalog.UPDATE)
        self.assertEqual(logs.count(), 2)
        log = logs.get(resource_id=str(self.first.pk))
        self.assertEqual(log.new_values['vigente_ate'], (CUT - timedelta(days=1)).isoformat())
        self.assertEqual(log.metadata['a_partir_de'], CUT.isoformat())
        self.assertEqual(log.metadata['aulas_encerradas'], 11)

    def test_refusal_leaves_no_audit_entry(self):
        with self.assertRaises(ValidationError):
            self.end(cut=date(2026, 10, 6))
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION).exists())

    def test_reimport_does_not_recreate_the_lesson(self):
        self.end()
        before = list(Allocation.objects.order_by('pk').values())
        allocation, action, changes = Allocation.objects.apply(
            self.semester, self.group, self.first.subject, Weekday.MONDAY, self.first.time_slot,
            space=self.room, teachers=[Teacher.objects.get(name='Viviane')],
        )
        self.assertEqual((action, changes), ('unchanged', {}))
        self.assertEqual(list(Allocation.objects.order_by('pk').values()), before)

    def test_public_calendar_before_and_after_the_date(self):
        self.end()
        before = Client().get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-09-28', 'fim': '2026-10-02'})
        after = Client().get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-10-05', 'fim': '2026-10-09'})
        self.assertContains(before, 'Cálculo III')
        self.assertNotContains(after, 'Cálculo III')


class EndingPermissionTests(EndingTestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = Client().get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=', response['Location'])

    def test_cancel_permission_does_not_grant_ending(self):
        client = Client()
        client.force_login(self.canceller)
        self.assertEqual(client.get(self.url()).status_code, 403)

    def test_teacher_of_the_lesson_does_not_end_it(self):
        with self.assertRaises(ValidationError):
            self.end(user=self.viviane)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.valid_until)

    def test_superadmin_ends_without_the_permission_granted(self):
        self.assertFalse(self.superadmin.role.permissions.filter(code=permissions.SPACE_ALLOCATION_END_RECURRENCE).exists())
        self.end(user=self.superadmin)
        self.first.refresh_from_db()
        self.assertEqual(self.first.valid_until, CUT - timedelta(days=1))

    def test_post_without_csrf_is_refused(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.ender)
        self.assertEqual(client.post(self.url()).status_code, 403)


class EndingScreenTests(EndingTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.ender)

    def test_get_shows_the_confirmation_without_changing(self):
        response = self.client.get(self.url())
        content = self.text(response)
        self.assertIn('Encerrar a aula de Cálculo III', content)
        self.assertIn('11 aulas', content)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.valid_until)

    def test_post_ends_and_returns_to_the_grid(self):
        response = self.client.post(self.url())
        self.first.refresh_from_db()
        self.assertEqual(self.first.valid_until, CUT - timedelta(days=1))
        self.assertEqual(response.status_code, 302)
        self.assertIn(GRID, response['Location'])

    def test_unknown_allocation_is_not_found(self):
        self.assertEqual(self.client.get(f'{END}?data={CUT.isoformat()}&alocacao=9999').status_code, 404)

    def test_date_without_the_lesson_is_not_found(self):
        self.assertEqual(self.client.get(self.url(date(2026, 10, 6))).status_code, 404)

    def test_grid_offers_the_action(self):
        response = self.client.get(f'{GRID}?semestre=2026/2&sala=Sala 5&semana={CUT.isoformat()}')
        self.assertContains(response, 'Encerrar recorrência')

    def test_grid_without_the_permission_hides_the_action(self):
        self.client.force_login(self.canceller)
        response = self.client.get(f'{GRID}?semestre=2026/2&sala=Sala 5&semana={CUT.isoformat()}')
        self.assertNotContains(response, 'Encerrar recorrência')

    def test_past_week_does_not_offer_the_action(self):
        response = self.client.get(f'{GRID}?semestre=2026/2&sala=Sala 5&semana={PAST.isoformat()}')
        self.assertNotContains(response, 'Encerrar recorrência')
