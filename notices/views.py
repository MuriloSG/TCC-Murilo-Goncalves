"""Telas das notificações do usuário.

Abrir e marcar como lida alteram dados, por isso são POST com CSRF, como as ações
de situação do usuário. Sem JavaScript, o painel continua funcionando: cada item é
um formulário comum, que recarrega a tela de origem.
"""

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from notices.models import Notification
from notices.utils import redirect_target


class NotificationOpenView(View):
    """Marca a notificação do usuário como lida e leva ao destino dela."""

    http_method_names = ['post']

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        return HttpResponseRedirect(redirect_target(request, notification))


class NotificationsReadAllView(View):
    """Marca como lidas todas as notificações não lidas do usuário."""

    http_method_names = ['post']

    def post(self, request):
        Notification.objects.mark_all_as_read(request.user)
        return HttpResponseRedirect(redirect_target(request))
