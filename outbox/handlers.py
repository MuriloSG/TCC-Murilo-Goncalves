"""Registro dos tratadores de cada tipo de envio (D3).

O worker só conhece o tipo gravado no envio, por isso cada app registra, no
AppConfig.ready, a função que monta o e-mail daquele tipo. A função recebe a
referência e devolve a mensagem pronta, ou None quando o envio não faz mais sentido.
"""

from django.core.exceptions import ImproperlyConfigured

_handlers = {}


def register(kind, handler):
    current = _handlers.get(kind)
    if current is not None and current is not handler:
        raise ImproperlyConfigured(f'O tipo de envio {kind} já tem um tratador registrado.')
    _handlers[kind] = handler


def get_handler(kind):
    return _handlers.get(kind)
