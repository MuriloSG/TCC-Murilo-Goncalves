"""Notificações de accounts, com o texto copiado para continuar legível depois."""

from notices import catalog
from notices.events import Delivery

ROLE_CHANGED = 'PERFIL_ALTERADO'


def role_changed(user, role):
    """Avisa o usuário do perfil trocado, mesmo inativo."""
    return [
        Delivery(
            recipient=user,
            type=catalog.ROLE_CHANGED,
            title='Perfil de acesso alterado',
            message=f'Seu perfil passou a ser {role.name}.',
        ),
    ]
