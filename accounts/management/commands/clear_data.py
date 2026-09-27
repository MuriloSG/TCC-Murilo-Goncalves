from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction

KEPT_APPS = {'accounts', 'account', 'auth', 'contenttypes', 'sessions'}


class Command(BaseCommand):
    """Exclui os dados de todos os apps, mantendo usuários, perfis, permissões e os e-mails do allauth.

    Usa `TRUNCATE ... RESTART IDENTITY CASCADE` nas tabelas dos apps fora de
    `KEPT_APPS`, o que também ignora a proteção do registro de auditoria, feita
    no model. As sessões ficam, para que ninguém perca o login.
    """

    help = 'Exclui os dados do sistema e mantém apenas os usuários, perfis e permissões.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Não pede confirmação.')

    def handle(self, *args, **options):
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
        self.stdout.write(self.style.SUCCESS(f'{len(tables)} tabelas limpas. Os usuários foram mantidos.'))
