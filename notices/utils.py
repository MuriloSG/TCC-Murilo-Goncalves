"""Auxiliares das telas de notificações."""

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def redirect_target(request, notification=None):
    """Destino da notificação, a tela de origem ou a página inicial, nessa ordem.

    A tela de origem só é aceita quando aponta para o próprio sistema, para que um
    endereço forjado no formulário não leve o usuário para fora.
    """
    if notification is not None and notification.target_url:
        return notification.target_url
    origin = request.POST.get('next', '')
    if origin and url_has_allowed_host_and_scheme(origin, {request.get_host()}, request.is_secure()):
        return origin
    return reverse('home')
