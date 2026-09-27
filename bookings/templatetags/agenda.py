"""Auxiliares dos templates da Agenda: o link de solicitação da faixa e as faixas de um dia."""

from urllib.parse import urlencode

from django import template
from django.urls import reverse
from django.utils import timezone

from bookings.models import moment


register = template.Library()


@register.simple_tag
def request_url(space, day, start, end, busy=()):
    """Endereço do modal "Solicitar agendamento" com a faixa, ou vazio quando ela já começou.

    A semana típica, sem data, não oferece a ação, nem a faixa que cruza um horário de
    `busy`, ocupado por outra pessoa e escondido em "Minha agenda".
    """
    if space is None or day is None or moment(day, start) <= timezone.now() or is_busy(busy, day, start, end):
        return ''
    query = {'espaco': space.pk, 'data': day.isoformat(), 'inicio': f'{start:%H:%M}', 'fim': f'{end:%H:%M}'}
    return f"{reverse('agenda_request_create')}?{urlencode(query)}"


def is_busy(busy, day, start, end):
    return any(date == day and begin < end and finish > start for date, begin, finish in busy)


@register.simple_tag
def busy_slot(busy, day, start, end):
    """Diz se a faixa cruza um horário ocupado por outra pessoa, escondido em "Minha agenda"."""
    return day is not None and is_busy(busy, day, start, end)


@register.filter
def day_rows(week, day):
    """Faixas de um dia com a célula de cada uma, para a lista por dia do celular."""
    index = week.days.index(day)
    return [(row, row.cells[index]) for row in week.rows]
