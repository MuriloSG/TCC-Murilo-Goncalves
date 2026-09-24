"""Sino e painel de notificações do usuário autenticado.

O componente visual fica no app `ui`; os dados vêm daqui, do app dono deles, como
as rotas de opções dos campos de escolha. O painel mostra as mais recentes, e o
restante fica na página de notificações.
"""

from django import template

from notices.models import Notification

PANEL_SIZE = 10

register = template.Library()


@register.inclusion_tag('ui/components/notifications.html', takes_context=True)
def notifications(context):
    request = context['request']
    user = request.user
    if not user.is_authenticated:
        return {'request': request, 'items': [], 'unread': 0}
    return {
        'request': request,
        'items': Notification.objects.for_user(user)[:PANEL_SIZE],
        'unread': Notification.objects.unread_count(user),
    }
