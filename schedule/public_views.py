"""View do calendário público, a única rota do sistema aberta sem autenticação além do login.

Não declara `permission_required` nem `audit_resource`, não herda de view autenticada e não
lê `request.user`: o PermissionMiddleware e o AuditMiddleware deixam a requisição passar sem
exigir login nem gravar acesso (D1 e D2 da Change calendario-publico). Só aceita GET e HEAD.
A rota é isenta de CSRF só para que um POST receba 405, e não 403: a view não grava nada,
não usa sessão e não tem formulário que altere dados.
"""

from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from schedule.forms import PublicCalendarFilterForm
from schedule.public import STAGE_CHOICES, public_calendar


class PublicCalendarView(TemplateView):
    template_name = 'schedule/public/calendar.html'
    http_method_names = ['get', 'head']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = public_calendar(self.request.GET, timezone.localdate())
        url = reverse('public_calendar')
        context.update(
            calendar=calendar,
            week=calendar.week,
            filter_form=PublicCalendarFilterForm(calendar, STAGE_CHOICES),
            calendar_url=url,
        )
        return context
