"""Execução das operações pendentes das importações pelo worker (D4, D6).

Cada operação passa por duas transações. A reserva conta a tentativa e adia a próxima,
para que uma queda do processo também consuma tentativa e para que outro worker não pegue
a mesma importação até a execução. A execução trava a importação com skip_locked, espera
por trava no máximo `IMPORT_LOCK_TIMEOUT` segundos e chama a operação do model, que grava o
resultado de negócio e o fim da operação no mesmo commit. O limite vale só para a espera
por trava: uma execução que já tem as travas roda o tempo que precisar.

Um erro inesperado desfaz a execução e fica em `last_error`; a operação continua pendente
até esgotar as tentativas. Uma recusa de regra que escape da execução encerra a operação
sem nova tentativa. O worker nunca grava a situação diretamente.
"""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from audit import catalog
from audit.context import Actor, acting_as
from imports.models import Import
from imports.registry import get_definition

logger = logging.getLogger('imports')


def locked_pending(pk):
    return Import.objects.select_for_update().filter(pk=pk, operation__isnull=False).first()


def reserve():
    """Reserva a próxima operação vencida e devolve a importação e a definição, ou None sem nenhuma.

    A importação que já esgotou as tentativas, como depois de quedas seguidas do processo, é
    encerrada aqui sem executar, e a importação de tipo sem definição registrada também.
    """
    with transaction.atomic():
        importation = Import.objects.due().select_for_update(skip_locked=True).first()
        if importation is None:
            return None
        definition = get_definition(importation.kind)
        if definition is None:
            importation.attempts = settings.IMPORT_MAX_ATTEMPTS
            importation.register_failure(LookupError(f'Tipo de importação sem definição registrada: {importation.kind}.'))
        if importation.is_exhausted:
            importation.exhaust(definition)
            logger.error('Importação %s esgotou as tentativas: %s', importation.pk, importation.last_error or 'queda do processo')
            return importation, None
        importation.reserve()
    return importation, definition


def execute(importation, definition):
    """Executa a operação reservada, e trata a recusa e o erro inesperado em transação própria."""
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('lock_timeout', %s, true)", [f'{settings.IMPORT_LOCK_TIMEOUT}s'])
            with acting_as(Actor(user=importation.requested_by, origin=catalog.INTERFACE)):
                importation.execute_pending(definition)
    except ValidationError as error:
        with transaction.atomic():
            current = locked_pending(importation.pk)
            if current is not None:
                current.refuse(' '.join(error.messages))
        logger.warning('Importação %s recusada na execução: %s', importation.pk, ' '.join(error.messages))
    except Exception as error:
        with transaction.atomic():
            current = locked_pending(importation.pk)
            if current is None:
                return
            current.register_failure(error)
            if current.is_exhausted:
                logger.error(
                    'Importação %s falhou na tentativa %s e não será tentada de novo: %s',
                    current.pk, current.attempts, current.last_error,
                )
                current.exhaust(definition)
            else:
                logger.warning('Importação %s falhou na tentativa %s: %s', current.pk, current.attempts, current.last_error)


def process_next():
    """Processa a próxima operação vencida. Devolve False quando não há nenhuma."""
    reserved = reserve()
    if reserved is None:
        return False
    importation, definition = reserved
    if definition is not None:
        execute(importation, definition)
    return True
