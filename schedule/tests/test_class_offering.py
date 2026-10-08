"""Ofertas de disciplina, docentes das ofertas e a consulta das combinações atuais."""

from datetime import date, time

from django.test import TestCase

from schedule.models import (
    Allocation,
    ClassGroup,
    ClassOffering,
    Course,
    Semester,
    Stage,
    Subject,
    Teacher,
    TeachingAssignment,
    Weekday,
)
from schedule.tests.test_timetable import allocate

def record(allocation):
    return ClassOffering.objects.record(allocation.semester, allocation.subject, allocation.class_group)


def current_of(offering):
    return {assignment.teacher.name: assignment.is_current for assignment in offering.assignments.select_related('teacher')}


class OfferingTestCase(TestCase):
    """Em 2026/2, João dá Matemática ao 1º Período A e ao 2º, e Maria ao 1º Período B."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.previous, _ = Semester.objects.resolve('2026/1')
        course, _ = Course.objects.resolve('SISTEMAS DE INFORMAÇÃO', stage=Stage.UNDERGRADUATE)
        cls.first_a, _ = ClassGroup.objects.resolve(course, '1º Período A')
        cls.first_b, _ = ClassGroup.objects.resolve(course, '1º Período B')
        cls.second, _ = ClassGroup.objects.resolve(course, '2º Período')
        cls.allocations = [
            allocate(cls.semester, cls.first_a, 'Matemática', Weekday.MONDAY, time(8, 0), time(9, 0), teachers=['João']),
            allocate(cls.semester, cls.second, 'Matemática', Weekday.TUESDAY, time(8, 0), time(9, 0), teachers=['João']),
            allocate(cls.semester, cls.first_b, 'Matemática', Weekday.MONDAY, time(8, 0), time(9, 0), teachers=['Maria']),
            allocate(cls.semester, cls.second, 'Física', Weekday.MONDAY, time(10, 0), time(11, 0), teachers=['Maria']),
        ]
        for allocation in cls.allocations:
            record(allocation)
        cls.math = Subject.objects.get(name='Matemática')
        cls.physics = Subject.objects.get(name='Física')
        cls.joao = Teacher.objects.get(name='João')
        cls.maria = Teacher.objects.get(name='Maria')


class OfferingTests(OfferingTestCase):
    def test_same_subject_in_several_semesters(self):
        before = allocate(self.previous, self.second, 'Matemática', Weekday.MONDAY, time(8, 0), time(9, 0), teachers=['Ana'])
        record(before)
        offerings = ClassOffering.objects.filter(subject=self.math, class_group=self.second)
        self.assertEqual(set(offerings.values_list('semester__code', flat=True)), {'2026/1', '2026/2'})
        self.assertEqual(current_of(offerings.get(semester=self.semester)), {'João': True})
        self.assertEqual(current_of(offerings.get(semester=self.previous)), {'Ana': True})

    def test_several_teachers_in_the_same_offering(self):
        allocation = allocate(self.semester, self.first_a, 'Banco de Dados', Weekday.FRIDAY, time(8, 0), time(9, 0), teachers=['João', 'Ana'])
        offering = record(allocation)
        self.assertEqual(current_of(offering), {'João': True, 'Ana': True})

    def test_offering_without_teacher(self):
        allocation = allocate(self.semester, self.first_a, 'Estágio', Weekday.FRIDAY, time(8, 0), time(9, 0))
        offering = record(allocation)
        self.assertEqual(offering.assignments.count(), 0)

    def test_record_is_idempotent(self):
        counts = (ClassOffering.objects.count(), TeachingAssignment.objects.count())
        for allocation in self.allocations:
            record(allocation)
        self.assertEqual((ClassOffering.objects.count(), TeachingAssignment.objects.count()), counts)

    def test_replaced_teacher_is_kept_as_history_and_comes_back(self):
        allocation = self.allocations[1]
        allocation.update_details(None, [self.maria])
        offering = record(allocation)
        self.assertEqual(current_of(offering), {'João': False, 'Maria': True})
        allocation.update_details(None, [self.joao])
        offering = record(allocation)
        self.assertEqual(current_of(offering), {'João': True, 'Maria': False})
        self.assertEqual(offering.assignments.count(), 2)

    def test_ended_version_does_not_make_the_teacher_current(self):
        allocation = self.allocations[1]
        Allocation.objects.filter(pk=allocation.pk).update(valid_until=date(2026, 10, 4))
        offering = record(allocation)
        self.assertEqual(current_of(offering), {'João': False})


class AvailableTests(OfferingTestCase):
    def combinations(self, **filters):
        return {
            (item.teacher.name, item.offering.subject.name, item.offering.class_group.label)
            for item in TeachingAssignment.objects.available(self.semester, **filters)
        }

    def test_teacher_to_subjects_to_class_groups(self):
        self.assertEqual(
            self.combinations(teacher=self.joao),
            {('João', 'Matemática', '1º Período A'), ('João', 'Matemática', '2º Período')},
        )

    def test_subject_to_class_groups_to_teachers(self):
        self.assertEqual(
            self.combinations(subject=self.math),
            {('João', 'Matemática', '1º Período A'), ('João', 'Matemática', '2º Período'), ('Maria', 'Matemática', '1º Período B')},
        )

    def test_class_group_to_subjects_to_teachers(self):
        self.assertEqual(
            self.combinations(class_group=self.second),
            {('João', 'Matemática', '2º Período'), ('Maria', 'Física', '2º Período')},
        )

    def test_missing_combination_is_not_offered(self):
        self.assertFalse(TeachingAssignment.objects.is_available(self.semester, self.joao, self.physics, self.second))
        self.assertTrue(TeachingAssignment.objects.is_available(self.semester, self.joao, self.math, self.second))

    def test_only_current_assignments_are_offered(self):
        allocation = self.allocations[1]
        allocation.update_details(None, [self.maria])
        record(allocation)
        self.assertEqual(
            self.combinations(subject=self.math, class_group=self.second), {('Maria', 'Matemática', '2º Período')},
        )
        self.assertTrue(TeachingAssignment.objects.filter(teacher=self.joao, offering__class_group=self.second).exists())

    def test_other_semester_is_not_offered(self):
        self.assertFalse(TeachingAssignment.objects.available(self.previous).exists())

    def test_single_query(self):
        with self.assertNumQueries(1):
            found = [
                (item.teacher.name, item.offering.subject.name, item.offering.class_group.label, item.offering.class_group.course.name)
                for item in TeachingAssignment.objects.available(self.semester)
            ]
        self.assertEqual(len(found), 4)
