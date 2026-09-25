"""Entidades do ensalamento: identificação, deduplicação e atualização."""

from datetime import time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

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

    def test_both_semesters_of_a_year_coexist(self):
        Semester.objects.resolve('2026/1')
        Semester.objects.resolve('2026/2')
        self.assertEqual(list(Semester.objects.values_list('code', flat=True)), ['2026/2', '2026/1'])


class NamedRecordTests(TestCase):
    def test_name_is_stored_as_informed(self):
        space, _ = Space.objects.resolve('Lab. Fenôm. de Transportes')
        teacher, _ = Teacher.objects.resolve('Élcio José')
        self.assertEqual(space.name, 'Lab. Fenôm. de Transportes')
        self.assertEqual(teacher.name, 'Élcio José')

    def test_borders_and_repeated_spaces_are_normalized(self):
        space, _ = Space.objects.resolve('  Lab.   Bromatologia ')
        self.assertEqual(space.name, 'Lab. Bromatologia')

    def test_equivalent_name_does_not_duplicate(self):
        first, _ = Space.objects.resolve('Lab. Bromatologia')
        second, created = Space.objects.resolve(' lab.  bromatologia ')
        self.assertEqual((first, created), (second, False))
        self.assertEqual(Space.objects.count(), 1)

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

    def test_the_same_name_in_two_entities_is_independent(self):
        Space.objects.resolve('Química')
        Subject.objects.resolve('Química')
        Teacher.objects.resolve('Química')
        self.assertEqual((Space.objects.count(), Subject.objects.count(), Teacher.objects.count()), (1, 1, 1))


class SubjectTests(TestCase):
    def test_subject_is_shared_between_courses(self):
        first, _ = Subject.objects.resolve('Química Orgânica')
        second, created = Subject.objects.resolve('QUÍMICA ORGÂNICA')
        self.assertEqual((first, created), (second, False))
        self.assertEqual(Subject.objects.count(), 1)


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

    def test_start_after_end_is_refused(self):
        with self.assertRaises(ValidationError) as context:
            TimeSlot.objects.resolve(self.semester, time(10, 0), time(9, 0))
        self.assertIn('end_time', context.exception.error_dict)

    def test_start_equal_to_end_is_refused(self):
        with self.assertRaises(ValidationError):
            TimeSlot.objects.resolve(self.semester, time(10, 0), time(10, 0))

    def test_database_refuses_an_inverted_range(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TimeSlot.objects.create(semester=self.semester, start_time=time(10, 0), end_time=time(9, 0))

    def test_label(self):
        slot, _ = TimeSlot.objects.resolve(self.semester, time(7, 20), time(8, 10))
        self.assertEqual(str(slot), '07:20 - 08:10')


class AllocationTestCase(TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/1')
        self.food, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        self.forest, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
        self.food_group, _ = ClassGroup.objects.resolve(self.food, '2º PERÍODO')
        self.forest_group, _ = ClassGroup.objects.resolve(self.forest, '2º PERÍODO')
        self.chemistry, _ = Subject.objects.resolve('Química Orgânica')
        self.calculus, _ = Subject.objects.resolve('Cálculo III')
        self.room, _ = Space.objects.resolve('1/13')
        self.other_room, _ = Space.objects.resolve('2/6')
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

    def test_different_subjects_in_the_same_space_and_slot_are_accepted(self):
        self.apply()
        _, action, _ = self.apply(class_group=self.forest_group, subject=self.calculus)
        self.assertEqual(action, 'create')
        self.assertEqual(Allocation.objects.count(), 2)

    def test_consecutive_slots_are_two_allocations(self):
        self.apply()
        self.apply(time_slot=self.second_slot)
        self.assertEqual(Allocation.objects.count(), 2)
        self.assertEqual(
            list(Allocation.objects.order_by('time_slot__start_time').values_list('time_slot__start_time', flat=True)),
            [time(13, 20), time(14, 10)],
        )

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
    def test_allocation_of_another_semester_is_independent(self):
        self.apply()
        other, _ = Semester.objects.resolve('2026/2')
        other_slot, _ = TimeSlot.objects.resolve(other, time(13, 20), time(14, 10))
        allocation, action, _ = Allocation.objects.apply(
            semester=other,
            class_group=self.food_group,
            subject=self.chemistry,
            weekday=Weekday.MONDAY,
            time_slot=other_slot,
            space=self.room,
            teachers=[self.elza],
        )
        self.assertEqual(action, 'create')
        self.assertEqual(Allocation.objects.filter(semester=self.semester).count(), 1)
        self.assertEqual(Allocation.objects.filter(semester=other).count(), 1)
        self.assertEqual(allocation.semester, other)

    def test_slot_of_another_semester_is_refused(self):
        other, _ = Semester.objects.resolve('2026/2')
        other_slot, _ = TimeSlot.objects.resolve(other, time(13, 20), time(14, 10))
        with self.assertRaises(ValidationError) as context:
            self.apply(time_slot=other_slot)
        self.assertIn('time_slot', context.exception.error_dict)


class QueryTests(AllocationTestCase):
    def test_occupation_of_a_space_by_day_and_slot(self):
        self.apply()
        self.apply(class_group=self.forest_group)
        self.apply(time_slot=self.second_slot, space=self.other_room)
        found = Allocation.objects.filter(
            semester=self.semester, space=self.room, weekday=Weekday.MONDAY, time_slot=self.first_slot,
        )
        self.assertEqual(found.count(), 2)

    def test_allocations_of_a_teacher(self):
        self.apply()
        self.apply(time_slot=self.second_slot, teachers=[self.viviane])
        self.assertEqual(Allocation.objects.filter(teachers=self.elza).count(), 1)
        self.assertEqual(Allocation.objects.filter(teachers=self.viviane).count(), 1)

    def test_allocations_of_a_class_group(self):
        self.apply()
        self.apply(class_group=self.forest_group)
        self.assertEqual(Allocation.objects.filter(class_group=self.food_group).count(), 1)
