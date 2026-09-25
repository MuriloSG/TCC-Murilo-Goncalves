"""Telas da importação de ensalamento: acesso, envio, confirmação, descarte e auditoria."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from accounts.permissions import SPACE_ALLOCATION_IMPORT, USER_VIEW
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from schedule.models import Allocation, Semester, Space
from schedule.tests.test_import import TEACHERS, SPACES, workbook_file
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

ROWS = len(TEACHERS) + len(SPACES) + 4


class ScreenTestCase(TestCase):
    def setUp(self):
        self.importer = self.user('importador@ifnmg.edu.br', SPACE_ALLOCATION_IMPORT)
        self.other = self.user('outro@ifnmg.edu.br', USER_VIEW)

    def user(self, email, *codes):
        code = email.partition('@')[0].upper()
        role = Role.objects.create_role(code=code, name=code, permissions=codes)
        return User.objects.register(email=email, name=code.capitalize(), role=role)

    def routes(self, pk=None):
        names = ['list', 'upload'] if pk is None else ['detail', 'confirm', 'discard']
        return [SPACE_ALLOCATION_IMPORT_SCREENS.url(name, *([pk] if pk else [])) for name in names]

    def upload(self, semester='2026/1', uploaded=None):
        self.client.force_login(self.importer)
        return self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'),
            {'own_semestre': semester, 'file': uploaded if uploaded is not None else workbook_file()},
            follow=True,
        )


class AccessTests(ScreenTestCase):
    def test_anonymous_is_sent_to_the_login_with_next(self):
        for url in self.routes() + self.routes(1):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response, f"{reverse('account_login')}?next={url}", fetch_redirect_response=False,
                )

    def test_without_the_permission_every_route_is_refused(self):
        self.client.force_login(self.other)
        for url in self.routes():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.upload_as_other()

    def upload_as_other(self):
        self.client.force_login(self.other)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'),
            {'own_semestre': '2026/1', 'file': workbook_file()},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Import.objects.exists())

    def test_with_the_permission_the_list_opens(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Importações de ensalamento')

    def test_confirm_and_discard_without_csrf_are_refused(self):
        importation = self.importation()
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.importer)
        for url in (
            SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk),
            SPACE_ALLOCATION_IMPORT_SCREENS.url('discard', importation.pk),
        ):
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, 403)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.VALIDATED)

    def test_confirm_only_accepts_post(self):
        importation = self.importation()
        self.client.force_login(self.importer)
        url = SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk)
        self.assertEqual(self.client.get(url).status_code, 405)

    def importation(self):
        self.upload()
        return Import.objects.get()


class UploadTests(ScreenTestCase):
    def test_upload_creates_the_import_and_opens_the_preview(self):
        response = self.upload()
        importation = Import.objects.get()
        self.assertEqual(importation.kind, 'ENSALAMENTO')
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        self.assertEqual(importation.created_by, self.importer)
        self.assertEqual(importation.rows.count(), ROWS)
        self.assertEqual(response.redirect_chain[-1][0], SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))
        self.assertFalse(Allocation.objects.exists())

    def test_modal_has_the_file_and_the_semester(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'), headers={'hx-request': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="file"')
        self.assertContains(response, 'name="own_semestre"')
        self.assertContains(response, 'Semestre')

    def test_upload_without_the_semester_shows_the_error(self):
        self.client.force_login(self.importer)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'), {'file': workbook_file()},
        )
        self.assertContains(response, 'Informe o semestre da planilha.')
        self.assertFalse(Import.objects.exists())

    def test_upload_with_a_semester_outside_the_format_shows_the_error(self):
        self.client.force_login(self.importer)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'), {'own_semestre': '2026', 'file': workbook_file()},
        )
        self.assertContains(response, 'Informe o semestre no formato 2026/1.')
        self.assertFalse(Import.objects.exists())

    def test_there_is_no_template_to_download(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertNotContains(response, 'Baixar modelo')
        self.assertFalse(SPACE_ALLOCATION_IMPORT_SCREENS.has_template)
        with self.assertRaises(Exception):
            SPACE_ALLOCATION_IMPORT_SCREENS.url('template')


class ConfirmationScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload()
        self.importation = Import.objects.get()

    def test_preview_shows_the_rows_and_the_confirm_control(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', self.importation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Semestre')
        self.assertContains(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', self.importation.pk))

    def test_confirmation_applies_and_shows_the_totals(self):
        self.client.force_login(self.importer)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', self.importation.pk), follow=True,
        )
        self.importation.refresh_from_db()
        self.assertEqual(self.importation.status, Import.Status.CONCLUDED)
        self.assertEqual(self.importation.resolved_by, self.importer)
        self.assertContains(response, 'Importação do ensalamento concluída.')
        self.assertEqual(Allocation.objects.count(), 4)
        self.assertEqual(Semester.objects.get().code, '2026/1')

    def test_audit_of_the_confirmation_has_the_actor_and_the_summary(self):
        self.client.force_login(self.importer)
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', self.importation.pk))
        record = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk')
        self.assertEqual(record.user, self.importer)
        self.assertEqual(record.resource, catalog.SPACE_ALLOCATION_IMPORT)
        self.assertEqual(record.origin, catalog.INTERFACE)
        self.assertEqual(record.metadata['semestre'], '2026/1')
        self.assertEqual(record.metadata['cadastrados'], ROWS)
        self.assertEqual(record.metadata['situacao'], 'CONCLUIDA')

    def test_no_audit_record_of_the_created_entities(self):
        self.client.force_login(self.importer)
        before = AuditLog.objects.latest('pk').pk
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', self.importation.pk))
        recorded = AuditLog.objects.filter(pk__gt=before)
        self.assertEqual(
            sorted(set(recorded.values_list('resource', flat=True))), [catalog.SPACE_ALLOCATION_IMPORT],
        )
        self.assertEqual(recorded.filter(action=catalog.IMPORT).count(), 1)

    def test_discard_keeps_the_domain_untouched(self):
        self.client.force_login(self.importer)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('discard', self.importation.pk), follow=True,
        )
        self.importation.refresh_from_db()
        self.assertEqual(self.importation.status, Import.Status.DISCARDED)
        self.assertEqual(self.importation.resolved_by, self.importer)
        self.assertContains(response, 'descartada')
        self.assertFalse(Allocation.objects.exists())
        self.assertFalse(Space.objects.exists())

    def test_history_lists_the_import(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, 'ensalamento.xlsx')


class RowFilterTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload()
        self.importation = Import.objects.get()
        self.client.force_login(self.importer)

    def detail(self, query=''):
        return self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', self.importation.pk) + query)

    def test_preview_offers_the_filters_with_their_totals(self):
        content = self.detail().content.decode()
        self.assertIn(f'Salas ({len(SPACES)})', content)
        self.assertIn(f'Docentes ({len(TEACHERS)})', content)
        self.assertIn('Atividades (4)', content)

    def test_only_the_spaces_are_listed(self):
        response = self.detail('?linhas=salas')
        self.assertEqual(response.context['page'].paginator.count, len(SPACES))
        content = response.content.decode()
        for raw in SPACES:
            self.assertIn(raw, content)
        self.assertNotIn('Viviane', content)

    def test_space_row_shows_the_name_that_will_be_created(self):
        content = self.detail('?linhas=salas').content.decode()
        self.assertIn('(1/13)', content)
        self.assertIn('Nome: 1/13', content)

    def test_space_filter_shows_only_the_useful_columns(self):
        response = self.detail('?linhas=salas')
        self.assertEqual(response.context['columns'], ['Célula', 'Nome'])
        content = response.content.decode()
        self.assertNotIn('<th scope="col">Turma</th>', content)
        self.assertNotIn('<th scope="col">Horário</th>', content)

    def test_activity_filter_shows_the_activity_columns(self):
        response = self.detail('?linhas=atividades')
        self.assertEqual(
            response.context['columns'], ['Célula', 'Dia', 'Horário', 'Turma', 'Curso', 'Atividade'],
        )

    def test_semester_appears_once_in_the_summary(self):
        content = self.detail().content.decode()
        self.assertIn('<dt>Semestre</dt><dd>2026/1</dd>', content)

    def test_only_the_activities_are_listed(self):
        response = self.detail('?linhas=atividades')
        self.assertEqual(response.context['page'].paginator.count, 4)
        self.assertIn('QUÍMICA ORGÂNICA (Elza) (1/13)', response.content.decode())

    def test_unknown_filter_is_not_found(self):
        self.assertEqual(self.detail('?linhas=inexistente').status_code, 404)

    def test_errors_filter_still_works(self):
        self.assertEqual(self.detail('?linhas=erros').context['page'].paginator.count, 0)

    def test_filters_are_offered_in_a_select_with_the_chosen_one_selected(self):
        content = self.detail('?linhas=salas').content.decode()
        self.assertIn('<select name="linhas"', content)
        self.assertIn(f'<option value="salas" selected>Salas ({len(SPACES)})</option>', content)
        self.assertIn('<option value="">Todas as linhas (', content)


class NavigationTests(ScreenTestCase):
    def test_item_appears_only_with_the_permission(self):
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list')), 'Ensalamento')
        self.client.force_login(self.other)
        response = self.client.get(reverse('user_list'))
        self.assertNotContains(response, 'Ensalamento')


class UserCreationTests(ScreenTestCase):
    def test_import_never_creates_a_user(self):
        before = set(User.objects.values_list('pk', flat=True))
        self.upload()
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.assertEqual(set(User.objects.values_list('pk', flat=True)), before)

    def test_teacher_without_a_matching_user_does_not_block_the_import(self):
        self.upload()
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        importation = Import.objects.get()
        self.assertEqual(importation.status, Import.Status.CONCLUDED)
        self.assertFalse(User.objects.filter(username__in=TEACHERS).exists())
        self.assertEqual(Allocation.objects.count(), 4)
