"""Registro das importações pelo tipo, que é tudo o que o worker conhece da importação."""

from django.core.exceptions import ImproperlyConfigured

_definitions = {}


def register(definition):
    current = _definitions.get(definition.kind)
    if current is not None and type(current) is not type(definition):
        raise ImproperlyConfigured(f'O tipo de importação {definition.kind} já tem uma definição registrada.')
    _definitions.setdefault(definition.kind, definition)


def get_definition(kind):
    return _definitions.get(kind)
