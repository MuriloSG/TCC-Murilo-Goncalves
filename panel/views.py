from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from accounts import permissions
from panel import indicators
from panel.forms import PanelFilterForm
from ui.pagination import paginate
from ui.views import ModalView


class PanelView(TemplateView):
    """Painel administrativo: o que pede ação e a ocupação dos espaços, numa tela (Change
    exibir-painel-administrativo).

    A rota exige `PAINEL.VISUALIZAR`, e cada bloco exige também a permissão do módulo dono dos
    dados; o bloco não liberado nem é calculado (D1). O painel só lê: os links levam às telas
    que executam cada ação. Não declara `audit_resource` (D9).
    """

    permission_required = permissions.PANEL_VIEW
    template_name = 'panel/panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        moment = indicators.now_local()
        today = moment.date()
        semesters, semester = indicators.chosen_semester(self.request.GET.get('semestre'), today)
        filters = PanelFilterForm(self.request.GET, semesters, semester)
        show_requests = user.has_perm(permissions.BOOKING_REVIEW)
        show_grid = user.has_perm(permissions.SPACE_ALLOCATION_VIEW)
        show_imports = user.has_perm(permissions.SPACE_ALLOCATION_IMPORT)
        context.update(
            filters=filters,
            semester=semester,
            today=today,
            show_requests=show_requests,
            show_grid=show_grid,
            show_imports=show_imports,
            any_block=show_requests or show_grid or show_imports,
        )
        if show_requests:
            context['requests'] = indicators.requests_summary(moment)
        if show_grid:
            context['occupancy'] = indicators.occupancy(filters.period, today)
            if semester is not None:
                context['issues'] = indicators.grid_issues(semester, moment, user.has_perm(permissions.BOOKING_VIEW))
                context['without_space'] = context['issues'][0].count
            context['issues'] = [
                *(group for group in context.get('issues', []) if group.key != 'sem-espaco'),
                indicators.idle_group(context['occupancy']),
            ]
        if show_imports:
            context['import_count'], context['imports'] = indicators.open_imports()
        return context


ISSUE_KEYS = ('sem-espaco', 'sem-docente', 'conflito', 'choque', 'sem-ocupacao')


class PanelIssueView(ModalView, TemplateView):
    """Itens de um bloco das pendências da grade, em modal pelo htmx e paginados.

    Os filtros do painel chegam pela URL. Além de `PAINEL.VISUALIZAR`, exige
    `ENSALAMENTO.VISUALIZAR` e, para os agendamentos em choque, `AGENDA.VISUALIZAR` (D1).
    Sem o htmx, a mesma URL mostra a página completa.
    """

    permission_required = permissions.PANEL_VIEW
    template_name = 'panel/issue_page.html'
    modal_template_name = 'panel/issue_modal.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if kwargs['key'] not in ISSUE_KEYS:
            raise Http404

    def get_close_url(self):
        query = self.request.GET.copy()
        query.pop('pagina', None)
        return f"{reverse('panel')}?{query.urlencode()}" if query else reverse('panel')

    def action_for(self, key, item, semester):
        """Botão da linha: a Agenda do espaço para os agendamentos em choque e a Grade nos demais."""
        if item.space is None:
            return None
        query = urlencode({**({'semestre': semester.code} if semester else {}), 'sala': item.space.name})
        if key == 'choque':
            return {'url': f"{reverse('agenda_grid')}?{query}", 'icon': 'calendar-clock', 'label': 'Abrir na Agenda', 'page': True}
        return {'url': f"{reverse('space_allocation_grid')}?{query}", 'icon': 'calendar-check', 'label': 'Abrir na Grade', 'page': True}

    def get_context_data(self, **kwargs):
        user = self.request.user
        key = self.kwargs['key']
        if not user.has_perm(permissions.SPACE_ALLOCATION_VIEW):
            raise PermissionDenied
        if key == 'choque' and not user.has_perm(permissions.BOOKING_VIEW):
            raise PermissionDenied
        moment = indicators.now_local()
        semesters, semester = indicators.chosen_semester(self.request.GET.get('semestre'), moment.date())
        filters = PanelFilterForm(self.request.GET, semesters, semester)
        if key == 'sem-ocupacao':
            group = indicators.idle_group(indicators.occupancy(filters.period, moment.date()))
        elif semester is None:
            raise Http404
        else:
            group = next(item for item in indicators.grid_issues(semester, moment, True) if item.key == key)
        page = paginate(self.request, group.items, indicators.MODAL_PAGE_SIZE)
        for item in page.object_list:
            item.action = self.action_for(key, item, semester)
        query = self.request.GET.copy()
        query.pop('pagina', None)
        return super().get_context_data(group=group, page=page, semester=semester, query=query.urlencode(), **kwargs)
