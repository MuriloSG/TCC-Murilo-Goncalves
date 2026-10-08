from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from accounts import permissions
from bookings.views import decorate, status_badge
from panel.indicators import chosen_semester, now_local
from reports import heatmap, requests
from reports.forms import HeatmapFilterForm, RequestsFilterForm
from schedule.models import WEEKDAY_ORDER
from ui.pagination import paginate
from ui.views import ModalView

CELL_PAGE_SIZE = 10


def heatmap_for(request):
    """Filtros e mapa calculado; sem `ENSALAMENTO.VISUALIZAR`, responde 403."""
    if not request.user.has_perm(permissions.SPACE_ALLOCATION_VIEW):
        raise PermissionDenied
    semesters, semester = chosen_semester(request.GET.get('semestre'), now_local().date())
    form = HeatmapFilterForm(request.GET, semesters, semester)
    filters = form.filters()
    return form, filters, heatmap.build(filters)


class HeatmapView(TemplateView):
    """Exige `RELATORIO.VISUALIZAR` pela rota e `ENSALAMENTO.VISUALIZAR` pelos dados."""

    permission_required = permissions.REPORT_VIEW
    template_name = 'reports/heatmap.html'

    def get_context_data(self, **kwargs):
        form, filters, result = heatmap_for(self.request)
        query = self.request.GET.copy()
        query.pop('pagina', None)
        return super().get_context_data(
            filters=form, semester=filters.semester, heatmap=result, query=query.urlencode(), **kwargs,
        )


class HeatmapCellView(ModalView, TemplateView):
    """Espaços de uma célula do mapa, paginados em modal pelo htmx ou na página completa."""

    permission_required = permissions.REPORT_VIEW
    template_name = 'reports/cell_page.html'
    modal_template_name = 'reports/cell_modal.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        slugs = [heatmap.day_slug(day) for day in WEEKDAY_ORDER]
        if kwargs['day'] not in slugs:
            raise Http404
        self.day_index = slugs.index(kwargs['day'])

    def get_close_url(self):
        query = self.request.GET.copy()
        query.pop('pagina', None)
        return f"{reverse('report_heatmap')}?{query.urlencode()}" if query else reverse('report_heatmap')

    def action_for(self, space, semester):
        query = urlencode({**({'semestre': semester.code} if semester else {}), 'sala': space.name})
        return {'url': f"{reverse('space_allocation_grid')}?{query}", 'icon': 'calendar-check', 'label': 'Abrir na Grade', 'page': True}

    def get_context_data(self, **kwargs):
        form, filters, result = heatmap_for(self.request)
        if result is None or self.kwargs['slot'] >= len(result.slots):
            raise Http404
        cell = result.cell(self.day_index, self.kwargs['slot'])
        busy, free = heatmap.cell_spaces(result, cell, filters)
        rows = [{'space': item.space, 'usage': item} for item in busy] + [{'space': space, 'usage': None} for space in free]
        page = paginate(self.request, rows, CELL_PAGE_SIZE)
        for row in page.object_list:
            row['action'] = self.action_for(row['space'], filters.semester)
        query = self.request.GET.copy()
        query.pop('pagina', None)
        return super().get_context_data(
            cell=cell, heatmap=result,
            busy_count=len(busy), free_count=len(free), page=page, query=query.urlencode(), **kwargs,
        )


class RequestsReportView(TemplateView):
    """Exige também `AGENDA.ANALISAR`, porque mostra as solicitações de todos os usuários."""

    permission_required = permissions.REPORT_VIEW
    template_name = 'reports/requests.html'

    def get_context_data(self, **kwargs):
        if not self.request.user.has_perm(permissions.BOOKING_REVIEW):
            raise PermissionDenied
        today = now_local().date()
        semesters, semester = chosen_semester(self.request.GET.get('semestre'), today)
        form = RequestsFilterForm(self.request.GET, semesters, semester)
        filters = form.filters()
        report = requests.build(filters, today)
        if report is not None:
            for row in report.statuses:
                row.badge = status_badge(row)
            for item in report.spaces:
                item.action = self.agenda_action(item.space)
            decorate(report.rejections, 'agenda_review_detail')
        return super().get_context_data(
            filters=form, semester=filters.semester, report=report, outcomes=self.outcomes(report), **kwargs,
        )

    def outcomes(self, report):
        """Desfechos das alternativas, com tom, ícone e percentual sobre as sugeridas."""
        if report is None:
            return []
        return [
            {'label': label, 'count': count, 'percent': requests.percent(count, report.suggested), 'tone': tone, 'icon': icon}
            for label, count, tone, icon in (
                ('Aceitas', report.suggestion_accepted, 'success', 'check'),
                ('Recusadas por quem solicitou', report.suggestion_declined, 'error', 'x'),
                ('Rejeitadas depois', report.suggestion_rejected, 'error', 'circle-x'),
                ('Resposta pendente', report.suggestion_awaiting, 'warning', 'clock'),
            )
        ]

    def agenda_action(self, space):
        url = f"{reverse('agenda_grid')}?{urlencode({'sala': space.name})}"
        return {'url': url, 'icon': 'calendar-clock', 'label': 'Abrir na Agenda', 'page': True}
