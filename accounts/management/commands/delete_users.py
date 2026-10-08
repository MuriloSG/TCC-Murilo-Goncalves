from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from accounts.models import User
from accounts.utils import require_safe_database


def references(model):
    """Chaves estrangeiras de todos os models, inclusive os intermediários, que apontam para `model`."""
    return [
        (related, field)
        for related in apps.get_models(include_auto_created=True)
        if related._meta.managed
        for field in related._meta.concrete_fields
        if (field.many_to_one or field.one_to_one) and field.remote_field.model is model
    ]


def purge(model, pks, excluded):
    """Exclui as linhas `pks` de `model` e, antes, o que depende delas.

    A referência que aceita nulo passa a nulo, e o registro que a tem fica. A referência
    obrigatória leva junto o registro que a tem, pelo mesmo caminho. A exclusão usa o
    gerenciador base e a exclusão direta do Django, sem o coletor: o `PROTECT` das chaves e
    a proteção do registro de auditoria ficam no coletor e no gerenciador próprio, e é isso
    que permite desfazer os vínculos sem abrir exceção nos models.
    """
    pks = [pk for pk in pks if pk not in excluded.setdefault(model, set())]
    if not pks:
        return 0
    excluded[model].update(pks)
    for related, field in references(model):
        linked = related._base_manager.filter(**{f'{field.attname}__in': pks})
        if field.null:
            linked.update(**{field.attname: None})
        else:
            purge(related, list(linked.values_list('pk', flat=True)), excluded)
    return model._base_manager.filter(pk__in=pks)._raw_delete(connection.alias)


class Command(BaseCommand):
    """Exclui todos os usuários que não são superadmin e os registros vinculados a eles.

    Os perfis e as permissões ficam, e os superadmins também, com o que lhes pertence. O que
    aponta para um usuário excluído por uma referência que aceita nulo, como o usuário de um
    registro de auditoria ou quem decidiu uma solicitação, fica com a referência vazia. O
    que depende dele obrigatoriamente, como o vínculo com o perfil, os e-mails do allauth, as
    solicitações e as importações que ele enviou, é excluído junto. Só roda com um
    superadmin ativo, para que o sistema não fique sem acesso administrativo, e só com
    o banco local comprovado (`require_safe_database`), verificado antes de tudo.
    """

    help = 'Exclui os usuários que não são superadmin e os vínculos deles, mantendo perfis e superadmins.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Não pede confirmação.')

    def handle(self, *args, **options):
        require_safe_database('delete_users')
        if not User.objects.filter(is_superadmin=True, is_active=True).exists():
            raise CommandError('Não há superadmin ativo. Crie um com create_superadmin antes de excluir os usuários.')
        pks = list(User.objects.filter(is_superadmin=False).values_list('pk', flat=True))
        if not pks:
            self.stdout.write('Nenhum usuário a excluir.')
            return
        if not options['yes']:
            answer = input(
                f'{len(pks)} usuários e os registros vinculados a eles serão excluídos. '
                'Os perfis e os superadmins ficam. Digite "sim" para continuar: '
            )
            if answer.strip().lower() != 'sim':
                self.stdout.write('Nada foi excluído.')
                return
        with transaction.atomic():
            deleted = purge(User, pks, {})
        self.stdout.write(self.style.SUCCESS(f'{deleted} usuários excluídos. Os perfis e os superadmins foram mantidos.'))
