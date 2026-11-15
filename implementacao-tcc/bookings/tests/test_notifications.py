"""Notificações das transições da Agenda: destinatários, texto, destino e recusa."""

from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.urls import reverse

from accounts import permissions
from accounts.models import Permission, Role, User
from bookings.models import BookingRequest
from bookings.tests.base import FRIDAY, REQUESTER, REVIEWER, frozen_clock, space, submit, user_with
from notices import catalog
from notices.models import MESSAGE_MAX_LENGTH, Notification

AGENDA_TYPES = [
    catalog.BOOKING_REQUESTED, catalog.BOOKING_APPROVED, catalog.BOOKING_REJECTED,
    catalog.BOOKING_SUGGESTED, catalog.SUGGESTION_ACCEPTED, catalog.SUGGESTION_DECLINED, catalog.BOOKING_CANCELLED,
]


def agenda_notifications():
    return Notification.objects.filter(type__in=AGENDA_TYPES)


class NotificationTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        frozen_clock(self)
        self.lab = space('Laboratório de Informática 2')
        self.other_lab = space('Laboratório de Informática 3')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.bruno = user_with('bruno@ifnmg.edu.br', *REQUESTER)
        self.carla = user_with('carla@ifnmg.edu.br', *REVIEWER)
        self.davi = user_with('davi@ifnmg.edu.br', *REVIEWER)

    def recipients(self, notice_type):
        return set(agenda_notifications().filter(type=notice_type).values_list('recipient__email', flat=True))

    def suggest(self, request, user=None):
        request.suggest(user or self.carla, self.other_lab, FRIDAY, time(14, 0), time(16, 0), 'O laboratório 2 recebe manutenção.')

    def only(self, notice_type):
        return agenda_notifications().get(type=notice_type)


class RequestedTests(NotificationTestCase):
    def test_new_request_notifies_each_active_reviewer_once(self):
        with self.case('analistas sim, solicitantes não'):
            request = submit(self.ana, self.lab)
            self.assertEqual(self.recipients(catalog.BOOKING_REQUESTED), {'carla@ifnmg.edu.br', 'davi@ifnmg.edu.br'})
            notification = agenda_notifications().filter(recipient=self.carla).get()
            self.assertEqual(notification.title, 'Nova solicitação de agendamento')
            self.assertEqual(
                notification.message,
                f'Ana solicitou o agendamento de Laboratório de Informática 2 em {request.schedule_text()}.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_review_detail', args=[request.pk]))
            self.assertTrue(notification.unread)
        with self.case('superadmin'):
            User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
            submit(self.ana, self.lab)
            self.assertIn('super@ifnmg.edu.br', self.recipients(catalog.BOOKING_REQUESTED))
        with self.case('o próprio pedido'):
            submit(self.carla, self.lab)
            self.assertEqual(self.recipients(catalog.BOOKING_REQUESTED), {'davi@ifnmg.edu.br'})
        with self.case('analista inativo'):
            User.objects.filter(pk=self.davi.pk).update(is_active=False)
            submit(self.ana, self.lab)
            self.assertEqual(self.recipients(catalog.BOOKING_REQUESTED), {'carla@ifnmg.edu.br'})
        with self.case('uma vez'):
            User.objects.filter(pk=self.carla.pk).update(is_superadmin=True)
            submit(self.ana, self.lab)
            self.assertEqual(agenda_notifications().filter(recipient=self.carla).count(), 1)

    def test_refused_request_notifies_nobody(self):
        with self.assertRaises(ValidationError):
            submit(self.ana, self.lab, start=time(18, 0), end=time(16, 0))
        with self.assertRaises(ValidationError):
            submit(self.bruno, self.lab, day=FRIDAY.replace(year=2020))
        self.assertFalse(agenda_notifications().exists())


class DecisionTests(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.request = submit(self.ana, self.lab)
        agenda_notifications().delete()

    def test_decisions_notify_the_requester(self):
        with self.case('aprovação'):
            self.request.approve(self.carla)
            self.assertEqual(self.recipients(catalog.BOOKING_APPROVED), {'ana@ifnmg.edu.br'})
            notification = self.only(catalog.BOOKING_APPROVED)
            self.assertEqual(notification.title, 'Agendamento aprovado')
            self.assertEqual(
                notification.message,
                f'A solicitação de agendamento de Laboratório de Informática 2 em {self.request.schedule_text()} foi aprovada.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_my_request', args=[self.request.pk]))
        with self.case('rejeição'):
            self.request.reject(self.carla, 'O espaço estará em manutenção.')
            notification = self.only(catalog.BOOKING_REJECTED)
            self.assertEqual(notification.recipient, self.ana)
            self.assertEqual(notification.title, 'Solicitação de agendamento rejeitada')
            self.assertEqual(
                notification.message,
                f'A solicitação de agendamento de Laboratório de Informática 2 em {self.request.schedule_text()} '
                'foi rejeitada. Veja o motivo na solicitação.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_my_request', args=[self.request.pk]))
        with self.case('sugestão'):
            self.suggest(self.request)
            notification = self.only(catalog.BOOKING_SUGGESTED)
            self.assertEqual(notification.recipient, self.ana)
            self.assertEqual(notification.title, 'Alternativa sugerida')
            self.assertEqual(
                notification.message,
                f'Para a solicitação de agendamento de Laboratório de Informática 2 em {self.request.schedule_text()}, '
                f'a alternativa é Laboratório de Informática 3 em {self.request.suggested_schedule_text()}. Aceite ou recuse.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_my_request', args=[self.request.pk]))

    def test_invalid_decisions_notify_nobody(self):
        with self.assertRaises(ValidationError):
            self.request.reject(self.carla, '  ')
        self.assertFalse(agenda_notifications().exists())
        self.request.approve(self.carla)
        agenda_notifications().delete()
        with self.assertRaises(ValidationError):
            self.request.approve(self.davi)
        with self.assertRaises(ValidationError):
            self.request.reject(self.davi, 'Motivo.')
        with self.assertRaises(ValidationError):
            self.suggest(self.request, self.davi)
        with self.assertRaises(ValidationError):
            BookingRequest.objects.get(pk=self.request.pk).reject(self.bruno, 'Sem permissão.')
        self.assertFalse(agenda_notifications().exists())

    def test_message_is_cut_at_the_notification_limit(self):
        long_space = space('Laboratório ' + 'L' * 180)
        request = submit(self.bruno, long_space)
        agenda_notifications().delete()
        request.approve(self.carla)
        self.assertLessEqual(len(self.only(catalog.BOOKING_APPROVED).message), MESSAGE_MAX_LENGTH)


class AnswerTests(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.request = submit(self.ana, self.lab)
        self.suggest(self.request)
        agenda_notifications().delete()

    def test_answers_notify_only_who_suggested(self):
        with self.case('aceite'):
            self.request.accept_suggestion(self.ana)
            self.assertEqual(self.recipients(catalog.SUGGESTION_ACCEPTED), {'carla@ifnmg.edu.br'})
            notification = self.only(catalog.SUGGESTION_ACCEPTED)
            self.assertEqual(notification.title, 'Alternativa aceita')
            self.assertEqual(
                notification.message,
                f'Ana aceitou a alternativa. Agendamento de Laboratório de Informática 3 em '
                f'{self.request.suggested_schedule_text()} aprovado.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_review_detail', args=[self.request.pk]))
        with self.case('recusa'):
            self.request.decline_suggestion(self.ana)
            self.assertEqual(self.recipients(catalog.SUGGESTION_DECLINED), {'carla@ifnmg.edu.br'})
            notification = self.only(catalog.SUGGESTION_DECLINED)
            self.assertEqual(notification.title, 'Alternativa recusada')
            self.assertEqual(
                notification.message,
                f'Ana recusou a alternativa de Laboratório de Informática 3 em {self.request.suggested_schedule_text()}. '
                'A solicitação foi encerrada sem agendamento.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_review_detail', args=[self.request.pk]))
        with self.case('respostas inválidas'):
            with self.assertRaises(ValidationError):
                self.request.accept_suggestion(self.bruno)
            with self.assertRaises(ValidationError):
                self.request.decline_suggestion(self.bruno)
            self.request.decline_suggestion(self.ana)
            agenda_notifications().delete()
            with self.assertRaises(ValidationError):
                self.request.accept_suggestion(self.ana)
            with self.assertRaises(ValidationError):
                self.request.decline_suggestion(self.ana)
            self.assertFalse(agenda_notifications().exists())

    def test_answer_falls_back_to_the_other_reviewers(self):
        with self.case('quem sugeriu está inativo'):
            User.objects.filter(pk=self.carla.pk).update(is_active=False)
            self.request.accept_suggestion(self.ana)
            self.assertEqual(self.recipients(catalog.SUGGESTION_ACCEPTED), {'davi@ifnmg.edu.br'})
        with self.case('quem sugeriu perdeu a permissão'):
            Role.objects.get(code='CARLA').permissions.remove(Permission.objects.get(code=permissions.BOOKING_REVIEW))
            self.request.decline_suggestion(self.ana)
            self.assertEqual(self.recipients(catalog.SUGGESTION_DECLINED), {'davi@ifnmg.edu.br'})


class CancelTests(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.request = submit(self.ana, self.lab)
        self.request.approve(self.carla)
        agenda_notifications().delete()

    def test_cancellation_notifies_the_other_side(self):
        with self.case('pelo solicitante'):
            self.request.cancel(self.ana)
            self.assertEqual(self.recipients(catalog.BOOKING_CANCELLED), {'carla@ifnmg.edu.br'})
            notification = self.only(catalog.BOOKING_CANCELLED)
            self.assertEqual(notification.title, 'Agendamento cancelado')
            self.assertEqual(
                notification.message,
                f'Ana cancelou o agendamento de Laboratório de Informática 2 em {self.request.schedule_text()}.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_review_detail', args=[self.request.pk]))
        with self.case('pelo analista'):
            self.request.cancel(self.davi, 'Laboratório em manutenção.')
            self.assertEqual(self.recipients(catalog.BOOKING_CANCELLED), {'ana@ifnmg.edu.br'})
            notification = self.only(catalog.BOOKING_CANCELLED)
            self.assertEqual(
                notification.message,
                f'O agendamento de Laboratório de Informática 2 em {self.request.schedule_text()} foi cancelado por Davi. '
                'Veja o motivo na solicitação.',
            )
            self.assertEqual(notification.target_url, reverse('agenda_my_request', args=[self.request.pk]))
        with self.case('recusado'):
            with self.assertRaises(ValidationError):
                self.request.cancel(self.bruno)
            self.assertFalse(agenda_notifications().filter(type=catalog.BOOKING_CANCELLED).exists())
