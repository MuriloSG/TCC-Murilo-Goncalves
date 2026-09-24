"""Notificações geradas pelas ações de accounts (D5).

O texto descreve o fato com os dados do momento em que ele aconteceu, e é copiado
para a notificação, de modo que ela continue legível depois.
"""

from notices import catalog
from notices.events import Delivery

ROLE_CHANGED = 'PERFIL_ALTERADO'


def role_changed(user, role):
    """Avisa o usuário que teve o perfil trocado.

    A notificação é criada mesmo com o usuário inativo, porque diz respeito a ele e
    fica disponível quando ele voltar a entrar.
    """
    return [
        Delivery(
            recipient=user,
            type=catalog.ROLE_CHANGED,
            title='Perfil de acesso alterado',
            message=f'Seu perfil passou a ser {role.name}.',
        ),
    ]
