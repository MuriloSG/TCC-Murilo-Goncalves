"""Grade da semana de uma sala, montada das alocações confirmadas de um semestre."""

from datetime import date, time, timedelta

from django.test import TestCase

from schedule.models import Allocation, ClassGroup, Course, Semester, Space, Stage, Subject, Teacher, TimeSlot, Weekday
from schedule.occupancy import occupancy
from schedule.timetable import (
    CLASH,
    CONTINUED,
    JOINT,
    SINGLE,
    Cell,
    Entry,
    current_semester_code,
    dated_space_month,
    dated_space_week,
    group_label,
    imported_semesters,
    month_dates,
    month_start,
    space_week,
    spaces_of,
    week_start,
)

FRIDAY = date(2026, 9, 25)
SATURDAY = date(2026, 9, 26)


def space_named(name):
    """Espaço de teste com este nome, cadastrado quando ainda não existe."""
    return Space.objects.named(name) or Space.objects.register(name)


def allocate(semester, group, subject, weekday, start, end, space=None, teachers=()):
    slot, _ = TimeSlot.objects.resolve(semester, start, end)
    allocation, _, _ = Allocation.objects.apply(
        semester,
        group,
        Subject.objects.resolve(subject)[0],
        weekday,
        slot,
        space=space_named(space) if space else None,
        teachers=[Teacher.objects.resolve(name)[0] for name in teachers],
    )
    return allocation


class CurrentSemesterTests(TestCase):
    def test_each_half_of_the_year_is_a_semester(self):
        self.assertEqual(current_semester_code(date(2026, 6, 30)), '2026/1')
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

    def test_semesters_and_spaces_offered(self):
        self.assertEqual([space.name for space in spaces_of(self.semester)], ['1/4', '1/13', 'HV 3'])
        self.assertEqual(spaces_of(None), [])
        Semester.objects.resolve('2025/2')
        self.assertEqual([semester.code for semester in imported_semesters()], ['2026/2', '2026/1'])
        Space.objects.register('1/3')
        Space.objects.register('Sala 8').deactivate()
        names = [space.name for space in spaces_of(self.semester)]
        self.assertIn('1/3', names)
        self.assertNotIn('Sala 8', names)
        self.assertEqual(len(names), len(set(names)))

    def test_rows_are_every_slot_and_consecutive_slots_become_one_block(self):
        week = self.week()
        self.assertEqual([row.start for row in week.rows], [time(7, 20), time(8, 10), time(9, 20), time(13, 0)])
        monday = week.days[0].cells
        self.assertEqual((monday[0].span, monday[0].end), (2, time(9, 0)))
        self.assertIs(monday[1], CONTINUED)
        self.assertEqual(monday[2].span, 1)

    def test_entries_counts_and_today(self):
        week = self.week()
        entry = week.days[0].cells[0].entries[0]
        self.assertEqual(
            (entry.subject, entry.group_label, entry.teachers),
            ('Química orgânica', 'Engenharia de Alimentos, 2º período', ('Elza',)),
        )
        self.assertEqual(group_label(self.group), 'Engenharia de Alimentos, 2º período')
        self.assertTrue(entry.is_undergraduate)
        self.assertFalse(self.week(Space.objects.get(name='HV 3')).days[0].cells[3].entries[0].is_undergraduate)
        self.assertEqual((week.occupied, week.available), (4, 16))
        self.assertFalse(week.days[4].has_activity)
        self.assertEqual(week.today_index, 4)
        self.assertIsNone(self.week(today=SATURDAY).today_index)
        self.assertFalse(space_week(self.semester, None, FRIDAY).has_activities)


class DatedWeekTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 5), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        allocate(cls.semester, group, 'Cálculo III', Weekday.MONDAY, time(19, 0), time(19, 50), '1/13', ['Viviane'])
        allocate(cls.semester, group, 'Cálculo III', Weekday.MONDAY, time(19, 50), time(20, 40), '1/13', ['Viviane'])
        allocate(cls.semester, group, 'Física', Weekday.WEDNESDAY, time(21, 0), time(21, 50), '1/4')
        cls.room = Space.objects.get(name='1/13')

    def week(self, start, today=date(2026, 10, 7)):
        occurrences = occupancy(self.room, start, start + timedelta(days=4))
        return dated_space_week(self.semester, self.room, start, today, occurrences)

    def test_week_start_stays_inside_the_period(self):
        self.assertEqual(week_start(self.semester, None, date(2026, 10, 7)), date(2026, 10, 5))
        self.assertEqual(week_start(self.semester, None, date(2026, 7, 1)), date(2026, 8, 3))
        self.assertEqual(week_start(self.semester, None, date(2027, 1, 10)), date(2026, 12, 14))
        self.assertEqual(week_start(self.semester, date(2026, 10, 14), date(2026, 7, 1)), date(2026, 10, 12))

    def test_dated_week_has_dates_blocks_counts_and_neighbours(self):
        week = self.week(date(2026, 10, 5))
        self.assertEqual([day.date.day for day in week.days], [5, 6, 7, 8, 9])
        self.assertEqual([day.is_today for day in week.days], [False, False, True, False, False])
        self.assertEqual((week.start, week.end), (date(2026, 10, 5), date(2026, 10, 9)))
        block = next(cell for cell in week.days[0].cells if cell)
        self.assertEqual((block.span, block.entries[0].subject), (2, 'Cálculo III'))
        self.assertEqual((week.occupied, week.available), (2, 13))
        self.assertEqual([day.available for day in week.days], [1, 3, 3, 3, 3])
        first = self.week(date(2026, 8, 3))
        self.assertEqual([day.in_period for day in first.days], [False, False, True, True, True])
        self.assertTrue(first.days[0].cells[0].is_outside)
        self.assertEqual(first.days[0].cells[0].span, 3)
        self.assertEqual((first.occupied, first.available), (0, 9))
        self.assertEqual((first.previous, first.following), (None, date(2026, 8, 10)))
        last = self.week(date(2026, 12, 14))
        self.assertEqual((last.previous, last.following), (date(2026, 12, 7), None))


class CellKindTests(TestCase):
    def entry(self, group, subject='Química orgânica', teachers=('Elza',)):
        return Entry(subject=subject, group_label=group, teachers=teachers, stage=Stage.UNDERGRADUATE)

    def cell(self, *entries):
        return Cell(entries=list(entries), start=time(13, 20), end=time(14, 10))

    def test_kind_of_the_cell(self):
        self.assertEqual(self.cell(self.entry('Eng. Alimentos, 2º período')).kind, SINGLE)
        joint = self.cell(self.entry('Eng. Alimentos, 2º período'), self.entry('Eng. Florestal, 2º período', 'QUÍMICA ORGÂNICA', ('elza',)))
        self.assertEqual((joint.kind, joint.group_count), (JOINT, 2))
        by_subject = self.cell(self.entry('A, 1º ano A'), self.entry('B, 1º ano B', 'Física'))
        by_teacher = self.cell(self.entry('A, 1º ano A'), self.entry('B, 1º ano B', teachers=('Viviane',)))
        self.assertEqual((by_subject.kind, by_teacher.kind), (CLASH, CLASH))

    def test_joint_groups_in_the_dated_week(self):
        semester, _ = Semester.objects.resolve('2026/2')
        semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        alimentos, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        florestal, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
        for course in (alimentos, florestal):
            group, _ = ClassGroup.objects.resolve(course, '2º período')
            allocate(semester, group, 'Química orgânica', Weekday.MONDAY, time(13, 20), time(14, 10), '1/13', ['Elza'])
        room = Space.objects.get(name='1/13')
        start = date(2026, 10, 5)
        week = dated_space_week(semester, room, start, start, occupancy(room, start, start + timedelta(days=4)))
        cell = next(cell for cell in week.days[0].cells if cell)
        self.assertEqual((cell.kind, cell.group_count, cell.span), (JOINT, 2, 1))


class DatedMonthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 5), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        allocate(cls.semester, group, 'Cálculo III', Weekday.MONDAY, time(19, 0), time(19, 50), '1/13', ['Viviane'])
        allocate(cls.semester, group, 'Física', Weekday.TUESDAY, time(21, 0), time(21, 50), '1/4')
        cls.room = Space.objects.get(name='1/13')

    def month(self, first, today=date(2026, 9, 25)):
        dates = month_dates(first)
        occurrences = occupancy(self.room, dates[0], dates[-1])
        return dated_space_month(self.semester, self.room, first, today, occurrences)

    def test_month_dates_and_navigation(self):
        dates = month_dates(date(2026, 10, 1))
        self.assertEqual((len(dates), dates[0], dates[-1]), (22, date(2026, 10, 1), date(2026, 10, 30)))
        self.assertTrue(all(day.weekday() < 5 for day in dates))
        month = self.month(date(2026, 9, 1))
        self.assertEqual([day.date.day for day in month.days if day.is_week_start], [7, 14, 21, 28])
        self.assertEqual([day.date for day in month.days if day.is_today], [date(2026, 9, 25)])
        self.assertEqual(month.days[0].short_label, 'Ter')
        first = self.month(date(2026, 8, 1))
        self.assertEqual([day.date.day for day in first.days if not day.in_period], [3, 4])
        self.assertEqual((first.previous, first.following), (None, date(2026, 9, 1)))
        last = self.month(date(2026, 12, 1))
        self.assertEqual((last.previous, last.following), (date(2026, 11, 1), None))
        self.assertEqual(month_start(self.semester, None, date(2026, 7, 1)), date(2026, 8, 1))
        self.assertEqual(month_start(self.semester, None, date(2027, 3, 1)), date(2026, 12, 1))
        self.assertEqual(month_start(self.semester, date(2026, 10, 20), date(2026, 7, 1)), date(2026, 10, 1))

    def test_month_has_the_same_cells_as_the_week(self):
        month = self.month(date(2026, 10, 1))
        self.assertEqual([day.date.day for day in month.days if day.has_activity], [5, 12, 19, 26])
        start = date(2026, 10, 5)
        week = dated_space_week(self.semester, self.room, start, date(2026, 9, 25), occupancy(self.room, start, start + timedelta(days=4)))
        in_month = next(day for day in month.days if day.date == start)
        self.assertEqual(in_month.cells, week.days[0].cells)
        self.assertEqual(in_month.available, week.days[0].available)
