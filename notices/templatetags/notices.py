"""Sino e painel de notificações do usuário autenticado.

O componente visual fica no app `ui`; os dados vêm daqui, do app dono deles, como
as rotas de opções dos campos de escolha.
"""

from django import template

from notices.utils import panel_context

register = template.Library()


@register.inclusion_tag('ui/components/notifications.html', takes_context=True)
def notifications(context):
    return panel_context(context['request'])
