"""Auxiliares dos templates da Agenda: o link de solicitação da faixa e as faixas de um dia."""

from urllib.parse import urlencode

from django import template
from django.urls import reverse
from django.utils import timezone

from bookings.models import moment


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
def day_rows(week, day):
    """Faixas de um dia com a célula de cada uma, para a lista por dia do celular."""
    index = week.days.index(day)
    return [(row, row.cells[index]) for row in week.rows]
