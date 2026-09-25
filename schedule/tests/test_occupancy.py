"""Ocorrências de um espaço num intervalo, calculadas das alocações e nunca gravadas."""

from datetime import date, time

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from schedule.models import Allocation, ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.occupancy import SPACE_ALLOCATION, AllocationSource, Occurrence, occupancy
from schedule.tests.test_timetable import allocate
from schedule.timetable import Entry


class OtherSource:
    """Fonte de teste, no lugar da reserva futura."""

    def occurrences(self, space, start_date, end_date):
        return [Occurrence(
            date=date(2026, 10, 6), start=time(21, 0), end=time(21, 50), space_id=space.pk,
            kind='TESTE', entry=Entry(subject='Reunião do curso', group_label='', teachers=(), stage=''),
        )]


class OccupancyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(19, 0), time(19, 50), '1/13', ['Viviane'])
        allocate(cls.semester, cls.group, 'Física', Weekday.WEDNESDAY, time(19, 0), time(19, 50), '1/4')
        allocate(cls.semester, cls.group, 'Estágio', Weekday.MONDAY, time(21, 0), time(21, 50))
        cls.room = Space.objects.get(name='1/13')

    def test_weekly_class_in_a_week(self):
        found = occupancy(self.room, date(2026, 10, 5), date(2026, 10, 9))
        self.assertEqual(len(found), 1)
        occurrence = found[0]
        self.assertEqual((occurrence.date, occurrence.start, occurrence.end), (date(2026, 10, 5), time(19, 0), time(19, 50)))
        self.assertEqual(occurrence.kind, SPACE_ALLOCATION)
        self.assertEqual(occurrence.entry.subject, 'Cálculo III')
        self.assertEqual(occurrence.entry.teachers, ('Viviane',))

    def test_dates_outside_the_period(self):
        self.assertEqual(occupancy(self.room, date(2026, 7, 27), date(2026, 7, 31)), [])
        self.assertEqual(occupancy(self.room, date(2026, 12, 21), date(2026, 12, 25)), [])

    def test_month_has_one_occurrence_per_monday(self):
        found = occupancy(self.room, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual([item.date.day for item in found], [5, 12, 19, 26])

    def test_semester_without_period_has_no_occurrence(self):
        older, _ = Semester.objects.resolve('2026/1')
        allocate(older, self.group, 'Biologia', Weekday.FRIDAY, time(7, 20), time(8, 10), '1/13')
        found = occupancy(self.room, date(2026, 3, 1), date(2026, 6, 30))
        self.assertEqual(found, [])

    def test_allocation_without_space_occupies_no_space(self):
        for space in Space.objects.all():
            found = occupancy(space, date(2026, 8, 3), date(2026, 12, 18))
            self.assertNotIn('Estágio', {item.entry.subject for item in found})

    def test_interval_crossing_two_semesters(self):
        next_one, _ = Semester.objects.resolve('2027/1')
        next_one.define_period(date(2027, 2, 1), date(2027, 6, 30))
        allocate(next_one, self.group, 'Cálculo IV', Weekday.MONDAY, time(19, 0), time(19, 50), '1/13')
        found = occupancy(self.room, date(2026, 12, 14), date(2027, 2, 5))
        self.assertEqual(
            [(item.date, item.entry.subject) for item in found],
            [(date(2026, 12, 14), 'Cálculo III'), (date(2027, 2, 1), 'Cálculo IV')],
        )

    def test_nothing_is_written_and_queries_do_not_grow(self):
        counts = []
        allocations = Allocation.objects.count()
        for end in [date(2026, 8, 7), date(2026, 8, 31), date(2026, 12, 18)]:
            with CaptureQueriesContext(connection) as context:
                occupancy(self.room, date(2026, 8, 3), end)
            counts.append(len(context.captured_queries))
            self.assertTrue(all(query['sql'].lstrip().upper().startswith('SELECT') for query in context.captured_queries))
        self.assertEqual(len(set(counts)), 1)
        self.assertEqual(Allocation.objects.count(), allocations)

    def test_another_source_joins_the_occupancy(self):
        found = occupancy(self.room, date(2026, 10, 5), date(2026, 10, 9), sources=[AllocationSource(), OtherSource()])
        self.assertEqual([(item.date, item.kind) for item in found], [(date(2026, 10, 5), SPACE_ALLOCATION), (date(2026, 10, 6), 'TESTE')])

    def test_empty_interval_and_missing_space(self):
        self.assertEqual(occupancy(self.room, date(2026, 10, 9), date(2026, 10, 5)), [])
        self.assertEqual(occupancy(None, date(2026, 10, 5), date(2026, 10, 9)), [])
