"""Telas da Agenda; as regras ficam nas operações do model."""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.views.generic import ListView, TemplateView

from accounts import permissions
from accounts.utils import add_operation_error
from accounts.views import ConfirmedActionView, OperationFormView
from audit import catalog
from bookings.forms import OWN_AGENDA, ALL_AGENDAS, AgendaFilterForm, BookingOnBehalfForm, BookingRequestForm, CancelForm, RejectForm, ReviewFilterForm, SuggestForm
from bookings.models import BookingRequest
from bookings.occupancy import agenda_sources, own_occurrences
from schedule.models import Space
from schedule.occupancy import occupancy
from schedule.views import AllocationExceptionListView, OccurrenceCancelView, with_cancel_actions
from schedule.timetable import (
    current_semester_code,
    dated_space_month,
    dated_space_week,
    imported_semesters,
    month_reference,
    month_start,
    natural_key,
    occupation_text,
    parse_date,
    parse_month,
    space_week,
    week_start,
)
from ui.pagination import paginate

WEEK_VIEW = 'semana'
MONTH_VIEW = 'mes'


def bookable_spaces():
    """Espaços ativos, na ordem natural do nome: só eles aceitam solicitação."""
    return sorted(Space.objects.filter(is_active=True), key=natural_key)


def next_school_day(today):
    """Hoje em dia útil; no fim de semana, a segunda seguinte, que ainda tem faixas a solicitar."""
    return today + timedelta(days=7 - today.weekday()) if today.weekday() >= 5 else today


class AgendaGridView(TemplateView):
    """Grade do Ensalamento com os agendamentos, montada sem usar a view do Ensalamento."""

    permission_required = permissions.BOOKING_VIEW
    template_name = 'bookings/agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        upcoming = next_school_day(today)
        semesters = {semester.code: semester for semester in imported_semesters()}
        current = current_semester_code(today)
        codes = sorted(set(semesters) | {current}, reverse=True)
        code = self.request.GET.get('semestre')
        code = code if code in codes else current
        semester = semesters.get(code)
        spaces = bookable_spaces()
        chosen = (self.request.GET.get('sala') or '').casefold()
        space = next((option for option in spaces if option.name.casefold() == chosen), spaces[0] if spaces else None)
        view = MONTH_VIEW if self.request.GET.get('visao') == MONTH_VIEW else WEEK_VIEW
        chosen_week = parse_date(self.request.GET.get('semana'))
        chosen_month = parse_month(self.request.GET.get('mes'))
        dated = semester is not None and semester.has_period
        sources = agenda_sources()
        agenda = OWN_AGENDA if self.request.GET.get('agenda') == OWN_AGENDA else ALL_AGENDAS
        user = self.request.user

        busy = []

        def filtered(occurrences):
            if agenda != OWN_AGENDA:
                return occurrences
            own = own_occurrences(occurrences, user)
            busy.extend((item.date, item.start, item.end) for item in occurrences if item not in own)
            return own
        if dated and view == MONTH_VIEW:
            first = month_start(semester, chosen_month or chosen_week, today)
            month_end = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            occurrences = filtered(occupancy(space, first, month_end, sources=sources)) if space else []
            week = dated_space_month(semester, space, first, today, occurrences, by_overlap=True)
        elif dated:
            reference = chosen_week or (month_reference(semester, chosen_month, today) if chosen_month else upcoming)
            start = week_start(semester, reference, today)
            occurrences = filtered(occupancy(space, start, start + timedelta(days=4), sources=sources)) if space else []
            week = dated_space_week(semester, space, start, today, occurrences, by_overlap=True)
        else:
            view = WEEK_VIEW
            week = space_week(semester, space, today)
        grid_url = reverse('agenda_grid')
        is_month = view == MONTH_VIEW

        def grid_link(target, day=None, fragment=''):
            query = {'semestre': code, 'sala': space.name if space else ''}
            if agenda == OWN_AGENDA:
                query['agenda'] = OWN_AGENDA
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
            filter_form=AgendaFilterForm(
                {
                    'agenda': agenda,
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
            busy=busy,
            previous_url=grid_link(view, week.previous) if week.previous else None,
            following_url=grid_link(view, week.following) if week.following else None,
            today_url=grid_link(view, fragment='#hoje' if is_month else ''),
            occupation_text=occupation_text(week, is_month),
            can_request=self.request.user.has_perm(permissions.BOOKING_REQUEST) and not creates_directly(self.request.user),
            can_create=creates_directly(self.request.user),
            shows_requester=self.request.user.has_perm(permissions.BOOKING_REVIEW),
        )
        if week.is_dated:
            with_cancel_actions(week, self.request.user, 'agenda_occurrence_cancel')
        return context


def creates_directly(user):
    """Abre direto a criação para outro usuário a quem tem `AGENDA.CRIAR` sem `AGENDA.SOLICITAR`."""
    return user.has_perm(permissions.BOOKING_CREATE) and (user.is_superadmin or not user.has_perm(permissions.BOOKING_REQUEST))


def agenda_link(space, day):
    """Grade da Agenda na sala e na semana de uma data."""
    return f"{reverse('agenda_grid')}?{urlencode({'sala': space.name, 'semana': day.isoformat()})}"


def request_related(queryset):
    """Solicitações com espaços, pessoas e vínculo acadêmico, sem consulta por linha."""
    return queryset.select_related(
        'space', 'suggested_space', 'requested_by', 'decided_by', 'created_by',
        'teaching_assignment__teacher', 'teaching_assignment__offering__semester',
        'teaching_assignment__offering__subject', 'teaching_assignment__offering__class_group__course',
    )


REQUEST_FIELDS = ('subject', 'teaching_assignment', 'space', 'date', 'start_time', 'end_time', 'description', 'student_count')


class BookingRequestCreateView(OperationFormView):
    """Solicitação em duas etapas: `prepare` mostra a revisão e o envio com `confirmar` grava."""

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/request_form.html'
    modal_template_name = 'bookings/request_form_modal.html'
    summary_template_name = 'bookings/request_summary_modal.html'
    form_class = BookingRequestForm
    field_names = REQUEST_FIELDS
    refresh_route = 'agenda_request_create'
    created = None

    def get_initial(self):
        query = self.request.GET
        initial = {
            'space': query.get('espaco'), 'date': query.get('data'), 'start_time': query.get('inicio'), 'end_time': query.get('fim'),
        }
        initial.update({name: query.get(name) for name in self.field_names if query.get(name)})
        return initial

    def get_form_kwargs(self):
        trigger = (self.request.htmx.trigger_name or '') if self.request.htmx else ''
        return super().get_form_kwargs() | {
            'user': self.request.user, 'refresh_url': reverse(self.refresh_route), 'trigger': trigger,
        }

    def get_close_url(self):
        return reverse('agenda_grid')

    def get_success_url(self):
        return agenda_link(self.created.space, self.created.date)

    def arguments(self, form):
        data = form.cleaned_data
        return [
            self.request.user, data['space'], data['date'], data['start_time'], data['end_time'], data['description'],
            data['student_count'], form.semester, data['teaching_assignment'], None, None, data['subject'],
        ]

    def form_valid(self, form):
        try:
            if self.request.POST.get('confirmar') != '1':
                return self.render_summary(form, BookingRequest.objects.prepare(*self.arguments(form)))
            self.created = BookingRequest.objects.submit(*self.arguments(form))
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f'Solicitação de agendamento de {self.created.space.name} em {self.created.schedule_text()} enviada.',
        )
        return self.redirect_to(self.get_success_url())

    def render_summary(self, form, prepared):
        """Revisão da solicitação conferida, com os valores do envio em campos ocultos."""
        hidden = [(name, value) for name in self.field_names for value in self.request.POST.getlist(name)]
        return self.response_class(
            request=self.request,
            template=[self.summary_template_name if self.request.htmx else self.template_name],
            context=self.get_context_data(form=form, prepared=prepared, hidden=hidden, summary=True),
            using=self.template_engine,
        )


ON_BEHALF_FIELDS = ('requested_for', 'course', *REQUEST_FIELDS)


class BookingOnBehalfCreateView(BookingRequestCreateView):
    """Criação em nome de outro usuário, nas mesmas duas etapas da solicitação."""

    permission_required = permissions.BOOKING_CREATE
    template_name = 'bookings/on_behalf_form.html'
    modal_template_name = 'bookings/on_behalf_form_modal.html'
    form_class = BookingOnBehalfForm
    field_names = ON_BEHALF_FIELDS
    refresh_route = 'agenda_create'

    def get_initial(self):
        """Sem faixa, a data começa no próximo dia letivo, para a lista de usuários vir do semestre dela."""
        initial = super().get_initial()
        if not initial.get('date'):
            initial['date'] = next_school_day(timezone.localdate()).isoformat()
        return initial

    def arguments(self, form):
        data = form.cleaned_data
        return [
            self.request.user, data['space'], data['date'], data['start_time'], data['end_time'], data['description'],
            data['student_count'], form.semester, data['teaching_assignment'], data['requested_for'], data['course'], data['subject'],
        ]


def status_badge(request):
    """Tom, ícone e rótulo do selo da situação; o texto sempre acompanha a cor."""
    Status = BookingRequest.Status
    return {
        Status.PENDING: ('info', 'clock', 'Pendente'),
        Status.APPROVED: ('success', 'check', 'Aprovada'),
        Status.REJECTED: ('error', 'x', 'Rejeitada'),
        Status.SUGGESTED: ('warning', 'arrow-left-right', 'Alternativa sugerida'),
        Status.DECLINED: ('error', 'x', 'Alternativa recusada'),
        Status.CANCELLED: ('error', 'calendar-x', 'Cancelada'),
    }[request.status]


def when(moment):
    return date_format(timezone.localtime(moment), 'DATETIME_FORMAT')


def event(title, icon, tone, who, moment):
    return {'title': title, 'icon': icon, 'tone': tone, 'who': who.name if who else '', 'when': when(moment) if moment else ''}


def history_of(request):
    """Linha do tempo da solicitação montada dos campos dela, sem tabela de eventos."""
    Status = BookingRequest.Status
    events = [event('Solicitação criada', 'calendar-plus', 'success', request.created_by or request.requested_by, request.created_at)]
    if request.decided_by_id:
        who, moment = request.decided_by, request.decided_at
        if request.status == Status.REJECTED:
            if request.has_suggestion:
                events.append(event('Alternativa sugerida', 'arrow-left-right', 'warning', None, None))
            events.append(event('Rejeitada', 'x', 'error', who, moment))
        elif request.has_suggestion:
            events.append(event('Alternativa sugerida', 'arrow-left-right', 'warning', who, moment))
        else:
            events.append(event('Aprovada', 'check', 'success', who, moment))
    if request.responded_at:
        if request.status in (Status.APPROVED, Status.CANCELLED):
            events.append(event('Alternativa aceita', 'check', 'success', request.requested_by, request.responded_at))
        else:
            events.append(event('Alternativa recusada', 'x', 'error', request.requested_by, request.responded_at))
    if request.cancelled_at:
        events.append(event('Agendamento cancelado', 'calendar-x', 'error', request.cancelled_by, request.cancelled_at))
    return events


def detailed(request):
    request.badge = status_badge(request)
    request.history = history_of(request)
    return request


def decorate(requests, url_name):
    """Selo e ação de abrir o detalhe de cada solicitação da página."""
    for item in requests:
        item.badge = status_badge(item)
        item.detail_action = {
            'url': reverse(url_name, args=[item.pk]), 'label': 'Ver solicitação', 'icon': 'list-checks', 'danger': False, 'page': True,
        }
    return requests


class MyBookingRequestListView(ListView):
    """Solicitações do próprio usuário, da mais recente para a mais antiga."""

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/my_requests.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return request_related(BookingRequest.objects.filter(requested_by=self.request.user)).order_by('-created_at', '-pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = paginate(self.request, self.object_list)
        context['requests'] = decorate(context['page'].object_list, 'agenda_my_request')
        return context


class MyBookingRequestDetailView(TemplateView):
    """Detalhe de uma solicitação do usuário; a de outro responde 404."""

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/my_request_detail.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(request_related(BookingRequest.objects), pk=kwargs['pk'], requested_by=request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            target=detailed(self.target), can_cancel=self.target.can_cancel(self.request.user), **kwargs,
        )


class OwnRequestActionView(ConfirmedActionView):
    """Resposta do solicitante à alternativa: só a própria solicitação, e o resto responde 404."""

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/answer_confirm.html'
    modal_template_name = 'bookings/answer_confirm_modal.html'
    action = ''

    def setup(self, request, *args, **kwargs):
        super(ConfirmedActionView, self).setup(request, *args, **kwargs)
        self.target = get_object_or_404(request_related(BookingRequest.objects), pk=kwargs['pk'], requested_by=request.user)

    def get_success_url(self):
        return reverse('agenda_my_request', args=[self.target.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(action=self.action, **kwargs)


class AcceptSuggestionView(OwnRequestActionView):
    action = 'aceitar'

    def perform(self):
        self.target.accept_suggestion(self.request.user)
        messages.success(
            self.request,
            f'Alternativa aceita. Agendamento de {self.target.suggested_space.name} em {self.target.suggested_schedule_text()} aprovado.',
        )


class DeclineSuggestionView(OwnRequestActionView):
    action = 'recusar'

    def perform(self):
        self.target.decline_suggestion(self.request.user)
        messages.success(self.request, 'Alternativa recusada. A solicitação foi encerrada sem agendamento.')


class BookingRequestReviewListView(ListView):
    """Solicitações de todos para análise, por padrão as pendentes de decisão, das mais antigas."""

    permission_required = permissions.BOOKING_REVIEW
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/review_list.html'
    context_object_name = 'requests'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = ReviewFilterForm(request.GET or {'situacao': 'decidir'})

    def get_queryset(self):
        requests = request_related(BookingRequest.objects.all())
        if self.filters.only_open():
            requests = requests.filter(status__in=BookingRequest.OPEN)
        return requests.order_by('created_at', 'pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(filters=self.filters, only_open=self.filters.only_open(), **kwargs)
        context['page'] = paginate(self.request, self.object_list)
        context['requests'] = decorate(context['page'].object_list, 'agenda_review_detail')
        return context


class BookingRequestReviewDetailView(TemplateView):
    """Detalhe para quem analisa: solicitante, espaço, horário, descrição, estado e histórico."""

    permission_required = permissions.BOOKING_REVIEW
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/review_detail.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(request_related(BookingRequest.objects), pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            target=detailed(self.target), can_cancel=self.target.can_cancel(self.request.user), **kwargs,
        )


def review_detail_url(target):
    return reverse('agenda_review_detail', args=[target.pk])


class ApproveView(ConfirmedActionView):
    """Aprovação, com a disponibilidade verificada de novo no POST."""

    permission_required = permissions.BOOKING_REVIEW
    audit_resource = catalog.BOOKING_REQUEST
    model = BookingRequest
    template_name = 'bookings/review_page.html'
    modal_template_name = 'bookings/approve_confirm_modal.html'

    def get_success_url(self):
        return review_detail_url(self.target)

    def perform(self):
        self.target.approve(self.request.user)
        messages.success(self.request, f'Solicitação de {self.target.space.name} em {self.target.schedule_text()} aprovada.')


class ReviewFormView(OperationFormView):
    permission_required = permissions.BOOKING_REVIEW
    audit_resource = catalog.BOOKING_REQUEST
    model = BookingRequest
    template_name = 'bookings/review_page.html'

    def get_success_url(self):
        return review_detail_url(self.target)

    def get_close_url(self):
        return review_detail_url(self.target)


class RejectView(ReviewFormView):
    modal_template_name = 'bookings/reject_form_modal.html'
    form_class = RejectForm
    title = 'Rejeitar solicitação'

    def perform(self, data):
        self.target.reject(self.request.user, data['rejection_reason'])
        messages.success(self.request, f'Solicitação de {self.target.space.name} em {self.target.schedule_text()} rejeitada.')


class SuggestView(ReviewFormView):
    modal_template_name = 'bookings/suggest_form_modal.html'
    form_class = SuggestForm
    title = 'Sugerir alternativa'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def perform(self, data):
        self.target.suggest(
            self.request.user, data['suggested_space'], data['suggested_date'], data['suggested_start_time'],
            data['suggested_end_time'], data['suggestion_message'],
        )
        messages.success(
            self.request,
            f'Alternativa de {self.target.suggested_space.name} em {self.target.suggested_schedule_text()} sugerida.',
        )


class CancelBookingView(OperationFormView):
    """Cancelamento com motivo opcional; o model confere quem cancela, o estado e o prazo."""

    audit_resource = catalog.BOOKING_REQUEST
    model = BookingRequest
    modal_template_name = 'bookings/cancel_form_modal.html'
    form_class = CancelForm
    title = 'Cancelar agendamento'

    def get_target_queryset(self):
        return request_related(BookingRequest.objects)

    def get_close_url(self):
        return self.get_success_url()

    def perform(self, data):
        space, schedule = self.target.booked_space.name, self.target.booked_schedule_text()
        self.target.cancel(self.request.user, data['cancellation_reason'])
        messages.success(self.request, f'Agendamento de {space} em {schedule} cancelado.')


class MyBookingCancelView(CancelBookingView):
    """Cancelamento por quem solicitou: só a própria solicitação, e o resto responde 404."""

    permission_required = permissions.BOOKING_REQUEST
    template_name = 'bookings/cancel_page.html'

    def get_target_queryset(self):
        return super().get_target_queryset().filter(requested_by=self.request.user)

    def get_success_url(self):
        return reverse('agenda_my_request', args=[self.target.pk])


class ReviewCancelView(CancelBookingView):
    """Cancelamento por quem analisa, a partir do detalhe da análise."""

    permission_required = permissions.BOOKING_REVIEW
    template_name = 'bookings/review_page.html'

    def get_success_url(self):
        return review_detail_url(self.target)


class AgendaOccurrenceCancelView(OccurrenceCancelView):
    """Cancelamento pela Grade da Agenda, com a view e a visibilidade do Ensalamento."""

    permission_required = permissions.BOOKING_VIEW
    success_url = reverse_lazy('agenda_grid')
    section_title = 'Agenda'


class AgendaExceptionListView(AllocationExceptionListView):
    """Exceções do ensalamento pela Agenda, com a mesma regra de visibilidade do Ensalamento."""

    permission_required = permissions.BOOKING_VIEW
    section_title = 'Agenda'
    section_url = reverse_lazy('agenda_grid')
