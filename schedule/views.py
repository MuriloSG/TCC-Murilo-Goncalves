"""Telas da importação de ensalamento, sobre as views base do motor de importação.

O acesso de toda rota exige `ENSALAMENTO.IMPORTAR`: a autenticação vem do `login_required`
no `urls.py` e a permissão é declarada aqui como dado, verificada pelo PermissionMiddleware.
A importação não tem modelo para baixar, porque a planilha é a do campus e não é alterada
pelo sistema.
"""

from django.utils import timezone
from django.views.generic import TemplateView

from accounts import permissions
from audit import catalog
from imports.models import Import
from imports.views import (
    ImportConfirmView,
    ImportDetailView,
    ImportDiscardView,
    ImportListView,
    ImportScreens,
    ImportUploadView,
    detail_head_context,
    load_importation,
    screens_context,
)
from schedule.forms import RoomFilterForm
from schedule.imports import SEMESTER_COLUMN, SpaceAllocationImport, concluded_message
from schedule.timetable import room_week_from_import

SPACE_ALLOCATION_IMPORT_SCREENS = ImportScreens(
    definition=SpaceAllocationImport(),
    url_prefix='space_allocation_import',
    section_title='Ensalamento',
    section_url_name='space_allocation_import_list',
    list_title='Importações de ensalamento',
    upload_title='Importar ensalamento',
    empty_message='Nenhuma importação de ensalamento.',
    concluded_message=concluded_message,
    tabs=(('detail', 'Grade', 'table'), ('review', 'Conferência', 'list-checks')),
    review_route='review',
)

STATUS_TEXTS = {
    Import.Status.VALIDATED: 'Prévia validada. Nenhum dado gravado.',
    Import.Status.WITH_ERRORS: 'Prévia com erros. Nenhum dado gravado.',
    Import.Status.CONCLUDED: 'Importação confirmada.',
    Import.Status.DISCARDED: 'Importação descartada. Nenhum dado gravado.',
}


def counted(total, singular, plural):
    return f'{total} {singular if total == 1 else plural}'


def occupation_text(week):
    """Faixas ocupadas, disponíveis e com choque da sala na semana."""
    text = f'{counted(week.occupied, "faixa ocupada", "faixas ocupadas")} e {counted(week.available, "disponível", "disponíveis")} na semana'
    if week.clash_count:
        text += f', {counted(week.clash_count, "com choque", "com choque")}'
    return text + '.'


def review_link(review_url, lines):
    """Conferência filtrada nas linhas de um bloco da Grade (D9)."""
    return review_url + '?' + '&'.join(f'numero={line}' for line in lines)


class SpaceAllocationImportListView(ImportListView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportUploadView(ImportUploadView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportGridView(TemplateView):
    """Grade da semana de uma sala, aberta por padrão no detalhe da importação (D3, D8)."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS
    template_name = 'schedule/import_grid.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.importation = load_importation(self.screens, kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs, **screens_context(self.screens))
        head = detail_head_context(self.screens, self.importation, 'detail')
        week = room_week_from_import(self.importation, self.request.GET.get('sala'), timezone.localdate())
        for day in week.days:
            for cell in day.cells:
                if cell and not cell.is_continued:
                    cell.review_link = review_link(head['review_url'], cell.lines)
        context.update(head)
        context.update(
            week=week,
            room_form=RoomFilterForm({'sala': week.space}, spaces=week.spaces),
            semester=dict(head['upload_values']).get(SEMESTER_COLUMN, ''),
            grid_url=self.screens.url('detail', self.importation.pk),
            status_text=STATUS_TEXTS.get(self.importation.status, ''),
            occupation_text=occupation_text(week),
            errors_text=counted(week.error_count, 'atividade desta sala com erro.', 'atividades desta sala com erro.'),
            outside_text=counted(
                week.outside_error_count, 'linha com erro fora da Grade.', 'linhas com erro fora da Grade.',
            ),
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
