"""Processamento dos envios pelo worker (D4).

Cada envio é processado numa transação própria e travado com skip_locked, para
que dois workers nunca processem o mesmo envio. Não existe estado intermediário:
se o processo cair depois do envio e antes do commit, o envio continua a enviar
e o e-mail pode sair de novo (entrega pelo menos uma vez).
"""

import logging

from django.db import transaction

from audit import catalog
from audit.models import AuditLog
from outbox.handlers import get_handler
from outbox.models import OutboxEntry

logger = logging.getLogger('outbox')


def record(action, entry):
    """Registra a ação automática do worker, sem usuário responsável (D11)."""
    AuditLog.objects.record(
        action,
        catalog.EMAIL,
        resource_id=entry.pk,
        metadata={'tipo': entry.kind, 'referencia': entry.reference},
    )


def process(entry):
    handler = get_handler(entry.kind)
    if handler is None:
        entry.mark_failed(f'Tipo de envio sem tratador registrado: {entry.kind}.')
        logger.error('Envio %s falhou: tipo %s sem tratador registrado.', entry.pk, entry.kind)
        record(catalog.FAIL, entry)
        return
    try:
        with transaction.atomic():
            message = handler(entry.reference)
            if message is not None:
                message.send()
    except Exception as error:
        entry.register_failure(error)
        if entry.status == OutboxEntry.Status.FAILED:
            record(catalog.FAIL, entry)
            logger.error(
                'Envio %s falhou na tentativa %s e não será tentado de novo: %s',
                entry.pk, entry.attempts, entry.last_error,
            )
        else:
            logger.warning('Envio %s falhou na tentativa %s: %s', entry.pk, entry.attempts, entry.last_error)
        return
    if message is None:
        entry.mark_discarded()
    else:
        entry.mark_sent()
        record(catalog.SEND, entry)


def process_next():
    """Processa o próximo envio vencido. Devolve False quando não há nenhum."""
    with transaction.atomic():
        entry = OutboxEntry.objects.due().select_for_update(skip_locked=True).first()
        if entry is None:
            return False
        process(entry)
    return True


def process_batch(size, should_stop=lambda: False):
    """Processa até `size` envios vencidos e devolve quantos foram processados."""
    processed = 0
    while processed < size and not should_stop() and process_next():
        processed += 1
    return processed
