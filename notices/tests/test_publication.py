from django.test import TestCase

from accounts.models import Role, User
from audit import catalog as audit_catalog
from audit.context import Actor, acting_as
from audit.models import AuditLog
from notices import catalog
from notices.models import NoRecipients, Notification, NotPublishedManually


class PublicationAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = Role.objects.get(code='DOCENTE')
        cls.administrador = Role.objects.get(code='ADMINISTRADOR')
        cls.ana = User.objects.register('ana@ifnmg.edu.br', 'Ana', cls.administrador)
        cls.bruno = User.objects.register('bruno@ifnmg.edu.br', 'Bruno', cls.docente)
        cls.carla = User.objects.register('carla@ifnmg.edu.br', 'Carla', cls.docente)

    def publish(self, destination, **kwargs):
        with acting_as(Actor(user=self.ana, origin=audit_catalog.INTERFACE)):
            return Notification.objects.publish_manually(
                catalog.NOTICE,
                'Nova versão do sistema',
                'Uma versão nova do sistema foi disponibilizada.',
                destination,
                **kwargs,
            )

    def records(self):
        return AuditLog.objects.filter(resource=audit_catalog.NOTICE)

    def test_publication_records_one_entry_with_the_reached_count(self):
        reached = self.publish(catalog.ALL_USERS)
        self.assertEqual(reached, 3)
        self.assertEqual(self.records().count(), 1)
        record = self.records().get()
        self.assertEqual(record.action, audit_catalog.PUBLISH)
        self.assertEqual(record.user, self.ana)
        self.assertEqual(record.origin, audit_catalog.INTERFACE)
        self.assertEqual(record.metadata['destinatarios'], 3)
        self.assertEqual(record.metadata['destino'], catalog.ALL_USERS)
        self.assertEqual(record.metadata['tipo'], catalog.NOTICE)
        self.assertEqual(record.metadata['titulo'], 'Nova versão do sistema')

    def test_recipients_are_resolved_at_the_publication(self):
        self.bruno.deactivate()
        self.assertEqual(self.publish(catalog.ROLE, role=self.docente), 1)
        self.assertEqual(self.records().get().metadata['destinatarios'], 1)

    def test_refused_publication_records_nothing(self):
        vazio = Role.objects.create_role('COORDENACAO', 'Coordenação')
        with self.assertRaises(NoRecipients):
            self.publish(catalog.ROLE, role=vazio)
        self.assertEqual(self.records().count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_type_not_published_manually_is_refused(self):
        with acting_as(Actor(user=self.ana, origin=audit_catalog.INTERFACE)):
            with self.assertRaises(NotPublishedManually):
                Notification.objects.publish_manually(
                    catalog.ROLE_CHANGED,
                    'Perfil alterado',
                    'Mensagem.',
                    catalog.ALL_USERS,
                )
        self.assertEqual(self.records().count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_delivery_without_publication_records_nothing(self):
        before = AuditLog.objects.count()
        Notification.objects.notify(self.bruno, catalog.ROLE_CHANGED, 'Perfil alterado', 'Mensagem.')
        self.assertEqual(AuditLog.objects.count(), before)

    def test_reading_is_not_audited(self):
        self.publish(catalog.ALL_USERS)
        before = AuditLog.objects.count()
        Notification.objects.for_user(self.bruno).first().mark_as_read()
        Notification.objects.mark_all_as_read(self.carla)
        self.assertEqual(AuditLog.objects.count(), before)
