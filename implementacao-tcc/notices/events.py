"""Registro dos eventos que geram notificações, criadas na transação de quem chama."""

from dataclasses import dataclass, field

from django.core.exceptions import ImproperlyConfigured

from notices.models import Notification

_events = {}


@dataclass(frozen=True)
class Delivery:
    """Uma notificação que um evento gera, já com o destinatário e o texto."""

    recipient: object
    type: str
    title: str
    message: str
    target_url: str = field(default='')


def register(name, event):
    current = _events.get(name)
    if current is not None and current is not event:
        raise ImproperlyConfigured(f'O evento {name} já tem um gerador registrado.')
    _events[name] = event


def announce(name, **context):
    event = _events.get(name)
    if event is None:
        raise ImproperlyConfigured(f'Evento sem gerador registrado: {name}.')
    return [
        Notification.objects.notify(
            delivery.recipient,
            delivery.type,
            delivery.title,
            delivery.message,
            target_url=delivery.target_url,
        )
        for delivery in event(**context)
    ]
