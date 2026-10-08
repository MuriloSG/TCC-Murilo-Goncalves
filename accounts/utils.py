from django.conf import settings
from django.core.management import CommandError
from django.db import DEFAULT_DB_ALIAS, connections

from config import test_runner

LOCAL_ENVIRONMENT = 'local'
LOCAL_DATABASE_MARK = 'ifagenda.environment'


def add_operation_error(form, error):
    """Leva para o formulário o ValidationError lançado por uma operação do model."""
    if hasattr(error, 'error_dict'):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


def require_safe_database(command, alias=DEFAULT_DB_ALIAS):
    """Recusa o comando destrutivo se o banco de destino não for comprovadamente o banco local.

    Um banco de teste criado pelo runner deste processo (`config.test_runner`) é liberado: o
    registro só existe entre a criação e a remoção dos bancos de teste, e um comando digitado
    à mão nunca o preenche, mesmo num banco com nome de teste.

    Fora disso, as três condições valem juntas, nesta ordem:

    1. `settings.ENVIRONMENT` é exatamente `local` (`DJANGO_ENVIRONMENT`). `DEBUG` não conta.
    2. A identidade configurada da conexão, `host:porta/nome`, é exatamente a declarada em
       `settings.LOCAL_DATABASE` (`DJANGO_LOCAL_DATABASE`). Ausente ou vazia, recusa.
    3. O banco conectado confirma: `current_database()` é o nome configurado e o próprio banco
       carrega a marca `ifagenda.environment = 'local'`, gravada uma vez com `make mark-local-db`.
       Um banco operacional não tem a marca, seja qual for o nome dele.

    As duas primeiras não consultam o banco; a terceira faz uma única consulta de leitura.
    Todas acontecem antes de qualquer pergunta ou escrita. A mensagem não repete valores
    configurados nem credenciais.
    """
    connection = connections[alias]
    config = connection.settings_dict
    if (alias, config['NAME']) in test_runner.created_test_databases:
        return
    refusal = (
        f'O comando {command} só pode ser executado no banco da máquina de desenvolvimento. Nada foi alterado. '
    )
    if getattr(settings, 'ENVIRONMENT', None) != LOCAL_ENVIRONMENT:
        raise CommandError(
            refusal + 'Esta instalação não está declarada como local. '
            'Na máquina de desenvolvimento, defina DJANGO_ENVIRONMENT=local no arquivo .env.'
        )
    expected = getattr(settings, 'LOCAL_DATABASE', None)
    if not isinstance(expected, str) or not expected or expected != database_identity(config):
        raise CommandError(
            refusal + 'O banco configurado não é o declarado em DJANGO_LOCAL_DATABASE, ou a variável está vazia. '
            'Confira POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB e DJANGO_LOCAL_DATABASE no arquivo .env.'
        )
    name, mark = connected_database(connection)
    if name != config['NAME'] or mark != LOCAL_ENVIRONMENT:
        raise CommandError(
            refusal + 'O banco conectado não está marcado como banco local. '
            'Se for mesmo o banco de desenvolvimento, marque-o com make mark-local-db.'
        )


def database_identity(config):
    """Identidade `host:porta/nome` de uma conexão, comparada com `DJANGO_LOCAL_DATABASE`."""
    return f"{config['HOST']}:{config['PORT']}/{config['NAME']}"


def connected_database(connection):
    """Nome e marca de ambiente do banco a que a conexão de fato chegou, numa só leitura."""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT current_database(), current_setting('{LOCAL_DATABASE_MARK}', true)")
        return cursor.fetchone()
