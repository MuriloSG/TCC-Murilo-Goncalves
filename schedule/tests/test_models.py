"""Entidades do ensalamento: identificação, deduplicação e atualização."""

from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from audit.models import AuditLog

from schedule.models import (
    Allocation,
    ClassGroup,
    Course,
    Origin,
    Semester,
    Space,
    Stage,
    Subject,
    Teacher,
    TimeSlot,
    Weekday,
)


class SemesterTests(TestCase):
    def test_code_is_created_once(self):
        first, created = Semester.objects.resolve('2026/1')
        second, created_again = Semester.objects.resolve('2026/1')
        self.assertEqual((created, created_again), (True, False))
        self.assertEqual(first, second)
        self.assertEqual(Semester.objects.count(), 1)

    def test_code_outside_the_format_is_refused(self):
        for code in ['2026', '2026-1', '2026/3', 'semestre', '26/1', '2026/']:
            with self.subTest(code=code), self.assertRaises(ValidationError) as context:
                Semester.objects.resolve(code)
            self.assertIn('code', context.exception.error_dict)
        self.assertFalse(Semester.objects.exists())


class NamedRecordTests(TestCase):
    def test_borders_and_repeated_spaces_are_normalized(self):
        space = Space.objects.register('  Lab.   Bromatologia ')
        self.assertEqual(space.name, 'Lab. Bromatologia')

    def test_equivalent_name_does_not_duplicate(self):
        first, _ = Teacher.objects.resolve('Aldo Gomes')
        second, created = Teacher.objects.resolve(' aldo  gomes ')
        self.assertEqual((first, created), (second, False))
        self.assertEqual(Teacher.objects.count(), 1)

    def test_accents_distinguish_two_records(self):
        Teacher.objects.resolve('Érica')
        Teacher.objects.resolve('Erica')
        self.assertEqual(Teacher.objects.count(), 2)

    def test_shared_prefix_is_never_matched(self):
        Teacher.objects.resolve('Gera Jr.')
        Teacher.objects.resolve('Gera Magela')
        teacher, created = Teacher.objects.resolve('Gera')
        self.assertTrue(created)
        self.assertEqual(Teacher.objects.count(), 3)
        self.assertEqual(teacher.name, 'Gera')

    def test_empty_name_is_refused(self):
        for value in ['', '   ', None]:
            with self.subTest(value=value), self.assertRaises(ValidationError) as context:
                Teacher.objects.resolve(value)
            self.assertIn('name', context.exception.error_dict)

    def test_repeated_name_is_refused_by_the_model(self):
        Space.objects.create(name='Zoo II')
        with self.assertRaises(ValidationError) as context:
            Space(name='zoo ii').full_clean()
        self.assertEqual(context.exception.error_dict['name'][0].code, 'name_taken')

    def test_repeated_name_is_refused_by_the_database(self):
        Space.objects.create(name='Zoo II')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Space.objects.create(name='zoo ii')


class ClassGroupTests(TestCase):
    def setUp(self):
        self.food, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        self.forest, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)

    def test_same_label_in_two_courses_gives_two_groups(self):
        first, _ = ClassGroup.objects.resolve(self.food, '2º PERÍODO')
        second, created = ClassGroup.objects.resolve(self.forest, '2º PERÍODO')
        self.assertTrue(created)
        self.assertNotEqual(first, second)
        self.assertEqual(ClassGroup.objects.count(), 2)

    def test_equivalent_label_in_the_same_course_does_not_duplicate(self):
        first, _ = ClassGroup.objects.resolve(self.food, '2º PERÍODO')
        second, created = ClassGroup.objects.resolve(self.food, ' 2º   período ')
        self.assertEqual((first, created), (second, False))

    def test_stage_comes_from_the_course(self):
        group, _ = ClassGroup.objects.resolve(self.food, '2º PERÍODO')
        self.assertEqual(group.stage, Stage.UNDERGRADUATE)

    def test_empty_label_is_refused(self):
        with self.assertRaises(ValidationError) as context:
            ClassGroup.objects.resolve(self.food, '  ')
        self.assertIn('label', context.exception.error_dict)


class TimeSlotTests(TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/1')

    def test_slot_is_created_once_per_semester(self):
        first, _ = TimeSlot.objects.resolve(self.semester, time(7, 20), time(8, 10))
        second, created = TimeSlot.objects.resolve(self.semester, time(7, 20), time(8, 10))
        self.assertEqual((first, created), (second, False))

    def test_the_same_slot_of_another_semester_is_another_record(self):
        other, _ = Semester.objects.resolve('2026/2')
        first, _ = TimeSlot.objects.resolve(self.semester, time(7, 20), time(8, 10))
        second, created = TimeSlot.objects.resolve(other, time(7, 20), time(8, 10))
        self.assertTrue(created)
        self.assertNotEqual(first, second)

    def test_start_not_before_the_end_is_refused(self):
        for end in (time(9, 0), time(10, 0)):
            with self.subTest(end=end), self.assertRaises(ValidationError) as context:
                TimeSlot.objects.resolve(self.semester, time(10, 0), end)
            self.assertIn('end_time', context.exception.error_dict)

    def test_database_refuses_an_inverted_range(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TimeSlot.objects.create(semester=self.semester, start_time=time(10, 0), end_time=time(9, 0))


class AllocationTestCase(TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/1')
        self.food, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        self.forest, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
        self.food_group, _ = ClassGroup.objects.resolve(self.food, '2º PERÍODO')
        self.forest_group, _ = ClassGroup.objects.resolve(self.forest, '2º PERÍODO')
        self.chemistry, _ = Subject.objects.resolve('Química Orgânica')
        self.calculus, _ = Subject.objects.resolve('Cálculo III')
        self.room = Space.objects.register('1/13')
        self.other_room = Space.objects.register('2/6')
        self.elza, _ = Teacher.objects.resolve('Elza')
        self.viviane, _ = Teacher.objects.resolve('Viviane')
        self.first_slot, _ = TimeSlot.objects.resolve(self.semester, time(13, 20), time(14, 10))
        self.second_slot, _ = TimeSlot.objects.resolve(self.semester, time(14, 10), time(15, 0))

    def apply(self, **overrides):
        values = {
            'semester': self.semester,
            'class_group': self.food_group,
            'subject': self.chemistry,
            'weekday': Weekday.MONDAY,
            'time_slot': self.first_slot,
            'space': self.room,
            'teachers': [self.elza],
        }
        return Allocation.objects.apply(**values | overrides)


class AllocationTests(AllocationTestCase):
    def test_create_gives_the_changes_and_the_imported_origin(self):
        allocation, action, changes = self.apply()
        self.assertEqual(action, 'create')
        self.assertEqual(changes, {'space': [None, '1/13'], 'teachers': [None, ['Elza']]})
        self.assertEqual(allocation.origin, Origin.IMPORTED)
        self.assertEqual(list(allocation.teachers.all()), [self.elza])

    def test_applying_twice_is_unchanged(self):
        first, _, _ = self.apply()
        second, action, changes = self.apply()
        self.assertEqual((second, action, changes), (first, 'unchanged', {}))
        self.assertEqual(Allocation.objects.count(), 1)

    def test_space_change_is_an_update(self):
        self.apply()
        allocation, action, changes = self.apply(space=self.other_room)
        self.assertEqual(action, 'update')
        self.assertEqual(changes, {'space': ['1/13', '2/6']})
        self.assertEqual(allocation.space, self.other_room)
        self.assertEqual(Allocation.objects.count(), 1)

    def test_teachers_change_is_an_update(self):
        self.apply()
        allocation, action, changes = self.apply(teachers=[self.elza, self.viviane])
        self.assertEqual(action, 'update')
        self.assertEqual(changes, {'teachers': [['Elza'], ['Elza', 'Viviane']]})
        self.assertEqual(list(allocation.teachers.order_by('name')), [self.elza, self.viviane])

    def test_teacher_order_does_not_matter(self):
        self.apply(teachers=[self.elza, self.viviane])
        _, action, changes = self.apply(teachers=[self.viviane, self.elza])
        self.assertEqual((action, changes), ('unchanged', {}))

    def test_allocation_without_space(self):
        allocation, action, changes = self.apply(space=None)
        self.assertEqual(action, 'create')
        self.assertIsNone(allocation.space)
        self.assertEqual(changes['space'], [None, None])

    def test_space_can_be_removed_and_added(self):
        self.apply()
        _, action, changes = self.apply(space=None)
        self.assertEqual((action, changes), ('update', {'space': ['1/13', None]}))
        _, action, changes = self.apply()
        self.assertEqual((action, changes), ('update', {'space': [None, '1/13']}))

    def test_allocation_without_teachers(self):
        allocation, action, changes = self.apply(teachers=[])
        self.assertEqual(action, 'create')
        self.assertEqual(list(allocation.teachers.all()), [])
        self.assertEqual(changes['teachers'], [None, []])


class SharedSpaceTests(AllocationTestCase):
    def test_two_groups_share_space_day_and_slot(self):
        self.apply()
        allocation, action, _ = self.apply(class_group=self.forest_group)
        self.assertEqual(action, 'create')
        self.assertEqual(Allocation.objects.filter(space=self.room, weekday=Weekday.MONDAY).count(), 2)
        self.assertEqual(allocation.space, self.room)

    def test_the_same_group_slot_and_subject_is_refused_by_the_database(self):
        self.apply()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Allocation.objects.create(
                semester=self.semester,
                class_group=self.food_group,
                subject=self.chemistry,
                weekday=Weekday.MONDAY,
                time_slot=self.first_slot,
                space=self.other_room,
            )


class SemesterIsolationTests(AllocationTestCase):
    def test_slot_of_another_semester_is_refused(self):
        other, _ = Semester.objects.resolve('2026/2')
        other_slot, _ = TimeSlot.objects.resolve(other, time(13, 20), time(14, 10))
        with self.assertRaises(ValidationError) as context:
            self.apply(time_slot=other_slot)
        self.assertIn('time_slot', context.exception.error_dict)


class SemesterPeriodTests(TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/2')

    def test_period_is_defined_without_its_own_audit(self):
        self.assertTrue(self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18)))
        self.semester.refresh_from_db()
        self.assertEqual((self.semester.start_date, self.semester.end_date), (date(2026, 8, 3), date(2026, 12, 18)))
        self.assertFalse(AuditLog.objects.exists())

    def test_same_period_is_not_a_change(self):
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        self.assertFalse(self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18)))

    def test_refusals_leave_the_semester_unchanged(self):
        cases = [
            (date(2026, 12, 18), date(2026, 8, 3)),
            (date(2026, 8, 3), None),
            (None, date(2026, 12, 18)),
            (date(2026, 1, 1), date(2027, 1, 2)),
        ]
        for start, end in cases:
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                self.semester.define_period(start, end)
            self.semester.refresh_from_db()
            self.assertIsNone(self.semester.start_date)
            self.assertIsNone(self.semester.end_date)

    def test_check_period_requires_the_dates_without_a_period(self):
        for code in ('2026/2', '2027/1'):
            with self.subTest(code=code), self.assertRaises(ValidationError) as context:
                Semester.objects.check_period(code, None, None)
            self.assertEqual(set(context.exception.error_dict), {'start_date', 'end_date'})

    def test_check_period_accepts_blank_dates_with_a_period(self):
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        Semester.objects.check_period('2026/2', None, None)

    def test_check_period_refuses_one_date_or_an_invalid_period(self):
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        for start, end in [(date(2026, 8, 3), None), (None, date(2026, 12, 18)), (date(2026, 12, 18), date(2026, 8, 3))]:
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                Semester.objects.check_period('2026/2', start, end)
        self.assertFalse(Semester.objects.filter(code='2026/2', start_date=date(2026, 12, 18)).exists())

    def test_contains_only_dates_of_the_period(self):
        self.assertFalse(self.semester.contains(date(2026, 10, 5)))
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        self.assertTrue(self.semester.contains(date(2026, 8, 3)))
        self.assertTrue(self.semester.contains(date(2026, 12, 18)))
        self.assertFalse(self.semester.contains(date(2026, 8, 2)))

    def test_database_refuses_period_with_one_date(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(pk=self.semester.pk).update(start_date=date(2026, 8, 3))
