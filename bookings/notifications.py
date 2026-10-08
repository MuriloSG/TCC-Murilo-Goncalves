"""Notificações das transições da Agenda, anunciadas dentro da transação e cortadas no limite do texto."""

from django.urls import reverse
from django.utils.text import Truncator

from accounts import permissions
from accounts.models import User
from notices import catalog
from notices.events import Delivery
from notices.models import MESSAGE_MAX_LENGTH

REQUESTED = 'AGENDA_SOLICITADA'
APPROVED = 'AGENDA_APROVADA'
REJECTED = 'AGENDA_REJEITADA'
SUGGESTED = 'AGENDA_ALTERNATIVA'
ACCEPTED = 'AGENDA_ALTERNATIVA_ACEITA'
DECLINED = 'AGENDA_ALTERNATIVA_RECUSADA'
CANCELLED = 'AGENDA_CANCELADA'


def review_url(request):
    return reverse('agenda_review_detail', args=[request.pk])


def own_url(request):
    return reverse('agenda_my_request', args=[request.pk])


def fit(message):
    return Truncator(message).chars(MESSAGE_MAX_LENGTH)


def original(request):
    return f'{request.space.name} em {request.schedule_text()}'


def suggested(request):
    return f'{request.suggested_space.name} em {request.suggested_schedule_text()}'


def reviewers(request):
    """Quem analisa a Agenda, sem o próprio solicitante."""
    return User.objects.with_permission(permissions.BOOKING_REVIEW).exclude(pk=request.requested_by_id).order_by('pk')


def deciders(request):
    """Quem sugeriu a alternativa; sem ele ativo e com a permissão, os demais que analisam."""
    decider = request.decided_by
    if decider is not None and decider.has_perm(permissions.BOOKING_REVIEW):
        return [decider]
    return reviewers(request)


def to_requester(request, notice_type, title, message):
    return [Delivery(recipient=request.requested_by, type=notice_type, title=title, message=fit(message), target_url=own_url(request))]


def to_reviewers(people, notice_type, title, message, request):
    return [
        Delivery(recipient=person, type=notice_type, title=title, message=fit(message), target_url=review_url(request))
        for person in people
    ]


def requested(request):
    return to_reviewers(
        reviewers(request),
        catalog.BOOKING_REQUESTED,
        'Nova solicitação de agendamento',
        f'{request.requested_by.name} solicitou o agendamento de {original(request)}.',
        request,
    )


def approved(request):
    return to_requester(
        request,
        catalog.BOOKING_APPROVED,
        'Agendamento aprovado',
        f'A solicitação de agendamento de {original(request)} foi aprovada.',
    )


def rejected(request):
    return to_requester(
        request,
        catalog.BOOKING_REJECTED,
        'Solicitação de agendamento rejeitada',
        f'A solicitação de agendamento de {original(request)} foi rejeitada. Veja o motivo na solicitação.',
    )


def suggested_alternative(request):
    return to_requester(
        request,
        catalog.BOOKING_SUGGESTED,
        'Alternativa sugerida',
        f'Para a solicitação de agendamento de {original(request)}, a alternativa é {suggested(request)}. Aceite ou recuse.',
    )


def accepted(request):
    return to_reviewers(
        deciders(request),
        catalog.SUGGESTION_ACCEPTED,
        'Alternativa aceita',
        f'{request.requested_by.name} aceitou a alternativa. Agendamento de {suggested(request)} aprovado.',
        request,
    )


def declined(request):
    return to_reviewers(
        deciders(request),
        catalog.SUGGESTION_DECLINED,
        'Alternativa recusada',
        f'{request.requested_by.name} recusou a alternativa de {suggested(request)}. A solicitação foi encerrada sem agendamento.',
        request,
    )


def cancelled(request):
    """Avisa a outra parte do cancelamento."""
    title = 'Agendamento cancelado'
    booked = f'{request.booked_space.name} em {request.booked_schedule_text()}'
    if request.cancelled_by_id == request.requested_by_id:
        message = f'{request.requested_by.name} cancelou o agendamento de {booked}.'
        return to_reviewers(deciders(request), catalog.BOOKING_CANCELLED, title, message, request)
    message = f'O agendamento de {booked} foi cancelado por {request.cancelled_by.name}.'
    if request.cancellation_reason:
        message += ' Veja o motivo na solicitação.'
    return to_requester(request, catalog.BOOKING_CANCELLED, title, message)


EVENTS = {
    REQUESTED: requested,
    APPROVED: approved,
    REJECTED: rejected,
    SUGGESTED: suggested_alternative,
    ACCEPTED: accepted,
    DECLINED: declined,
    CANCELLED: cancelled,
}
