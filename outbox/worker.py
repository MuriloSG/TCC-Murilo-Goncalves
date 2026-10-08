"""Processamento dos envios pelo worker (D4).

Cada envio é processado numa transação própria e travado com skip_locked, para
que dois workers nunca processem o mesmo envio. Não existe estado intermediário:
se o processo cair depois do envio e antes do commit, o envio continua a enviar
e o e-mail pode sair de novo (entrega pelo menos uma vez).

Cada lote carrega a configuração SMTP gravada antes de travar qualquer envio. Sem
ela, ou com ela inválida, o lote não toca nos envios: eles continuam a enviar, sem
tentativa consumida (D5 da Change configurar-servidor-de-email).

O log de falha leva o número, o tipo e a classe da exceção, sem a mensagem, que pode
conter endereços de e-mail; o texto completo fica em `last_error`.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from audit import catalog
from audit.models import AuditLog
from outbox.handlers import get_handler
from outbox.models import OutboxEntry
from system_settings.models import SystemSetting

logger = logging.getLogger('outbox')


def record(action, entry):
    """Registra a ação automática do worker, sem usuário responsável (D11)."""
    AuditLog.objects.record(
        action,
        catalog.EMAIL,
        resource_id=entry.pk,
        metadata={'tipo': entry.kind, 'referencia': entry.reference},
    )


class SmtpUnavailable(Exception):
    """O servidor de e-mail não está configurado ou a configuração é inválida."""


def load_smtp():
    """Configuração SMTP vigente, lida a cada lote para valer sem reiniciar o worker (D6)."""
    try:
        smtp = SystemSetting.objects.smtp()
    except ValidationError:
        raise SmtpUnavailable('A configuração do servidor de e-mail é inválida.') from None
    if smtp is None:
        raise SmtpUnavailable('O servidor de e-mail não está configurado.')
    return smtp


def process(entry, smtp, connection):
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
                smtp.prepare(message, connection).send()
    except Exception as error:
        entry.register_failure(error)
        if entry.status == OutboxEntry.Status.FAILED:
            record(catalog.FAIL, entry)
            logger.error(
                'Envio %s (%s) falhou na tentativa %s e não será tentado de novo: %s.',
                entry.pk, entry.kind, entry.attempts, type(error).__name__,
            )
        else:
            logger.warning(
                'Envio %s (%s) falhou na tentativa %s: %s.', entry.pk, entry.kind, entry.attempts, type(error).__name__,
            )
        return
    if message is None:
        entry.mark_discarded()
    else:
        entry.mark_sent()
        record(catalog.SEND, entry)


def process_next(smtp=None, connection=None):
    """Processa o próximo envio vencido. Devolve False quando não há nenhum.

    Sem `smtp`, carrega a configuração e lança SmtpUnavailable quando ela falta.
    """
    if smtp is None:
        smtp = load_smtp()
        connection = smtp.connection()
    with transaction.atomic():
        entry = OutboxEntry.objects.due().select_for_update(skip_locked=True).first()
        if entry is None:
            return False
        process(entry, smtp, connection)
    return True


def process_batch(size, should_stop=lambda: False):
    """Processa até `size` envios vencidos e devolve quantos foram processados.

    Lança SmtpUnavailable, sem tocar nos envios, quando há envio vencido e o
    servidor de e-mail não está configurado.
    """
    if not OutboxEntry.objects.due().exists():
        return 0
    smtp = load_smtp()
    connection = smtp.connection()
    processed = 0
    while processed < size and not should_stop() and process_next(smtp, connection):
        processed += 1
    return processed
