from django.db import IntegrityError, transaction
from django.test import TestCase

from outbox.models import OutboxEntry


class EnqueueTests(TestCase):
    def test_enqueues_pending_entry_with_text_reference(self):
        OutboxEntry.objects.enqueue('TESTE', 7)
        entry = OutboxEntry.objects.get()
        self.assertEqual((entry.kind, entry.reference, entry.status), ('TESTE', '7', 'A_ENVIAR'))
        self.assertEqual(entry.attempts, 0)

    def test_repeated_enqueue_keeps_single_pending_entry_and_attempts(self):
        OutboxEntry.objects.enqueue('TESTE', 1)
        OutboxEntry.objects.update(attempts=1)
        OutboxEntry.objects.enqueue('TESTE', 1)
        entry = OutboxEntry.objects.get()
        self.assertEqual(entry.attempts, 1)

    def test_new_entry_allowed_after_previous_was_sent(self):
        OutboxEntry.objects.enqueue('TESTE', 1)
        OutboxEntry.objects.update(status=OutboxEntry.Status.SENT)
        OutboxEntry.objects.enqueue('TESTE', 1)
        self.assertEqual(OutboxEntry.objects.filter(status='A_ENVIAR').count(), 1)
        self.assertEqual(OutboxEntry.objects.count(), 2)

    def test_same_reference_of_other_kind_is_independent(self):
        OutboxEntry.objects.enqueue('TESTE', 1)
        OutboxEntry.objects.enqueue('OUTRO', 1)
        self.assertEqual(OutboxEntry.objects.count(), 2)

    def test_database_refuses_second_pending_entry(self):
        OutboxEntry.objects.create(kind='TESTE', reference='1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            OutboxEntry.objects.create(kind='TESTE', reference='1')
