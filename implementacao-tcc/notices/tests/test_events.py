from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import SimpleTestCase, TestCase
from config.testing import IsolatedCasesMixin

from accounts.models import AdministrativeContinuityViolation, User
from accounts.tests.roles import management_role, requester_role
from notices import catalog
from notices.events import announce, register
from notices.models import Notification


class RegistryTests(SimpleTestCase):
    def test_each_event_has_one_generator(self):
        with self.subTest('sem gerador'):
            with self.assertRaises(ImproperlyConfigured):
                announce('INEXISTENTE')
        with self.subTest('dois geradores'):
            def one(**context):
                return []

            def another(**context):
                return []

            register('EVENTO_DE_TESTE', one)
            register('EVENTO_DE_TESTE', one)
            with self.assertRaises(ImproperlyConfigured):
                register('EVENTO_DE_TESTE', another)


class RoleChangeEventTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = requester_role()
        cls.administrador = management_role()
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', cls.administrador)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', cls.docente)

    def test_role_change_notifies_the_affected_user(self):
        with self.case('usuário afetado'):
            self.bruno.change_role(self.administrador)
            notification = Notification.objects.for_user(self.bruno).get()
            self.assertEqual(notification.type, catalog.ROLE_CHANGED)
            self.assertEqual(notification.title, 'Perfil de acesso alterado')
            self.assertEqual(notification.message, 'Seu perfil passou a ser Gestão.')
            self.assertTrue(notification.unread)
            self.assertEqual(Notification.objects.count(), 1)
        with self.case('usuário inativo'):
            self.bruno.deactivate()
            self.bruno.change_role(self.administrador)
            self.assertEqual(Notification.objects.for_user(self.bruno).unread().count(), 1)

    def test_no_change_or_no_commit_notifies_nobody(self):
        with self.case('mesmo perfil'):
            self.bruno.change_role(self.docente)
            self.assertEqual(Notification.objects.count(), 0)
        with self.case('operação recusada'):
            with self.assertRaises(AdministrativeContinuityViolation):
                self.ana.change_role(self.docente)
            self.assertEqual(Notification.objects.count(), 0)
            self.assertEqual(User.objects.get(pk=self.ana.pk).role, self.administrador)
        with self.case('transação desfeita'):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.bruno.change_role(self.administrador)
                    raise RuntimeError('operação desfeita')
            self.assertEqual(Notification.objects.count(), 0)
            self.assertEqual(User.objects.get(pk=self.bruno.pk).role, self.docente)
