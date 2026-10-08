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

O log leva o número da importação, o tipo, a operação e a classe da exceção, nunca o texto
dela: a mensagem pode trazer valores das linhas. O texto completo fica em `last_error`,
visível na tela da importação, e o traceback sai só no nível DEBUG.
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
            logger.error(
                'Importação %s esgotou as tentativas: %s', importation.pk,
                error_class(importation.last_error) or 'queda do processo',
            )
            return importation, None
        importation.reserve()
    return importation, definition


def error_class(last_error):
    """Classe da exceção guardada em `last_error` (`Tipo: mensagem`), sem a mensagem."""
    return last_error.partition(':')[0]


def execute(importation, definition):
    """Executa a operação reservada, e trata a recusa e o erro inesperado em transação própria."""
    operation = importation.operation
    logger.info(
        'Importação %s (%s): %s iniciada, tentativa %s.',
        importation.pk, importation.kind, operation, importation.attempts,
    )
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('lock_timeout', %s, true)", [f'{settings.IMPORT_LOCK_TIMEOUT}s'])
            with acting_as(Actor(user=importation.requested_by, origin=catalog.INTERFACE)):
                executed = importation.execute_pending(definition)
    except ValidationError as error:
        with transaction.atomic():
            current = locked_pending(importation.pk)
            if current is not None:
                current.refuse(' '.join(error.messages))
        logger.warning('Importação %s (%s): %s recusada na execução.', importation.pk, importation.kind, operation)
    except Exception as error:
        logger.debug('Traceback da importação %s.', importation.pk, exc_info=True)
        with transaction.atomic():
            current = locked_pending(importation.pk)
            if current is None:
                return
            current.register_failure(error)
            if current.is_exhausted:
                logger.error(
                    'Importação %s (%s): %s falhou na tentativa %s e não será tentada de novo: %s.',
                    current.pk, current.kind, operation, current.attempts, type(error).__name__,
                )
                current.exhaust(definition)
            else:
                logger.warning(
                    'Importação %s (%s): %s falhou na tentativa %s: %s.',
                    current.pk, current.kind, operation, current.attempts, type(error).__name__,
                )
    else:
        if executed:
            logger.info(
                'Importação %s (%s): %s concluída, situação %s, resultado %s.',
                importation.pk, importation.kind, operation, importation.status, importation.outcome or '-',
            )


def process_next():
    """Processa a próxima operação vencida. Devolve False quando não há nenhuma."""
    reserved = reserve()
    if reserved is None:
        return False
    importation, definition = reserved
    if definition is not None:
        execute(importation, definition)
    return True
