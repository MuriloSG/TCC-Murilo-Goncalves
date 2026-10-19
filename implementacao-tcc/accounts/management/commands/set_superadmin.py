from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = 'Concede ou retira o superadmin de um usuário, identificado pelo e-mail.'

    def add_arguments(self, parser):
        parser.add_argument('email', help='E-mail do usuário.')
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument('--grant', action='store_true', help='Concede o superadmin.')
        action.add_argument('--revoke', action='store_true', help='Retira o superadmin.')

    def handle(self, *args, **options):
        email = User.objects.normalize_email(options['email'])
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise CommandError(f'Não existe usuário com o e-mail {email}.') from None

        value = options['grant']
        try:
            user.set_superadmin(value)
        except ValidationError as error:
            raise CommandError(' '.join(error.messages)) from error

        situation = 'agora é superadmin' if value else 'deixou de ser superadmin'
        self.stdout.write(self.style.SUCCESS(f'O usuário {user.email} {situation}.'))
