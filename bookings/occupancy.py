"""Conflitos de horário no intervalo semiaberto `[início, fim)` e a ocupação da Grade da Agenda."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.apps import apps
from django.utils import timezone

from schedule.models import Allocation
from schedule.occupancy import Occurrence, grid_sources
from schedule.timetable import readable_course, readable_group

BOOKING = 'AGENDAMENTO'
SPACE_ALLOCATION = 'ENSALAMENTO'


@dataclass(frozen=True)
class Conflict:
    kind: str
    start: time
    end: time


def conflict_message(conflict):
    if conflict.kind == SPACE_ALLOCATION:
        return f'Este espaço está ocupado pelo ensalamento das {conflict.start:%H:%M} às {conflict.end:%H:%M}. Escolha outro horário.'
    return f'Este espaço está ocupado das {conflict.start:%H:%M} às {conflict.end:%H:%M}. Escolha outro horário.'


def allocation_conflict(space, day, start, end):
    """Aula do espaço na data, sem a ocorrência cancelada."""
    found = (
        Allocation.objects.active_on(day)
        .filter(space=space, time_slot__start_time__lt=end, time_slot__end_time__gt=start)
        .order_by('time_slot__start_time')
        .values_list('time_slot__start_time', 'time_slot__end_time')
        .first()
    )
    return Conflict(SPACE_ALLOCATION, *found) if found else None


def booking_conflict(space, day, start, end):
    Booking = apps.get_model('bookings', 'Booking')
    starts_at = timezone.make_aware(datetime.combine(day, start))
    ends_at = timezone.make_aware(datetime.combine(day, end))
    found = (
        Booking.objects.filter(space=space, starts_at__lt=ends_at, ends_at__gt=starts_at)
        .order_by('starts_at')
        .values_list('starts_at', 'ends_at')
        .first()
    )
    if not found:
        return None
    return Conflict(BOOKING, timezone.localtime(found[0]).time(), timezone.localtime(found[1]).time())


def find_conflict(space, day, start, end):
    """Primeiro intervalo ocupado do espaço na data, ou None quando está disponível."""
    return allocation_conflict(space, day, start, end) or booking_conflict(space, day, start, end)


@dataclass(frozen=True)
class BookingEntry:
    """Agendamento na Grade, com os campos que a célula espera das demais entradas."""

    pk: int
    description: str
    start: time
    end: time
    requester: str
    subject: str = ''
    teachers: tuple = ()
    stage: str = ''
    course: str = ''
    group: str = ''
    teacher: str = ''
    requester_id: int | None = None
    is_booking = True

    @property
    def group_label(self):
        return f'agendamento {self.pk}'

    @property
    def is_undergraduate(self):
        return False


def offering_fields(assignment):
    """Disciplina, curso, turma e docente do agendamento, vazios quando não há oferta."""
    if assignment is None:
        return {}
    class_group = assignment.offering.class_group
    return {
        'subject': assignment.offering.subject.name,
        'course': readable_course(class_group.course.name),
        'group': readable_group(class_group.label),
        'teacher': assignment.teacher.name,
    }


class BookingSource:
    """Ocorrências dos agendamentos aprovados do espaço no intervalo, numa consulta."""

    kind = BOOKING

    def occurrences(self, space, start_date, end_date):
        Booking = apps.get_model('bookings', 'Booking')
        first = timezone.make_aware(datetime.combine(start_date, time.min))
        last = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
        bookings = (
            Booking.objects.filter(space=space, starts_at__lt=last, ends_at__gt=first)
            .select_related(
                'requested_by',
                'request__teaching_assignment__teacher',
                'request__teaching_assignment__offering__subject',
                'request__teaching_assignment__offering__class_group__course',
            )
        )
        result = []
        for booking in bookings:
            starts_at, ends_at = timezone.localtime(booking.starts_at), timezone.localtime(booking.ends_at)
            result.append(Occurrence(
                date=starts_at.date(),
                start=starts_at.time(),
                end=ends_at.time(),
                space_id=space.pk,
                kind=self.kind,
                entry=BookingEntry(
                    pk=booking.pk,
                    description=booking.description,
                    start=starts_at.time(),
                    end=ends_at.time(),
                    requester=booking.requested_by.name,
                    requester_id=booking.requested_by_id,
                    **offering_fields(booking.request.teaching_assignment),
                ),
            ))
        return result


    def public_occurrences(self, start_date, end_date, space=None, teacher_name=None):
        """Agendamentos do intervalo para o calendário público, sem a descrição."""
        Booking = apps.get_model('bookings', 'Booking')
        first = timezone.make_aware(datetime.combine(start_date, time.min))
        last = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
        bookings = Booking.objects.filter(starts_at__lt=last, ends_at__gt=first)
        if space is not None:
            bookings = bookings.filter(space=space)
        if teacher_name is not None:
            bookings = bookings.filter(requested_by__username__iexact=teacher_name)
        bookings = bookings.select_related(
            'space', 'requested_by',
            'request__teaching_assignment__teacher',
            'request__teaching_assignment__offering__subject',
            'request__teaching_assignment__offering__class_group__course',
        )
        result = []
        for booking in bookings:
            starts_at, ends_at = timezone.localtime(booking.starts_at), timezone.localtime(booking.ends_at)
            result.append(PublicOccurrence(
                date=starts_at.date(),
                start=starts_at.time(),
                end=ends_at.time(),
                space=booking.space.name,
                requester=booking.requested_by.name,
                email=booking.requested_by.email,
                **offering_fields(booking.request.teaching_assignment),
            ))
        return result


@dataclass(frozen=True)
class PublicOccurrence:
    """Agendamento aprovado como o calendário público recebe: sem descrição e sem IDs."""

    date: object
    start: time
    end: time
    space: str
    requester: str
    email: str
    subject: str = ''
    course: str = ''
    group: str = ''
    teacher: str = ''


def own_occurrences(occurrences, user):
    """Só os agendamentos do usuário e as aulas em que ele é docente."""
    username = (user.username or '').casefold()
    return [
        item for item in occurrences
        if (item.kind == BOOKING and item.entry.requester_id == user.pk)
        or (item.kind == SPACE_ALLOCATION and username and username in {name.casefold() for name in item.entry.teachers})
    ]


def agenda_sources():
    """Fontes da Grade da Agenda: o ensalamento e os agendamentos aprovados."""
    return grid_sources()
