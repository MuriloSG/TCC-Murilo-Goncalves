"""Entidades do ensalamento: identificação, deduplicação e atualização."""

from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from audit import catalog
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin

from schedule.models import (
    Allocation,
    ClassGroup,
    ClassOffering,
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
    def test_code_is_resolved_once_and_only_in_the_format(self):
        first, created = Semester.objects.resolve('2026/1')
        second, created_again = Semester.objects.resolve('2026/1')
        self.assertEqual((first, created, created_again), (second, True, False))
        for code in ['2026', '2026-1', '2026/3', 'semestre', '26/1', '2026/']:
            with self.subTest(code=code), self.assertRaises(ValidationError) as context:
                Semester.objects.resolve(code)
            self.assertIn('code', context.exception.error_dict)
        self.assertEqual(Semester.objects.count(), 1)


class NamedRecordTests(TestCase):
    def test_names_are_normalized_and_matched_exactly(self):
        self.assertEqual(Space.objects.register('  Lab.   Bromatologia ').name, 'Lab. Bromatologia')
        first, _ = Teacher.objects.resolve('Aldo Gomes')
        second, created = Teacher.objects.resolve(' aldo  gomes ')
        self.assertEqual((first, created), (second, False))
        Teacher.objects.resolve('Érica')
        self.assertTrue(Teacher.objects.resolve('Erica')[1])
        Teacher.objects.resolve('Gera Jr.')
        Teacher.objects.resolve('Gera Magela')
        teacher, created = Teacher.objects.resolve('Gera')
        self.assertEqual((teacher.name, created), ('Gera', True))
        self.assertEqual(Teacher.objects.count(), 6)

    def test_empty_or_repeated_name_is_refused(self):
        for value in ['', '   ', None]:
            with self.subTest(value=value), self.assertRaises(ValidationError) as context:
                Teacher.objects.resolve(value)
            self.assertIn('name', context.exception.error_dict)
        course, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        with self.assertRaises(ValidationError) as context:
            ClassGroup.objects.resolve(course, '  ')
        self.assertIn('label', context.exception.error_dict)
        Space.objects.create(name='Zoo II')
        with self.assertRaises(ValidationError) as context:
            Space(name='zoo ii').full_clean()
        self.assertEqual(context.exception.error_dict['name'][0].code, 'name_taken')


class ClassGroupTests(TestCase):
    def test_label_is_resolved_per_course_and_takes_its_stage(self):
        food, _ = Course.objects.resolve('Eng. Alimentos', stage=Stage.UNDERGRADUATE)
        forest, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
        first, _ = ClassGroup.objects.resolve(food, '2º PERÍODO')
        other, created = ClassGroup.objects.resolve(forest, '2º PERÍODO')
        self.assertTrue(created)
        self.assertNotEqual(first, other)
        same, created = ClassGroup.objects.resolve(food, ' 2º   período ')
        self.assertEqual((same, created), (first, False))
        self.assertEqual(first.stage, Stage.UNDERGRADUATE)
        self.assertEqual(ClassGroup.objects.count(), 2)


class TimeSlotTests(TestCase):
    def test_slot_is_resolved_per_semester_with_the_start_before_the_end(self):
        semester, _ = Semester.objects.resolve('2026/1')
        other, _ = Semester.objects.resolve('2026/2')
        first, _ = TimeSlot.objects.resolve(semester, time(7, 20), time(8, 10))
        self.assertEqual(TimeSlot.objects.resolve(semester, time(7, 20), time(8, 10)), (first, False))
        second, created = TimeSlot.objects.resolve(other, time(7, 20), time(8, 10))
        self.assertTrue(created)
        self.assertNotEqual(first, second)
        for end in (time(9, 0), time(10, 0)):
            with self.subTest(end=end), self.assertRaises(ValidationError) as context:
                TimeSlot.objects.resolve(semester, time(10, 0), end)
            self.assertIn('end_time', context.exception.error_dict)


class AllocationTestCase(IsolatedCasesMixin, TestCase):
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
        with self.case('com espaço e docente'):
            allocation, action, changes = self.apply()
            self.assertEqual((action, changes), ('create', {'space': [None, '1/13'], 'teachers': [None, ['Elza']]}))
            self.assertEqual(allocation.origin, Origin.IMPORTED)
            self.assertEqual(list(allocation.teachers.all()), [self.elza])
        with self.case('sem espaço'):
            allocation, action, changes = self.apply(space=None)
            self.assertEqual((action, allocation.space, changes['space']), ('create', None, [None, None]))
        with self.case('sem docentes'):
            allocation, action, changes = self.apply(teachers=[])
            self.assertEqual((action, list(allocation.teachers.all()), changes['teachers']), ('create', [], [None, []]))

    def test_the_same_data_is_unchanged_in_any_teacher_order(self):
        first, _, _ = self.apply(teachers=[self.elza, self.viviane])
        self.assertEqual(self.apply(teachers=[self.elza, self.viviane]), (first, 'unchanged', {}))
        self.assertEqual(self.apply(teachers=[self.viviane, self.elza]), (first, 'unchanged', {}))
        self.assertEqual(Allocation.objects.count(), 1)

    def test_space_and_teacher_changes_are_updates(self):
        self.apply()
        with self.case('troca de espaço'):
            allocation, action, changes = self.apply(space=self.other_room)
            self.assertEqual((action, changes, allocation.space), ('update', {'space': ['1/13', '2/6']}, self.other_room))
        with self.case('troca de docentes'):
            allocation, action, changes = self.apply(teachers=[self.elza, self.viviane])
            self.assertEqual((action, changes), ('update', {'teachers': [['Elza'], ['Elza', 'Viviane']]}))
            self.assertEqual(list(allocation.teachers.order_by('name')), [self.elza, self.viviane])
        with self.case('espaço retirado e devolvido'):
            self.assertEqual(self.apply(space=None)[1:], ('update', {'space': ['1/13', None]}))
            self.assertEqual(self.apply()[1:], ('update', {'space': [None, '1/13']}))
        self.assertEqual(Allocation.objects.count(), 1)

    def test_two_groups_share_space_day_and_slot(self):
        self.apply()
        allocation, action, _ = self.apply(class_group=self.forest_group)
        self.assertEqual((action, allocation.space), ('create', self.room))
        self.assertEqual(Allocation.objects.filter(space=self.room, weekday=Weekday.MONDAY).count(), 2)

    def test_slot_of_another_semester_is_refused(self):
        other, _ = Semester.objects.resolve('2026/2')
        other_slot, _ = TimeSlot.objects.resolve(other, time(13, 20), time(14, 10))
        with self.assertRaises(ValidationError) as context:
            self.apply(time_slot=other_slot)
        self.assertIn('time_slot', context.exception.error_dict)


class SemesterPeriodTests(TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/2')

    def test_period_is_defined_once_and_refusals_change_nothing(self):
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
            self.assertEqual((self.semester.start_date, self.semester.end_date), (None, None))
        self.assertFalse(self.semester.contains(date(2026, 10, 5)))
        self.assertTrue(self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18)))
        self.assertFalse(self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18)))
        self.semester.refresh_from_db()
        self.assertEqual((self.semester.start_date, self.semester.end_date), (date(2026, 8, 3), date(2026, 12, 18)))
        self.assertFalse(AuditLog.objects.exists())
        for day, inside in ((date(2026, 8, 3), True), (date(2026, 12, 18), True), (date(2026, 8, 2), False)):
            self.assertEqual(self.semester.contains(day), inside, day)

    def test_check_period_requires_dates_only_without_a_period(self):
        for code in ('2026/2', '2027/1'):
            with self.subTest(code=code), self.assertRaises(ValidationError) as context:
                Semester.objects.check_period(code, None, None)
            self.assertEqual(set(context.exception.error_dict), {'start_date', 'end_date'})
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        Semester.objects.check_period('2026/2', None, None)
        for start, end in [(date(2026, 8, 3), None), (None, date(2026, 12, 18)), (date(2026, 12, 18), date(2026, 8, 3))]:
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                Semester.objects.check_period('2026/2', start, end)
        self.assertFalse(Semester.objects.filter(code='2026/2', start_date=date(2026, 12, 18)).exists())


class CourseTests(AllocationTestCase):
    def audit_of(self, course, action):
        return AuditLog.objects.get(resource=catalog.COURSE, resource_id=str(course.pk), action=action)

    def test_register_normalizes_audits_and_refuses_invalid_data(self):
        course = Course.objects.register('  Eng.   Pesca ', Stage.UNDERGRADUATE)
        self.assertEqual(course.name, 'Eng. Pesca')
        self.assertEqual(self.audit_of(course, catalog.CREATE).new_values, {'name': 'Eng. Pesca', 'etapa': Stage.UNDERGRADUATE})
        for name, stage, field in (
            ('eng. alimentos', Stage.UNDERGRADUATE, 'name'),
            ('   ', Stage.UNDERGRADUATE, 'name'),
            ('Eng. Outra', 'DOUTORADO', 'stage'),
            ('Eng. Outra', '', 'stage'),
        ):
            with self.subTest(name=name, stage=stage), self.assertRaises(ValidationError) as context:
                Course.objects.register(name, stage)
            self.assertIn(field, context.exception.error_dict)
        self.assertEqual(Course.objects.count(), 3)

    def test_update_of_a_course_without_use(self):
        self.food.update_details(' Eng.  Alimentos ', Stage.UNDERGRADUATE)
        self.assertFalse(AuditLog.objects.filter(resource=catalog.COURSE, action=catalog.UPDATE).exists())
        self.food.update_details('Engenharia de Alimentos', Stage.SECONDARY)
        self.assertEqual((self.food.name, self.food.stage), ('Engenharia de Alimentos', Stage.SECONDARY))
        self.assertEqual(
            self.audit_of(self.food, catalog.UPDATE).new_values, {'name': 'Engenharia de Alimentos', 'etapa': Stage.SECONDARY},
        )

    def test_update_of_a_course_in_use_is_refused(self):
        uses = {
            'oferta': lambda: ClassOffering.objects.record(self.semester, self.chemistry, self.food_group),
            'aula': self.apply,
        }
        for use, create in uses.items():
            for name, stage in (('Engenharia de Alimentos', Stage.UNDERGRADUATE), ('Eng. Alimentos', Stage.SECONDARY)):
                with self.subTest(use=use, name=name, stage=stage), transaction.atomic():
                    create()
                    with self.assertRaises(ValidationError) as context:
                        self.food.update_details(name, stage)
                    self.assertEqual(context.exception.code, 'course_in_use')
                    self.food.refresh_from_db()
                    self.assertEqual((self.food.name, self.food.stage), ('Eng. Alimentos', Stage.UNDERGRADUATE))
                    transaction.set_rollback(True)

    def test_only_a_course_without_class_groups_is_deleted(self):
        with self.assertRaises(ValidationError) as context:
            self.food.delete_course()
        self.assertEqual(
            context.exception.messages, ['O curso Eng. Alimentos tem turmas cadastradas e não pode ser excluído. Exclua as turmas antes.'],
        )
        self.assertTrue(Course.objects.filter(pk=self.food.pk).exists())
        course = Course.objects.register('Eng. Pesca', Stage.UNDERGRADUATE)
        pk = course.pk
        course.delete_course()
        self.assertFalse(Course.objects.filter(pk=pk).exists())
        entry = AuditLog.objects.get(resource=catalog.COURSE, resource_id=str(pk), action=catalog.DELETE)
        self.assertEqual(entry.old_values, {'name': 'Eng. Pesca', 'etapa': Stage.UNDERGRADUATE})
