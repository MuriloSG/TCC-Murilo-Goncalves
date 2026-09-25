"""Grade da semana de uma sala, montada das alocações confirmadas de um semestre."""

from datetime import date, time

from django.test import TestCase

from schedule.models import Allocation, ClassGroup, Course, Semester, Space, Stage, Subject, Teacher, TimeSlot, Weekday
from schedule.timetable import CONTINUED, current_semester_code, group_label, imported_semesters, space_week, spaces_of

FRIDAY = date(2026, 9, 25)
SATURDAY = date(2026, 9, 26)


def allocate(semester, group, subject, weekday, start, end, space=None, teachers=()):
    slot, _ = TimeSlot.objects.resolve(semester, start, end)
    allocation, _, _ = Allocation.objects.apply(
        semester,
        group,
        Subject.objects.resolve(subject)[0],
        weekday,
        slot,
        space=Space.objects.resolve(space)[0] if space else None,
        teachers=[Teacher.objects.resolve(name)[0] for name in teachers],
    )
    return allocation


class CurrentSemesterTests(TestCase):
    def test_first_half_is_the_first_semester(self):
        self.assertEqual(current_semester_code(date(2026, 6, 30)), '2026/1')

    def test_second_half_is_the_second_semester(self):
        self.assertEqual(current_semester_code(date(2026, 7, 1)), '2026/2')


class SpaceWeekTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        other, _ = ClassGroup.objects.resolve(course, '4º período')
        high_school, _ = Course.objects.resolve('Informática', stage=Stage.SECONDARY)
        secondary, _ = ClassGroup.objects.resolve(high_school, '1º ano A')
        allocate(cls.semester, cls.group, 'Química orgânica', Weekday.MONDAY, time(7, 20), time(8, 10), '1/13', ['Elza'])
        allocate(cls.semester, cls.group, 'Química orgânica', Weekday.MONDAY, time(8, 10), time(9, 0), '1/13', ['Elza'])
        allocate(cls.semester, cls.group, 'Química orgânica', Weekday.MONDAY, time(9, 20), time(10, 10), '1/13', ['Elza'])
        allocate(cls.semester, other, 'Cálculo III', Weekday.TUESDAY, time(7, 20), time(8, 10), '1/13', ['Viviane'])
        allocate(cls.semester, secondary, 'Física', Weekday.MONDAY, time(13, 0), time(13, 50), 'HV 3')
        allocate(cls.semester, secondary, 'Química', Weekday.FRIDAY, time(13, 0), time(13, 50), '1/4')
        allocate(cls.semester, cls.group, 'Estágio', Weekday.WEDNESDAY, time(7, 20), time(8, 10))
        older, _ = Semester.objects.resolve('2026/1')
        allocate(older, cls.group, 'Biologia', Weekday.FRIDAY, time(7, 20), time(8, 10), '1/13')
        cls.room = Space.objects.get(name='1/13')

    def week(self, space=None, today=FRIDAY):
        return space_week(self.semester, space or self.room, today)

    def test_semesters_are_the_imported_ones_newest_first(self):
        Semester.objects.resolve('2025/2')
        self.assertEqual([semester.code for semester in imported_semesters()], ['2026/2', '2026/1'])

    def test_spaces_of_the_semester_by_name(self):
        self.assertEqual([space.name for space in spaces_of(self.semester)], ['1/4', '1/13', 'HV 3'])
        self.assertEqual(spaces_of(None), [])

    def test_group_label_is_readable(self):
        self.assertEqual(group_label(self.group), 'Engenharia de Alimentos, 2º período')

    def test_rows_are_every_slot_of_the_semester(self):
        starts = [row.start for row in self.week().rows]
        self.assertEqual(starts, [time(7, 20), time(8, 10), time(9, 20), time(13, 0)])

    def test_consecutive_slots_become_one_block_without_crossing_the_break(self):
        monday = self.week().days[0].cells
        self.assertEqual(monday[0].span, 2)
        self.assertEqual(monday[0].end, time(9, 0))
        self.assertIs(monday[1], CONTINUED)
        self.assertEqual(monday[2].span, 1)

    def test_entry_has_subject_group_and_teachers(self):
        entry = self.week().days[0].cells[0].entries[0]
        self.assertEqual(
            (entry.subject, entry.group_label, entry.teachers),
            ('Química orgânica', 'Engenharia de Alimentos, 2º período', ('Elza',)),
        )
        self.assertTrue(entry.is_undergraduate)

    def test_secondary_entry_has_its_stage(self):
        entry = self.week(Space.objects.get(name='HV 3')).days[0].cells[3].entries[0]
        self.assertFalse(entry.is_undergraduate)

    def test_counts(self):
        week = self.week()
        self.assertEqual((week.occupied, week.available), (4, 16))

    def test_other_semester_is_not_mixed(self):
        self.assertFalse(self.week().days[4].has_activity)

    def test_today_is_marked(self):
        self.assertEqual(self.week().today_index, 4)
        self.assertIsNone(self.week(today=SATURDAY).today_index)

    def test_without_space_the_week_is_empty(self):
        self.assertFalse(space_week(self.semester, None, FRIDAY).has_activities)

    def test_fixed_number_of_queries(self):
        with self.assertNumQueries(3):
            self.week()
