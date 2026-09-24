"""Ator da ação auditada (D3).

O ator fica num ContextVar, e não num parâmetro das operações: assim
`User.objects.register` registra o cadastro sem conhecer a requisição, e a mesma
operação chamada pela tela, por uma planilha ou por um comando produz registros
com origens diferentes. Sem ninguém definir nada, o ator é o do sistema, o que
mantém auditada a ação de um comando ou do worker.
"""

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
def acting_from_import():
    """Mantém o usuário responsável e troca a origem para a importação."""
    with acting_as(replace(current_actor(), origin=catalog.IMPORTED)):
        yield
