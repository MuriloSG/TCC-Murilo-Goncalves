from django.test import SimpleTestCase, TestCase

from accounts.models import Role, User
from audit import catalog
from audit.context import Actor, acting_as, acting_from_import, current_actor
from audit.models import AuditLog, AuditLogProtected, UnknownAuditCode, sanitize


class SanitizeTests(SimpleTestCase):
    def test_sensitive_fields_are_dropped(self):
        values = {
            'email': 'ana@ifnmg.edu.br',
            'password': 'segredo',
            'senha': 'segredo',
            'reset_token': 'abc',
            'api_key': 'abc',
            'password_hash': 'abc',
            'chave': 'abc',
        }
        self.assertEqual(sanitize(values), {'email': 'ana@ifnmg.edu.br'})

    def test_empty_values(self):
        self.assertEqual(sanitize(None), {})


class ActorTests(SimpleTestCase):
    def test_default_actor_is_the_system(self):
        actor = current_actor()
        self.assertIsNone(actor.user)
        self.assertEqual(actor.origin, catalog.SYSTEM)

    def test_acting_as_is_restored(self):
        with acting_as(Actor(user=None, ip_address='10.0.0.1', origin=catalog.INTERFACE)):
            self.assertEqual(current_actor().ip_address, '10.0.0.1')
        self.assertEqual(current_actor(), Actor())

    def test_import_origin_keeps_the_executor(self):
        with acting_as(Actor(user='ana', ip_address='10.0.0.1', origin=catalog.INTERFACE)):
            with acting_from_import('ana'):
                self.assertEqual(current_actor().origin, catalog.IMPORTED)
                self.assertEqual(current_actor().user, 'ana')
                self.assertEqual(current_actor().ip_address, '10.0.0.1')
            self.assertEqual(current_actor().origin, catalog.INTERFACE)


class RecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.user = User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=cls.teacher)

    def test_record_uses_the_actor_of_the_context(self):
        actor = Actor(user=self.user, ip_address='192.168.0.10', user_agent='Firefox', origin=catalog.INTERFACE)
        with acting_as(actor):
            entry = AuditLog.objects.record(
                catalog.UPDATE, catalog.USER, resource_id=25,
                old_values={'name': 'Ana'}, new_values={'name': 'Ana Souza'},
            )
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.action, catalog.UPDATE)
        self.assertEqual(entry.resource, catalog.USER)
        self.assertEqual(entry.resource_id, '25')
        self.assertEqual(entry.old_values, {'name': 'Ana'})
        self.assertEqual(entry.new_values, {'name': 'Ana Souza'})
        self.assertEqual(entry.ip_address, '192.168.0.10')
        self.assertEqual(entry.user_agent, 'Firefox')
        self.assertEqual(entry.origin, catalog.INTERFACE)
        self.assertIsNotNone(entry.created_at)

    def test_record_without_actor_is_from_the_system(self):
        entry = AuditLog.objects.record(catalog.SEND, catalog.EMAIL, resource_id=7)
        self.assertIsNone(entry.user)
        self.assertEqual(entry.origin, catalog.SYSTEM)
        self.assertIsNone(entry.ip_address)
        self.assertEqual(entry.user_agent, '')

    def test_record_refuses_unknown_codes(self):
        with self.assertRaises(UnknownAuditCode):
            AuditLog.objects.record('APAGAR_TUDO', catalog.USER)
        with self.assertRaises(UnknownAuditCode):
            AuditLog.objects.record(catalog.CREATE, 'RESERVA')

    def test_record_drops_sensitive_fields(self):
        entry = AuditLog.objects.record(
            catalog.UPDATE, catalog.USER,
            new_values={'email': 'ana@ifnmg.edu.br', 'password': 'segredo'},
            metadata={'token': 'abc', 'rota': 'user_update'},
        )
        self.assertEqual(entry.new_values, {'email': 'ana@ifnmg.edu.br'})
        self.assertEqual(entry.metadata, {'rota': 'user_update'})

    def test_new_action_needs_only_the_catalog(self):
        catalog.ACTION_LABELS['REVISAR'] = 'Revisão'
        try:
            entry = AuditLog.objects.record('REVISAR', catalog.USER)
        finally:
            del catalog.ACTION_LABELS['REVISAR']
        self.assertEqual(AuditLog.objects.get(pk=entry.pk).action, 'REVISAR')

    def test_labels_come_from_the_catalog(self):
        entry = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION)
        self.assertEqual(entry.action_label, 'Entrada')
        self.assertEqual(entry.resource_label, 'Autenticação')
        self.assertEqual(entry.origin_label, 'Sistema')

    def test_most_recent_first(self):
        first = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION)
        second = AuditLog.objects.record(catalog.LOGOUT, catalog.AUTHENTICATION)
        listed = list(AuditLog.objects.filter(resource=catalog.AUTHENTICATION))
        self.assertEqual(listed, [second, first])


class IntegrityTests(TestCase):
    def setUp(self):
        self.entry = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION)

    def test_saving_again_is_refused(self):
        self.entry.action = catalog.LOGOUT
        with self.assertRaises(AuditLogProtected):
            self.entry.save()
        self.assertEqual(AuditLog.objects.get(pk=self.entry.pk).action, catalog.LOGIN)

    def test_queryset_update_is_refused(self):
        with self.assertRaises(AuditLogProtected):
            AuditLog.objects.filter(pk=self.entry.pk).update(action=catalog.LOGOUT)
        self.assertEqual(AuditLog.objects.get(pk=self.entry.pk).action, catalog.LOGIN)

    def test_delete_is_refused(self):
        with self.assertRaises(AuditLogProtected):
            self.entry.delete()
        with self.assertRaises(AuditLogProtected):
            AuditLog.objects.filter(pk=self.entry.pk).delete()
        self.assertTrue(AuditLog.objects.filter(pk=self.entry.pk).exists())
