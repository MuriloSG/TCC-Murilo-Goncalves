"""Views públicas do ensalamento: o calendário e o horário original, as únicas rotas do sistema
abertas sem autenticação além do login.

Não declaram `permission_required` nem `audit_resource`, não herdam de view autenticada e não
leem `request.user`: o PermissionMiddleware e o AuditMiddleware deixam a requisição passar sem
exigir login nem gravar acesso (D1 e D2 da Change calendario-publico). Só aceitam GET e HEAD.
As rotas são isentas de CSRF só para que um POST receba 405, e não 403: as views não gravam
nada, não usam sessão e não têm formulário que altere dados.
"""

from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

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


class PublicCalendarView(TemplateView):
    template_name = 'schedule/public/calendar.html'
    http_method_names = ['get', 'head']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = public_calendar(self.request.GET, timezone.localdate())
        context.update(
            calendar=calendar,
            week=calendar.week,
            filter_form=PublicCalendarFilterForm(calendar, STAGE_CHOICES),
            calendar_url=reverse('public_calendar'),
            other_url=url_with_filters('public_original_timetable', self.request.GET, DATE_PARAMS),
        )
        return context


class OriginalTimetableView(TemplateView):
    """Horário original: a semana típica importada, sem alterações, cancelamentos e agendamentos."""

    template_name = 'schedule/public/original.html'
    http_method_names = ['get', 'head']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = original_timetable(self.request.GET, timezone.localdate())
        context.update(
            calendar=calendar,
            week=calendar.week,
            filter_form=PublicCalendarFilterForm(calendar, STAGE_CHOICES, with_dates=False),
            calendar_url=reverse('public_original_timetable'),
            other_url=url_with_filters('public_calendar', self.request.GET, DATE_PARAMS),
        )
        return context
