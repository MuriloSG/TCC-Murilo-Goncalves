from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from accounts import notifications
from accounts.models import AdministrativeContinuityViolation, Role, User
from notices import catalog
from notices.events import Delivery, announce, register
from notices.models import Notification


class RegistryTests(SimpleTestCase):
    def test_event_without_generator_is_refused(self):
        with self.assertRaises(ImproperlyConfigured):
            announce('INEXISTENTE')

    def test_two_generators_for_the_same_event_are_refused(self):
        def one(**context):
            return []

        def another(**context):
            return []

        register('EVENTO_DE_TESTE', one)
        register('EVENTO_DE_TESTE', one)
        with self.assertRaises(ImproperlyConfigured):
            register('EVENTO_DE_TESTE', another)

    def test_delivery_has_an_optional_target(self):
        delivery = Delivery(recipient=None, type=catalog.INFORMATION, title='Título', message='Mensagem.')
        self.assertEqual(delivery.target_url, '')


class RoleChangeEventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = Role.objects.get(code='DOCENTE')
        cls.administrador = Role.objects.get(code='ADMINISTRADOR')
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', cls.administrador)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', cls.docente)

    def test_role_change_notifies_the_affected_user(self):
        self.bruno.change_role(self.administrador)
        notification = Notification.objects.for_user(self.bruno).get()
        self.assertEqual(notification.type, catalog.ROLE_CHANGED)
        self.assertEqual(notification.title, 'Perfil de acesso alterado')
        self.assertEqual(notification.message, 'Seu perfil passou a ser Administrador.')
        self.assertTrue(notification.unread)
        self.assertEqual(Notification.objects.count(), 1)

    def test_role_change_to_the_same_role_notifies_nobody(self):
        self.bruno.change_role(self.docente)
        self.assertEqual(Notification.objects.count(), 0)

    def test_refused_operation_notifies_nobody(self):
        with self.assertRaises(AdministrativeContinuityViolation):
            self.ana.change_role(self.docente)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(User.objects.get(pk=self.ana.pk).role, self.administrador)

    def test_undone_transaction_leaves_no_notification(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.bruno.change_role(self.administrador)
                raise RuntimeError('operação desfeita')
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(User.objects.get(pk=self.bruno.pk).role, self.docente)

    def test_inactive_user_is_notified(self):
        self.bruno.deactivate()
        self.bruno.change_role(self.administrador)
        self.assertEqual(Notification.objects.for_user(self.bruno).unread().count(), 1)

    def test_event_is_registered_by_the_owning_app(self):
        self.assertEqual(notifications.ROLE_CHANGED, 'PERFIL_ALTERADO')
        self.assertEqual(
            [delivery.recipient for delivery in notifications.role_changed(self.bruno, self.administrador)],
            [self.bruno],
        )
