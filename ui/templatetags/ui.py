"""Tags e filtros dos componentes da interface (D10, D12)."""

from django import template
from django.template.loader import get_template
from django.urls import reverse

from ui.pagination import PAGE_PARAMETER

register = template.Library()


@register.simple_tag
def icon(name, css='size-5'):
    """Inclui o SVG do Lucide de ui/icons com a classe de tamanho."""
    return get_template(f'ui/icons/{name}.svg').render({'class_name': css})


@register.inclusion_tag('ui/components/nav_link.html', takes_context=True)
def nav_link(context, url_name, label, icon_name, prefix=None):
    """Item da navegação, marcado como atual quando o nome da rota começa com `prefix`."""
    match = getattr(context.get('request'), 'resolver_match', None)
    current = bool(match and match.url_name and match.url_name.startswith(prefix or url_name))
    return {'url': reverse(url_name), 'label': label, 'icon_name': icon_name, 'current': current}


@register.filter
def initials(name):
    """Primeira letra do primeiro e do último nome, em maiúsculas."""
    parts = (name or '').split()
    if not parts:
        return ''
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')).upper()


@register.filter
def first_name(name):
    """Primeiro nome, para exibir o usuário em espaços estreitos."""
    parts = (name or '').split()
    return parts[0] if parts else ''


@register.simple_tag
def row_action(url_name, pk, label, icon_name, when=True, danger=False):
    """Ação de uma linha de tabela para ui/components/row_actions.html.

    Devolve None quando `when` é falso, para que a ação sem permissão seja
    descartada por `action_list`.
    """
    if not when:
        return None
    return {'url': reverse(url_name, args=[pk]), 'label': label, 'icon': icon_name, 'danger': danger}


@register.simple_tag
def action_list(*actions):
    return [action for action in actions if action]


@register.simple_tag(takes_context=True)
def page_url(context, number):
    """Endereço da página `number` da lista atual, com os demais parâmetros da URL.

    A página 1 omite o parâmetro, para coincidir com o endereço sem paginação.
    """
    request = context['request']
    query = request.GET.copy()
    query.pop(PAGE_PARAMETER, None)
    if number != 1:
        query[PAGE_PARAMETER] = number
    encoded = query.urlencode()
    return f'{request.path}?{encoded}' if encoded else request.path
