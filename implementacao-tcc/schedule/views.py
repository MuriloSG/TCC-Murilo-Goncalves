"""Grade, importação e cadastro de espaços do ensalamento; as permissões são conferidas de novo no model."""

from dataclasses import replace
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_list_or_404, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.views.generic import FormView, ListView, TemplateView
from django_htmx.http import HttpResponseClientRedirect

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
    ImportStatusView,
    ImportUploadView,
    load_importation,
)
from imports.models import Import
from schedule.forms import (
    ClassGroupFilterForm,
    ClassGroupForm,
    CourseFilterForm,
    CourseForm,
    GridFilterForm,
    RecurrenceChangeForm,
    RecurrenceCreateForm,
    SpaceAssociateForm,
    SpaceFilterForm,
    SpaceForm,
    SubjectFilterForm,
    SubjectForm,
)
from schedule.models import (
    SPACE_PERMISSION_MESSAGE,
    Allocation,
    AllocationException,
    ClassGroup,
    ClassOffering,
    Course,
    Semester,
    Space,
    SpaceDecision,
    Subject,
    Weekday,
    manages,
)
from schedule.spaces import CREATE, INACTIVE, REACTIVATE, SIMILAR, classify_import, decision_permissions, options_of
from schedule.imports import SpaceAllocationImport, concluded_message
from ui.pagination import paginate
from ui.views import ModalView
from schedule.occupancy import occupancy
from schedule.timetable import (
    current_semester_code,
    month_reference,
    occupation_text,
    parse_date,
    parse_month,
    dated_space_month,
    dated_space_week,
    imported_semesters,
    month_start,
    natural_key,
    space_week,
    spaces_of,
    week_start,
)


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


class SpaceAllocationImportListView(ImportListView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationImportUploadView(ImportUploadView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS


class SpaceAllocationGridView(TemplateView):
    """Grade da semana de uma sala, com semestre e sala padrão quando a URL não serve."""

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
            week = dated_space_month(semester, space, first, today, occurrences, by_overlap=True)
        elif dated:
            reference = chosen_week or (month_reference(semester, chosen_month, today) if chosen_month else None)
            start = week_start(semester, reference, today)
            occurrences = occupancy(space, start, start + timedelta(days=4)) if space else []
            week = dated_space_week(semester, space, start, today, occurrences, by_overlap=True)
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
        if week.is_dated:
            with_cancel_actions(week, self.request.user)
            with_change_actions(week, self.request.user, today)
            with_end_actions(week, self.request.user, today)
            context['create_url'] = create_url(self.request.user, code, space)
            with_create_actions(week, self.request.user, today)
        return context


def cancel_url(entry, day, url_name):
    query = urlencode({'data': day.isoformat(), 'alocacao': entry.allocation_ids}, doseq=True)
    return f'{reverse(url_name)}?{query}'


def with_cancel_actions(week, user, url_name='space_allocation_occurrence_cancel'):
    """Dá a ação de cancelar às aulas que o usuário administra; esconder a ação não é a proteção."""
    for day in week.days:
        if day.date is None or not day.in_period:
            continue
        for cell in day.cells:
            if not cell or cell.is_continued or cell.is_outside:
                continue
            cell.entries = [
                replace(entry, cancel_url=cancel_url(entry, day.date, url_name))
                if getattr(entry, 'allocation_ids', ()) and manages(user, entry.teachers) else entry
                for entry in cell.entries
            ]


def with_end_actions(week, user, today):
    """Dá a ação de encerrar às aulas datadas de hoje em diante; esconder a ação não é a proteção."""
    if not user.has_perm(permissions.SPACE_ALLOCATION_END_RECURRENCE):
        return
    url = reverse('space_allocation_recurrence_end')
    for day in week.days:
        if day.date is None or not day.in_period or day.date < today:
            continue
        for cell in day.cells:
            if not cell or cell.is_continued or cell.is_outside:
                continue
            cell.entries = [
                replace(entry, end_url=f"{url}?{urlencode({'data': day.date.isoformat(), 'alocacao': entry.allocation_ids}, doseq=True)}")
                if getattr(entry, 'allocation_ids', ()) else entry
                for entry in cell.entries
            ]


def with_change_actions(week, user, today):
    """Dá a ação de alterar às aulas datadas de hoje em diante; esconder a ação não é a proteção."""
    if not user.has_perm(permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE):
        return
    url = reverse('space_allocation_recurrence_change')
    for day in week.days:
        if day.date is None or not day.in_period or day.date < today:
            continue
        for cell in day.cells:
            if not cell or cell.is_continued or cell.is_outside:
                continue
            cell.entries = [
                replace(entry, change_url=f"{url}?{urlencode({'data': day.date.isoformat(), 'alocacao': entry.allocation_ids}, doseq=True)}")
                if getattr(entry, 'allocation_ids', ()) else entry
                for entry in cell.entries
            ]


def create_url(user, code, space):
    """Cadastro de aula com o semestre e a sala da Grade, ou None sem a permissão."""
    if not user.has_perm(permissions.SPACE_ALLOCATION_CREATE_RECURRENCE):
        return None
    query = {'semestre': code}
    if space:
        query['sala'] = space.name
    return f"{reverse('space_allocation_recurrence_create')}?{urlencode(query)}"


def with_create_actions(week, user, today):
    """Marca os dias de hoje em diante que oferecem o cadastro; esconder a ação não é a proteção."""
    if not user.has_perm(permissions.SPACE_ALLOCATION_CREATE_RECURRENCE):
        return
    for day in week.days:
        day.can_create = day.date is not None and day.in_period and day.date >= today


class PlannedOperationView(OperationFormView):
    """Confere e mostra o resumo no primeiro envio e executa no envio de confirmação, conferindo de novo."""

    summary_template_name = None

    @property
    def is_confirmed(self):
        return self.request.POST.get('confirmar') == '1'

    def render_summary(self, form, plan):
        hidden = [
            (name, value)
            for name in form.fields
            for value in self.request.POST.getlist(name)
        ]
        template = self.summary_template_name if self.request.htmx else self.template_name
        return self.response_class(
            request=self.request,
            template=[template],
            context=self.get_context_data(form=form, plan=plan, hidden=hidden, summary=True),
            using=self.template_engine,
        )


class RecurrenceChangeView(PlannedOperationView):
    """Altera a recorrência; no sucesso, a Grade abre na semana da data e na sala nova."""

    permission_required = permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE
    template_name = 'schedule/recurrence_change.html'
    modal_template_name = 'schedule/recurrence_change_modal.html'
    summary_template_name = 'schedule/recurrence_change_summary.html'
    form_class = RecurrenceChangeForm
    title = 'Alterar recorrência'
    submit_label = 'Revisar alteração'
    section_title = 'Ensalamento'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.day = parse_date(request.GET.get('data'))
        ids = request.GET.getlist('alocacao')
        if self.day is None or not ids or not all(value.isdigit() for value in ids):
            raise Http404
        ids = {int(value) for value in ids}
        allocations = get_list_or_404(
            Allocation.objects.filter(pk__in=ids)
            .select_related('semester', 'subject', 'time_slot', 'space', 'class_group__course')
            .prefetch_related('teachers')
            .order_by('time_slot__start_time'),
        )
        if len(allocations) != len(ids) or not all(allocation.occurs_on(self.day) for allocation in allocations):
            raise Http404
        self.allocations = allocations

    def get_success_url(self):
        first = self.allocations[0]
        query = {'semestre': first.semester.code, 'semana': self.plan.cut.isoformat() if getattr(self, 'plan', None) else self.day.isoformat()}
        space = self.plan.after.space if getattr(self, 'plan', None) else (first.space.name if first.space else '')
        if space:
            query['sala'] = space
        return f"{reverse('space_allocation_grid')}?{urlencode(query)}"

    def get_close_url(self):
        first = self.allocations[0]
        query = {'semestre': first.semester.code, 'semana': self.day.isoformat()}
        if first.space:
            query['sala'] = first.space.name
        return f"{reverse('space_allocation_grid')}?{urlencode(query)}"

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'allocations': self.allocations}

    def get_initial(self):
        first = self.allocations[0]
        return {
            'data': self.day,
            'dia': first.weekday,
            'horario': f'{first.time_slot.start_time:%H:%M}',
            'duracao': len(self.allocations),
            'espaco': first.space_id,
            'docentes': [teacher.pk for teacher in first.teachers.all()],
        }

    def get_context_data(self, **kwargs):
        first, last = self.allocations[0], self.allocations[-1]
        return super().get_context_data(
            lesson=first,
            start=first.time_slot.start_time,
            end=last.time_slot.end_time,
            section_title=self.section_title,
            section_url=self.get_close_url(),
            **kwargs,
        )

    def arguments(self, data):
        return {
            'allocation_ids': [allocation.pk for allocation in self.allocations],
            'cut': data['data'],
            'executor': self.request.user,
            'weekday': data['dia'],
            'start_time': data['horario'],
            'slot_count': data['duracao'],
            'space': data['espaco'],
            'teachers': list(data['docentes']),
        }

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            if not self.is_confirmed:
                plan = Allocation.objects.plan_recurrence(**self.arguments(data))
                return self.render_summary(form, plan)
            self.plan = Allocation.objects.change_recurrence(**self.arguments(data))
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f'Recorrência de {self.allocations[0].subject.name} alterada a partir de {date_format(self.plan.cut, "SHORT_DATE_FORMAT")}.',
        )
        if self.request.htmx:
            return HttpResponseClientRedirect(self.get_success_url())
        return self.redirect_to(self.get_success_url())

class RecurrenceCreateView(PlannedOperationView):
    """Cadastra uma aula recorrente; semestre inexistente ou sem período responde 404."""

    permission_required = permissions.SPACE_ALLOCATION_CREATE_RECURRENCE
    template_name = 'schedule/recurrence_create.html'
    modal_template_name = 'schedule/recurrence_create_modal.html'
    summary_template_name = 'schedule/recurrence_create_summary.html'
    form_class = RecurrenceCreateForm
    title = 'Cadastrar aula'
    submit_label = 'Revisar cadastro'
    section_title = 'Ensalamento'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.semester = Semester.objects.filter(code=request.GET.get('semestre')).first()
        if self.semester is None or not self.semester.has_period:
            raise Http404
        self.day = parse_date(request.GET.get('data'))
        self.space = Space.objects.filter(name__iexact=request.GET.get('sala') or '', is_active=True).first()

    def grid_url(self, day=None):
        query = {'semestre': self.semester.code}
        if day is not None:
            query['semana'] = day.isoformat()
        if self.space:
            query['sala'] = self.space.name
        return f"{reverse('space_allocation_grid')}?{urlencode(query)}"

    def get_success_url(self):
        return self.grid_url(self.plan.cut)

    def get_close_url(self):
        return self.grid_url(self.day)

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'semester': self.semester}

    def get_initial(self):
        return {
            'data': self.day,
            'horario': self.request.GET.get('horario'),
            'espaco': self.space.pk if self.space else None,
            'duracao': 1,
        }

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            semester=self.semester,
            section_title=self.section_title,
            section_url=self.get_close_url(),
            **kwargs,
        )

    def arguments(self, data):
        return {
            'semester': self.semester,
            'class_group': data['turma'],
            'subject': data['disciplina'],
            'start': data['data'],
            'end': data['fim'],
            'executor': self.request.user,
            'start_time': data['horario'],
            'slot_count': data['duracao'],
            'space': data['espaco'],
            'teachers': list(data['docentes']),
        }

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            if not self.is_confirmed:
                plan = Allocation.objects.plan_creation(**self.arguments(data))
                return self.render_summary(form, plan)
            self.plan = Allocation.objects.create_recurrence(**self.arguments(data))
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f'Aula de {data["disciplina"].name} cadastrada a partir de '
            f'{date_format(self.plan.cut, "SHORT_DATE_FORMAT")}.',
        )
        if self.request.htmx:
            return HttpResponseClientRedirect(self.get_success_url())
        return self.redirect_to(self.get_success_url())


class OccurrenceCancelView(ConfirmedActionView):
    """Cancela uma ocorrência; aula de outro docente responde 404, sem revelar a aula."""

    permission_required = permissions.SPACE_ALLOCATION_VIEW
    template_name = 'schedule/occurrence_cancel.html'
    modal_template_name = 'schedule/occurrence_cancel_modal.html'
    success_url = reverse_lazy('space_allocation_grid')
    section_title = 'Ensalamento'

    def setup(self, request, *args, **kwargs):
        super(ConfirmedActionView, self).setup(request, *args, **kwargs)
        self.day = parse_date(request.GET.get('data'))
        ids = request.GET.getlist('alocacao')
        if self.day is None or not ids or not all(value.isdigit() for value in ids):
            raise Http404
        ids = {int(value) for value in ids}
        allocations = get_list_or_404(
            Allocation.objects.managed_by(request.user)
            .filter(pk__in=ids)
            .select_related('semester', 'subject', 'time_slot', 'space', 'class_group__course')
            .order_by('time_slot__start_time'),
        )
        if len(allocations) != len(ids) or not all(allocation.occurs_on(self.day) for allocation in allocations):
            raise Http404
        self.allocations = allocations

    def get_context_data(self, **kwargs):
        first, last = self.allocations[0], self.allocations[-1]
        return super(ConfirmedActionView, self).get_context_data(
            day=self.day,
            lesson=first,
            start=first.time_slot.start_time,
            end=last.time_slot.end_time,
            section_title=self.section_title,
            section_url=self.success_url,
            **kwargs,
        )

    def perform(self):
        AllocationException.objects.cancel([allocation.pk for allocation in self.allocations], self.day, self.request.user)
        messages.success(self.request, f'Ocorrência de {date_format(self.day, "SHORT_DATE_FORMAT")} cancelada.')


class RecurrenceEndView(ConfirmedActionView):
    """Encerra a aula, com o GET mostrando quantas aulas deixam de existir."""

    permission_required = permissions.SPACE_ALLOCATION_END_RECURRENCE
    template_name = 'schedule/recurrence_end.html'
    modal_template_name = 'schedule/recurrence_end_modal.html'
    success_url = reverse_lazy('space_allocation_grid')
    section_title = 'Ensalamento'

    def setup(self, request, *args, **kwargs):
        super(ConfirmedActionView, self).setup(request, *args, **kwargs)
        self.day = parse_date(request.GET.get('data'))
        ids = request.GET.getlist('alocacao')
        if self.day is None or not ids or not all(value.isdigit() for value in ids):
            raise Http404
        ids = {int(value) for value in ids}
        allocations = get_list_or_404(
            Allocation.objects.filter(pk__in=ids)
            .select_related('semester', 'subject', 'time_slot', 'space', 'class_group__course')
            .order_by('time_slot__start_time'),
        )
        if len(allocations) != len(ids) or not all(allocation.occurs_on(self.day) for allocation in allocations):
            raise Http404
        self.allocations = allocations

    def grid_url(self, day):
        first = self.allocations[0]
        query = {'semestre': first.semester.code, 'semana': day.isoformat()}
        if first.space:
            query['sala'] = first.space.name
        return f"{reverse('space_allocation_grid')}?{urlencode(query)}"

    def get_success_url(self):
        return self.grid_url(self.day)

    def get_context_data(self, **kwargs):
        first, last = self.allocations[0], self.allocations[-1]
        plan = Allocation.objects.plan_ending(
            [allocation.pk for allocation in self.allocations], self.day, self.request.user,
        )
        return super(ConfirmedActionView, self).get_context_data(
            day=self.day,
            lesson=first,
            plan=plan,
            start=first.time_slot.start_time,
            end=last.time_slot.end_time,
            section_title=self.section_title,
            section_url=self.grid_url(self.day),
            **kwargs,
        )

    def perform(self):
        plan = Allocation.objects.end_recurrence(
            [allocation.pk for allocation in self.allocations], self.day, self.request.user,
        )
        messages.success(
            self.request,
            f'Aula de {plan.lesson.subject.name} encerrada a partir de {date_format(self.day, "SHORT_DATE_FORMAT")}.',
        )


class AllocationExceptionListView(ListView):
    """Exceções do ensalamento; o docente vê só as das aulas dele."""

    permission_required = permissions.SPACE_ALLOCATION_VIEW
    audit_resource = catalog.SPACE_ALLOCATION_EXCEPTION
    template_name = 'schedule/exception_list.html'
    context_object_name = 'exceptions'
    section_title = 'Ensalamento'
    section_url = reverse_lazy('space_allocation_grid')

    def get_queryset(self):
        return (
            AllocationException.objects.filter(allocation__in=Allocation.objects.managed_by(self.request.user))
            .select_related(
                'allocation__semester', 'allocation__subject', 'allocation__time_slot',
                'allocation__space', 'allocation__class_group__course', 'created_by',
            )
            .prefetch_related('allocation__teachers')
            .order_by('-created_at', '-pk')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = paginate(self.request, self.object_list)
        context['exceptions'] = context['page'].object_list
        context.update(section_title=self.section_title, section_url=self.section_url)
        return context


class SpaceAllocationImportDetailView(ImportDetailView):
    """Detalhe da importação com o quadro "Espaços desta importação" antes das linhas."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    audit_resource = catalog.SPACE_ALLOCATION_IMPORT
    screens = SPACE_ALLOCATION_IMPORT_SCREENS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['space_panel'] = space_panel(self.object, self.request.user)
        return context


class SpaceAllocationImportStatusView(ImportStatusView):
    permission_required = permissions.SPACE_ALLOCATION_IMPORT
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
    """Lista de espaços pela URL, na ordem natural do nome: `1/4` antes de `1/10`."""

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


def audit_history_action(resource, pk):
    """Ação da linha que abre a consulta da auditoria filtrada pelo registro."""
    query = urlencode({'recurso': resource, 'registro': pk})
    return {'url': f"{reverse('audit_log_list')}?{query}", 'label': 'Ver auditoria', 'icon': 'scroll-text', 'danger': False, 'page': True}


class CourseListView(ListView):
    """Lista de cursos pela URL, sem escopo de docente."""

    permission_required = permissions.COURSE_VIEW
    audit_resource = catalog.COURSE
    template_name = 'schedule/course_list.html'
    table_template_name = 'schedule/partials/course_table.html'
    table_target = 'tabela-cursos'
    context_object_name = 'courses'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = CourseFilterForm(request.GET)
        self.term, self.stage = self.filters.criteria()

    def get_queryset(self):
        return Course.objects.search(self.term, self.stage).annotate(class_group_count=Count('class_groups')).order_by('name')

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == self.table_target:
            return [self.table_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            filters=self.filters,
            filtered=bool(self.term) or bool(self.stage),
            total=Course.objects.count(),
            table_target=self.table_target,
            **kwargs,
        )
        context['page'] = paginate(self.request, self.object_list)
        context['courses'] = context['page'].object_list
        user = self.request.user
        for course in context['courses']:
            course.deletable = not course.class_group_count and user.has_perm(permissions.COURSE_DELETE)
            course.history_action = audit_history_action(catalog.COURSE, course.pk) if user.has_perm(permissions.AUDIT_VIEW) else None
        return context


class CourseDetailView(TemplateView):
    """Detalhe do curso com as turmas, cada uma com o total de ofertas e de aulas."""

    permission_required = permissions.COURSE_VIEW
    audit_resource = catalog.COURSE
    template_name = 'schedule/course_detail.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(Course, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        class_groups = self.target.class_groups.annotate(
            offering_count=Count('offerings', distinct=True), lesson_count=Count('allocations', distinct=True),
        ).order_by('label')
        user = self.request.user
        history = audit_history_action(catalog.COURSE, self.target.pk) if user.has_perm(permissions.AUDIT_VIEW) else None
        return super().get_context_data(
            target=self.target, class_groups=class_groups, in_use=self.target.is_in_use, history=history, **kwargs,
        )


class CourseFormView(OperationFormView):
    audit_resource = catalog.COURSE
    template_name = 'schedule/course_form.html'
    modal_template_name = 'schedule/course_form_modal.html'
    success_url = reverse_lazy('courses_list')
    form_class = CourseForm


class CourseCreateView(CourseFormView):
    permission_required = permissions.COURSE_CREATE
    title = 'Cadastrar curso'
    submit_label = 'Cadastrar'

    def perform(self, data):
        course = Course.objects.register(data['name'], data['stage'])
        messages.success(self.request, f'Curso {course.name} cadastrado.')


class CourseUpdateView(CourseFormView):
    permission_required = permissions.COURSE_EDIT
    model = Course
    title = 'Editar curso'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def get_context_data(self, **kwargs):
        return super().get_context_data(in_use=self.target.is_in_use, **kwargs)

    def perform(self, data):
        self.target.update_details(data['name'], data['stage'])
        messages.success(self.request, f'Curso {self.target.name} atualizado.')


class CourseDeleteView(ConfirmedActionView):
    permission_required = permissions.COURSE_DELETE
    audit_resource = catalog.COURSE
    model = Course
    template_name = 'schedule/course_confirm.html'
    modal_template_name = 'schedule/course_confirm_modal.html'
    success_url = reverse_lazy('courses_list')

    def perform(self):
        self.target.delete_course()
        messages.success(self.request, f'Curso {self.target.name} excluído.')


class AcademicListView(ListView):
    """Disciplinas ou turmas do escopo do usuário, aplicado na consulta."""

    model = None
    filter_form_class = None
    table_template_name = ''
    table_target = ''
    delete_permission = ''

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = self.filter_form_class(request.GET)
        self.criteria = self.filters.criteria()

    def scope(self):
        return self.model.objects.visible_to(self.request.user)

    def get_queryset(self):
        return self.filtered(self.scope()).annotate(
            offering_count=Count('offerings', distinct=True), lesson_count=Count('allocations', distinct=True),
        )

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == self.table_target:
            return [self.table_template_name]
        return super().get_template_names()

    def is_filtered(self):
        return bool(self.criteria)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            filters=self.filters, filtered=self.is_filtered(), total=self.scope().count(), table_target=self.table_target, **kwargs,
        )
        context['page'] = paginate(self.request, self.object_list)
        context[self.context_object_name] = context['page'].object_list
        user = self.request.user
        for item in context['page'].object_list:
            item.deletable = not item.offering_count and not item.lesson_count and user.has_perm(self.delete_permission)
            item.history_action = audit_history_action(self.audit_resource, item.pk) if user.has_perm(permissions.AUDIT_VIEW) else None
        return context


class SubjectListView(AcademicListView):
    permission_required = permissions.SUBJECT_VIEW
    audit_resource = catalog.SUBJECT
    model = Subject
    filter_form_class = SubjectFilterForm
    template_name = 'schedule/subject_list.html'
    table_template_name = 'schedule/partials/subject_table.html'
    table_target = 'tabela-disciplinas'
    context_object_name = 'subjects'
    delete_permission = permissions.SUBJECT_DELETE

    def filtered(self, queryset):
        return queryset.search(self.criteria).order_by('name')


class ClassGroupListView(AcademicListView):
    permission_required = permissions.CLASS_GROUP_VIEW
    audit_resource = catalog.CLASS_GROUP
    model = ClassGroup
    filter_form_class = ClassGroupFilterForm
    template_name = 'schedule/class_group_list.html'
    table_template_name = 'schedule/partials/class_group_table.html'
    table_target = 'tabela-turmas'
    context_object_name = 'class_groups'
    delete_permission = permissions.CLASS_GROUP_DELETE

    def filtered(self, queryset):
        term, course = self.criteria
        return queryset.search(term, course).select_related('course').order_by('course__name', 'label')

    def is_filtered(self):
        term, course = self.criteria
        return bool(term) or course is not None


class AcademicDetailView(TemplateView):
    """Detalhe no escopo do usuário; fora dele, 404."""

    model = None
    offering_field = ''

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(self.model.objects.visible_to(request.user), pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        offerings = (
            ClassOffering.objects.filter(**{self.offering_field: self.target})
            .select_related('semester', 'subject', 'class_group__course')
            .prefetch_related('assignments__teacher')
            .order_by('-semester__code', 'subject__name', 'class_group__course__name', 'class_group__label')
        )
        user = self.request.user
        history = audit_history_action(self.audit_resource, self.target.pk) if user.has_perm(permissions.AUDIT_VIEW) else None
        return super().get_context_data(
            target=self.target, offerings=offerings, lessons=self.target.allocations.count(),
            in_use=self.target.is_in_use, history=history, **kwargs,
        )


class SubjectDetailView(AcademicDetailView):
    permission_required = permissions.SUBJECT_VIEW
    audit_resource = catalog.SUBJECT
    model = Subject
    offering_field = 'subject'
    template_name = 'schedule/subject_detail.html'


class ClassGroupDetailView(AcademicDetailView):
    permission_required = permissions.CLASS_GROUP_VIEW
    audit_resource = catalog.CLASS_GROUP
    model = ClassGroup
    offering_field = 'class_group'
    template_name = 'schedule/class_group_detail.html'


class SubjectFormView(OperationFormView):
    audit_resource = catalog.SUBJECT
    template_name = 'schedule/subject_form.html'
    modal_template_name = 'schedule/subject_form_modal.html'
    success_url = reverse_lazy('subjects_list')
    form_class = SubjectForm


class SubjectCreateView(SubjectFormView):
    permission_required = permissions.SUBJECT_CREATE
    title = 'Cadastrar disciplina'
    submit_label = 'Cadastrar'

    def perform(self, data):
        subject = Subject.objects.register(data['name'])
        messages.success(self.request, f'Disciplina {subject.name} cadastrada.')


class SubjectUpdateView(SubjectFormView):
    permission_required = permissions.SUBJECT_EDIT
    model = Subject
    title = 'Editar disciplina'

    def get_target_queryset(self):
        return Subject.objects.visible_to(self.request.user)

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def get_context_data(self, **kwargs):
        return super().get_context_data(in_use=self.target.is_in_use, **kwargs)

    def perform(self, data):
        self.target.update_details(data['name'])
        messages.success(self.request, f'Disciplina {self.target.name} atualizada.')


class SubjectDeleteView(ConfirmedActionView):
    permission_required = permissions.SUBJECT_DELETE
    audit_resource = catalog.SUBJECT
    model = Subject
    template_name = 'schedule/subject_confirm.html'
    modal_template_name = 'schedule/subject_confirm_modal.html'
    success_url = reverse_lazy('subjects_list')

    def get_target_queryset(self):
        return Subject.objects.visible_to(self.request.user)

    def perform(self):
        self.target.delete_subject()
        messages.success(self.request, f'Disciplina {self.target.name} excluída.')


class ClassGroupFormView(OperationFormView):
    audit_resource = catalog.CLASS_GROUP
    template_name = 'schedule/class_group_form.html'
    modal_template_name = 'schedule/class_group_form_modal.html'
    success_url = reverse_lazy('class_groups_list')
    form_class = ClassGroupForm


class ClassGroupCreateView(ClassGroupFormView):
    permission_required = permissions.CLASS_GROUP_CREATE
    title = 'Cadastrar turma'
    submit_label = 'Cadastrar'

    def perform(self, data):
        group = ClassGroup.objects.register(data['course'], data['label'])
        messages.success(self.request, f'Turma {group.label} de {group.course.name} cadastrada.')


class ClassGroupUpdateView(ClassGroupFormView):
    permission_required = permissions.CLASS_GROUP_EDIT
    model = ClassGroup
    title = 'Editar turma'

    def get_target_queryset(self):
        return ClassGroup.objects.visible_to(self.request.user).select_related('course')

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def get_context_data(self, **kwargs):
        return super().get_context_data(in_use=self.target.is_in_use, **kwargs)

    def perform(self, data):
        self.target.update_details(data['label'], course=data['course'])
        messages.success(self.request, f'Turma {self.target.label} de {self.target.course.name} atualizada.')


class ClassGroupDeleteView(ConfirmedActionView):
    permission_required = permissions.CLASS_GROUP_DELETE
    audit_resource = catalog.CLASS_GROUP
    model = ClassGroup
    template_name = 'schedule/class_group_confirm.html'
    modal_template_name = 'schedule/class_group_confirm_modal.html'
    success_url = reverse_lazy('class_groups_list')

    def get_target_queryset(self):
        return ClassGroup.objects.visible_to(self.request.user).select_related('course')

    def perform(self):
        self.target.delete_class_group()
        messages.success(self.request, f'Turma {self.target.label} de {self.target.course.name} excluída.')


PERMISSION_MESSAGE = SPACE_PERMISSION_MESSAGE


def plural(total, singular, many):
    return singular if total == 1 else many


def usage_text(usage):
    """Uso agregado de um nome encontrado: aulas, turmas e dias da semana."""
    if not usage.lessons:
        return 'Sem aula nesta planilha'
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
    """Botões de decisão que o nome aceita e que o usuário pode usar."""
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
    """Quadro "Espaços desta importação", aberto só quando pede atenção."""
    status = importation.status
    if status in (Import.Status.DISCARDED, Import.Status.RECEIVED, Import.Status.FAILED) or importation.is_busy:
        return None
    if status == Import.Status.CONCLUDED:
        return {'concluded': True, 'created': sorted(Space.objects.filter(source_import=importation), key=natural_key)}
    resolution = classify_import(importation)
    is_open = status in (Import.Status.VALIDATED, Import.Status.PENDING) and not importation.is_busy
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
    refresh_failed = is_open and importation.outcome == Import.Outcome.REFRESH_FAILED
    with_errors = status == Import.Status.WITH_ERRORS
    return {
        'concluded': False,
        'expanded': bool(pending) or blocked or refresh_failed or with_errors,
        'open': is_open,
        'ready': status == Import.Status.VALIDATED and not importation.is_busy,
        'busy': importation.is_busy,
        'with_errors': with_errors,
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
        'blocked': blocked,
        'permission_message': PERMISSION_MESSAGE,
        'refresh_failed': refresh_failed,
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
    """Pede a atualização da prévia quando não resta pendência ou ela estava pronta."""
    current = Import.objects.get(pk=importation.pk)
    if classify_import(current).pending and current.status != Import.Status.VALIDATED:
        return
    try:
        current.request_refresh(request.user)
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)


def panel_url(importation):
    return SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk) + '#espacos'


class SpaceDecisionView(View):
    """Grava a decisão de um nome encontrado e atualiza a prévia, sem formulário de cadastro."""

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
    """Pede de novo a atualização da prévia depois de uma falha: é a recuperação, e não o fluxo normal."""

    permission_required = permissions.SPACE_ALLOCATION_IMPORT
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        importation = load_importation(SPACE_ALLOCATION_IMPORT_SCREENS, kwargs['pk'])
        try:
            importation.request_refresh(request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        return HttpResponseRedirect(panel_url(importation))


class SpaceAssociateView(ModalView, FormView):
    """Escolha do espaço do cadastro que é o mesmo que o nome encontrado."""

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
