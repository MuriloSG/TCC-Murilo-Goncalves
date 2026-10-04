"""Tags e filtros dos componentes da interface (D10, D12)."""

from django import template
from django.template.loader import get_template
from django.urls import reverse

from ui.navigation import MenuGroup, menu_for
from ui.pagination import PAGE_PARAMETER

register = template.Library()


@register.simple_tag
def icon(name, css='size-5'):
    """Inclui o SVG do Lucide de ui/icons com a classe de tamanho."""
    return get_template(f'ui/icons/{name}.svg').render({'class_name': css})


@register.simple_tag(takes_context=True)
def navigation(context):
    """Itens do menu liberados ao usuário, com a marca do item atual."""
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    current_name = (match and match.url_name) or ''
    items = []
    for item, url in menu_for(request.user):
        entry = {'url': url, 'label': item.label, 'icon_name': item.icon}
        if isinstance(item, MenuGroup):
            entry['children'] = [
                {'url': child_url, 'label': child.label, 'icon_name': child.icon, 'current': current_name.startswith(child.prefix)}
                for child, child_url in item.entries_for(request.user)
            ]
            entry['current'] = any(child['current'] for child in entry['children'])
        else:
            entry['current'] = current_name.startswith(item.prefix)
        items.append(entry)
    return items


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
