"""Auditoria das mudanças de estado da Agenda (D9)."""

from datetime import time

from django.core.exceptions import ValidationError

from audit import catalog
from audit.models import AuditLog
from bookings.models import Booking
from bookings.tests.base import FRIDAY, THURSDAY, submit
from bookings.tests.test_models import BookingTestCase


class AuditTests(BookingTestCase):
    def logs(self, resource=None):
        logs = AuditLog.objects.filter(resource__in=[catalog.BOOKING_REQUEST, catalog.BOOKING]).order_by('pk')
        return list(logs.filter(resource=resource) if resource else logs)

    def test_creation(self):
        request = submit(self.ana, self.lab)
        [log] = self.logs()
        self.assertEqual((log.action, log.resource, log.resource_id), (catalog.CREATE, catalog.BOOKING_REQUEST, str(request.pk)))
        self.assertEqual(log.new_values, {
            'situacao': 'PENDENTE',
            'espaco': 'Laboratório de Informática 2',
            'data': '2026-10-15',
            'horario': '16:00 às 18:00',
            'description': 'Reunião do projeto de extensão com os alunos.',
        })

    def test_approval_records_the_transition_and_the_booking(self):
        request = submit(self.ana, self.lab)
        request.approve(self.reviewer)
        approval, created = self.logs()[1:]
        self.assertEqual(approval.action, catalog.APPROVE)
        self.assertEqual((approval.old_values, approval.new_values), ({'situacao': 'PENDENTE'}, {'situacao': 'APROVADA'}))
        self.assertEqual((created.action, created.resource), (catalog.CREATE, catalog.BOOKING))
        self.assertEqual(created.resource_id, str(Booking.objects.get().pk))
        self.assertEqual(created.new_values, {
            'espaco': 'Laboratório de Informática 2', 'data': '2026-10-15', 'horario': '16:00 às 18:00', 'solicitacao': request.pk,
        })

    def test_rejection_records_the_reason(self):
        request = submit(self.ana, self.lab)
        request.reject(self.reviewer, 'Laboratório em manutenção.')
        log = self.logs()[-1]
        self.assertEqual(log.action, catalog.REJECT)
        self.assertEqual(log.new_values, {'situacao': 'REJEITADA', 'motivo': 'Laboratório em manutenção.'})

    def test_suggestion_acceptance_and_decline(self):
        accepted = submit(self.ana, self.lab)
        accepted.suggest(self.reviewer, self.other_lab, FRIDAY, time(14, 0), time(16, 0), 'Manutenção no dia 15.')
        suggestion = self.logs()[-1]
        self.assertEqual(suggestion.action, catalog.SUGGEST)
        self.assertEqual(suggestion.new_values, {
            'situacao': 'ALTERNATIVA_SUGERIDA', 'espaco_sugerido': 'Laboratório de Informática 3', 'data_sugerida': '2026-10-16',
            'horario_sugerido': '14:00 às 16:00', 'mensagem': 'Manutenção no dia 15.',
        })
        accepted.accept_suggestion(self.ana)
        acceptance, created = self.logs()[-2:]
        self.assertEqual((acceptance.action, acceptance.user), (catalog.ACCEPT, None))
        self.assertEqual(acceptance.new_values, {'situacao': 'APROVADA'})
        self.assertEqual((created.action, created.resource), (catalog.CREATE, catalog.BOOKING))

        declined = submit(self.ana, self.lab, start=time(8, 0), end=time(9, 0))
        declined.suggest(self.reviewer, self.other_lab, FRIDAY, time(8, 0), time(9, 0))
        declined.decline_suggestion(self.ana)
        log = self.logs()[-1]
        self.assertEqual((log.action, log.old_values, log.new_values), (catalog.DECLINE, {'situacao': 'ALTERNATIVA_SUGERIDA'}, {'situacao': 'ALTERNATIVA_RECUSADA'}))

    def test_refused_operations_are_not_recorded(self):
        request = submit(self.ana, self.lab)
        other = submit(self.bruno, self.lab)
        request.approve(self.reviewer)
        before = len(self.logs())
        refusals = (
            lambda: other.approve(self.reviewer),
            lambda: request.approve(self.reviewer),
            lambda: other.reject(self.reviewer, ''),
            lambda: other.approve(self.ana),
            lambda: other.decline_suggestion(self.bruno),
            lambda: submit(self.ana, self.lab, description=''),
            lambda: submit(self.ana, self.lab, THURSDAY, time(14, 0), time(16, 0)),
        )
        for refusal in refusals:
            with self.assertRaises(ValidationError):
                refusal()
        self.assertEqual(len(self.logs()), before)
