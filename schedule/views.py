"""Grade do ensalamento confirmado, telas da importação e cadastro de espaços.

A grade exige `ENSALAMENTO.VISUALIZAR`, as telas da importação exigem
`ENSALAMENTO.IMPORTAR` e a exclusão de importação exige `ENSALAMENTO.EXCLUIR_IMPORTACAO`.
O cadastro de espaços exige a permissão de cada operação do recurso `ESPACO` (D15 da Change
manipulacao-dos-espacos). A autenticação vem do `login_required` no `urls.py` e a
permissão é declarada aqui como dado, verificada pelo PermissionMiddleware.
A importação não tem modelo para baixar, porque a planilha é a do campus e não é alterada
pelo sistema.
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from accounts import permissions
from accounts.views import ConfirmedActionView, OperationFormView
from audit import catalog
from imports.views import (
    ImportConfirmView,
    ImportDeleteView,
    ImportDetailView,
    ImportDiscardView,
    ImportListView,
    ImportScreens,
    ImportUploadView,
)
from schedule.forms import GridFilterForm, SpaceFilterForm, SpaceForm
from schedule.models import Space
from schedule.imports import SpaceAllocationImport, concluded_message
from ui.pagination import paginate
from schedule.occupancy import occupancy
from schedule.timetable import (
    current_semester_code,
    dated_space_month,
    dated_space_week,
    imported_semesters,
    month_start,
    month_dates,
    natural_key,
    space_week,
    spaces_of,
    week_start,
)

WEEK_VIEW = 'semana'
MONTH_VIEW = 'mes'


SPACE_ALLOCATION_IMPORT_SCREENS = ImportScreens(
    definition=SpaceAllocationImport(),
    url_prefix='space_allocation_import',
    section_title='Ensalamento',
    section_url_name='space_allocation_grid',
    section_permission=permissions.SPACE_ALLOCATION_VIEW,
    list_title='Importações de ensalamento',
    upload_title='Importar ensalamento',
    empty_message='Nenhuma importação de ensalamento.',
    concluded_message=concluded_message,
    delete_permission=permissions.SPACE_ALLOCATION_IMPORT_DELETE,
)


def counted(total, singular, plural):
    return f'{total} {singular if total == 1 else plural}'


def occupation_text(week, is_month=False):
    """Faixas ocupadas e disponíveis da sala na semana ou no mês."""
    period = 'no mês' if is_month else 'na semana'
    return f'{counted(week.occupied, "faixa ocupada", "faixas ocupadas")} e {counted(week.available, "disponível", "disponíveis")} {period}.'


def parse_date(value):
    """Data no formato AAAA-MM-DD da URL, ou None quando não serve."""
    try:
        return date.fromisoformat(value or '')
    except ValueError:
        return None


def month_reference(semester, first, today):
    """Data que leva do mês à semana: hoje, quando está no mês, ou o primeiro dia dele no período."""
    in_period = [day for day in month_dates(first) if semester.contains(day)]
    if today in in_period:
        return today
    return in_period[0] if in_period else first


def parse_month(value):
    """Primeiro dia do mês no formato AAAA-MM da URL, ou None quando não serve."""
    return parse_date(f'{value}-01') if value and len(value) == 7 else None


class SpaceAllocationImportListView(ImportListView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportUploadView(ImportUploadView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationGridView(TemplateView):
    """Grade da semana de uma sala no ensalamento confirmado, a tela de entrada do módulo (D15).

    O semestre padrão é o atual, calculado pela data, e as opções são ele e os semestres
    com alocação confirmada. A sala padrão é a primeira do semestre, pelo nome, e um valor que não
    existe na lista cai no padrão, sem erro. Com o período do semestre, a semana é datada e
    navegável pelo parâmetro `semana`; sem ele, é a semana típica com o aviso (D3 e D7 da
    Change visualizar-ocupacao-por-semana-e-mes).
    """

    permission_required = permissions.SPACE_ALLOCATION_VIEW
    template_name = 'schedule/grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        semesters = {semester.code: semester for semester in imported_semesters()}
        current = current_semester_code(today)
        codes = sorted(set(semesters) | {current}, reverse=True)
        code = self.request.GET.get('semestre')
        code = code if code in codes else current
        semester = semesters.get(code)
        spaces = spaces_of(semester)
        chosen = (self.request.GET.get('sala') or '').casefold()
        space = next((option for option in spaces if option.name.casefold() == chosen), spaces[0] if spaces else None)
        view = MONTH_VIEW if self.request.GET.get('visao') == MONTH_VIEW else WEEK_VIEW
        chosen_week = parse_date(self.request.GET.get('semana'))
        chosen_month = parse_month(self.request.GET.get('mes'))
        dated = semester is not None and semester.has_period
        if dated and view == MONTH_VIEW:
            first = month_start(semester, chosen_month or chosen_week, today)
            month_end = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            occurrences = occupancy(space, first, month_end) if space else []
            week = dated_space_month(semester, space, first, today, occurrences)
        elif dated:
            reference = chosen_week or (month_reference(semester, chosen_month, today) if chosen_month else None)
            start = week_start(semester, reference, today)
            occurrences = occupancy(space, start, start + timedelta(days=4)) if space else []
            week = dated_space_week(semester, space, start, today, occurrences)
        else:
            view = WEEK_VIEW
            week = space_week(semester, space, today)
        grid_url = reverse('space_allocation_grid')
        is_month = view == MONTH_VIEW

        def grid_link(target, day=None, fragment=''):
            query = {'semestre': code, 'sala': space.name if space else ''}
            if target == MONTH_VIEW:
                query['visao'] = MONTH_VIEW
                if day is not None:
                    query['mes'] = f'{day:%Y-%m}'
            elif day is not None:
                query['semana'] = day.isoformat()
            return f'{grid_url}?{urlencode(query)}{fragment}'

        context.update(
            week=week,
            is_month=is_month,
            semester_code=code,
            space=space,
            semester=semester,
            period_missing=semester is not None and not semester.has_period,
            filter_form=GridFilterForm(
                {
                    'semestre': code,
                    'sala': space.name if space else '',
                    'visao': view,
                    'semana': week.start.isoformat() if week.start and not is_month else '',
                    'mes': f'{week.start:%Y-%m}' if week.start and is_month else '',
                },
                semesters=codes,
                spaces=spaces,
            ),
            grid_url=grid_url,
            previous_url=grid_link(view, week.previous) if week.previous else None,
            following_url=grid_link(view, week.following) if week.following else None,
            today_url=grid_link(view, fragment='#hoje' if is_month else ''),
            import_list_url=SPACE_ALLOCATION_IMPORT_SCREENS.url('list'),
            occupation_text=occupation_text(week, is_month),
        )
        return context


class SpaceAllocationImportDetailView(ImportDetailView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportConfirmView(ImportConfirmView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportDiscardView(ImportDiscardView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportDeleteView(ImportDeleteView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT_DELETE
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceListView(ListView):
    """Lista de espaços com busca e filtros pela URL, como a lista de usuários.

    Quando o formulário de filtros pede pelo htmx, responde só com a tabela e o rodapé. A
    ordem é a natural do nome, a mesma da Grade: `1/4` vem antes de `1/10`.
    """

    permission_required = permissions.SPACE_VIEW
    audit_resource = catalog.SPACE
    template_name = 'schedule/space_list.html'
    table_template_name = 'schedule/partials/space_table.html'
    table_target = 'tabela-espacos'
    context_object_name = 'spaces'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = SpaceFilterForm(request.GET)
        self.term, self.status, self.origin = self.filters.criteria()

    def get_queryset(self):
        spaces = Space.objects.search(self.term, self.status, self.origin)
        spaces = spaces.select_related('source_import').prefetch_related('names').annotate(lessons=Count('allocations'))
        return sorted(spaces, key=natural_key)

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == self.table_target:
            return [self.table_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            filters=self.filters,
            filtered=bool(self.term) or self.status != 'todos' or self.origin != 'todas',
            total=Space.objects.count(),
            table_target=self.table_target,
            **kwargs,
        )
        context['page'] = paginate(self.request, self.object_list)
        context['spaces'] = context['page'].object_list
        user = self.request.user
        for space in context['spaces']:
            space.deletable = not space.lessons and user.has_perm(permissions.SPACE_DELETE)
            space.history_action = history_action(space) if user.has_perm(permissions.AUDIT_VIEW) else None
        return context


def history_action(space):
    """Ação da linha que abre a consulta da auditoria filtrada pelo espaço."""
    query = urlencode({'recurso': catalog.SPACE, 'registro': space.pk})
    return {'url': f"{reverse('audit_log_list')}?{query}", 'label': 'Ver auditoria', 'icon': 'scroll-text', 'danger': False, 'page': True}


class SpaceFormView(OperationFormView):
    audit_resource = catalog.SPACE
    template_name = 'schedule/space_form.html'
    modal_template_name = 'schedule/space_form_modal.html'
    success_url = reverse_lazy('spaces_list')
    form_class = SpaceForm


class SpaceCreateView(SpaceFormView):
    permission_required = permissions.SPACE_CREATE
    title = 'Cadastrar espaço'
    submit_label = 'Cadastrar'

    def perform(self, data):
        space = Space.objects.register(data['name'], other_names=data['other_names'])
        messages.success(self.request, f'Espaço {space.name} cadastrado.')


class SpaceUpdateView(SpaceFormView):
    permission_required = permissions.SPACE_EDIT
    model = Space
    title = 'Editar espaço'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def perform(self, data):
        self.target.update_details(data['name'], data['other_names'])
        messages.success(self.request, f'Espaço {self.target.name} atualizado.')


class SpaceActionView(ConfirmedActionView):
    audit_resource = catalog.SPACE
    model = Space
    template_name = 'schedule/space_confirm.html'
    modal_template_name = 'schedule/space_confirm_modal.html'
    success_url = reverse_lazy('spaces_list')
    action = ''

    def get_context_data(self, **kwargs):
        return super().get_context_data(action=self.action, **kwargs)


class SpaceDeactivateView(SpaceActionView):
    permission_required = permissions.SPACE_CHANGE_STATUS
    action = 'desativar'

    def perform(self):
        self.target.deactivate()
        messages.success(self.request, f'Espaço {self.target.name} desativado.')


class SpaceReactivateView(SpaceActionView):
    permission_required = permissions.SPACE_CHANGE_STATUS
    action = 'reativar'

    def perform(self):
        self.target.reactivate()
        messages.success(self.request, f'Espaço {self.target.name} reativado.')


class SpaceDeleteView(SpaceActionView):
    permission_required = permissions.SPACE_DELETE
    action = 'excluir'

    def perform(self):
        self.target.delete_space()
        messages.success(self.request, f'Espaço {self.target.name} excluído.')
