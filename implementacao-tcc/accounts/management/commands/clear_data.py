from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from accounts.utils import require_safe_database
from schedule import public_cache

KEPT_APPS = {'accounts', 'account', 'auth', 'contenttypes', 'sessions'}


class Command(BaseCommand):
    """Trunca os dados dos apps fora de KEPT_APPS, sem a proteção da auditoria; só roda no banco local."""

    help = 'Exclui os dados do sistema e mantém apenas os usuários, perfis e permissões.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Não pede confirmação.')

    def handle(self, *args, **options):
        require_safe_database('clear_data')
        tables = sorted({
            model._meta.db_table
            for model in apps.get_models(include_auto_created=True)
            if model._meta.app_label not in KEPT_APPS and model._meta.managed
        })
        if not options['yes']:
            answer = input('Todos os dados, exceto os usuários, serão excluídos. Digite "sim" para continuar: ')
            if answer.strip().lower() != 'sim':
                self.stdout.write('Nada foi excluído.')
                return

        quoted = ', '.join(connection.ops.quote_name(table) for table in tables)
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f'TRUNCATE {quoted} RESTART IDENTITY CASCADE')
            public_cache.invalidate_on_commit()
        self.stdout.write(self.style.SUCCESS(f'{len(tables)} tabelas limpas. Os usuários foram mantidos.'))
