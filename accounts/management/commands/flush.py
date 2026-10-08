from django.core.management.commands import flush
from django.db import DEFAULT_DB_ALIAS

from accounts.utils import require_safe_database


class Command(flush.Command):
    """`flush` do Django com a trava de banco local do `clear_data`."""

    def handle(self, **options):
        require_safe_database('flush', options['database'] or DEFAULT_DB_ALIAS)
        return super().handle(**options)
