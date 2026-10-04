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
    SPACE_CREATE,
    USER_VIEW,
)
from audit import catalog
from audit.models import AuditLog
from imports.models import Import
from schedule.models import Allocation, Semester, Space
from schedule.tests.test_import import PERIOD, TEACHERS, SPACES, workbook_file
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

ROWS = len(TEACHERS) + len(SPACES) + 4


class ScreenTestCase(TestCase):
    def setUp(self):
        self.importer = self.user('importador@ifnmg.edu.br', SPACE_ALLOCATION_VIEW, SPACE_ALLOCATION_IMPORT, SPACE_CREATE)
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
            {'own_semestre': semester, **PERIOD, 'file': uploaded if uploaded is not None else workbook_file()},
            follow=True,
        )


class AccessTests(ScreenTestCase):
    def test_with_the_permission_the_detail_is_the_review_without_grid(self):
        importation = self.importation()
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'imports/detail.html')
        self.assertEqual(response.context['tabs'], [])
        self.assertNotContains(response, 'Grade do ensalamento')

    def test_with_the_permission_the_list_opens(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Importações de ensalamento')

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

    def test_upload_without_the_semester_shows_the_error(self):
        self.client.force_login(self.importer)
        response = self.client.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'), {'file': workbook_file()},
        )
        self.assertContains(response, 'Informe o semestre da planilha.')
        self.assertFalse(Import.objects.exists())


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
        self.assertEqual(record.metadata['espacos_cadastrados'], 4)
        self.assertEqual(record.metadata['situacao'], 'CONCLUIDA')

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

    def test_space_filter_shows_only_the_useful_columns(self):
        response = self.detail('?linhas=salas')
        self.assertEqual(response.context['columns'], ['Célula', 'Nome'])

    def test_activity_filter_shows_the_activity_columns(self):
        response = self.detail('?linhas=atividades')
        self.assertEqual(
            response.context['columns'], ['Célula', 'Dia', 'Horário', 'Turma', 'Curso', 'Atividade'],
        )

    def test_only_the_activities_are_listed(self):
        response = self.detail('?linhas=atividades')
        self.assertEqual(response.context['page'].paginator.count, 4)
        self.assertIn('QUÍMICA ORGÂNICA (Elza) (1/13)', response.content.decode())

    def test_unknown_filter_is_not_found(self):
        self.assertEqual(self.detail('?linhas=inexistente').status_code, 404)

    def test_errors_filter_still_works(self):
        self.assertEqual(self.detail('?linhas=erros').context['page'].paginator.count, 0)


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
        self.assertContains(response, 'Agroindústria')
        self.assertContains(response, '1º ano A')
        self.assertContains(response, 'Érica')

    def test_unknown_space_falls_back_to_the_first(self):
        response = self.grid('?sala=Sala 99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['space'].name, '1/13')


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
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)
        response = self.grid()
        self.assertContains(response, 'Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre.')
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


class MonthGridScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload(semester='2026/2')
        self.client.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.url = reverse('space_allocation_grid')
        Semester.objects.get(code='2026/2').define_period(date(2026, 8, 5), date(2026, 12, 18))

    def grid(self, query='', today=date(2026, 9, 25)):
        with mock.patch('schedule.views.timezone.localdate', return_value=today):
            return self.client.get(self.url + query)

    def test_default_month_is_the_current_one(self):
        response = self.grid('?visao=mes')
        self.assertContains(response, 'Mês da sala 1/13')
        self.assertContains(response, 'Setembro de 2026')
        self.assertEqual(len(response.context['week'].days), 22)
        self.assertContains(response, '<span class="timetable-daynum">25</span> <span class="timetable-weekday">Sex</span>', html=False)
        self.assertContains(response, 'id="hoje"')

    def test_navigation_between_months(self):
        response = self.grid('?visao=mes')
        self.assertContains(response, 'visao=mes&amp;mes=2026-10')
        self.assertContains(response, 'visao=mes&amp;mes=2026-08')
        first = self.grid('?visao=mes&mes=2026-08')
        self.assertContains(first, 'Agosto de 2026')
        self.assertContains(first, 'Fora do semestre', count=2)

    def test_switching_from_week_to_month_opens_the_month_of_the_week(self):
        response = self.grid('?sala=HV 3&visao=mes&semana=2026-10-12&mes=')
        self.assertContains(response, 'Mês da sala HV 3')
        self.assertContains(response, 'Outubro de 2026')

    def test_switching_from_month_to_week_opens_its_first_week_or_today(self):
        response = self.grid('?visao=semana&mes=2026-10&semana=')
        self.assertContains(response, '28/09/2026 a 02/10/2026')
        current = self.grid('?visao=semana&mes=2026-09&semana=')
        self.assertContains(current, '21/09/2026 a 25/09/2026')

    def test_without_period_there_is_no_view_select(self):
        semester = Semester.objects.get(code='2026/2')
        Semester.objects.filter(pk=semester.pk).update(start_date=None, end_date=None)
        self.assertNotContains(self.grid(), 'name="visao"')

    def test_invalid_month_falls_back_to_the_default(self):
        for value in ['2026-13', 'abc', '2026-1']:
            with self.subTest(value=value):
                response = self.grid(f'?visao=mes&mes={value}')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Setembro de 2026')

    def test_month_without_period_shows_the_typical_week(self):
        semester = Semester.objects.get(code='2026/2')
        Semester.objects.filter(pk=semester.pk).update(start_date=None, end_date=None)
        response = self.grid('?visao=mes')
        self.assertContains(response, 'Período do semestre 2026/2 não definido.')
        self.assertContains(response, 'Semana da sala 1/13')


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


class UploadPeriodScreenTests(ScreenTestCase):
    def test_upload_modal_has_the_file_the_semester_and_the_period(self):
        self.client.force_login(self.importer)
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'))
        self.assertContains(response, 'name="file"')
        self.assertContains(response, 'name="own_semestre"')
        self.assertContains(response, 'Início do semestre')
        self.assertContains(response, 'Fim do semestre')
        self.assertContains(response, 'type="date"', count=2)
        self.assertNotContains(response, 'Início do semestre <span class="optional">')
        self.assertNotContains(response, 'Fim do semestre <span class="optional">')
