"""Runner que registra os bancos de teste que criou, os únicos liberados pela trava sem o banco local."""

import logging
import os

from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner

created_test_databases = set()


class TestRunner(DiscoverRunner):
    """Deixa os loggers em WARNING após a descoberta, que reconfigura o log, salvo com `DJANGO_LOG_LEVEL`."""

    def setup_databases(self, **kwargs):
        level = os.environ.setdefault('DJANGO_LOG_LEVEL', 'WARNING').upper()
        for name in settings.APP_LOGGERS:
            logging.getLogger(name).setLevel(level)
        old_config = super().setup_databases(**kwargs)
        for alias in connections:
            creation = connections[alias].creation
            created_test_databases.add((alias, connections[alias].settings_dict['NAME']))
            created_test_databases.update(
                (alias, creation.get_test_db_clone_settings(str(index))['NAME'])
                for index in range(1, self.parallel + 1)
            )
        return old_config

    def teardown_databases(self, old_config, **kwargs):
        try:
            super().teardown_databases(old_config, **kwargs)
        finally:
            created_test_databases.clear()
