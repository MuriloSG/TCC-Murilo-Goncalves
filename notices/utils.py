"""Auxiliares das telas de notificações."""

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from notices.models import Notification

PANEL_SIZE = 10


def panel_context(request):
    """Dados do sino: a contagem de não lidas e as notificações mais recentes.

    Serve tanto ao painel renderizado com a página quanto ao fragmento buscado
    depois de um aviso do canal de tempo real, para que os dois mostrem sempre o
    mesmo estado gravado.
    """
    user = request.user
    if not user.is_authenticated:
        return {'request': request, 'origin': panel_origin(request), 'items': [], 'unread': 0}
    return {
        'request': request,
        'origin': panel_origin(request),
        'items': Notification.objects.for_user(user)[:PANEL_SIZE],
        'unread': Notification.objects.unread_count(user),
    }


def safe_origin(request, origin):
    if origin and url_has_allowed_host_and_scheme(origin, {request.get_host()}, request.is_secure()):
        return origin
    return ''


def panel_origin(request):
    """Tela para onde as ações do sino voltam.

    O fragmento buscado depois de um aviso do canal é renderizado em outra rota,
    por isso recebe a tela aberta em `origem`; sem ela, volta à página inicial, e
    nunca ao próprio fragmento.
    """
    if request.path == reverse('notifications_panel'):
        return safe_origin(request, request.GET.get('origem', '')) or reverse('home')
    return request.get_full_path()


def redirect_target(request, notification=None):
    """Destino da notificação, a tela de origem ou a página inicial, nessa ordem.

    A tela de origem só é aceita quando aponta para o próprio sistema, para que um
    endereço forjado no formulário não leve o usuário para fora.
    """
    if notification is not None and notification.target_url:
        return notification.target_url
    return safe_origin(request, request.POST.get('next', '')) or reverse('home')
