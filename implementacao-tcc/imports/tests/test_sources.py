"""Capacidades do motor usadas pelo ensalamento, testadas sem depender de app de domínio."""

import io
import zipfile

from django import forms
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from config.testing import IsolatedCasesMixin
from openpyxl import Workbook

from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from imports.definitions import Column
from imports.forms import ImportUploadForm
from imports.models import Import
from imports.reader import FileRejected
from imports.tests.definitions import GroupImport
from imports.tests.worker import confirm, preview
from imports.workbook import WorkbookSource, cell_reference

SEMESTER_LABEL = 'Semestre'


class GridGroupImport(GroupImport):
    """Importação de grade: cada célula preenchida das abas declaradas vira um grupo."""

    kind = 'GRUPO_GRADE'
    columns = GroupImport.columns + (Column('Célula'), Column(SEMESTER_LABEL))
    identifier = 'Célula'
    sheets = ('Primeira', 'Segunda')
    has_template = False
    upload_fields = {SEMESTER_LABEL: forms.CharField(label=SEMESTER_LABEL, max_length=7)}

    def source(self):
        return WorkbookSource()

    def read_cells(self, workbook):
        for title in self.sheets:
            sheet = workbook[title]
            for row in range(1, sheet.max_row + 1):
                for column in range(1, sheet.max_column + 1):
                    value = sheet.cell(row, column).value
                    if value is None or not str(value).strip():
                        continue
                    yield {'Nome': str(value), 'Célula': cell_reference(title, row, column)}

    def audit_metadata(self, rows):
        codes = {row.values.get(SEMESTER_LABEL) for row in rows}
        return {'semestre': codes.pop() if len(codes) == 1 else None}


def workbook_file(sheets, name='planilha.xlsx'):
    book = Workbook()
    book.remove(book.active)
    for title, cells in sheets.items():
        sheet = book.create_sheet(title)
        for coordinate, value in cells.items():
            sheet[coordinate] = value
    stream = io.BytesIO()
    book.save(stream)
    return SimpleUploadedFile(
        name,
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def two_sheets():
    return {'Primeira': {'A1': 'Docentes', 'B2': 'Técnicos'}, 'Segunda': {'A1': 'Direção'}}


class WorkbookTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.definition = GridGroupImport()

    def read(self, uploaded):
        return self.definition.source().read(uploaded, self.definition)

    def assertRejected(self, uploaded, message):
        with self.assertRaises(FileRejected) as context:
            self.read(uploaded)
        self.assertIn(message, context.exception.message)


class WorkbookSourceTests(WorkbookTestCase):
    def test_reads_one_raw_row_per_cell_of_the_declared_sheets(self):
        with self.case('uma linha por célula'):
            rows = self.read(workbook_file(two_sheets()))
            self.assertEqual([row.line_number for row in rows], [1, 2, 3])
            self.assertEqual(
                [row.values['Célula'] for row in rows], ['Primeira!A1', 'Primeira!B2', 'Segunda!A1'],
            )
            self.assertEqual([row.values['Nome'] for row in rows], ['Docentes', 'Técnicos', 'Direção'])
            self.assertEqual([row.errors for row in rows], [[], [], []])
        with self.case('aba a mais'):
            sheets = two_sheets() | {'Calculada': {'A1': 'não importa'}}
            rows = self.read(workbook_file(sheets))
            self.assertEqual([row.values['Nome'] for row in rows], ['Docentes', 'Técnicos', 'Direção'])
        with self.case('valores brutos'):
            rows = self.read(workbook_file({'Primeira': {'A1': ' Docentes\n do campus '}, 'Segunda': {'A1': 'Direção'}}))
            self.assertEqual(rows[0].values['Nome'], ' Docentes\n do campus ')
        with self.case('fórmula sem valor'):
            sheets = {'Primeira': {'A1': '=UPPER(B1)', 'A2': 'Docentes'}, 'Segunda': {'A1': 'Direção'}}
            rows = self.read(workbook_file(sheets))
            self.assertEqual([row.values['Nome'] for row in rows], ['Docentes', 'Direção'])

    def test_invalid_workbooks_are_rejected(self):
        with self.case('aba declarada ausente'):
            self.assertRejected(workbook_file({'Primeira': {'A1': 'Docentes'}}), 'Falta a aba "Segunda"')
        with self.case('não é planilha'):
            uploaded = SimpleUploadedFile('planilha.xlsx', b'Nome;Perfil\n', content_type='text/csv')
            self.assertRejected(uploaded, 'não pôde ser lido como planilha')
        with self.case('sem dados'):
            self.assertRejected(workbook_file({'Primeira': {}, 'Segunda': {}}), 'não tem linhas de dados')


XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def rebuilt(uploaded, extra=(), drop=()):
    """Copia o pacote XLSX acrescentando ou retirando entradas, como um arquivo forjado."""
    source = zipfile.ZipFile(io.BytesIO(uploaded.read()))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as package:
        for entry in source.infolist():
            if entry.filename not in drop:
                package.writestr(entry, source.read(entry))
        for name, content in extra:
            package.writestr(name, content)
    return SimpleUploadedFile('planilha.xlsx', stream.getvalue(), content_type=XLSX_TYPE)


class PackageTests(WorkbookTestCase):
    """Pacote XLSX conferido antes do openpyxl: tipo, entradas, expansão e dimensões das abas."""

    def test_unsafe_packages_are_rejected(self):
        with self.case('zip que não é planilha'):
            self.assertRejected(rebuilt(workbook_file(two_sheets()), drop=('xl/workbook.xml',)), 'não pôde ser lido como planilha')
        with self.case('pacote truncado'):
            content = workbook_file(two_sheets()).read()
            uploaded = SimpleUploadedFile('planilha.xlsx', content[: len(content) // 2], content_type=XLSX_TYPE)
            self.assertRejected(uploaded, 'não pôde ser lido como planilha')
        with self.case('conteúdo que expande demais'):
            with override_settings(IMPORT_MAX_XLSX_UNCOMPRESSED_SIZE=1024 * 1024):
                bomb = rebuilt(workbook_file(two_sheets()), extra=[('xl/media/vazio.bin', b'0' * (2 * 1024 * 1024))])
                self.assertLess(bomb.size, 64 * 1024)
                self.assertRejected(bomb, 'passa de 1 MB quando descompactado')
        with self.case('entradas demais'):
            with override_settings(IMPORT_MAX_XLSX_ENTRIES=20):
                crowded = rebuilt(workbook_file(two_sheets()), extra=[(f'xl/media/{n}.bin', b'') for n in range(20)])
                self.assertRejected(crowded, 'O limite é 20')
        with self.case('célula distante'):
            self.assertRejected(
                workbook_file({'Primeira': {'A1': 'Docentes', 'A1048576': 'x'}, 'Segunda': {'A1': 'Direção'}}),
                'A aba "Primeira" vai até a linha 1.048.576',
            )
            self.assertRejected(
                workbook_file({'Primeira': {'A1': 'Docentes', 'XFD1': 'x'}, 'Segunda': {'A1': 'Direção'}}),
                'e a coluna XFD',
            )

    def test_valid_workbook_is_read_and_can_be_read_again(self):
        uploaded = workbook_file(two_sheets())
        self.assertEqual(len(self.read(uploaded)), 3)
        uploaded.seek(0)
        self.assertEqual(len(self.read(uploaded)), 3)


class LimitTests(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.definition = GridGroupImport()

    def test_definition_limits_replace_the_configured_ones(self):
        with self.case('linhas'):
            with override_settings(IMPORT_MAX_ROWS=2):
                self.definition = GridGroupImport()
                self.definition.max_rows = 3
                rows = self.definition.source().read(workbook_file(two_sheets()), self.definition)
                self.assertEqual(len(rows), 3)
        with self.case('acima do próprio limite'):
            with override_settings(IMPORT_MAX_ROWS=10):
                self.definition = GridGroupImport()
                self.definition.max_rows = 2
                with self.assertRaises(FileRejected) as context:
                    self.definition.source().read(workbook_file(two_sheets()), self.definition)
                self.assertIn('O arquivo tem 3 linhas. O limite é 2.', context.exception.message)
        with self.case('tamanho'):
            with override_settings(IMPORT_MAX_FILE_SIZE=10):
                self.definition = GridGroupImport()
                self.definition.max_file_size = 1024 * 1024
                rows = self.definition.source().read(workbook_file(two_sheets()), self.definition)
                self.assertEqual(len(rows), 3)

    @override_settings(IMPORT_MAX_ROWS=2)
    def test_configured_limit_applies_without_a_declared_one(self):
        with self.assertRaises(FileRejected) as context:
            self.definition.source().read(workbook_file(two_sheets()), self.definition)
        self.assertIn('O limite é 2.', context.exception.message)


class UploadFieldTests(TestCase):
    def setUp(self):
        self.definition = GridGroupImport()

    def form(self, data=None, uploaded=None):
        return ImportUploadForm(
            data=data if data is not None else {'own_semestre': '2026/1'},
            files={'file': uploaded if uploaded is not None else workbook_file(two_sheets())},
            definition=self.definition,
        )

    def test_own_value_is_recorded_in_every_row(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual({row.values[SEMESTER_LABEL] for row in form.cleaned_data['rows']}, {'2026/1'})

    def test_missing_own_required_field_is_a_form_error(self):
        form = self.form(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('own_semestre', form.errors)
        self.assertNotIn('rows', form.cleaned_data)


class AuditMetadataTests(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.executor = User.objects.create(email='admin@ifnmg.edu.br', name='Admin')
        self.definition = GridGroupImport()

    def preview(self):
        form = ImportUploadForm(
            data={'own_semestre': '2026/1'},
            files={'file': workbook_file(two_sheets())},
            definition=self.definition,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return preview(
            self.definition, form.cleaned_data['rows'], form.cleaned_data['file'].name, self.executor,
        )

    def record(self, action):
        return AuditLog.objects.filter(action=action).latest('pk')

    def test_preview_and_discard_records_have_the_definition_metadata(self):
        with self.case('prévia'):
            self.preview()
            metadata = self.record(catalog.CREATE).metadata
            self.assertEqual(metadata['semestre'], '2026/1')
            self.assertEqual((metadata['arquivo'], metadata['situacao'], metadata['linhas']), ('planilha.xlsx', 'VALIDADA', 3))
        with self.case('descarte'):
            importation = self.preview()
            importation.discard(self.definition, self.executor)
            self.assertEqual(self.record(catalog.DISCARD).metadata['semestre'], '2026/1')

    def test_confirmation_records_only_the_summary(self):
        with self.case('resumo'):
            importation = self.preview()
            self.assertTrue(confirm(importation, self.definition, self.executor))
            record = self.record(catalog.IMPORT)
            self.assertEqual(importation.resolved_by, self.executor)
            self.assertEqual(str(record.resource_id), str(importation.pk))
            self.assertEqual(
                record.metadata,
                {
                    'arquivo': 'planilha.xlsx',
                    'situacao': 'CONCLUIDA',
                    'cadastrados': 3,
                    'atualizados': 0,
                    'sem_alteracao': 0,
                    'com_erro': 0,
                    'semestre': '2026/1',
                },
            )
            self.assertIsNotNone(record.created_at)
        with self.case('só a importação'):
            importation = self.preview()
            confirm(importation, self.definition, self.executor)
            self.assertEqual(Group.objects.count(), 3)
            self.assertEqual(
                list(AuditLog.objects.order_by('pk').values_list('action', 'resource')),
                [(catalog.CREATE, self.definition.audit_resource), (catalog.IMPORT, self.definition.audit_resource)],
            )
