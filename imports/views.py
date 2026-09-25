"""Views base das telas de importação (D16).

O motor não conhece o app de domínio. Cada app descreve as telas da sua importação
num ImportScreens e cria as próprias rotas, com login_required e a permissão
declarada nas subclasses destas views.
"""

from dataclasses import dataclass
from typing import Callable

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.formats import number_format
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from audit import catalog
from audit.models import AuditLog
from imports.definitions import ImportDefinition
from imports.forms import ImportUploadForm, RowFilterForm
from imports.models import Import, ImportRow
from imports.reader import listing
from ui.pagination import ROWS_PAGE_SIZE, paginate
from ui.views import ModalView

DIVERGENCE_MESSAGE = 'Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo.'


@dataclass(frozen=True)
class ImportScreens:
    """Descrição das telas de uma importação: definição, textos e prefixo das rotas.

    As rotas do app seguem o prefixo: `<prefixo>_list`, `_upload`, `_template`,
    `_detail`, `_confirm`, `_discard` e `_delete`. A rota do modelo existe só quando a
    importação tem modelo, e a de exclusão só quando `delete_permission` é declarada.

    `section_permission` é a permissão da tela da seção: sem ela, o caminho de navegação
    mostra a seção sem link.

    `tabs` declara as abas do detalhe, cada uma com a rota, o rótulo e o ícone, e
    `review_route` é a rota da tabela de linhas. Sem abas, o detalhe é a própria tabela
    (D8 da Change visualizar-grade-do-ensalamento).

    `panel_template` é um quadro próprio da importação específica, mostrado no detalhe
    antes das linhas, com o contexto que a view dela acrescenta (D10 da Change
    manipulacao-dos-espacos).
    """

    definition: ImportDefinition
    url_prefix: str
    section_title: str
    section_url_name: str
    list_title: str
    upload_title: str
    empty_message: str
    concluded_message: Callable
    template_file_name: str | None = None
    tabs: tuple = ()
    review_route: str = 'detail'
    delete_permission: str | None = None
    section_permission: str | None = None
    panel_template: str | None = None

    @property
    def has_template(self):
        """O modelo é oferecido só quando a importação o declara e o arquivo tem nome."""
        return self.definition.has_template and self.template_file_name is not None

    def url(self, name, *args):
        return reverse(f'{self.url_prefix}_{name}', args=args)


def section_url(screens, user):
    """Link da seção no caminho de navegação, só para quem pode abrir a tela dela."""
    if screens.section_permission and not user.has_perm(screens.section_permission):
        return None
    return reverse(screens.section_url_name)


def screens_context(screens, user):
    return {
        'screens': screens,
        'section_url': section_url(screens, user),
        'list_url': screens.url('list'),
        'upload_url': screens.url('upload'),
        'template_url': screens.url('template') if screens.has_template else None,
    }


STATUS_BADGES = {
    Import.Status.VALIDATED.value: ('info', 'info'),
    Import.Status.PENDING.value: ('warning', 'triangle-alert'),
    Import.Status.WITH_ERRORS.value: ('error', 'circle-x'),
    Import.Status.CONCLUDED.value: ('success', 'circle-check'),
    Import.Status.DISCARDED.value: ('info', 'circle-minus'),
}


def status_badge(status):
    return STATUS_BADGES[str(status)]


def detail_tabs(screens, pk, current):
    """Abas do detalhe da importação, com a atual marcada, ou nenhuma quando não declaradas."""
    return [
        {'url': screens.url(route, pk), 'label': label, 'icon': icon, 'current': route == current}
        for route, label, icon in screens.tabs
    ]


def confirmation_refusal(screens, importation, user):
    """Mensagem da verificação própria da confirmação para este usuário, ou None quando ele pode confirmar."""
    if not importation.is_validated:
        return None
    try:
        screens.definition.check_confirmation(importation, user)
    except ValidationError as error:
        return ' '.join(error.messages)
    return None


def detail_head_context(screens, importation, current, user):
    """Contexto do cabeçalho do detalhe, igual em todas as abas: situação, ações e resumo."""
    importation.tone, importation.icon = status_badge(importation.status)
    return {
        'confirm_refusal': confirmation_refusal(screens, importation, user),
        'importation': importation,
        'summary': importation.summary(),
        'upload_values': upload_values(screens.definition, importation),
        'confirm_url': screens.url('confirm', importation.pk),
        'discard_url': screens.url('discard', importation.pk),
        'delete_url': delete_url(screens, importation, user),
        'review_url': screens.url(screens.review_route, importation.pk),
        'tabs': detail_tabs(screens, importation.pk, current),
    }


def delete_url(screens, importation, user):
    """Rota da exclusão, oferecida só na situação que a permite e a quem tem a permissão."""
    if screens.delete_permission and importation.is_deletable and user.has_perm(screens.delete_permission):
        return screens.url('delete', importation.pk)
    return None


def rows_title(numbers, only_errors):
    """Título da tabela de linhas, conforme o filtro escolhido."""
    if numbers:
        return f'Linha {numbers[0]}' if len(numbers) == 1 else f'Linhas {listing(numbers)}'
    return 'Linhas com erro' if only_errors else 'Linhas do arquivo'


def line_numbers(request):
    """Números de linha pedidos na consulta, descartando os que não são inteiros (D9)."""
    return sorted({int(value) for value in request.GET.getlist('numero') if value.isdigit()})


def with_summary(queryset):
    no_errors = Q(rows__errors=[])
    return queryset.annotate(
        created_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.CREATE)),
        updated_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.UPDATE)),
        unchanged_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.UNCHANGED)),
        pending_count=Count('rows', filter=no_errors & ~Q(rows__pending=[])),
        error_count=Count('rows', filter=~no_errors),
    )


class ImportListView(ListView):
    screens = None
    template_name = 'imports/list.html'
    context_object_name = 'importations'

    def get_queryset(self):
        queryset = Import.objects.filter(kind=self.screens.definition.kind).select_related('created_by')
        return with_summary(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs, **screens_context(self.screens, self.request.user))
        context['page'] = paginate(self.request, self.object_list)
        context['importations'] = context['page'].object_list
        for importation in context['importations']:
            importation.tone, importation.icon = status_badge(importation.status)
            importation.detail_url = self.screens.url('detail', importation.pk)
        return context


class ImportUploadView(ModalView, FormView):
    screens = None
    form_class = ImportUploadForm
    template_name = 'imports/upload.html'
    modal_template_name = 'imports/upload_modal.html'

    def get_success_url(self):
        return self.screens.url('detail', self.importation.pk)

    def get_close_url(self):
        return self.screens.url('list')

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'definition': self.screens.definition}

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **screens_context(self.screens, self.request.user))

    def form_valid(self, form):
        self.importation = Import.objects.preview(
            self.screens.definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, self.request.user,
        )
        return super().form_valid(form)


class ImportTemplateView(View):
    """Modelo em UTF-8 com BOM, separado por ";", só com o cabeçalho (D18).

    A rota só existe nas importações que têm modelo, e por isso a view não confere nada.
    """

    screens = None

    def get(self, request, *args, **kwargs):
        header = ';'.join(column.label for column in self.screens.definition.file_columns())
        response = HttpResponse('﻿' + header + '\r\n', content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{self.screens.template_file_name}"'
        AuditLog.objects.record(
            catalog.EXPORT,
            self.screens.definition.audit_resource,
            metadata={'arquivo': self.screens.template_file_name},
        )
        return response


def chosen_row_filter(definition, slug):
    """Recorte escolhido na consulta, ou 404 quando a importação não o declara."""
    chosen = next((item for item in definition.row_filters if item.slug == slug), None)
    if chosen is None:
        raise Http404('Recorte desconhecido.')
    return chosen


def row_filter_form(definition, importation, chosen, errors):
    """Select dos recortes das linhas, cada opção com a sua quantidade."""
    choices = [('', f'Todas as linhas ({number_format(importation.rows.count(), force_grouping=True)})')]
    if errors or chosen == 'erros':
        choices.append(('erros', f'Com erro ({number_format(errors, force_grouping=True)})'))
    for item in definition.row_filters:
        total = importation.rows.filter(**{f'values__{item.column}': item.value}).count()
        if total or chosen == item.slug:
            choices.append((item.slug, f'{item.label} ({number_format(total, force_grouping=True)})'))
    return RowFilterForm({'linhas': chosen}, choices=choices)


def upload_values(definition, importation):
    """Valores dos campos próprios do envio, iguais em todas as linhas, exibidos uma vez."""
    if not definition.upload_fields:
        return []
    first = importation.rows.values_list('values', flat=True).first() or {}
    return [(label, definition.upload_display(label, first.get(label, ''))) for label in definition.upload_fields]


def load_importation(screens, pk):
    return get_object_or_404(Import, pk=pk, kind=screens.definition.kind)


class ImportDetailView(DetailView):
    """Prévia e detalhe da mesma importação, conforme a situação."""

    screens = None
    template_name = 'imports/detail.html'
    context_object_name = 'importation'

    def get_object(self, queryset=None):
        return load_importation(self.screens, self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs, **screens_context(self.screens, self.request.user))
        importation = self.object
        definition = self.screens.definition
        context.update(detail_head_context(self.screens, importation, self.screens.review_route, self.request.user))
        chosen = self.request.GET.get('linhas', '')
        only_errors = chosen == 'erros'
        numbers = line_numbers(self.request)
        columns = [column.label for column in definition.file_columns()]
        rows = importation.rows.all()
        if only_errors:
            rows = rows.exclude(errors=[])
        elif chosen:
            found = chosen_row_filter(definition, chosen)
            rows = rows.filter(**{f'values__{found.column}': found.value})
            columns = list(found.columns) or columns
        if numbers:
            rows = rows.filter(line_number__in=numbers)
        page = paginate(self.request, rows, ROWS_PAGE_SIZE)
        context.update(
            only_errors=only_errors,
            chosen_filter=chosen,
            numbers=numbers,
            rows_title=rows_title(numbers, only_errors),
            row_filter=row_filter_form(definition, importation, chosen, context['summary']['errors']),
            columns=columns,
            page=page,
            rows=[self.describe(row, definition, columns) for row in page.object_list],
            detail_url=context['review_url'],
        )
        return context

    def action_label(self, row, definition):
        if row.errors:
            return 'Com erro'
        if row.pending:
            return 'Precisa de decisão'
        return definition.action_labels.get(row.action, 'Sem ação')

    def describe(self, row, definition, columns):
        return {
            'line_number': row.line_number,
            'cells': [(label, row.values.get(label, '')) for label in columns],
            'action': self.action_label(row, definition),
            'changes': [
                f'{definition.field_labels.get(name, name)}: {before} → {after}'
                if row.action == ImportRow.Action.UPDATE
                else f'{definition.field_labels.get(name, name)}: {after}'
                for name, (before, after) in row.changes.items()
                if row.action in (ImportRow.Action.UPDATE, ImportRow.Action.CREATE)
            ],
            'warnings': [definition.warning_labels.get(code, code) for code in row.warnings],
            'pending': [definition.pending_label(item['code'], item['key']) for item in row.pending],
            'errors': [
                f'{error["column"]}: {error["message"]}' if error['column'] else error['message']
                for error in row.errors
            ],
        }


class ImportConfirmView(View):
    """Confirmação por POST. A página de prévia é o GET que mostra o que será confirmado (D16)."""

    screens = None
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        importation = load_importation(self.screens, kwargs['pk'])
        try:
            concluded = importation.confirm(self.screens.definition, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            if concluded:
                messages.success(request, self.screens.concluded_message(importation.summary()))
            else:
                messages.warning(request, DIVERGENCE_MESSAGE)
        return HttpResponseRedirect(self.screens.url('detail', importation.pk))


class ImportDiscardView(ModalView, TemplateView):
    screens = None
    template_name = 'imports/discard.html'
    modal_template_name = 'imports/discard_modal.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = load_importation(self.screens, kwargs['pk'])

    def get_close_url(self):
        return self.screens.url('detail', self.target.pk)

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=self.target, **kwargs, **screens_context(self.screens, self.request.user))

    def post(self, request, *args, **kwargs):
        try:
            self.target.discard(self.screens.definition, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, f'Importação do arquivo {self.target.file_name} descartada.')
        return self.redirect_to(self.screens.url('detail', self.target.pk))


class ImportDeleteView(ModalView, TemplateView):
    """Exclusão definitiva de uma importação descartada ou com erros: GET confirma, POST exclui."""

    screens = None
    template_name = 'imports/delete.html'
    modal_template_name = 'imports/delete_modal.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = load_importation(self.screens, kwargs['pk'])

    def get_close_url(self):
        return self.screens.url('detail', self.target.pk)

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=self.target, **kwargs, **screens_context(self.screens, self.request.user))

    def post(self, request, *args, **kwargs):
        try:
            self.target.remove(self.screens.definition, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return self.redirect_to(self.screens.url('detail', self.target.pk))
        messages.success(request, f'Importação do arquivo {self.target.file_name} excluída.')
        return self.redirect_to(self.screens.url('list'))
