"""Conflitos de horário e a ocupação que a Grade da Agenda reúne.

O intervalo é semiaberto, `[início, fim)`: há conflito quando `início < outro_fim` e
`fim > outro_início`, e `14:00–15:00` não conflita com `15:00–16:00` (D5 da Change
agendar-uso-eventual-dos-espacos). A verificação usa duas consultas, uma do ensalamento e
uma dos agendamentos, e devolve o primeiro intervalo ocupado para a mensagem.
"""

from dataclasses import dataclass
from datetime import datetime, time

from django.apps import apps
from django.utils import timezone

from schedule.models import Allocation
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

