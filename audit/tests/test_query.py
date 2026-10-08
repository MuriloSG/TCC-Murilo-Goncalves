from datetime import datetime, timezone as time_zone
from unittest import mock

from django.test import Client, TestCase

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.context import Actor, acting_as
from audit.models import AuditLog

LIST_URL = '/auditoria/'


def at(day, hour=10):
    return datetime(2026, 9, day, hour, 0, tzinfo=time_zone.utc)


class AuditQueryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')

    def setUp(self):
        self.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=self.administrator)
        self.plain = User.objects.register(email='docente@ifnmg.edu.br', name='Docente', role=self.teacher)
        self.client.force_login(self.admin)

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def listed(self, query=''):
        """Registros exibidos, sem os acessos à própria auditoria, que tornariam a comparação instável."""
        entries = self.client.get(f'{LIST_URL}{query}').context['entries']
        return [entry for entry in entries if entry.resource != catalog.AUDIT]


class AuthorizationTests(AuditQueryTestCase):
    def test_user_with_permission_is_allowed(self):
        self.teacher.set_permissions([permissions.AUDIT_VIEW])
        entry = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION)
        client = self.client_for(self.plain)
        self.assertEqual(client.get(LIST_URL).status_code, 200)
        self.assertEqual(client.get(f'/auditoria/{entry.pk}/').status_code, 200)

    def test_consulting_the_audit_is_audited(self):
        self.client.get(LIST_URL)
        entry = AuditLog.objects.filter(action=catalog.ACCESS, resource=catalog.AUDIT).get()
        self.assertEqual(entry.user, self.admin)


class FilterTests(AuditQueryTestCase):
    def setUp(self):
        super().setUp()
        with mock.patch('django.utils.timezone.now', return_value=at(20)):
            self.old = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION, resource_id=self.admin.pk)
        with mock.patch('django.utils.timezone.now', return_value=at(24)):
            self.recent = AuditLog.objects.record(catalog.SEND, catalog.EMAIL, resource_id=7)
        with acting_as(Actor(user=self.plain, origin=catalog.INTERFACE)):
            self.by_teacher = AuditLog.objects.record(catalog.ACCESS, catalog.USER)

    def test_most_recent_first(self):
        listed = self.listed()
        self.assertEqual(listed, sorted(listed, key=lambda entry: (entry.created_at, entry.pk), reverse=True))
        self.assertEqual(listed[0], self.by_teacher)
        self.assertEqual(self.listed('?pagina=99')[-1], self.old)

    def test_filter_by_action(self):
        self.assertEqual(self.listed(f'?acao={catalog.SEND}'), [self.recent])

    def test_filter_by_resource(self):
        listed = self.listed(f'?recurso={catalog.AUTHENTICATION}')
        self.assertIn(self.old, listed)
        self.assertNotIn(self.recent, listed)

    def test_filter_by_origin(self):
        listed = self.listed(f'?origem={catalog.INTERFACE}')
        self.assertIn(self.by_teacher, listed)
        self.assertNotIn(self.recent, listed)

    def test_filter_by_resource_id(self):
        self.assertEqual(self.listed('?registro=7'), [self.recent])

    def test_filter_by_period(self):
        self.assertEqual(self.listed('?de=2026-09-20&ate=2026-09-20'), [self.old])
        self.assertNotIn(self.old, self.listed('?de=2026-09-24'))
        self.assertIn(self.recent, self.listed(f'?recurso={catalog.EMAIL}&de=2026-09-24&ate=2026-09-24'))

    def test_filter_by_user(self):
        self.assertEqual(self.listed(f'?usuario={self.plain.pk}'), [self.by_teacher])

    def test_combined_filters(self):
        self.assertEqual(self.listed(f'?acao={catalog.SEND}&recurso={catalog.AUTHENTICATION}'), [])

    def test_invalid_filters_are_ignored(self):
        query = f'?recurso={catalog.EMAIL}&acao=INEXISTENTE&de=trinta-de-fevereiro&usuario=999'
        self.assertEqual(self.listed(query), [self.recent])

    def test_empty_result_offers_clearing_the_filters(self):
        response = self.client.get(f'{LIST_URL}?registro=inexistente')
        self.assertContains(response, 'Nenhum registro de auditoria encontrado para os filtros.')
        self.assertContains(response, 'Limpar filtros')


class DetailTests(AuditQueryTestCase):
    def test_detail_shows_the_recorded_values(self):
        entry = AuditLog.objects.record(
            catalog.UPDATE, catalog.USER, resource_id=self.plain.pk,
            old_values={'name': 'Docente'}, new_values={'name': 'Docente Silva'},
            metadata={'rota': 'user_update'},
        )
        response = self.client.get(f'/auditoria/{entry.pk}/')
        self.assertContains(response, 'Alteração')
        self.assertContains(response, 'Usuários')
        self.assertContains(response, 'Nome')
        self.assertContains(response, 'Docente')
        self.assertContains(response, 'Docente Silva')
        self.assertContains(response, 'Rota')
        self.assertContains(response, 'user_update')
        self.assertContains(response, str(self.plain.pk))

    def test_detail_opens_as_a_modal_with_htmx_and_as_a_page_without_it(self):
        entry = AuditLog.objects.record(catalog.LOGIN, catalog.AUTHENTICATION)
        response = self.client.get(f'/auditoria/{entry.pk}/', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='modal')
        self.assertContains(response, 'Registro de auditoria')
        self.assertNotContains(response, 'Menu principal')
        response = self.client.get(f'/auditoria/{entry.pk}/')
        self.assertContains(response, 'Menu principal')
        self.assertContains(response, 'Registro de auditoria')

    def test_system_action_is_shown_without_user(self):
        entry = AuditLog.objects.record(catalog.SEND, catalog.EMAIL, resource_id=3)
        response = self.client.get(f'/auditoria/{entry.pk}/')
        self.assertContains(response, 'Sistema')
        self.assertContains(response, 'Não informado')
