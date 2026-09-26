"""Conflitos de horário e a ocupação que a Grade da Agenda reúne.

O intervalo é semiaberto, `[início, fim)`: há conflito quando `início < outro_fim` e
`fim > outro_início`, e `14:00–15:00` não conflita com `15:00–16:00` (D5 da Change
agendar-uso-eventual-dos-espacos). A verificação usa duas consultas, uma do ensalamento e
uma dos agendamentos, e devolve o primeiro intervalo ocupado para a mensagem.

Os agendamentos aprovados entram em `grid_sources()` e no calendário público por
`register_source`, feito no `ready()` do app (D7).
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.apps import apps
from django.utils import timezone

from schedule.models import Allocation
from schedule.occupancy import Occurrence, grid_sources
from schedule.timetable import WEEKDAYS

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
    """Aula do espaço na data: semestre com período que a contém, no dia da semana dela."""
    if day.weekday() >= len(WEEKDAYS):
        return None
    found = (
        Allocation.objects.filter(
            space=space,
            weekday=WEEKDAYS[day.weekday()],
            semester__start_date__lte=day,
            semester__end_date__gte=day,
            time_slot__start_time__lt=end,
            time_slot__end_time__gt=start,
        )
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
    """Agendamento aprovado no card da Grade da Agenda.

    Os campos `subject`, `group_label`, `teachers` e `stage` existem para que a célula da
    Grade trate a entrada como as demais; o template da Agenda usa `is_booking`.
    """

    pk: int
    description: str
    start: time
    end: time
    requester: str
    subject: str = ''
    teachers: tuple = ()
    stage: str = ''
    is_booking = True

    @property
    def group_label(self):
        return f'agendamento {self.pk}'

    @property
    def is_undergraduate(self):
        return False


class BookingSource:
    """Ocorrências dos agendamentos aprovados do espaço no intervalo, numa consulta."""

    kind = BOOKING

    def occurrences(self, space, start_date, end_date):
        Booking = apps.get_model('bookings', 'Booking')
        first = timezone.make_aware(datetime.combine(start_date, time.min))
        last = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
        bookings = (
            Booking.objects.filter(space=space, starts_at__lt=last, ends_at__gt=first)
            .select_related('requested_by')
            .only('pk', 'space_id', 'starts_at', 'ends_at', 'description', 'requested_by__name')
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
                ),
            ))
        return result


def agenda_sources():
    """Fontes da Grade da Agenda: o ensalamento e os agendamentos aprovados, as mesmas da
    Grade do Ensalamento."""
    return grid_sources()
