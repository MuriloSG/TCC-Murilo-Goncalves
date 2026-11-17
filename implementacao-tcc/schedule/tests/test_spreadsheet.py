"""Leitura de `schedule/tests/fixtures/planilha_example.xlsx`, com números que acusam mudança de comportamento diante do arquivo real."""

import collections
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from openpyxl import Workbook, load_workbook

from imports.reader import FileRejected

from schedule.activities import Catalog, resolve
from schedule.imports import (
    ACTIVITY_COLUMN,
    CELL_COLUMN,
    COURSE_COLUMN,
    DAY_COLUMN,
    GROUP_COLUMN,
    KIND_COLUMN,
    SLOT_COLUMN,
    SpaceAllocationImport,
    sheet_of,
)
from schedule.sheets import (
    ACTIVITY_KIND,
    CATALOG_SHEET,
    INSTRUCTIONS_SHEET,
    SECONDARY_SHEET,
    SHEET_LAYOUTS,
    SPACE_KIND,
    TEACHER_KIND,
    TEMPLATE_FILE,
    UNDERGRADUATE_SHEET,
    USER_COLUMNS,
    USER_KIND,
    USERS_SHEET,
    catalog_entries,
    group_columns,
    header_rows,
    parse_weekday,
    sheet_cells,
    user_entries,
)

FIXTURES = Path(__file__).parent / 'fixtures'
SPREADSHEET = FIXTURES / 'planilha_example.xlsx'
IGNORED_SHEETS = (
    'Ensalamento - Geral',
    'Horário - Professor',
    'Horário - Professor - 1',
    'Horário - Professor - Separado',
    'Eng. Alimentos',
    'BSI',
    'Lic. em Química',
)


def workbook():
    return load_workbook(SPREADSHEET, data_only=True)


class SpreadsheetTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.definition = SpaceAllocationImport()
        cls.book = workbook()
        cls.rows = list(cls.definition.read_cells(cls.book))
        cls.catalog_rows = [row for row in cls.rows if row[KIND_COLUMN] in (SPACE_KIND, TEACHER_KIND)]
        cls.activity_rows = [row for row in cls.rows if row[KIND_COLUMN] == ACTIVITY_KIND]

    def catalog(self):
        return Catalog.build(
            [self.definition.catalog_name(row) for row in self.catalog_rows if row[KIND_COLUMN] == TEACHER_KIND],
            [self.definition.catalog_name(row) for row in self.catalog_rows if row[KIND_COLUMN] == SPACE_KIND],
        )


class StructureTests(SpreadsheetTestCase):
    def test_portrait_of_the_real_file(self):
        """Números da análise do arquivo real, conferidos juntos para acusar mudança na leitura."""
        self.assertEqual(header_rows(self.book[UNDERGRADUATE_SHEET]), [2, 23, 44, 65, 86, 107])
        self.assertEqual(header_rows(self.book[SECONDARY_SHEET]), [2, 17, 32, 47, 62, 77])
        entries = catalog_entries(self.book)
        teachers = [entry for entry in entries if entry['kind'] == TEACHER_KIND]
        spaces = [entry for entry in entries if entry['kind'] == SPACE_KIND]
        self.assertEqual((len(teachers), len(spaces)), (124, 82))
        self.assertEqual((teachers[0]['value'], teachers[0]['reference']), ('Adailton', f'{CATALOG_SHEET}!A2'))
        self.assertEqual((spaces[0]['value'], spaces[0]['reference']), ('(1/10)', f'{CATALOG_SHEET}!B2'))
        undergraduate = {row[SLOT_COLUMN] for row in self.activity_rows if sheet_of(row) == UNDERGRADUATE_SHEET}
        secondary = {row[SLOT_COLUMN] for row in self.activity_rows if sheet_of(row) == SECONDARY_SHEET}
        self.assertEqual((len(undergraduate), len(secondary)), (15, 9))
        self.assertTrue(secondary < undergraduate)
        self.assertFalse({'INTERVALO', 'ALMOÇO'} & (undergraduate | secondary))
        for title, expected in ((UNDERGRADUATE_SHEET, 39), (SECONDARY_SHEET, 20)):
            layout = next(item for item in SHEET_LAYOUTS if item.title == title)
            sheet = self.book[title]
            columns = group_columns(sheet, layout, header_rows(sheet)[0])
            self.assertEqual(len({column.header_text for column in columns.values()}), expected, title)
        with_activity = {row[GROUP_COLUMN] for row in self.activity_rows if sheet_of(row) == UNDERGRADUATE_SHEET}
        self.assertEqual(len(with_activity), 36)
        origins = [row[CELL_COLUMN] for row in self.activity_rows]
        self.assertIn(f'{UNDERGRADUATE_SHEET}!F69#1', origins)
        self.assertIn(f'{UNDERGRADUATE_SHEET}!F69#2', origins)
        self.assertEqual(len([origin for origin in origins if '#' in origin]), 45)
        self.assertEqual((len(self.catalog_rows), len(self.activity_rows), len(self.rows)), (206, 1500, 1706))
        kinds = [row[KIND_COLUMN] for row in self.rows]
        self.assertEqual(set(kinds[:206]), {SPACE_KIND, TEACHER_KIND})
        self.assertEqual(set(kinds[206:]), {ACTIVITY_KIND})

    def test_only_the_schedule_sheets_are_read_with_the_five_weekdays(self):
        for title in IGNORED_SHEETS:
            self.assertIn(title, self.book.sheetnames)
        self.assertEqual({sheet_of(row) for row in self.rows}, {UNDERGRADUATE_SHEET, SECONDARY_SHEET, CATALOG_SHEET})
        for title in (UNDERGRADUATE_SHEET, SECONDARY_SHEET):
            days = {parse_weekday(row[DAY_COLUMN]) for row in self.activity_rows if sheet_of(row) == title}
            self.assertEqual(days, {'SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA'}, title)
        names = [self.definition.catalog_name(row) for row in self.catalog_rows if row[KIND_COLUMN] == SPACE_KIND]
        for name in ('1/10', 'Lab. de Madeira', 'Lab. Reprodução Animal'):
            self.assertIn(name, names)
        self.assertNotIn('(1/10)', names)

    def test_group_and_course_of_each_column(self):
        physics = [
            row for row in self.activity_rows
            if sheet_of(row) == UNDERGRADUATE_SHEET and row[GROUP_COLUMN].startswith('4º PERÍODO\nLic. Física')
        ]
        friday = [row for row in physics if parse_weekday(row[DAY_COLUMN]) == 'SEXTA']
        self.assertTrue(friday)
        self.assertEqual({row[GROUP_COLUMN] for row in friday}, {row[GROUP_COLUMN] for row in physics})
        food = [
            row for row in self.activity_rows
            if row[GROUP_COLUMN].endswith('Eng. Alimentos') or row[GROUP_COLUMN].endswith('Eng. Alimento')
        ]
        self.assertTrue(food)
        self.assertEqual({row[COURSE_COLUMN] for row in food}, {''})
        forest = [row for row in self.activity_rows if row[GROUP_COLUMN].endswith('Eng. Florestal')]
        self.assertEqual({row[COURSE_COLUMN] for row in forest}, {'BACHARELADO EM ENGENHARIA FLORESTAL'})


class ActivityReadingTests(SpreadsheetTestCase):
    def setUp(self):
        self.file_catalog = self.catalog()

    def activity(self, origin):
        row = next(row for row in self.activity_rows if row[CELL_COLUMN] == origin)
        return resolve(row[ACTIVITY_COLUMN], self.file_catalog)

    def test_cells_of_the_real_file_are_read(self):
        cases = [
            ('completa', f'{UNDERGRADUATE_SHEET}!D6', 'CÁLCULO III', ['Viviane'], '2/6', []),
            ('parênteses na disciplina', f'{UNDERGRADUATE_SHEET}!M3', 'Gestão Ambiental (optativa)', ['Élcio José'], '3/10', []),
            ('sem sala', f'{SECONDARY_SHEET}!F3', 'Ed. Física', ['Gera Jr.'], None, []),
            ('docentes separados por barra', f'{UNDERGRADUATE_SHEET}!V10', 'UCE 2', ['Eduardo Garrido', 'Antônio', 'Lídia'], 'HV 3', ['docente_desconhecido']),
            ('quebra de linha', f'{SECONDARY_SHEET}!C3', 'Química', ['Juliana Diniz'], 'Mini 1', []),
            ('sala com espaço no nome', f'{UNDERGRADUATE_SHEET}!U10', None, None, 'HV 2', []),
            ('primeira de duas na célula', f'{UNDERGRADUATE_SHEET}!F69#1', 'Óleos e Gorduras (OPTATIVA I)', ['Bruna Porto'], 'Sl. Fenômenos', []),
            ('segunda de duas na célula', f'{UNDERGRADUATE_SHEET}!F69#2', 'Massas e Panificação (OPTATIVA II)', ['Márcia Antunes'], 'Sl. Oficina', []),
            ('válida numa célula com problema', f'{UNDERGRADUATE_SHEET}!AQ64#1', 'Educação e Diversidade', None, ..., []),
            ('outra válida na mesma célula', f'{UNDERGRADUATE_SHEET}!AQ64#2', 'TCC I - Química', None, ..., []),
            ('sala fora do catálogo', f'{SECONDARY_SHEET}!J33', None, None, None, []),
            ('sala com outra grafia', f'{UNDERGRADUATE_SHEET}!T25', None, ['Valéria'], None, []),
        ]
        for label, origin, subject, teachers, space, problems in cases:
            with self.subTest(label, origin=origin):
                activity = self.activity(origin)
                if subject is not None:
                    self.assertEqual(activity.subject_name, subject)
                if teachers is not None:
                    self.assertEqual(activity.teacher_names, teachers)
                if space is not ...:
                    self.assertEqual(activity.space_name, space)
                self.assertEqual([code for code, _ in activity.problems], problems)
        self.assertEqual(self.activity(f'{SECONDARY_SHEET}!J33').cell_space_name, 'Zoo I')
        self.assertEqual(self.activity(f'{UNDERGRADUATE_SHEET}!T25').cell_space_name, 'HV1')
        statistics = self.activity(f'{UNDERGRADUATE_SHEET}!AM21')
        self.assertEqual((statistics.subject_name, statistics.teacher_names, statistics.space_name), ('Estatística Básica', ['Arilson'], '1/16'))
        self.assertIn('Agnaldo', statistics.problems[0][1])
        rows = [row for row in self.activity_rows if row[CELL_COLUMN] == f'{UNDERGRADUATE_SHEET}!V3']
        self.assertEqual(len(rows), 1)
        self.assertIn('Eduardo Garrido/ Thaís/ Antônio', rows[0][ACTIVITY_COLUMN])

    def test_malformed_cells_are_problems(self):
        catalog = Catalog.build(['Elza'], ['1/1'])
        for label, activity, code in (
            ('parênteses vazios no lugar da sala', resolve('Física (Elza) ()', catalog), 'sala_vazia'),
            ('sem parênteses', resolve('Somente um texto', catalog), 'sem_parenteses'),
            ('sem disciplina', self.activity(f'{UNDERGRADUATE_SHEET}!AQ64#3'), 'sem_disciplina'),
        ):
            with self.subTest(label):
                self.assertEqual([found for found, _ in activity.problems], [code])

    def test_names_match_ignoring_case_but_never_by_prefix_or_without_accents(self):
        activity = resolve('Física (Gera) (1/1)', Catalog.build(['Gera Jr.', 'Gera Magela'], ['1/1']))
        self.assertEqual(([code for code, _ in activity.problems], activity.teacher_names), (['docente_desconhecido'], []))
        activity = resolve('Biologia (Erica) (1/1)', Catalog.build(['Érica'], ['1/1']))
        self.assertEqual([code for code, _ in activity.problems], ['docente_desconhecido'])
        activity = resolve('Biologia (ÉRICA) (MINI 1)', Catalog.build(['Érica'], ['Mini 1']))
        self.assertEqual((activity.problems, activity.teacher_names, activity.space_name), ([], ['Érica'], 'Mini 1'))


class RealFileProblemTests(SpreadsheetTestCase):
    def test_how_many_activities_the_real_file_rejects(self):
        file_catalog = self.catalog()
        problems = [resolve(row[ACTIVITY_COLUMN], file_catalog).problems for row in self.activity_rows]
        with_problem = [found for found in problems if found]
        codes = sorted({code for found in with_problem for code, _ in found})
        self.assertEqual(len(with_problem), 121)
        self.assertEqual(codes, ['docente_desconhecido', 'sem_disciplina'])
        by_code = collections.Counter(code for found in with_problem for code, _ in found)
        self.assertEqual(by_code, {'docente_desconhecido': 120, 'sem_disciplina': 1})


class UserSheetReadingTests(SimpleTestCase):
    """Leitura da aba opcional `usuários - sistema`."""

    def book(self, rows=None, title=USERS_SHEET):
        book = Workbook()
        book.remove(book.active)
        catalog_sheet = book.create_sheet(CATALOG_SHEET)
        catalog_sheet['A1'] = 'Disciplina (Professor)'
        catalog_sheet['B1'] = 'Salas Disponíveis'
        catalog_sheet['A2'] = 'Elza'
        catalog_sheet['B2'] = '(1/13)'
        if rows is not None:
            sheet = book.create_sheet(title)
            for row in rows:
                sheet.append(list(row))
        return book

    def test_entries_keep_the_raw_values_of_each_data_row(self):
        self.assertEqual(user_entries(self.book()), [])
        self.assertEqual(user_entries(self.book([])), [])
        self.assertEqual(user_entries(self.book([USER_COLUMNS])), [])
        entries = user_entries(self.book([
            USER_COLUMNS,
            (' elza@ifnmg.edu.br ', 'Elza', 'DOCENTE', 'Elza'),
            (None, None, None, None),
            ('viviane@ifnmg.edu.br', 'Viviane', 'DOCENTE', None),
        ]))
        self.assertEqual([entry['reference'] for entry in entries], ['usuários - sistema!A2', 'usuários - sistema!A4'])
        self.assertEqual(entries[0]['values']['E-mail'], ' elza@ifnmg.edu.br ')
        self.assertEqual(entries[1]['values']['Nome de usuário'], '')
        book = self.book([USER_COLUMNS, ('elza@ifnmg.edu.br', 'Elza', 'DOCENTE', 'Elza')], title='Usuarios - Sistema')
        self.assertEqual(user_entries(book)[0]['reference'], 'Usuarios - Sistema!A2')
        entries = user_entries(self.book([
            ('e-mail', 'NOME', 'Observação', 'perfil', 'nome de usuario'),
            ('elza@ifnmg.edu.br', 'Elza', 'qualquer', 'DOCENTE', 'Elza'),
        ]))
        self.assertEqual(
            entries[0]['values'],
            {'E-mail': 'elza@ifnmg.edu.br', 'Nome': 'Elza', 'Perfil': 'DOCENTE', 'Nome de usuário': 'Elza'},
        )
        book = self.book([USER_COLUMNS, ('elza@ifnmg.edu.br', 'Elza', 'DOCENTE', 'Elza')])
        with patch('schedule.imports.SHEET_LAYOUTS', ()):
            rows = list(SpaceAllocationImport().read_cells(book))
        self.assertEqual([row[KIND_COLUMN] for row in rows], [USER_KIND, SPACE_KIND, TEACHER_KIND])

    def test_missing_or_repeated_column_rejects_the_file(self):
        with self.assertRaises(FileRejected) as raised:
            user_entries(self.book([('E-mail', 'Nome', 'Nome de usuário'), ('a@ifnmg.edu.br', 'A', 'A')]))
        self.assertIn('"Perfil"', raised.exception.message)
        self.assertIn('"usuários - sistema"', raised.exception.message)
        with self.assertRaises(FileRejected) as raised:
            user_entries(self.book([(*USER_COLUMNS, 'Perfil')]))
        self.assertIn('"Perfil" aparece mais de uma vez', raised.exception.message)


class TemplateTests(SimpleTestCase):
    """Modelo em branco de `make space-template`: estrutura da sugerida, sem aulas, listas nem usuários."""

    def test_template_keeps_the_structure_and_reads_once_filled(self):
        book = load_workbook(TEMPLATE_FILE)
        self.assertEqual(book.sheetnames, [INSTRUCTIONS_SHEET, *(layout.title for layout in SHEET_LAYOUTS), CATALOG_SHEET, USERS_SHEET])
        for layout, turmas in zip(SHEET_LAYOUTS, (39, 20)):
            with self.subTest(layout.title):
                sheet = book[layout.title]
                self.assertEqual(len(group_columns(sheet, layout, header_rows(sheet)[0])), turmas)
                self.assertEqual(list(sheet_cells(sheet, layout)), [])
        self.assertEqual(book[UNDERGRADUATE_SHEET]['C1'].value, 'BACHARELADO EM ENGENHARIA DE ALIMENTOS')
        catalog_sheet, users = book[CATALOG_SHEET], book[USERS_SHEET]
        self.assertEqual((catalog_sheet['A2'].value, catalog_sheet['B2'].value, users['A2'].value), (None, None, None))
        self.assertTrue(catalog_sheet['C2'].value.startswith('=IF(A2=""'))
        self.assertTrue(users['E2'].value.startswith('=IF(D2=""'))
        with self.assertRaisesMessage(FileRejected, 'está vazia'):
            catalog_entries(book)

        catalog_sheet['A2'], catalog_sheet['B2'] = 'Ana Souza', '(2/6)'
        book[UNDERGRADUATE_SHEET]['C3'] = 'Cálculo III (Ana Souza) (2/6)'
        rows = list(SpaceAllocationImport().read_cells(book))
        activity = next(row for row in rows if row[KIND_COLUMN] == ACTIVITY_KIND)
        self.assertEqual(
            (activity[CELL_COLUMN], activity[DAY_COLUMN], activity[SLOT_COLUMN], activity[COURSE_COLUMN]),
            (f'{UNDERGRADUATE_SHEET}!C3', 'SEGUNDA ', '07:20 - 08:10', 'BACHARELADO EM ENGENHARIA DE ALIMENTOS'),
        )
