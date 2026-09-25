"""Telas da importação de ensalamento: acesso, envio, confirmação, descarte e auditoria."""

from datetime import date
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from accounts.permissions import (
    SPACE_ALLOCATION_IMPORT,
    SPACE_ALLOCATION_IMPORT_DELETE,
    SPACE_ALLOCATION_VIEW,
    USER_VIEW,
)
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from schedule.models import Allocation, Semester, Space
from schedule.tests.test_import import TEACHERS, SPACES, workbook_file
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

ROWS = len(TEACHERS) + len(SPACES) + 4


class ScreenTestCase(TestCase):
    def setUp(self):
        self.importer = self.user('importador@ifnmg.edu.br', SPACE_ALLOCATION_VIEW, SPACE_ALLOCATION_IMPORT)
        self.other = self.user('outro@ifnmg.edu.br', USER_VIEW)

    def user(self, email, *codes):
        code = email.partition('@')[0].upper()
        role = Role.objects.create_role(code=code, name=code, permissions=codes)
        return User.objects.register(email=email, name=code.capitalize(), role=role)

    def routes(self, pk=None):
        names = ['list', 'upload'] if pk is None else ['detail', 'confirm', 'discard']
        urls = [SPACE_ALLOCATION_IMPORT_SCREENS.url(name, *([pk] if pk else [])) for name in names]
        return urls if pk else [reverse('space_allocation_grid'), *urls]

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

    def test_without_the_permission_the_detail_is_refused(self):
        importation = self.importation()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk)).status_code, 403)

    def test_with_the_permission_the_detail_is_the_review_without_grid(self):
        importation = self.importation()
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'imports/detail.html')
        self.assertEqual(response.context['tabs'], [])
        self.assertNotContains(response, 'Grade do ensalamento')

    def test_with_the_permission_the_grid_opens(self):
        self.client.force_login(self.importer)
        self.assertEqual(self.client.get(reverse('space_allocation_grid')).status_code, 200)

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


class GridScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload(semester='2026/2')
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.url = reverse('space_allocation_grid')

    def grid(self, query='', today=date(2026, 9, 25)):
        with mock.patch('schedule.views.timezone.localdate', return_value=today):
            return self.client.get(self.url + query)

    def test_menu_opens_the_grid(self):
        response = self.grid()
        self.assertTemplateUsed(response, 'schedule/grid.html')
        self.assertContains(response, f'href="{self.url}"')
        self.assertContains(response, f'href="{SPACE_ALLOCATION_IMPORT_SCREENS.url("list")}"')

    def test_current_semester_is_the_default(self):
        response = self.grid()
        self.assertEqual(response.context['semester_code'], '2026/2')
        self.assertContains(response, 'QUÍMICA ORGÂNICA')
        self.assertContains(response, 'Semana da sala 1/13')

    def test_current_semester_without_import_is_offered_and_empty(self):
        response = self.grid(today=date(2027, 3, 1))
        self.assertEqual(response.context['semester_code'], '2027/1')
        self.assertContains(response, '<option value="2026/2">2026/2</option>', html=False)
        self.assertContains(response, 'Nenhum ensalamento importado no semestre 2027/1.')

    def test_imported_semester_in_the_url(self):
        response = self.grid('?semestre=2026/2', today=date(2027, 3, 1))
        self.assertEqual(response.context['semester_code'], '2026/2')
        self.assertTrue(response.context['week'].has_activities)

    def test_unknown_semester_falls_back_to_the_current(self):
        self.assertEqual(self.grid('?semestre=1999/1').context['semester_code'], '2026/2')

    def test_space_in_the_url(self):
        response = self.grid('?sala=HV 3')
        self.assertEqual(response.context['space'].name, 'HV 3')
        self.assertContains(response, 'Biologia')
        self.assertContains(response, 'Agroindústria, 1º ano A')
        self.assertContains(response, 'Érica')

    def test_unknown_space_falls_back_to_the_first(self):
        response = self.grid('?sala=Sala 99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['space'].name, '1/13')

    def test_occupation_counts(self):
        self.assertContains(self.grid(), '2 faixas ocupadas e 18 disponíveis na semana.')

    def test_today_is_marked(self):
        self.assertContains(self.grid(), 'Hoje')
        self.assertNotContains(self.grid(today=date(2026, 9, 26)), 'Hoje')

    def test_grid_changes_nothing(self):
        before = (Allocation.objects.count(), Space.objects.count(), Semester.objects.count())
        self.grid()
        self.grid(today=date(2027, 3, 1))
        self.assertEqual((Allocation.objects.count(), Space.objects.count(), Semester.objects.count()), before)


class DatedGridScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload(semester='2026/2')
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.url = reverse('space_allocation_grid')
        self.semester = Semester.objects.get(code='2026/2')

    def grid(self, query='', today=date(2026, 10, 7)):
        with mock.patch('schedule.views.timezone.localdate', return_value=today):
            return self.client.get(self.url + query)

    def define_period(self):
        self.semester.define_period(date(2026, 8, 5), date(2026, 12, 18))

    def test_without_period_the_typical_week_has_the_notice(self):
        response = self.grid()
        self.assertContains(response, 'Período do semestre 2026/2 não definido.')
        self.assertFalse(response.context['week'].is_dated)
        self.assertNotContains(response, 'Próxima semana')

    def test_current_semester_without_import_has_no_notice(self):
        self.assertNotContains(self.grid(today=date(2027, 3, 1)), 'não definido')

    def test_default_week_with_the_period(self):
        self.define_period()
        response = self.grid()
        self.assertNotContains(response, 'não definido')
        self.assertContains(response, '05/10/2026 a 09/10/2026')
        self.assertContains(response, 'QUÍMICA ORGÂNICA')
        self.assertContains(response, '2 faixas ocupadas e 18 disponíveis na semana.')

    def test_navigation_to_the_next_week(self):
        self.define_period()
        response = self.grid()
        following = '?semestre=2026%2F2&amp;sala=1%2F13&amp;semana=2026-10-12'
        self.assertContains(response, f'href="{self.url}{following}"')
        response = self.grid('?semestre=2026/2&sala=1/13&semana=2026-10-12')
        self.assertContains(response, '12/10/2026 a 16/10/2026')

    def test_any_date_of_the_week_opens_it(self):
        self.define_period()
        self.assertContains(self.grid('?semana=2026-10-14'), '12/10/2026 a 16/10/2026')

    def test_invalid_week_falls_back_to_the_default(self):
        self.define_period()
        for value in ['abc', '2026-13-01', '']:
            with self.subTest(value=value):
                response = self.grid(f'?semana={value}')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '05/10/2026 a 09/10/2026')

    def test_partial_first_week(self):
        self.define_period()
        response = self.grid('?semana=2026-08-03')
        self.assertContains(response, 'Fora do semestre')
        self.assertContains(response, '0 faixas ocupadas e 12 disponíveis na semana.')
        self.assertContains(response, '<span class="btn-secondary" aria-disabled="true">', count=1)

    def test_today_is_the_date(self):
        self.define_period()
        self.assertContains(self.grid(), '<span class="timetable-today">Hoje</span>Quarta', html=False)
        self.assertNotContains(self.grid('?semana=2026-10-12'), '<span class="timetable-today">Hoje</span>')

    def test_available_slot_is_empty_with_its_accessible_name(self):
        self.define_period()
        response = self.grid()
        self.assertContains(response, '<span class="sr-only">Segunda-feira, 05/10/2026, das 09:20 às 10:10, disponível</span>', html=False)
        self.assertNotContains(response, '>Disponível<')

    def test_grid_changes_nothing(self):
        self.define_period()
        before = (Allocation.objects.count(), Semester.objects.get(code='2026/2').start_date)
        self.grid()
        self.grid('?semana=2026-08-03')
        self.assertEqual((Allocation.objects.count(), Semester.objects.get(code='2026/2').start_date), before)


class ClashConfirmationTests(ScreenTestCase):
    def test_clash_does_not_block_the_confirmation(self):
        clash = {
            ('SEGUNDA ', '07:20 - 08:10', 0): 'Física (Viviane) (HV 3)',
            ('SEGUNDA ', '07:20 - 08:10', 1): 'Química (Elza) (HV 3)',
        }
        self.upload(uploaded=workbook_file(undergraduate=clash))
        importation = Import.objects.get()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        response = self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk), follow=True)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.CONCLUDED)
        self.assertEqual(response.redirect_chain[-1][0], SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))
        self.assertTemplateUsed(response, 'imports/detail.html')


class NavigationTests(ScreenTestCase):
    def test_item_appears_only_with_the_permission(self):
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list')), f'href="{reverse("space_allocation_grid")}"')
        self.client.force_login(self.other)
        response = self.client.get(reverse('user_list'))
        self.assertNotContains(response, 'Ensalamento')


class ViewPermissionTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.viewer = self.user('consulta@ifnmg.edu.br', SPACE_ALLOCATION_VIEW)
        self.only_importer = self.user('sograde@ifnmg.edu.br', SPACE_ALLOCATION_IMPORT)

    def test_viewer_opens_the_grid_without_the_import_screens(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('space_allocation_grid'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertEqual(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list')).status_code, 403)

    def test_importer_without_the_view_permission_is_refused_in_the_grid(self):
        self.client.force_login(self.only_importer)
        self.assertEqual(self.client.get(reverse('space_allocation_grid')).status_code, 403)

    def test_menu_points_to_the_imports_when_the_grid_is_not_allowed(self):
        self.client.force_login(self.only_importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, f'href="{SPACE_ALLOCATION_IMPORT_SCREENS.url("list")}"')
        self.assertNotContains(response, f'href="{reverse("space_allocation_grid")}"')

    def test_menu_points_to_the_grid_for_the_viewer(self):
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(reverse('space_allocation_grid')), f'href="{reverse("space_allocation_grid")}"')


class DeletionTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.remover = self.user('removedor@ifnmg.edu.br', SPACE_ALLOCATION_IMPORT, SPACE_ALLOCATION_IMPORT_DELETE)
        self.upload()
        self.importation = Import.objects.get()
        self.importation.discard(SPACE_ALLOCATION_IMPORT_SCREENS.definition, self.importer)
        self.url = SPACE_ALLOCATION_IMPORT_SCREENS.url('delete', self.importation.pk)

    def test_anonymous_is_sent_to_the_login_with_next(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('account_login')}?next={self.url}", fetch_redirect_response=False)

    def test_without_the_permission_the_deletion_is_refused(self):
        self.client.force_login(self.importer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Import.objects.exists())

    def test_without_csrf_the_deletion_is_refused(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.remover)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertTrue(Import.objects.exists())

    def test_with_the_permission_the_import_is_deleted(self):
        self.client.force_login(self.remover)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, 'excluída')
        self.assertFalse(Import.objects.exists())
        record = AuditLog.objects.filter(action=catalog.DELETE).get()
        self.assertEqual((record.user, record.resource), (self.remover, catalog.SPACE_ALLOCATION_IMPORT))

    def test_button_appears_only_with_the_permission(self):
        detail = SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', self.importation.pk)
        self.client.force_login(self.remover)
        self.assertContains(self.client.get(detail), self.url)
        self.client.force_login(self.importer)
        self.assertNotContains(self.client.get(detail), self.url)

    def test_pending_import_is_not_deleted(self):
        self.upload()
        pending = Import.objects.get(status=Import.Status.VALIDATED)
        self.client.force_login(self.remover)
        url = SPACE_ALLOCATION_IMPORT_SCREENS.url('delete', pending.pk)
        self.assertNotContains(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', pending.pk)), url)
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'não pode ser excluída')
        self.assertTrue(Import.objects.filter(pk=pending.pk).exists())


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


class SemesterPeriodScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload(semester='2026/2')
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.semester = Semester.objects.get(code='2026/2')
        self.url = reverse('semester_period', args=[self.semester.pk])
        self.viewer = self.user('consulta@ifnmg.edu.br', SPACE_ALLOCATION_VIEW)
        self.grid_url = f"{reverse('space_allocation_grid')}?semestre=2026%2F2"

    def post(self, start='2026-08-03', end='2026-12-18', client=None):
        return (client or self.client).post(self.url, {'start_date': start, 'end_date': end})

    def test_anonymous_is_sent_to_the_login_with_next(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('account_login')}?next={self.url}", fetch_redirect_response=False)

    def test_without_the_permission_it_is_refused(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.post().status_code, 403)
        self.semester.refresh_from_db()
        self.assertFalse(self.semester.has_period)

    def test_without_csrf_it_is_refused(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.importer)
        self.assertEqual(self.post(client=client).status_code, 403)

    def test_with_the_permission_the_period_is_defined_and_audited(self):
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(self.url, headers={'HX-Request': 'true'}), 'Semestre 2026/2.')
        response = self.post()
        self.assertRedirects(response, self.grid_url, fetch_redirect_response=False)
        self.semester.refresh_from_db()
        self.assertEqual((self.semester.start_date, self.semester.end_date), (date(2026, 8, 3), date(2026, 12, 18)))
        record = AuditLog.objects.get(resource=catalog.SEMESTER)
        self.assertEqual((record.user, record.action, record.resource_id), (self.importer, catalog.UPDATE, '2026/2'))
        self.assertContains(self.client.get(self.grid_url), 'Período do semestre 2026/2 definido.')

    def test_htmx_success_reloads_the_grid(self):
        self.client.force_login(self.importer)
        response = self.client.post(self.url, {'start_date': '2026-08-03', 'end_date': '2026-12-18'}, headers={'HX-Request': 'true'})
        self.assertEqual(response.headers['HX-Redirect'], self.grid_url)

    def test_refusal_is_a_form_error(self):
        self.client.force_login(self.importer)
        response = self.post(start='2026-12-18', end='2026-08-03')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O fim deve ser igual ou posterior ao início.')
        self.semester.refresh_from_db()
        self.assertFalse(self.semester.has_period)

    def test_current_period_is_the_initial_value(self):
        self.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(self.url), 'value="2026-08-03"')

    def test_button_appears_only_with_the_permission(self):
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(self.grid_url), f'href="{self.url}"')
        self.client.force_login(self.viewer)
        response = self.client.get(self.grid_url)
        self.assertContains(response, 'Período do semestre 2026/2 não definido.')
        self.assertNotContains(response, self.url)

    def test_unknown_semester_is_not_found(self):
        self.client.force_login(self.importer)
        self.assertEqual(self.client.get(reverse('semester_period', args=[9999])).status_code, 404)
