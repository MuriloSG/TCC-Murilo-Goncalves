from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from accounts.utils import require_safe_database

DEFAULT_PASSWORD = 'senha123#'


class Command(BaseCommand):
    """Define a mesma senha para todos os usuários, sem as regras de força; só roda no banco local."""

    help = 'Define a mesma senha para todos os usuários (padrão: senha123#).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Senha a definir.')
        parser.add_argument('--yes', action='store_true', help='Não pede confirmação.')

    def handle(self, *args, **options):
        require_safe_database('set_passwords')
        users = list(User.objects.order_by('pk'))
        if not options['yes']:
            answer = input(f'A senha de {len(users)} usuários será substituída. Digite "sim" para continuar: ')
            if answer.strip().lower() != 'sim':
                self.stdout.write('Nenhuma senha foi alterada.')
                return
        for user in users:
            user.set_password(options['password'])
        with transaction.atomic():
            User.objects.bulk_update(users, ['password'])
        self.stdout.write(self.style.SUCCESS(f'Senha definida para {len(users)} usuários.'))
