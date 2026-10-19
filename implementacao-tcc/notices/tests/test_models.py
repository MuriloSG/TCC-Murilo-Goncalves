from pathlib import Path

from django.test import SimpleTestCase, TestCase

from accounts.models import Role, User
from accounts.tests.roles import management_role, requester_role
from notices import catalog
from notices.models import (
    NoRecipients,
    Notification,
    UnknownDestination,
    UnknownNoticeType,
    resolve_recipients,
)


def make_user(email, role, active=True):
    user = User.objects.register(email, email.split('@')[0].title(), role)
    if not active:
        user.deactivate()
    return user


class CatalogTests(SimpleTestCase):
    def test_types_have_label_icon_and_tone(self):
        for code, data in catalog.TYPES.items():
            with self.subTest(code=code):
                self.assertTrue(data['label'])
                self.assertTrue(data['icon'])
                self.assertIn(data['tone'], {'info', 'success', 'warning', 'error'})

    def test_manual_types_are_the_three_of_the_publication(self):
        self.assertEqual(
            catalog.manual_choices(),
            [(catalog.INFORMATION, 'Informação'), (catalog.SUCCESS, 'Sucesso'), (catalog.WARNING, 'Aviso')],
        )
        self.assertFalse(catalog.is_manual(catalog.ROLE_CHANGED))


class MechanismIndependenceTests(SimpleTestCase):
    """O mecanismo não importa apps de domínio; o `audit` não é um deles."""

    def test_mechanism_modules_do_not_import_domain_apps(self):
        for name in ('catalog.py', 'models.py'):
            with self.subTest(module=name):
                source = (Path(__file__).resolve().parent.parent / name).read_text()
                self.assertNotIn('accounts', source)


class DeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = requester_role()
        cls.administrador = management_role()
        cls.ana = make_user('ana@ifnmg.edu.br', cls.docente)
        cls.bruno = make_user('bruno@ifnmg.edu.br', cls.docente)
        cls.carla = make_user('carla@ifnmg.edu.br', cls.administrador)

    def publish(self, recipients):
        return Notification.objects.publish(
            catalog.INFORMATION,
            'Nova versão do sistema',
            'Uma versão nova do sistema foi disponibilizada.',
            recipients,
        )

    def test_one_notification_per_recipient(self):
        reached = self.publish(User.objects.filter(is_active=True))
        self.assertEqual(reached, 3)
        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(Notification.objects.unread().count(), 3)
        self.assertEqual(
            set(Notification.objects.values_list('recipient', flat=True)),
            {self.ana.pk, self.bruno.pk, self.carla.pk},
        )
        self.assertEqual(
            set(Notification.objects.values_list('title', 'message', 'type')),
            {('Nova versão do sistema', 'Uma versão nova do sistema foi disponibilizada.', catalog.INFORMATION)},
        )

    def test_reading_is_individual(self):
        self.publish(User.objects.filter(is_active=True))
        Notification.objects.for_user(self.ana).first().mark_as_read()
        self.assertEqual(Notification.objects.for_user(self.ana).unread().count(), 0)
        self.assertEqual(Notification.objects.for_user(self.bruno).unread().count(), 1)

    def test_type_outside_the_catalog_is_refused(self):
        with self.assertRaises(UnknownNoticeType):
            Notification.objects.publish('INEXISTENTE', 'Título', 'Mensagem', [self.ana])
        self.assertEqual(Notification.objects.count(), 0)

    def test_publication_without_recipients_is_refused(self):
        with self.assertRaises(NoRecipients):
            self.publish(User.objects.none())
        self.assertEqual(Notification.objects.count(), 0)

    def test_most_recent_first(self):
        Notification.objects.notify(self.ana, catalog.INFORMATION, 'Primeira', 'Mensagem.')
        Notification.objects.notify(self.ana, catalog.INFORMATION, 'Segunda', 'Mensagem.')
        self.assertEqual(
            list(Notification.objects.for_user(self.ana).values_list('title', flat=True)),
            ['Segunda', 'Primeira'],
        )


class RecipientResolutionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = requester_role()
        cls.administrador = management_role()
        cls.ana = make_user('ana@ifnmg.edu.br', cls.docente)
        cls.bruno = make_user('bruno@ifnmg.edu.br', cls.docente)
        cls.carla = make_user('carla@ifnmg.edu.br', cls.administrador)
        cls.inativo = make_user('inativo@ifnmg.edu.br', cls.docente, active=False)

    def test_all_eligible_users_are_the_active_ones(self):
        self.assertEqual(
            set(resolve_recipients(catalog.ALL_USERS)),
            {self.ana, self.bruno, self.carla},
        )

    def test_role_reaches_only_its_active_users(self):
        self.assertEqual(
            set(resolve_recipients(catalog.ROLE, role=self.docente)),
            {self.ana, self.bruno},
        )

    def test_role_without_active_users_is_empty(self):
        vazio = Role.objects.create_role('COORDENACAO', 'Coordenação')
        self.assertEqual(list(resolve_recipients(catalog.ROLE, role=vazio)), [])

    def test_specific_users(self):
        self.assertEqual(
            set(resolve_recipients(catalog.USERS, users=[self.ana, self.carla])),
            {self.ana, self.carla},
        )

    def test_inactive_user_chosen_one_by_one_is_left_out(self):
        recipients = resolve_recipients(catalog.USERS, users=[self.ana, self.inativo])
        self.assertEqual(set(recipients), {self.ana})

    def test_destination_outside_the_catalog_is_refused(self):
        with self.assertRaises(UnknownDestination):
            resolve_recipients('INEXISTENTE')


class ReadingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = make_user('ana@ifnmg.edu.br', requester_role())

    def test_unread_count(self):
        for title in ('Uma', 'Outra', 'Mais uma'):
            Notification.objects.notify(self.ana, catalog.INFORMATION, title, 'Mensagem.')
        self.assertEqual(Notification.objects.unread_count(self.ana), 3)

    def test_mark_as_read_changes_the_state_once(self):
        notification = Notification.objects.notify(self.ana, catalog.INFORMATION, 'Uma', 'Mensagem.')
        self.assertTrue(notification.mark_as_read())
        read_at = notification.read_at
        self.assertFalse(notification.mark_as_read())
        self.assertEqual(notification.read_at, read_at)
        self.assertEqual(Notification.objects.unread_count(self.ana), 0)

    def test_mark_all_as_read(self):
        for title in ('Uma', 'Outra'):
            Notification.objects.notify(self.ana, catalog.INFORMATION, title, 'Mensagem.')
        self.assertEqual(Notification.objects.mark_all_as_read(self.ana), 2)
        self.assertEqual(Notification.objects.unread_count(self.ana), 0)
        self.assertEqual(Notification.objects.mark_all_as_read(self.ana), 0)
