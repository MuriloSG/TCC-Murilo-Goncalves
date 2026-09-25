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
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from audit import catalog
from audit.models import AuditLog
from imports.definitions import ImportDefinition
from imports.forms import ImportUploadForm
from imports.models import Import, ImportRow
from ui.pagination import ROWS_PAGE_SIZE, paginate
from ui.views import ModalView

DIVERGENCE_MESSAGE = 'Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo.'


@dataclass(frozen=True)
class ImportScreens:
    """Descrição das telas de uma importação: definição, textos e prefixo das rotas.

    As rotas do app seguem o prefixo: `<prefixo>_list`, `_upload`, `_template`,
    `_detail`, `_confirm` e `_discard`. A rota do modelo existe só quando a importação
    tem modelo.
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

    @property
    def has_template(self):
        """O modelo é oferecido só quando a importação o declara e o arquivo tem nome."""
        return self.definition.has_template and self.template_file_name is not None

    def url(self, name, *args):
        return reverse(f'{self.url_prefix}_{name}', args=args)


def screens_context(screens):
    return {
        'screens': screens,
        'section_url': reverse(screens.section_url_name),
        'list_url': screens.url('list'),
        'upload_url': screens.url('upload'),
        'template_url': screens.url('template') if screens.has_template else None,
    }


STATUS_BADGES = {
    Import.Status.VALIDATED.value: ('info', 'info'),
    Import.Status.WITH_ERRORS.value: ('error', 'circle-x'),
    Import.Status.CONCLUDED.value: ('success', 'circle-check'),
    Import.Status.DISCARDED.value: ('info', 'circle-minus'),
}


def status_badge(status):
    return STATUS_BADGES[str(status)]


def with_summary(queryset):
    no_errors = Q(rows__errors=[])
    return queryset.annotate(
        created_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.CREATE)),
        updated_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.UPDATE)),
        unchanged_count=Count('rows', filter=no_errors & Q(rows__action=ImportRow.Action.UNCHANGED)),
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
        context = super().get_context_data(**kwargs, **screens_context(self.screens))
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
        return super().get_context_data(**kwargs, **screens_context(self.screens))

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


def row_filters(definition, importation, screens):
    """Recortes das linhas oferecidos na prévia, cada um com a sua quantidade."""
    detail_url = screens.url('detail', importation.pk)
    found = []
    for item in definition.row_filters:
        total = importation.rows.filter(**{f'values__{item.column}': item.value}).count()
        if total:
            found.append({'slug': item.slug, 'label': item.label, 'total': total, 'url': f'{detail_url}?linhas={item.slug}'})
    return found


def upload_values(definition, importation):
    """Valores dos campos próprios do envio, iguais em todas as linhas, exibidos uma vez."""
    if not definition.upload_fields:
        return []
    first = importation.rows.values_list('values', flat=True).first() or {}
    return [(label, first.get(label, '')) for label in definition.upload_fields]


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
        context = super().get_context_data(**kwargs, **screens_context(self.screens))
        importation = self.object
        definition = self.screens.definition
        chosen = self.request.GET.get('linhas', '')
        only_errors = chosen == 'erros'
        columns = [column.label for column in definition.columns]
        rows = importation.rows.all()
        if only_errors:
            rows = rows.exclude(errors=[])
        elif chosen:
            found = chosen_row_filter(definition, chosen)
            rows = rows.filter(**{f'values__{found.column}': found.value})
            columns = list(found.columns) or columns
        summary = importation.summary()
        page = paginate(self.request, rows, ROWS_PAGE_SIZE)
        importation.tone, importation.icon = status_badge(importation.status)
        context.update(
            summary=summary,
            only_errors=only_errors,
            chosen_filter=chosen,
            row_filters=row_filters(definition, importation, self.screens),
            columns=columns,
            upload_values=upload_values(definition, importation),
            page=page,
            rows=[self.describe(row, definition, columns) for row in page.object_list],
            confirm_url=self.screens.url('confirm', importation.pk),
            discard_url=self.screens.url('discard', importation.pk),
            detail_url=self.screens.url('detail', importation.pk),
        )
        return context

    def describe(self, row, definition, columns):
        return {
            'line_number': row.line_number,
            'cells': [(label, row.values.get(label, '')) for label in columns],
            'action': 'Com erro' if row.errors else definition.action_labels.get(row.action, 'Sem ação'),
            'changes': [
                f'{definition.field_labels.get(name, name)}: {before} → {after}'
                if row.action == ImportRow.Action.UPDATE
                else f'{definition.field_labels.get(name, name)}: {after}'
                for name, (before, after) in row.changes.items()
                if row.action in (ImportRow.Action.UPDATE, ImportRow.Action.CREATE)
            ],
            'warnings': [definition.warning_labels.get(code, code) for code in row.warnings],
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
        return super().get_context_data(target=self.target, **kwargs, **screens_context(self.screens))

    def post(self, request, *args, **kwargs):
        try:
            self.target.discard(self.screens.definition, request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, f'Importação do arquivo {self.target.file_name} descartada.')
        return self.redirect_to(self.screens.url('detail', self.target.pk))
