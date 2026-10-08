"""Views públicas do ensalamento: o calendário e o horário original, as únicas rotas do sistema
abertas sem autenticação além do login.

Não declaram `permission_required` nem `audit_resource`, não herdam de view autenticada e não
leem `request.user`: o PermissionMiddleware e o AuditMiddleware deixam a requisição passar sem
exigir login nem gravar acesso (D1 e D2 da Change calendario-publico). Só aceitam GET e HEAD.
As rotas são isentas de CSRF só para que um POST receba 405, e não 403: as views não gravam
nada, não usam sessão e não têm formulário que altere dados.

As opções dos filtros e o HTML da Grade vêm do cache público (`schedule.public_cache`). A
resposta informa o uso do cache em `X-Public-Cache` e pede `Cache-Control: no-cache`, para que
um cache intermediário que respeite o cabeçalho revalide a página; a consistência não depende
dele, e sim da invalidação por geração (Change cachear-telas-publicas-com-redis).
"""

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from schedule import public_cache
from schedule.forms import PublicCalendarFilterForm
from schedule.public import STAGE_CHOICES, original_timetable, public_calendar

DATE_PARAMS = ('inicio', 'fim')


def url_with_filters(name, params, drop=()):
    """URL da outra tela pública com os filtros escolhidos, para alternar sem perdê-los."""
    query = params.copy()
    for key in drop:
        query.pop(key, None)
    url = reverse(name)
    return f'{url}?{query.urlencode()}' if query else url


def grid_html(calendar, lookup, resource):
    """HTML da Grade pelo cache público; sem aulas a consultar, nada é lido nem gravado."""
    if calendar.assemble is None:
        return ''

    def render():
        return render_to_string('schedule/public/grid.html', {'calendar': calendar, 'week': calendar.assemble()})

    return mark_safe(lookup.fetch(resource, calendar.grid_params, render))


class PublicPageView(TemplateView):
    """Base das duas telas públicas: a leitura do cache da requisição e os cabeçalhos da resposta."""

    http_method_names = ['get', 'head']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lookup = public_cache.Lookup()

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['X-Public-Cache'] = self.lookup.status
        patch_cache_control(response, no_cache=True)
        return response


class PublicCalendarView(PublicPageView):
    template_name = 'schedule/public/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = public_calendar(self.request.GET, timezone.localdate(), self.lookup, deferred=True)
        grid = grid_html(calendar, self.lookup, public_cache.CALENDAR_GRID)
        context.update(
            calendar=calendar,
            week=calendar.week,
            grid_html=grid,
            filter_form=PublicCalendarFilterForm(calendar, STAGE_CHOICES),
            calendar_url=reverse('public_calendar'),
            other_url=url_with_filters('public_original_timetable', self.request.GET, DATE_PARAMS),
        )
        return context


class OriginalTimetableView(PublicPageView):
    """Horário original: a semana típica importada, sem alterações, cancelamentos e agendamentos."""

    template_name = 'schedule/public/original.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = original_timetable(self.request.GET, timezone.localdate(), self.lookup, deferred=True)
        grid = grid_html(calendar, self.lookup, public_cache.ORIGINAL_GRID)
        context.update(
            calendar=calendar,
            week=calendar.week,
            grid_html=grid,
            filter_form=PublicCalendarFilterForm(calendar, STAGE_CHOICES, with_dates=False),
            calendar_url=reverse('public_original_timetable'),
            other_url=url_with_filters('public_calendar', self.request.GET, DATE_PARAMS),
        )
        return context
