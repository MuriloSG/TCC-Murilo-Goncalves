"""Salas ativas sem aula listadas no Ensalamento e no calendário público, com a Grade vazia."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from schedule.models import ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.tests.test_timetable import allocate


class SpacesWithoutLessonsTests(TestCase):
    def setUp(self):
        semester, _ = Semester.objects.resolve('2026/2')
        semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('INFORMÁTICA', stage=Stage.SECONDARY)
        group, _ = ClassGroup.objects.resolve(course, '2º ANO A')
        allocate(semester, group, 'Redes', Weekday.MONDAY, time(7, 20), time(8, 10), '1/2')
        Space.objects.register('1/3')
        Space.objects.register('Sala 8').deactivate()
        role = Role.objects.create_role(code='CONSULTA', name='Consulta', permissions=[permissions.SPACE_ALLOCATION_VIEW])
        self.client.force_login(User.objects.register(email='consulta@ifnmg.edu.br', name='Consulta', role=role))

    def test_space_allocation_grid_lists_and_shows_the_empty_week(self):
        response = self.client.get(reverse('space_allocation_grid'), {'semestre': '2026/2', 'sala': '1/3', 'semana': '2026-10-05'})
        self.assertEqual(response.context['space'].name, '1/3')
        self.assertContains(response, '<option value="1/3"')
        self.assertNotContains(response, '<option value="Sala 8"')
        week = response.context['week']
        self.assertEqual(len(week.rows), 1)
        self.assertEqual(week.occupied, 0)
        self.assertNotContains(response, 'Redes')

    def test_public_calendar_lists_and_shows_the_empty_grid(self):
        self.client.logout()
        response = self.client.get(reverse('public_calendar'), {'semestre': '2026/2', 'sala': '1/3', 'inicio': '2026-10-05', 'fim': '2026-10-09'})
        self.assertContains(response, '<option value="1/3" selected')
        self.assertNotContains(response, '<option value="Sala 8"')
        self.assertContains(response, 'timetable-grid')
        self.assertNotContains(response, 'Redes')
