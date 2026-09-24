"""Catálogo dos tipos de notificação e das formas de destinar (D4).

O tipo é gravado como código em português, e o rótulo, o ícone e o tom existem
só para a interface. Acrescentar um tipo é acrescentar a entrada deste catálogo,
sem migration de esquema e sem alteração nas telas. A criação de uma notificação
de tipo fora daqui é recusada.

`manual` marca os tipos que aparecem na publicação manual. Um tipo gerado por
evento não é oferecido na escolha nem aceito no envio do formulário.
"""

NOTICE = 'COMUNICADO'
ROLE_CHANGED = 'PERFIL_ALTERADO'

TYPES = {
    NOTICE: {'label': 'Comunicado', 'icon': 'info', 'tone': 'info', 'manual': True},
    ROLE_CHANGED: {'label': 'Perfil alterado', 'icon': 'shield-check', 'tone': 'info', 'manual': False},
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


def icon(code):
    return TYPES.get(code, {}).get('icon', 'info')


def tone(code):
    return TYPES.get(code, {}).get('tone', 'info')


def manual_choices():
    """Pares de código e rótulo dos tipos publicáveis manualmente, na ordem do catálogo."""
    return [(code, data['label']) for code, data in TYPES.items() if data['manual']]


def destination_choices():
    return list(DESTINATION_LABELS.items())
