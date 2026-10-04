import logging
import signal
import threading

from django.conf import settings
from django.core.management.base import BaseCommand

from outbox.worker import SmtpUnavailable, process_batch

logger = logging.getLogger('outbox')


class Command(BaseCommand):
    """Worker do outbox (D4).

    Processa os envios vencidos em lotes e espera o intervalo configurado quando
    não há nenhum. SIGTERM e SIGINT param o laço entre um envio e outro. Sem
    servidor de e-mail configurado, os envios ficam retidos e o motivo vai ao log
    só quando muda, para não repetir a cada ciclo (D5 da Change configurar-servidor-de-email).
    """

    help = 'Envia os e-mails registrados no outbox.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Processa um único lote e termina.')

    def handle(self, *args, **options):
        stop = threading.Event()
        if not options['once']:
            for signum in (signal.SIGTERM, signal.SIGINT):
                signal.signal(signum, lambda *_: stop.set())
        reason = None
        while True:
            try:
                processed = process_batch(settings.OUTBOX_BATCH_SIZE, should_stop=stop.is_set)
            except SmtpUnavailable as error:
                processed = 0
                if str(error) != reason:
                    logger.warning('Envios retidos: %s', error)
                reason = str(error)
            else:
                if reason is not None and processed:
                    logger.info('Servidor de e-mail disponível. Envios retidos liberados.')
                    reason = None
            if options['once'] or stop.is_set():
                break
            if processed == 0:
                stop.wait(settings.OUTBOX_POLL_INTERVAL)
