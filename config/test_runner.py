"""Runner dos testes, que registra os bancos de teste que ele mesmo criou.

A trava dos comandos destrutivos (`accounts.utils.require_safe_database`) libera, sem
exigir o banco local, só um banco desta lista. Ela existe apenas no processo do runner, entre a
criação e a remoção dos bancos de teste: um `manage.py flush` digitado à mão nunca a
preenche, mesmo que o banco tenha nome parecido com o de teste. Com `--parallel`, entram
também as cópias que o runner cria para cada processo (`test_<nome>_1`, `_2`, ...), que os
processos herdam do runner. O Django chama `teardown_databases` num `finally`, e a lista
é esvaziada mesmo se a remoção dos bancos falhar.
"""

import logging
import os

from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner

created_test_databases = set()


class TestRunner(DiscoverRunner):
    """Também deixa os loggers do projeto em WARNING, para a saída da suíte não repetir cada
    importação dos testes, salvo `DJANGO_LOG_LEVEL` informado. A variável vale para os
    processos do `--parallel`, que releem as configurações; o `assertLogs` ajusta o nível
    sozinho e continua vendo o INFO. O ajuste fica depois da descoberta dos testes, porque
    importar `config.asgi` chama `django.setup()` e reconfigura o log.
    """

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
