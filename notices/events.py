"""Registro dos eventos do sistema que geram notificações (D5).

O mecanismo não conhece os eventos nem os apps que os declaram: cada app registra,
no `AppConfig.ready`, a função que descreve o que aconteceu, como o `outbox` faz
com os tratadores de e-mail. A função recebe o contexto da operação e devolve as
entregas, e `announce` as cria na transação de quem chama, de modo que uma
operação desfeita não deixe notificação e uma operação recusada não notifique.
"""

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
    """Cria as notificações do evento e as devolve."""
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
