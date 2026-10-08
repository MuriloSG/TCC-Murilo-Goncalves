"""Registro das importações específicas pelo tipo (D4 da Change processar-importacao-em-segundo-plano).

O worker só conhece o tipo gravado na importação, por isso cada app registra, no
AppConfig.ready, a definição da sua importação, como os tratadores do outbox.
"""

from django.core.exceptions import ImproperlyConfigured

_definitions = {}


def register(definition):
    current = _definitions.get(definition.kind)
    if current is not None and type(current) is not type(definition):
        raise ImproperlyConfigured(f'O tipo de importação {definition.kind} já tem uma definição registrada.')
    _definitions.setdefault(definition.kind, definition)


def get_definition(kind):
    return _definitions.get(kind)
