from django.conf import settings
from django.core.management import CommandError

LOCAL_ENVIRONMENT = 'local'


def add_operation_error(form, error):
    """Leva para o formulário o ValidationError lançado por uma operação do model."""
    if hasattr(error, 'error_dict'):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


def require_local_environment(command):
    """Recusa o comando fora do ambiente local de desenvolvimento, antes de qualquer acesso ao banco.

    O ambiente local é declarado só por `DJANGO_ENVIRONMENT=local`, com esse valor exato. A
    variável ausente ou vazia, outro ambiente (`producao`, `homologacao`, `staging`) ou um valor
    ambíguo (`Local`, `local `, `local,producao`) recusam o comando. `DEBUG` não é evidência de
    ambiente local e não é consultado. A mensagem não repete o valor configurado.
    """
    if getattr(settings, 'ENVIRONMENT', None) != LOCAL_ENVIRONMENT:
        raise CommandError(
            f'O comando {command} só pode ser executado na máquina de desenvolvimento, '
            'e esta instalação não está declarada como local. Nada foi alterado. '
            'Na máquina de desenvolvimento, defina DJANGO_ENVIRONMENT=local no arquivo .env.'
        )
