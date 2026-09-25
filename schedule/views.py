"""Grade do ensalamento confirmado e telas da importação, sobre as views base do motor de importação.

A grade exige `ENSALAMENTO.VISUALIZAR`, as telas da importação exigem
`ENSALAMENTO.IMPORTAR` e a exclusão de importação exige `ENSALAMENTO.EXCLUIR_IMPORTACAO`: a autenticação vem do `login_required`
no `urls.py` e a permissão é declarada aqui como dado, verificada pelo PermissionMiddleware.
A importação não tem modelo para baixar, porque a planilha é a do campus e não é alterada
pelo sistema.
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from accounts import permissions
from accounts.views import OperationFormView
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
from schedule.forms import GridFilterForm, SemesterPeriodForm
from schedule.imports import SpaceAllocationImport, concluded_message
from schedule.models import Semester
from schedule.occupancy import occupancy
from schedule.timetable import (
    current_semester_code,
    dated_space_week,
    imported_semesters,
    space_week,
    spaces_of,
    week_start,
)

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


def occupation_text(week):
    """Faixas ocupadas e disponíveis da sala na semana."""
    return f'{counted(week.occupied, "faixa ocupada", "faixas ocupadas")} e {counted(week.available, "disponível", "disponíveis")} na semana.'


def parse_date(value):
    """Data no formato AAAA-MM-DD da URL, ou None quando não serve."""
    try:
        return date.fromisoformat(value or '')
    except ValueError:
        return None


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
        reference = parse_date(self.request.GET.get('semana'))
        if semester is not None and semester.has_period:
            start = week_start(semester, reference, today)
            occurrences = occupancy(space, start, start + timedelta(days=4)) if space else []
            week = dated_space_week(semester, space, start, today, occurrences)
        else:
            week = space_week(semester, space, today)
        grid_url = reverse('space_allocation_grid')

        def week_url(day):
            query = {'semestre': code, 'sala': space.name if space else ''}
            if day is not None:
                query['semana'] = day.isoformat()
            return f'{grid_url}?{urlencode(query)}'

        context.update(
            week=week,
            semester_code=code,
            space=space,
            semester=semester,
            period_missing=semester is not None and not semester.has_period,
            filter_form=GridFilterForm(
                {'semestre': code, 'sala': space.name if space else '', 'semana': week.start.isoformat() if week.start else ''},
                semesters=codes,
                spaces=spaces,
            ),
            grid_url=grid_url,
            previous_week_url=week_url(week.previous) if week.previous else None,
            following_week_url=week_url(week.following) if week.following else None,
            today_week_url=week_url(None),
            import_list_url=SPACE_ALLOCATION_IMPORT_SCREENS.url('list'),
            occupation_text=occupation_text(week),
        )
        return context


def grid_url_of(semester):
    return f"{reverse('space_allocation_grid')}?{urlencode({'semestre': semester.code})}"


class SemesterPeriodView(OperationFormView):
    """Período do semestre, definido em modal aberto pela Grade (D3).

    Exige `ENSALAMENTO.IMPORTAR`, a permissão de quem administra o semestre ao importá-lo.
    A rota usa a chave, e não o código, porque o código tem barra.
    """

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    model = Semester
    template_name = 'schedule/semester_period.html'
    modal_template_name = 'schedule/semester_period_modal.html'
    form_class = SemesterPeriodForm
    title = 'Definir período'
    submit_label = 'Salvar período'

    def get_success_url(self):
        return grid_url_of(self.target)

    def get_close_url(self):
        return grid_url_of(self.target)

    def get_initial(self):
        return {'start_date': self.target.start_date, 'end_date': self.target.end_date}

    def perform(self, data):
        self.target.define_period(data['start_date'], data['end_date'])
        messages.success(self.request, f'Período do semestre {self.target.code} definido.')


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
