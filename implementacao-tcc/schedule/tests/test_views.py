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
from config.testing import IsolatedCasesMixin
from imports.models import Import
from imports.tests.worker import poll, run_worker
from imports.workbook import XLSX_CONTENT_TYPE
from schedule.models import Allocation, Semester, Space
from schedule.sheets import TEMPLATE_FILE
from schedule.tests.test_import import PERIOD, TEACHERS, SPACES, workbook_file
from schedule.views import SPACE_ALLOCATION_IMPORT_SCREENS

ROWS = len(TEACHERS) + len(SPACES) + 4


class ScreenTestCase(IsolatedCasesMixin, TestCase):
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

    def post(self, url, data=None, follow=False):
        """Envia o POST e deixa o worker executar a operação pedida antes de abrir a página seguinte."""
        response = self.client.post(url, data or {})
        run_worker(SPACE_ALLOCATION_IMPORT_SCREENS.definition)
        if not follow or response.status_code != 302:
            return response
        poll(self.client, response.url)
        page = self.client.get(response.url, follow=True)
        page.redirect_chain = [(response.url, response.status_code), *page.redirect_chain]
        return page

    def upload(self, semester='2026/1', uploaded=None):
        self.client.force_login(self.importer)
        return self.post(
            SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'),
            {'own_semestre': semester, **PERIOD, 'file': uploaded if uploaded is not None else workbook_file()},
            follow=True,
        )


class UploadTests(ScreenTestCase):
    def test_upload_creates_the_import_and_opens_the_preview(self):
        self.client.force_login(self.importer)
        response = self.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('upload'), {'file': workbook_file()})
        self.assertContains(response, 'Informe o semestre da planilha.')
        self.assertFalse(Import.objects.exists())

        response = self.upload()
        importation = Import.objects.get()
        self.assertEqual(
            (importation.kind, importation.status, importation.created_by, importation.rows.count()),
            ('ENSALAMENTO', Import.Status.VALIDATED, self.importer, ROWS),
        )
        detail = SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk)
        self.assertEqual(response.redirect_chain[-1][0], detail)
        self.assertFalse(Allocation.objects.exists())
        response = self.client.get(detail)
        self.assertTemplateUsed(response, 'imports/detail.html')
        self.assertEqual(response.context['tabs'], [])
        self.assertNotContains(response, 'Grade do ensalamento')
        self.assertContains(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk))
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, 'Importações de ensalamento')
        self.assertContains(response, 'ensalamento.xlsx')


class TemplateTests(ScreenTestCase):
    def test_template_downloads_the_blank_workbook_and_audits(self):
        self.client.force_login(self.importer)
        self.assertContains(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('list')), 'Baixar modelo')
        response = self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('template'))
        self.assertEqual(response['Content-Type'], XLSX_CONTENT_TYPE)
        self.assertIn('modelo-importacao-ensalamento.xlsx', response['Content-Disposition'])
        self.assertEqual(response.content, TEMPLATE_FILE.read_bytes())
        record = AuditLog.objects.get(action=catalog.EXPORT)
        self.assertEqual((record.user, record.resource), (self.importer, catalog.SPACE_ALLOCATION_IMPORT))


class ConfirmationScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload()
        self.importation = Import.objects.get()

    def test_confirmation_applies_audits_and_shows_the_totals(self):
        response = self.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', self.importation.pk), follow=True)
        self.importation.refresh_from_db()
        self.assertEqual((self.importation.status, self.importation.resolved_by), (Import.Status.CONCLUDED, self.importer))
        self.assertContains(response, 'Importação do ensalamento concluída.')
        self.assertEqual(Allocation.objects.count(), 4)
        self.assertEqual(Semester.objects.get().code, '2026/1')
        record = AuditLog.objects.filter(action=catalog.IMPORT).latest('pk')
        self.assertEqual(
            (record.user, record.resource, record.origin), (self.importer, catalog.SPACE_ALLOCATION_IMPORT, catalog.INTERFACE),
        )
        self.assertEqual(
            {key: record.metadata[key] for key in ('semestre', 'cadastrados', 'espacos_cadastrados', 'situacao')},
            {'semestre': '2026/1', 'cadastrados': ROWS, 'espacos_cadastrados': 4, 'situacao': 'CONCLUIDA'},
        )

    def test_discard_keeps_the_domain_untouched(self):
        response = self.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('discard', self.importation.pk), follow=True)
        self.importation.refresh_from_db()
        self.assertEqual((self.importation.status, self.importation.resolved_by), (Import.Status.DISCARDED, self.importer))
        self.assertContains(response, 'descartada')
        self.assertFalse(Allocation.objects.exists())
        self.assertFalse(Space.objects.exists())

    def test_row_filters_list_their_rows_and_columns(self):
        def detail(query=''):
            return self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', self.importation.pk) + query)

        content = detail().content.decode()
        for label in (f'Salas ({len(SPACES)})', f'Docentes ({len(TEACHERS)})', 'Atividades (4)'):
            self.assertIn(label, content)
        response = detail('?linhas=salas')
        self.assertEqual(response.context['page'].paginator.count, len(SPACES))
        self.assertEqual(response.context['columns'], ['Célula', 'Nome'])
        content = response.content.decode()
        for raw in SPACES:
            self.assertIn(raw, content)
        self.assertNotIn('Viviane', content)
        response = detail('?linhas=atividades')
        self.assertEqual(response.context['page'].paginator.count, 4)
        self.assertEqual(response.context['columns'], ['Célula', 'Dia', 'Horário', 'Turma', 'Curso', 'Atividade'])
        self.assertIn('QUÍMICA ORGÂNICA (Elza) (1/13)', response.content.decode())
        self.assertEqual(detail('?linhas=erros').context['page'].paginator.count, 0)
        self.assertEqual(detail('?linhas=inexistente').status_code, 404)


class GridScreenTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.upload(semester='2026/2')
        self.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', Import.objects.get().pk))
        self.url = reverse('space_allocation_grid')
        self.semester = Semester.objects.get(code='2026/2')

    def grid(self, query='', today=date(2026, 9, 25)):
        with mock.patch('schedule.views.timezone.localdate', return_value=today):
            return self.client.get(self.url + query)

    def without_period(self):
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)

    def test_semester_and_space_come_from_the_url_or_the_default(self):
        response = self.grid()
        self.assertEqual(response.context['semester_code'], '2026/2')
        self.assertContains(response, 'QUÍMICA ORGÂNICA')
        self.assertContains(response, 'Semana da sala 1/13')
        response = self.grid(today=date(2027, 3, 1))
        self.assertEqual(response.context['semester_code'], '2027/1')
        self.assertContains(response, '<option value="2026/2">2026/2</option>', html=False)
        self.assertContains(response, 'Nenhum ensalamento importado no semestre 2027/1.')
        self.assertNotContains(response, 'não definido')
        response = self.grid('?semestre=2026/2', today=date(2027, 3, 1))
        self.assertEqual(response.context['semester_code'], '2026/2')
        self.assertTrue(response.context['week'].has_activities)
        self.assertEqual(self.grid('?semestre=1999/1').context['semester_code'], '2026/2')
        response = self.grid('?sala=HV 3')
        self.assertEqual(response.context['space'].name, 'HV 3')
        for text in ('Biologia', 'Agroindústria', '1º ano A', 'Érica'):
            self.assertContains(response, text)
        self.assertEqual(self.grid('?sala=Sala 99').context['space'].name, '1/13')

    def test_dated_week(self):
        with self.case('sem período, semana típica com aviso'):
            self.without_period()
            response = self.grid(today=date(2026, 10, 7))
            self.assertContains(response, 'Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre.')
            self.assertFalse(response.context['week'].is_dated)
            self.assertNotContains(response, 'Próxima semana')
        self.semester.define_period(date(2026, 8, 5), date(2026, 12, 18))
        response = self.grid(today=date(2026, 10, 7))
        self.assertNotContains(response, 'não definido')
        self.assertContains(response, '05/10/2026 a 09/10/2026')
        self.assertContains(response, 'QUÍMICA ORGÂNICA')
        self.assertContains(response, '2 faixas ocupadas e 18 disponíveis na semana.')
        self.assertContains(response, f'href="{self.url}?semestre=2026%2F2&amp;sala=1%2F13&amp;semana=2026-10-12"')
        self.assertContains(self.grid('?semestre=2026/2&sala=1/13&semana=2026-10-12'), '12/10/2026 a 16/10/2026')
        for value in ['abc', '2026-13-01', '']:
            with self.subTest(semana=value):
                self.assertContains(self.grid(f'?semana={value}', today=date(2026, 10, 7)), '05/10/2026 a 09/10/2026')
        response = self.grid('?semana=2026-08-03')
        self.assertContains(response, 'Fora do semestre')
        self.assertContains(response, '0 faixas ocupadas e 12 disponíveis na semana.')

    def test_month_view(self):
        with self.case('sem período não há mês'):
            self.without_period()
            self.assertNotContains(self.grid(), 'name="visao"')
            response = self.grid('?visao=mes')
            self.assertContains(response, 'Período do semestre 2026/2 não definido.')
            self.assertContains(response, 'Semana da sala 1/13')
        self.semester.define_period(date(2026, 8, 5), date(2026, 12, 18))
        response = self.grid('?visao=mes')
        self.assertContains(response, 'Mês da sala 1/13')
        self.assertContains(response, 'Setembro de 2026')
        self.assertEqual(len(response.context['week'].days), 22)
        self.assertContains(response, 'id="hoje"')
        self.assertContains(response, 'visao=mes&amp;mes=2026-10')
        self.assertContains(response, 'visao=mes&amp;mes=2026-08')
        first = self.grid('?visao=mes&mes=2026-08')
        self.assertContains(first, 'Agosto de 2026')
        self.assertContains(first, 'Fora do semestre', count=2)
        response = self.grid('?sala=HV 3&visao=mes&semana=2026-10-12&mes=')
        self.assertContains(response, 'Mês da sala HV 3')
        self.assertContains(response, 'Outubro de 2026')
        self.assertContains(self.grid('?visao=semana&mes=2026-10&semana='), '28/09/2026 a 02/10/2026')
        self.assertContains(self.grid('?visao=semana&mes=2026-09&semana='), '21/09/2026 a 25/09/2026')
        for value in ['2026-13', 'abc', '2026-1']:
            with self.subTest(mes=value):
                self.assertContains(self.grid(f'?visao=mes&mes={value}'), 'Setembro de 2026')


class ClashConfirmationTests(ScreenTestCase):
    def test_clash_does_not_block_the_confirmation(self):
        clash = {
            ('SEGUNDA ', '07:20 - 08:10', 0): 'Física (Viviane) (HV 3)',
            ('SEGUNDA ', '07:20 - 08:10', 1): 'Química (Elza) (HV 3)',
        }
        self.upload(uploaded=workbook_file(undergraduate=clash))
        importation = Import.objects.get()
        self.assertEqual(importation.status, Import.Status.VALIDATED)
        response = self.post(SPACE_ALLOCATION_IMPORT_SCREENS.url('confirm', importation.pk), follow=True)
        importation.refresh_from_db()
        self.assertEqual(importation.status, Import.Status.CONCLUDED)
        self.assertEqual(response.redirect_chain[-1][0], SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', importation.pk))


class ViewPermissionTests(ScreenTestCase):
    def test_viewer_opens_the_grid_without_the_import_screens(self):
        self.client.force_login(self.user('consulta@ifnmg.edu.br', SPACE_ALLOCATION_VIEW))
        response = self.client.get(reverse('space_allocation_grid'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))


class DeletionTests(ScreenTestCase):
    def setUp(self):
        super().setUp()
        self.remover = self.user('removedor@ifnmg.edu.br', SPACE_ALLOCATION_IMPORT, SPACE_ALLOCATION_IMPORT_DELETE)
        self.upload()
        self.importation = Import.objects.get()
        self.importation.discard(SPACE_ALLOCATION_IMPORT_SCREENS.definition, self.importer)
        self.url = SPACE_ALLOCATION_IMPORT_SCREENS.url('delete', self.importation.pk)

    def test_with_the_permission_the_import_is_deleted(self):
        detail = SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', self.importation.pk)
        self.assertNotContains(self.client.get(detail), self.url)
        self.client.force_login(self.remover)
        self.assertContains(self.client.get(detail), self.url)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        response = self.post(self.url, follow=True)
        self.assertRedirects(response, SPACE_ALLOCATION_IMPORT_SCREENS.url('list'))
        self.assertContains(response, 'excluída')
        self.assertFalse(Import.objects.exists())
        record = AuditLog.objects.filter(action=catalog.DELETE).get()
        self.assertEqual((record.user, record.resource), (self.remover, catalog.SPACE_ALLOCATION_IMPORT))

    def test_pending_import_is_not_deleted(self):
        self.upload()
        pending = Import.objects.get(status=Import.Status.VALIDATED)
        self.client.force_login(self.remover)
        url = SPACE_ALLOCATION_IMPORT_SCREENS.url('delete', pending.pk)
        self.assertNotContains(self.client.get(SPACE_ALLOCATION_IMPORT_SCREENS.url('detail', pending.pk)), url)
        response = self.post(url, follow=True)
        self.assertContains(response, 'não pode ser excluída')
        self.assertTrue(Import.objects.filter(pk=pending.pk).exists())
