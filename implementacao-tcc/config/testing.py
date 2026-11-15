"""Auxiliar dos testes que juntam variações de um caso com `subTest`."""

from contextlib import contextmanager

from django.core import mail
from django.db import transaction


class IsolatedCasesMixin:
    """`self.case(...)` roda cada variação num `subTest` dentro de um savepoint desfeito ao final.

    Assim as variações que gravam no banco partem do mesmo estado do `setUp`, como se fossem testes
    separados, e a caixa de e-mails de teste começa vazia, como o Django faz entre testes. O estado em
    memória (instâncias, cookies do cliente, relógios simulados) não volta: cada caso cuida do seu.
    Só para `TestCase`: o `TransactionTestCase` não roda dentro de uma transação.
    """

    @contextmanager
    def case(self, msg=None, **params):
        with self.subTest(msg, **params):
            if hasattr(mail, 'outbox'):
                mail.outbox.clear()
            savepoint = transaction.savepoint()
            try:
                yield
            finally:
                transaction.savepoint_rollback(savepoint)
