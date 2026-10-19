"""Sino e painel de notificações; o componente visual fica no app `ui`."""

from django import template

from notices.utils import panel_context

register = template.Library()


@register.inclusion_tag('ui/components/notifications.html', takes_context=True)
def notifications(context):
    return panel_context(context['request'])
