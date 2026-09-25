"""Grade do ensalamento confirmado, telas da importação e cadastro de espaços.

A grade exige `ENSALAMENTO.VISUALIZAR`, as telas da importação exigem
`ENSALAMENTO.IMPORTAR` e a exclusão de importação exige `ENSALAMENTO.EXCLUIR_IMPORTACAO`.
O cadastro de espaços exige a permissão de cada operação do recurso `ESPACO` (D15 da Change
manipulacao-dos-espacos). A autenticação vem do `login_required` no `urls.py` e a
permissão é declarada aqui como dado, verificada pelo PermissionMiddleware.
A importação não tem modelo para baixar, porque a planilha é a do campus e não é alterada
pelo sistema.
"""

import logging
from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from accounts import permissions
from accounts.utils import add_operation_error
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
    load_importation,
)
from imports.models import Import
from schedule.forms import GridFilterForm, SpaceAssociateForm, SpaceFilterForm, SpaceForm
from schedule.models import SPACE_PERMISSION_MESSAGE, Space, SpaceDecision, Weekday
from schedule.spaces import CREATE, INACTIVE, REACTIVATE, SIMILAR, classify_import, decision_permissions, options_of
from schedule.imports import SpaceAllocationImport, concluded_message
from ui.pagination import paginate
from ui.views import ModalView
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

logger = logging.getLogger(__name__)

WEEK_VIEW = 'semana'
MONTH_VIEW = 'mes'


SPACE_PANEL_TEMPLATE = 'schedule/partials/space_panel.html'

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
    panel_template=SPACE_PANEL_TEMPLATE,
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
    """Detalhe da importação com o quadro "Espaços desta importação" antes das linhas (D14)."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['space_panel'] = space_panel(self.object, self.request.user)
        return context


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


PERMISSION_MESSAGE = SPACE_PERMISSION_MESSAGE
REFRESH_FAILED_MESSAGE = 'Não foi possível atualizar a prévia.'


def plural(total, singular, many):
    return singular if total == 1 else many


def usage_text(usage):
    """Uso agregado de um nome encontrado: aulas, turmas e dias da semana."""
    lessons = f'{usage.lessons} {plural(usage.lessons, "aula", "aulas")}'
    groups = f'{len(usage.groups)} {plural(len(usage.groups), "turma", "turmas")}'
    days = [Weekday(code).label.lower() for code in Weekday.values if code in usage.weekdays]
    joined = days[0] if len(days) == 1 else f'{", ".join(days[:-1])} e {days[-1]}' if days else ''
    return ' · '.join(part for part in (lessons, groups, joined) if part)


def effect_text(entry, resolution):
    """O que a confirmação fará com o nome encontrado, sempre no futuro."""
    if entry.outcome == CREATE:
        return 'Será cadastrado como espaço novo.'
    if entry.outcome == REACTIVATE:
        return f'O espaço {entry.space.name} será reativado.'
    if entry.target_key is not None:
        target = resolution.found[entry.target_key].name
        return f'Será guardado como outro nome de {target}, que será cadastrado.'
    text = f'Será guardado como outro nome de {entry.target.name}.'
    if not entry.target.is_active:
        text += f' O espaço {entry.target.name} será reativado.'
    return text


def decision_actions(entry, user):
    """Botões de decisão que o nome aceita e que o usuário pode usar (D11 e D14)."""
    allowed = options_of(entry)
    actions = []

    def add(kind, label, space=None, target_name='', note=''):
        if kind in allowed and all(user.has_perm(code) for code in decision_permissions(entry, kind, space, target_name)):
            actions.append({
                'kind': kind, 'label': label, 'space': space.pk if space else '', 'target': target_name, 'note': note,
            })

    if entry.identifies_inactive:
        add(SpaceDecision.Kind.REACTIVATE, f'Reativar {entry.space.name}')
    for candidate in entry.candidates:
        if candidate.space is not None:
            note = 'desativado, será reativado' if candidate.is_inactive else ''
            add(SpaceDecision.Kind.SAME, f'É o mesmo que {candidate.name}', space=candidate.space, note=note)
        else:
            add(SpaceDecision.Kind.SAME, f'É o mesmo que {candidate.name}', target_name=candidate.name)
    add(SpaceDecision.Kind.NEW, 'É um espaço novo')
    return actions


def can_choose(entry, user):
    """Diz se o usuário pode escolher, entre os espaços do cadastro, o que é o mesmo."""
    return SpaceDecision.Kind.SAME in options_of(entry) and user.has_perm(permissions.SPACE_EDIT)


def space_panel(importation, user):
    """Contexto do quadro "Espaços desta importação", calculado pela classificação (D14).

    Enquanto a importação está aberta, tudo é descrito no futuro, porque nada foi gravado no
    cadastro. Na importação com erros, só os nomes que vão precisar de decisão aparecem, sem
    controles. Na concluída, aparecem os espaços que ela cadastrou.
    """
    status = importation.status
    if status == Import.Status.DISCARDED:
        return None
    if status == Import.Status.CONCLUDED:
        return {'concluded': True, 'created': sorted(Space.objects.filter(source_import=importation), key=natural_key)}
    resolution = classify_import(importation)
    is_open = status in (Import.Status.VALIDATED, Import.Status.PENDING)
    pending = []
    for entry in resolution.pending:
        actions = decision_actions(entry, user) if is_open else []
        pending.append({
            'entry': entry,
            'origin': 'Lista de salas' if entry.from_list else 'Só nas aulas',
            'usage': usage_text(entry.usage),
            'actions': actions,
            'choose': is_open and can_choose(entry, user),
            'question': pending_question(entry),
        })
    decided = [
        {
            'entry': entry,
            'effect': effect_text(entry, resolution),
            'withdraw': is_open and all(
                user.has_perm(code)
                for code in decision_permissions(entry, entry.decision.kind, entry.decision.space, entry.decision.target_name)
            ),
        }
        for entry in resolution.found.values() if entry.decision is not None
    ]
    associated = resolution.to_associate
    blocked = is_open and any(not item['actions'] and not item['choose'] for item in pending)
    lines = summary_lines(resolution) if is_open else []
    return {
        'concluded': False,
        'open': is_open,
        'ready': status == Import.Status.VALIDATED,
        'with_errors': status == Import.Status.WITH_ERRORS,
        'recognized': sorted((entry.name for entry in resolution.recognized), key=str.casefold),
        'proposed': [
            {'entry': entry, 'change': is_open and user.has_perm(permissions.SPACE_EDIT)}
            for entry in sorted(resolution.proposed, key=lambda item: item.name.casefold())
        ],
        'to_create': len(resolution.to_create),
        'associated': len(associated),
        'reactivated': len(resolution.to_reactivate),
        'pending': pending,
        'decided': decided,
        'unused': resolution.unused,
        'blocked': blocked,
        'permission_message': PERMISSION_MESSAGE,
        'refresh_failed': status == Import.Status.PENDING and not resolution.pending,
        'summary': ready_summary(resolution),
        'lines': lines,
    }


def summary_lines(resolution):
    """Quantidades do quadro, no futuro, cada uma com os nomes que conta; as zero são omitidas."""
    recognized = sorted((entry.name for entry in resolution.recognized), key=str.casefold)
    created = sorted((entry.name for entry in resolution.to_create), key=str.casefold)
    associated = sorted((entry.name for entry in resolution.to_associate), key=str.casefold)
    reactivated = sorted({entry.reactivates.name for entry in resolution.to_reactivate}, key=str.casefold)
    pending = len(resolution.pending)
    lines = []
    if recognized:
        total = len(recognized)
        lines.append((f'{total} {plural(total, "espaço já cadastrado foi reconhecido", "espaços já cadastrados foram reconhecidos")}.', recognized))
    if created:
        total = len(created)
        lines.append((f'{total} {plural(total, "espaço novo será cadastrado", "espaços novos serão cadastrados")} ao confirmar esta importação.', created))
    if associated:
        total = len(associated)
        lines.append((f'{total} {plural(total, "nome será associado como outro nome de um espaço cadastrado", "nomes serão associados como outros nomes de espaços cadastrados")}.', associated))
    if reactivated:
        total = len(reactivated)
        lines.append((f'{total} {plural(total, "espaço será reativado", "espaços serão reativados")}.', reactivated))
    if pending:
        lines.append((f'{pending} {plural(pending, "espaço precisa", "espaços precisam")} de decisão antes de concluir.', []))
    if resolution.unused:
        total = len(resolution.unused)
        lines.append((
            f'A lista de salas da planilha tem {total} {plural(total, "sala sem aula, que não será cadastrada", "salas sem aula, que não serão cadastradas")}.',
            sorted(resolution.unused, key=str.casefold),
        ))
    return lines


def pending_question(entry):
    """Pergunta do nome que precisa de decisão, conforme o motivo."""
    if entry.reason == INACTIVE:
        return f'O espaço {entry.space.name} está desativado e tem {usage_text(entry.usage).split(" · ")[0]} nesta planilha.'
    if entry.reason == SIMILAR and len(entry.candidates) == 1:
        return f'{entry.name} parece ser {entry.candidates[0].name}. É o mesmo espaço?'
    if entry.reason == SIMILAR:
        return f'{entry.name} parece com mais de um espaço. Escolha o que é o mesmo, ou informe que é um espaço novo.'
    return f'{entry.name} aparece nas aulas e não está na lista de salas da planilha.'


def ready_summary(resolution):
    """Frase do que a confirmação gravará no cadastro de espaços, sem as quantidades zero."""
    parts = []
    created, associated, reactivated = len(resolution.to_create), len(resolution.to_associate), len(resolution.to_reactivate)
    if created:
        parts.append(f'{plural(created, "será cadastrado", "serão cadastrados")} {created} {plural(created, "espaço", "espaços")}')
    if associated:
        parts.append(f'{plural(associated, "será guardado", "serão guardados")} {associated} {plural(associated, "outro nome", "outros nomes")}')
    if reactivated:
        parts.append(f'{plural(reactivated, "será reativado", "serão reativados")} {reactivated} {plural(reactivated, "espaço", "espaços")}')
    if not parts:
        return 'A confirmação não altera o cadastro de espaços.'
    joined = parts[0] if len(parts) == 1 else f'{", ".join(parts[:-1])} e {parts[-1]}'
    return f'Ao confirmar, {joined}.'


def refresh_after_decision(request, importation):
    """Atualiza a prévia quando não resta pendência ou quando a importação estava pronta (D12).

    A decisão já está gravada, numa transação própria. Uma falha inesperada da atualização é
    registrada no log e deixa a importação como estava; o quadro mostra a recuperação.
    """
    current = Import.objects.get(pk=importation.pk)
    if classify_import(current).pending and current.status != Import.Status.VALIDATED:
        return
    try:
        current.refresh(SPACE_ALLOCATION_IMPORT_SCREENS.definition, request.user)
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)
    except Exception:
        logger.exception('Falha ao atualizar a prévia da importação %s.', current.pk)
        messages.error(request, REFRESH_FAILED_MESSAGE)


def panel_url(importation):
    return SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk) + '#espacos'


class SpaceDecisionView(View):
    """Grava a decisão de um nome encontrado e atualiza a prévia, sem formulário de cadastro (D12)."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        importation = load_importation(SPACE_ALLOCATION_IMPORT_SCREENS, kwargs['pk'])
        name = request.POST.get('nome', '')
        try:
            space = Space.objects.filter(pk=request.POST['espaco']).first() if request.POST.get('espaco', '').isdigit() else None
            SpaceDecision.objects.decide(
                importation, name, request.POST.get('decisao', ''), request.user,
                space=space, target_name=request.POST.get('destino', ''),
            )
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, f'Decisão sobre o espaço {name} gravada.')
            refresh_after_decision(request, importation)
        return HttpResponseRedirect(panel_url(importation))


class SpaceWithdrawView(View):
    """Desfaz a decisão de um nome encontrado e atualiza a prévia quando ela estava pronta."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        importation = load_importation(SPACE_ALLOCATION_IMPORT_SCREENS, kwargs['pk'])
        name = request.POST.get('nome', '')
        try:
            SpaceDecision.objects.withdraw(importation, name, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, f'Decisão sobre o espaço {name} desfeita.')
            refresh_after_decision(request, importation)
        return HttpResponseRedirect(panel_url(importation))


class SpaceRefreshView(View):
    """Refaz a atualização da prévia depois de uma falha: é a recuperação, e não o fluxo normal."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        importation = load_importation(SPACE_ALLOCATION_IMPORT_SCREENS, kwargs['pk'])
        try:
            importation.refresh(SPACE_ALLOCATION_IMPORT_SCREENS.definition, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        except Exception:
            logger.exception('Falha ao atualizar a prévia da importação %s.', importation.pk)
            messages.error(request, REFRESH_FAILED_MESSAGE)
        return HttpResponseRedirect(panel_url(importation))


class SpaceAssociateView(ModalView, FormView):
    """Escolha, entre os espaços do cadastro, do que é o mesmo que um nome encontrado.

    Serve à pendência ("É o mesmo que…") e ao novo proposto ("Não é um espaço novo"). O
    campo é obrigatório e por isso não usa fonte paginada: o select mostra todos os espaços,
    com a busca do componente.
    """

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    template_name = 'schedule/space_associate.html'
    modal_template_name = 'schedule/space_associate_modal.html'
    form_class = SpaceAssociateForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.importation = load_importation(SPACE_ALLOCATION_IMPORT_SCREENS, kwargs['pk'])
        self.found_name = request.GET.get('nome') or request.POST.get('nome', '')

    def get_success_url(self):
        return panel_url(self.importation)

    def get_close_url(self):
        return panel_url(self.importation)

    def get_context_data(self, **kwargs):
        return super().get_context_data(found_name=self.found_name, importation=self.importation, **kwargs)

    def form_valid(self, form):
        try:
            SpaceDecision.objects.decide(
                self.importation, self.found_name, SpaceDecision.Kind.SAME, self.request.user,
                space=form.cleaned_data['espaco'],
            )
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        messages.success(self.request, f'Decisão sobre o espaço {self.found_name} gravada.')
        refresh_after_decision(self.request, self.importation)
        return super().form_valid(form)
