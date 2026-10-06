"""Catálogo dos tipos de notificação e das formas de destinar (D4).

O tipo é gravado como código em português, e o rótulo, a descrição, o ícone e o
tom existem só para a interface. Acrescentar um tipo é acrescentar a entrada deste
catálogo, sem migration de esquema e sem alteração nas telas. A criação de uma
notificação de tipo fora daqui é recusada.

O tom vem do tipo, e não de uma escolha própria de quem publica: assim a cor
continua com função definida e um comunicado nunca sai com a cor de outro estado.
`manual` marca os tipos oferecidos na publicação manual; um tipo gerado por evento
não aparece na escolha nem é aceito no envio.
"""

INFORMATION = 'INFORMACAO'
SUCCESS = 'SUCESSO'
WARNING = 'AVISO'
ROLE_CHANGED = 'PERFIL_ALTERADO'
BOOKING_REQUESTED = 'AGENDA_SOLICITADA'
BOOKING_APPROVED = 'AGENDA_APROVADA'
BOOKING_REJECTED = 'AGENDA_REJEITADA'
BOOKING_SUGGESTED = 'AGENDA_ALTERNATIVA'
SUGGESTION_ACCEPTED = 'AGENDA_ALTERNATIVA_ACEITA'
SUGGESTION_DECLINED = 'AGENDA_ALTERNATIVA_RECUSADA'
BOOKING_CANCELLED = 'AGENDA_CANCELADA'

TYPES = {
    INFORMATION: {
        'label': 'Informação',
        'description': 'Uma atualização ou comunicado',
        'icon': 'info',
        'tone': 'info',
        'manual': True,
    },
    SUCCESS: {
        'label': 'Sucesso',
        'description': 'Uma ação concluída',
        'icon': 'circle-check',
        'tone': 'success',
        'manual': True,
    },
    WARNING: {
        'label': 'Aviso',
        'description': 'Algo que merece atenção',
        'icon': 'triangle-alert',
        'tone': 'warning',
        'manual': True,
    },
    ROLE_CHANGED: {
        'label': 'Perfil alterado',
        'description': 'O perfil de acesso do usuário mudou',
        'icon': 'shield-check',
        'tone': 'info',
        'manual': False,
    },
    BOOKING_REQUESTED: {
        'label': 'Nova solicitação de agendamento',
        'description': 'Uma solicitação de agendamento aguarda análise',
        'icon': 'calendar-plus',
        'tone': 'info',
        'manual': False,
    },
    BOOKING_APPROVED: {
        'label': 'Agendamento aprovado',
        'description': 'A solicitação de agendamento foi aprovada',
        'icon': 'calendar-check',
        'tone': 'success',
        'manual': False,
    },
    BOOKING_REJECTED: {
        'label': 'Solicitação rejeitada',
        'description': 'A solicitação de agendamento foi rejeitada',
        'icon': 'calendar-x',
        'tone': 'warning',
        'manual': False,
    },
    BOOKING_SUGGESTED: {
        'label': 'Alternativa sugerida',
        'description': 'A solicitação de agendamento recebeu uma alternativa',
        'icon': 'calendar-clock',
        'tone': 'warning',
        'manual': False,
    },
    SUGGESTION_ACCEPTED: {
        'label': 'Alternativa aceita',
        'description': 'O solicitante aceitou a alternativa sugerida',
        'icon': 'calendar-check',
        'tone': 'success',
        'manual': False,
    },
    SUGGESTION_DECLINED: {
        'label': 'Alternativa recusada',
        'description': 'O solicitante recusou a alternativa sugerida',
        'icon': 'calendar-x',
        'tone': 'info',
        'manual': False,
    },
    BOOKING_CANCELLED: {
        'label': 'Agendamento cancelado',
        'description': 'Um agendamento aprovado foi cancelado',
        'icon': 'calendar-x',
        'tone': 'warning',
        'manual': False,
    },
}

ALL_USERS = 'TODOS'
ROLE = 'PERFIL'
USERS = 'USUARIOS'

DESTINATION_LABELS = {
    ALL_USERS: 'Todos os usuários',
    ROLE: 'Usuários de um perfil',
    USERS: 'Usuários específicos',
}


def label(code):
    return TYPES.get(code, {}).get('label', code)


def description(code):
    return TYPES.get(code, {}).get('description', '')


def icon(code):
    return TYPES.get(code, {}).get('icon', 'info')


def tone(code):
    return TYPES.get(code, {}).get('tone', 'info')


def is_manual(code):
    return TYPES.get(code, {}).get('manual', False)


def manual_choices():
    """Pares de código e rótulo dos tipos publicáveis manualmente, na ordem do catálogo."""
    return [(code, data['label']) for code, data in TYPES.items() if data['manual']]


def destination_choices():
    return list(DESTINATION_LABELS.items())
