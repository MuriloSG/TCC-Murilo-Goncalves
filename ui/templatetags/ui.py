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


SAMPLE_NOTIFICATIONS = [
    {
        'icon': 'calendar-check',
        'tone': 'success',
        'title': 'Reserva aprovada',
        'text': 'Laboratório de Informática 2 em 22/09, das 10:00 às 12:00.',
        'time': 'Há 5 minutos',
        'unread': True,
    },
    {
        'icon': 'calendar-plus',
        'tone': 'info',
        'title': 'Nova solicitação de reserva',
        'text': 'João Lima solicitou o Auditório para 24/09, das 14:00 às 17:00.',
        'time': 'Há 1 hora',
        'unread': True,
    },
    {
        'icon': 'calendar-x',
        'tone': 'error',
        'title': 'Reserva cancelada',
        'text': 'A reserva da Sala 12 em 20/09 foi cancelada pelo solicitante.',
        'time': 'Ontem, 16:40',
        'unread': False,
    },
    {
        'icon': 'wrench',
        'tone': 'warning',
        'title': 'Manutenção programada',
        'text': 'O Laboratório de Química fica fechado para reservas de 25/09 a 27/09.',
        'time': '17/09, 09:15',
        'unread': False,
    },
    {
        'icon': 'shield-check',
        'tone': 'info',
        'title': 'Perfil de acesso alterado',
        'text': 'Seu perfil passou a ser Administrador.',
        'time': '15/09, 11:02',
        'unread': False,
    },
]


@register.inclusion_tag('ui/components/notifications.html')
def notifications():
    """Sino e painel de notificações com dados fixos de exemplo.

    Os dados são estáticos até que o domínio de notificações exista; o
    painel serve para validar a interface.
    """
    unread = sum(1 for item in SAMPLE_NOTIFICATIONS if item['unread'])
    return {'items': SAMPLE_NOTIFICATIONS, 'unread': unread}


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
