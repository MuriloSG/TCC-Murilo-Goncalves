"""Aviso de mudança disparado no on_commit; falha do canal só vai ao log."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from notices.consumers import CHANGED, CLOSED, group_name

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


def close_connections(user_id):
    """Agenda o fechamento das conexões do usuário para depois da confirmação da transação."""
    transaction.on_commit(lambda: send_close(user_id))


def send_close(user_id):
    try:
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(group_name(user_id), {'type': CLOSED})
    except Exception:
        logger.exception('Falha ao encerrar as conexões do usuário %s.', user_id)
