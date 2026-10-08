from django.core.management.commands import flush
from django.db import DEFAULT_DB_ALIAS, connections

from accounts.utils import require_local_environment
from config import test_runner


class Command(flush.Command):
    """`flush` do Django com a mesma trava de ambiente do `clear_data`.

    Substitui o comando nativo, porque um app do projeto tem precedência sobre o
    `django.core`. Antes de qualquer acesso ao banco, recusa a execução fora de
    `DJANGO_ENVIRONMENT=local` (`require_local_environment`), exceto num banco de teste
    criado pelo runner deste processo (`config.test_runner`), que é o caso do
    `TransactionTestCase`. O nome do banco sozinho não dispensa a trava.
    """

    def handle(self, **options):
        alias = options['database'] or DEFAULT_DB_ALIAS
        if (alias, connections[alias].settings_dict['NAME']) not in test_runner.created_test_databases:
            require_local_environment('flush')
        return super().handle(**options)
