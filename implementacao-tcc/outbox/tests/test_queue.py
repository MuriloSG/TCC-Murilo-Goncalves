from django.db import IntegrityError, transaction
from django.test import TestCase
from config.testing import IsolatedCasesMixin

from outbox.models import OutboxEntry


class EnqueueTests(IsolatedCasesMixin, TestCase):
    def test_enqueues_one_pending_entry_per_kind_and_reference(self):
        with self.case('entrada pendente'):
            OutboxEntry.objects.enqueue('TESTE', 7)
            entry = OutboxEntry.objects.get()
            self.assertEqual((entry.kind, entry.reference, entry.status), ('TESTE', '7', 'A_ENVIAR'))
            self.assertEqual(entry.attempts, 0)
        with self.case('outro tipo'):
            OutboxEntry.objects.enqueue('TESTE', 1)
            OutboxEntry.objects.enqueue('OUTRO', 1)
            self.assertEqual(OutboxEntry.objects.count(), 2)

    def test_repeated_enqueue_keeps_a_single_pending_entry(self):
        with self.case('repetida'):
            OutboxEntry.objects.enqueue('TESTE', 1)
            OutboxEntry.objects.update(attempts=1)
            OutboxEntry.objects.enqueue('TESTE', 1)
            entry = OutboxEntry.objects.get()
            self.assertEqual(entry.attempts, 1)
        with self.case('depois do envio'):
            OutboxEntry.objects.enqueue('TESTE', 1)
            OutboxEntry.objects.update(status=OutboxEntry.Status.SENT)
            OutboxEntry.objects.enqueue('TESTE', 1)
            self.assertEqual(OutboxEntry.objects.filter(status='A_ENVIAR').count(), 1)
            self.assertEqual(OutboxEntry.objects.count(), 2)
