"""Telas da Agenda: a Grade, a solicitação, as solicitações do usuário e a análise.

Cada rota tem `login_required` no `urls.py` e declara a sua permissão, verificada pelo
PermissionMiddleware (D1 e D2 da Change agendar-uso-eventual-dos-espacos). As rotas de
"Minhas solicitações" carregam só as solicitações do próprio usuário, e o ID de outro
usuário responde 404. As regras ficam nas operações do model; as views só as chamam.
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.generic import ListView, TemplateView

from accounts import permissions
from accounts.views import ConfirmedActionView, OperationFormView
from audit import catalog
from bookings.forms import BookingRequestForm
from bookings.models import BookingRequest
from bookings.occupancy import agenda_sources
from schedule.forms import GridFilterForm
from schedule.models import Space
from schedule.occupancy import occupancy
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


class AgendaGridView(TemplateView):
    """Grade da Agenda: a mesma Grade do Ensalamento, com o ensalamento e os agendamentos.

    Reúne as fontes de `agenda_sources()` pela mesma `occupancy()` e monta a semana ou o mês
    pelas funções de `schedule.timetable`, com os agendamentos postos em todas as faixas que
    cruzam (D7). Não usa a view do Ensalamento.
    """

    permission_required = permissions.BOOKING_VIEW
    template_name = 'bookings/agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
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
        if dated and view == MONTH_VIEW:
            first = month_start(semester, chosen_month or chosen_week, today)
            month_end = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            occurrences = occupancy(space, first, month_end, sources=sources) if space else []
            week = dated_space_month(semester, space, first, today, occurrences, by_overlap=True)
        elif dated:
            reference = chosen_week or (month_reference(semester, chosen_month, today) if chosen_month else None)
            start = week_start(semester, reference, today)
            occurrences = occupancy(space, start, start + timedelta(days=4), sources=sources) if space else []
            week = dated_space_week(semester, space, start, today, occurrences, by_overlap=True)
        else:
            view = WEEK_VIEW
            week = space_week(semester, space, today)
        grid_url = reverse('agenda_grid')
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
            occupation_text=occupation_text(week, is_month),
            can_request=self.request.user.has_perm(permissions.BOOKING_REQUEST),
            shows_requester=self.request.user.has_perm(permissions.BOOKING_REVIEW),
        )
        return context


def agenda_link(space, day):
    """Grade da Agenda na sala e na semana de uma data."""
    return f"{reverse('agenda_grid')}?{urlencode({'sala': space.name, 'semana': day.isoformat()})}"


def request_related(queryset):
    """Solicitações com o espaço, o espaço sugerido e as pessoas, sem consulta por linha."""
    return queryset.select_related('space', 'suggested_space', 'requested_by', 'decided_by')


class BookingRequestCreateView(OperationFormView):
    """Modal "Solicitar agendamento", com o espaço, a data e o horário vindos da faixa (D8).

    O envio cria a solicitação pendente, sem agendamento, e volta para a semana da faixa.
    """

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/request_form.html'
    modal_template_name = 'bookings/request_form_modal.html'
    form_class = BookingRequestForm
    created = None

    def get_initial(self):
        query = self.request.GET
        return {'space': query.get('espaco'), 'date': query.get('data'), 'start_time': query.get('inicio'), 'end_time': query.get('fim')}

    def chosen_space(self):
        value = self.request.POST.get('space') or self.request.GET.get('espaco') or ''
        return Space.objects.filter(pk=value).first() if value.isdigit() else None

    def get_close_url(self):
        return reverse('agenda_grid')

    def get_success_url(self):
        return agenda_link(self.created.space, self.created.date)

    def get_context_data(self, **kwargs):
        return super().get_context_data(chosen_space=self.chosen_space(), **kwargs)

    def perform(self, data):
        self.created = BookingRequest.objects.submit(
            self.request.user, data['space'], data['date'], data['start_time'], data['end_time'], data['description'],
        )
        messages.success(
            self.request,
            f'Solicitação de agendamento de {self.created.space.name} em {self.created.schedule_text()} enviada.',
        )


def status_badge(request):
    """Tom, ícone e rótulo do selo da situação; o texto sempre acompanha a cor."""
    Status = BookingRequest.Status
    return {
        Status.PENDING: ('info', 'clock', 'Pendente'),
        Status.APPROVED: ('success', 'check', 'Aprovada'),
        Status.REJECTED: ('error', 'x', 'Rejeitada'),
        Status.SUGGESTED: ('warning', 'arrow-left-right', 'Alternativa sugerida'),
        Status.DECLINED: ('info', 'circle-minus', 'Alternativa recusada'),
    }[request.status]


def when(moment):
    return date_format(timezone.localtime(moment), 'DATETIME_FORMAT')


def history_of(request):
    """Histórico da solicitação montado dos campos dela, sem tabela de eventos (D3)."""
    Status = BookingRequest.Status
    lines = [f'Criada por {request.requested_by.name} em {when(request.created_at)}.']
    if request.decided_by_id:
        who = f'{request.decided_by.name} em {when(request.decided_at)}'
        if request.status == Status.REJECTED:
            if request.has_suggestion:
                lines.append('Alternativa sugerida.')
            lines.append(f'Rejeitada por {who}.')
        elif request.has_suggestion:
            lines.append(f'Alternativa sugerida por {who}.')
        else:
            lines.append(f'Aprovada por {who}.')
    if request.responded_at:
        answer = 'aceita' if request.status == Status.APPROVED else 'recusada'
        lines.append(f'Alternativa {answer} por {request.requested_by.name} em {when(request.responded_at)}.')
    return lines


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
    """Detalhe de uma solicitação do usuário, com o original e a alternativa lado a lado.

    O ID de uma solicitação de outro usuário responde 404, sem revelar que ela existe.
    """

    permission_required = permissions.BOOKING_REQUEST
    audit_resource = catalog.BOOKING_REQUEST
    template_name = 'bookings/my_request_detail.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(request_related(BookingRequest.objects), pk=kwargs['pk'], requested_by=request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=detailed(self.target), **kwargs)


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
