from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from accounts import permissions
from panel.indicators import chosen_semester, now_local
from reports import heatmap
from reports.forms import HeatmapFilterForm
from schedule.models import WEEKDAY_ORDER
from ui.pagination import paginate
from ui.views import ModalView

CELL_PAGE_SIZE = 10


def heatmap_for(request):
    """Filtros da URL e o mapa calculado, ou None quando o semestre não tem período.

    Os dados são do ensalamento: sem `ENSALAMENTO.VISUALIZAR`, a resposta é 403 (D9).
    """
    if not request.user.has_perm(permissions.SPACE_ALLOCATION_VIEW):
        raise PermissionDenied
    semesters, semester = chosen_semester(request.GET.get('semestre'), now_local().date())
    form = HeatmapFilterForm(request.GET, semesters, semester)
    filters = form.filters()
    return form, filters, heatmap.build(filters)


class HeatmapView(TemplateView):
    """Mapa de calor dos espaços: faixa × dia na semana típica do semestre (Change
    gerar-mapa-de-calor-dos-espacos).

    Exige `RELATORIO.VISUALIZAR` pela rota e `ENSALAMENTO.VISUALIZAR` pelos dados, como os
    blocos do painel (D9). Só lê os dados e não declara `audit_resource`.
    """

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
    """Espaços ocupados e disponíveis de uma célula do mapa, em modal pelo htmx e paginados (D7).

    Os filtros do mapa chegam pela URL. Sem o htmx, a mesma URL mostra a página completa.
    """

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
