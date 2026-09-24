"""Aviso de que as notificações de um usuário mudaram (D11).

O aviso é disparado no `transaction.on_commit` da operação que grava, e nunca
dentro dela: uma transação desfeita não avisa sobre uma notificação que não
existe. Uma falha do canal é registrada no log e não desfaz a notificação nem
recusa a publicação, porque a entrega imediata é uma camada sobre o estado
gravado, e não a fonte dele.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from notices.consumers import CHANGED, group_name

logger = logging.getLogger(__name__)


def announce_change(recipients):
    """Agenda o aviso dos destinatários para depois da confirmação da transação."""
    user_ids = sorted({getattr(person, 'pk', person) for person in recipients})
    if user_ids:
        transaction.on_commit(lambda: send_change(user_ids))


def send_change(user_ids):
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        for user_id in user_ids:
            async_to_sync(layer.group_send)(group_name(user_id), {'type': CHANGED})
    except Exception:
        logger.exception('Falha ao avisar as notificações dos usuários %s.', user_ids)
