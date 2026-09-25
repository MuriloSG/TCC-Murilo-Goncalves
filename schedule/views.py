"""Grade do ensalamento confirmado e telas da importação, sobre as views base do motor de importação.

O acesso de toda rota exige `ENSALAMENTO.IMPORTAR`: a autenticação vem do `login_required`
no `urls.py` e a permissão é declarada aqui como dado, verificada pelo PermissionMiddleware.
A importação não tem modelo para baixar, porque a planilha é a do campus e não é alterada
pelo sistema.
"""

from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from accounts import permissions
from audit import catalog
from imports.views import (
    ImportConfirmView,
    ImportDetailView,
    ImportDiscardView,
    ImportListView,
    ImportScreens,
    ImportUploadView,
)
from schedule.forms import GridFilterForm
from schedule.imports import SpaceAllocationImport, concluded_message
from schedule.timetable import current_semester_code, imported_semesters, space_week, spaces_of

SPACE_ALLOCATION_IMPORT_SCREENS = ImportScreens(
    definition=SpaceAllocationImport(),
    url_prefix='space_allocation_import',
    section_title='Ensalamento',
    section_url_name='space_allocation_grid',
    list_title='Importações de ensalamento',
    upload_title='Importar ensalamento',
    empty_message='Nenhuma importação de ensalamento.',
    concluded_message=concluded_message,
)


def counted(total, singular, plural):
    return f'{total} {singular if total == 1 else plural}'


def occupation_text(week):
    """Faixas ocupadas e disponíveis da sala na semana."""
    return f'{counted(week.occupied, "faixa ocupada", "faixas ocupadas")} e {counted(week.available, "disponível", "disponíveis")} na semana.'


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
    existe na lista cai no padrão, sem erro.
    """

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
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
        week = space_week(semester, space, today)
        context.update(
            week=week,
            semester_code=code,
            space=space,
            filter_form=GridFilterForm({'semestre': code, 'sala': space.name if space else ''}, semesters=codes, spaces=spaces),
            grid_url=reverse('space_allocation_grid'),
            import_list_url=SPACE_ALLOCATION_IMPORT_SCREENS.url('list'),
            occupation_text=occupation_text(week),
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
