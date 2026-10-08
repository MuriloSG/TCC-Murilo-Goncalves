from django.core.management.commands import flush
from django.db import DEFAULT_DB_ALIAS

from accounts.utils import require_safe_database


class Command(flush.Command):
    """`flush` do Django com a mesma trava do `clear_data`.

    Substitui o comando nativo, porque um app do projeto tem precedência sobre o
    `django.core`. Antes de apagar, confirma que o banco do alias escolhido é o banco local
    comprovado ou um banco de teste criado pelo runner deste processo, que é o caso do
    `TransactionTestCase` (`require_safe_database`).
    """

    def handle(self, **options):
        require_safe_database('flush', options['database'] or DEFAULT_DB_ALIAS)
        return super().handle(**options)
