"""Aviso de mudança disparado no on_commit; falha do canal só vai ao log."""

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
