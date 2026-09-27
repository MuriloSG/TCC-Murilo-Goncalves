from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User

DEFAULT_PASSWORD = 'senha123#'


class Command(BaseCommand):
    """Define a mesma senha para todos os usuários, inclusive os superadmins e os inativos.

    Serve ao ambiente de desenvolvimento, para entrar com qualquer usuário. A senha é gravada
    com o hash do Django, e não em texto puro, e não passa pelas regras de força da senha.
    """

    help = 'Define a mesma senha para todos os usuários (padrão: senha123#).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Senha a definir.')
        parser.add_argument('--yes', action='store_true', help='Não pede confirmação.')

    def handle(self, *args, **options):
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
