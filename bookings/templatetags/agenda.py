"""Auxiliares dos templates da Agenda: o link de solicitação da faixa e a classe da célula."""

from urllib.parse import urlencode

from django import template
from django.urls import reverse
from django.utils import timezone

from bookings.models import moment

from schedule.timetable import CLASH, JOINT, SINGLE

register = template.Library()


@register.simple_tag
def request_url(space, day, start, end):
    """Endereço do modal "Solicitar agendamento" com a faixa, ou vazio quando ela já começou.

    A semana típica, sem data, não oferece a ação.
    """
    if space is None or day is None or moment(day, start) <= timezone.now():
        return ''
    query = {'espaco': space.pk, 'data': day.isoformat(), 'inicio': f'{start:%H:%M}', 'fim': f'{end:%H:%M}'}
    return f"{reverse('agenda_request_create')}?{urlencode(query)}"


@register.filter
def lesson_kind(cell):
    """Uma turma, turmas juntas ou choque, contando só as aulas da célula.

    Os agendamentos têm o próprio selo e não entram na classificação das turmas.
    """
    lessons = [entry for entry in cell.entries if not getattr(entry, 'is_booking', False)]
    groups = {entry.group_label for entry in lessons}
    if len(groups) <= 1:
        return SINGLE
    kinds = {(entry.subject.casefold(), frozenset(name.casefold() for name in entry.teachers)) for entry in lessons}
    return JOINT if len(kinds) == 1 else CLASH


@register.filter
def lesson_groups(cell):
    return len({entry.group_label for entry in cell.entries if not getattr(entry, 'is_booking', False)})


@register.filter
def day_rows(week, day):
    """Faixas de um dia com a célula de cada uma, para a lista por dia do celular."""
    index = week.days.index(day)
    return [(row, row.cells[index]) for row in week.rows]
