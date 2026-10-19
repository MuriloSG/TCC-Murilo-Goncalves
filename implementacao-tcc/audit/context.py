"""Ator da ação num ContextVar, para que as operações auditem sem conhecer a requisição."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace

from audit import catalog


@dataclass(frozen=True)
class Actor:
    """Quem executa a ação, de onde e com qual cliente."""

    user: object = None
    ip_address: str | None = None
    user_agent: str = ''
    origin: str = catalog.SYSTEM


SYSTEM_ACTOR = Actor()

_actor = ContextVar('audit_actor', default=SYSTEM_ACTOR)


def current_actor():
    return _actor.get()


@contextmanager
def acting_as(actor):
    token = _actor.set(actor)
    try:
        yield
    finally:
        _actor.reset(token)


@contextmanager
def acting_from_import(user):
    """Origem de importação, com quem executou a planilha como responsável."""
    with acting_as(replace(current_actor(), user=user, origin=catalog.IMPORTED)):
        yield


@contextmanager
def acting_as_user(user):
    """Ator com o usuário do sinal, já que o ator da requisição de login é definido antes da sessão."""
    with acting_as(replace(current_actor(), user=user)):
        yield
