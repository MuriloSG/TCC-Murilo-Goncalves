"""Registro dos tratadores de envio por tipo, que montam o e-mail ou devolvem None."""

from django.core.exceptions import ImproperlyConfigured

_handlers = {}


def register(kind, handler):
    current = _handlers.get(kind)
    if current is not None and current is not handler:
        raise ImproperlyConfigured(f'O tipo de envio {kind} já tem um tratador registrado.')
    _handlers[kind] = handler


def get_handler(kind):
    return _handlers.get(kind)
