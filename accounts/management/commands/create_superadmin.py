from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = 'Cria um usuário ativo, superadmin, com o perfil ADMINISTRADOR.'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='E-mail do superadmin. Se omitido, é solicitado no terminal.')
        parser.add_argument('--name', help='Nome do superadmin. Se omitido, é solicitado no terminal.')

    def handle(self, *args, **options):
        email = User.objects.normalize_email(options['email'] or input('E-mail: '))
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(
                f'Já existe um usuário com o e-mail {email}. Para torná-lo superadmin, use '
                f'make manage cmd="set_superadmin {email} --grant".'
            )
        name = options['name'] or input('Nome: ')

        password = getpass('Senha: ')
        if password != getpass('Senha (novamente): '):
            raise CommandError('As senhas informadas não conferem.')
        try:
            validate_password(password, user=User(email=email, name=name))
            user = User.objects.create_superadmin(email=email, name=name, password=password)
        except ValidationError as error:
            raise CommandError(' '.join(error.messages)) from error

        self.stdout.write(self.style.SUCCESS(f'Superadmin {user.email} criado com o perfil ADMINISTRADOR.'))
