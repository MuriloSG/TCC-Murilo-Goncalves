"""Dados e relógio comuns aos testes da Agenda.

O relógio é fixado em 01/10/2026 às 10:00, no fuso do campus, para que as datas dos
cenários da spec (15/10/2026, uma quinta-feira) estejam sempre no futuro.
"""

from datetime import date, datetime, time
from unittest import mock

from django.utils import timezone

from accounts import permissions
from accounts.models import Role, User
from bookings.models import BookingRequest
from schedule.models import ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.tests.test_timetable import allocate

NOW = timezone.make_aware(datetime(2026, 10, 1, 10, 0))
THURSDAY = date(2026, 10, 15)
FRIDAY = date(2026, 10, 16)

REQUESTER = (permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST)
REVIEWER = (permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST, permissions.BOOKING_REVIEW)


def user_with(email, *codes):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role)


def frozen_clock(test_case):
    patcher = mock.patch('django.utils.timezone.now', return_value=NOW)
    patcher.start()
    test_case.addCleanup(patcher.stop)


def semester_with_lesson(space_name='Laboratório de Informática 2'):
    """Semestre 2026/2 com período e uma aula às quintas-feiras, das 14:10 às 15:00."""
    semester, _ = Semester.objects.resolve('2026/2')
    semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
    course, _ = Course.objects.resolve('INFORMÁTICA', stage=Stage.SECONDARY)
    group, _ = ClassGroup.objects.resolve(course, '2º ANO A')
    allocate(semester, group, 'Redes', Weekday.THURSDAY, time(14, 10), time(15, 0), space_name, ['Viviane'])
    return semester


def submit(user, space, day=THURSDAY, start=time(16, 0), end=time(18, 0), description='Reunião do projeto de extensão com os alunos.'):
    return BookingRequest.objects.submit(user, space, day, start, end, description)


def space(name):
    return Space.objects.register(name)
