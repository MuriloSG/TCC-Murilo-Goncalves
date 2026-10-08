import logging
import signal
import threading

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from imports.worker import process_next

logger = logging.getLogger('imports')



class Command(BaseCommand):
    """Worker das importações; descarta a conexão inválida antes de cada ciclo e para entre operações no SIGTERM."""

    help = 'Executa as prévias, as atualizações e as confirmações pendentes das importações.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Processa as operações vencidas e termina.')

    def handle(self, *args, **options):
        stop = threading.Event()
        if not options['once']:
            for signum in (signal.SIGTERM, signal.SIGINT):
                signal.signal(signum, lambda *_: stop.set())
        logger.info('Worker das importações iniciado.')
        while True:
            close_old_connections()
            processed = 0
            while not stop.is_set() and process_next():
                processed += 1
            if options['once'] or stop.is_set():
                break
            if processed == 0:
                stop.wait(settings.IMPORT_POLL_INTERVAL)
        logger.info('Worker das importações encerrado.')
