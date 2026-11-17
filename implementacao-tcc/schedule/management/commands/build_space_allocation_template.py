from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from schedule.sheets import (
    CATALOG_FIRST_ROW,
    CATALOG_SHEET,
    FIRST_GROUP_COLUMN,
    INSTRUCTIONS_SHEET,
    SECONDARY_SHEET,
    SHEET_LAYOUTS,
    SPACE_CATALOG_COLUMN,
    TEACHER_CATALOG_COLUMN,
    TEMPLATE_FILE,
    UNDERGRADUATE_SHEET,
    USER_COLUMNS,
    USER_HEADER_ROW,
    USERS_SHEET,
    header_rows,
)

DEFAULT_SOURCE = 'sources/planilha_example_sugerida_corrigida.xlsx'

FIXES = {
    (UNDERGRADUATE_SHEET, 'C1'): 'BACHARELADO EM ENGENHARIA DE ALIMENTOS',
    (SECONDARY_SHEET, 'A1'): None,
    (CATALOG_SHEET, 'A1'): 'Docentes',
}
HEADER_TYPOS = {'Eng. Alimento': 'Eng. Alimentos'}

HEADER_FILL = PatternFill('solid', fgColor='FFB7B7B7')
SECTION_FILL = PatternFill('solid', fgColor='FFEFEFEF')
THIN = Side(style='thin')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical='top')

INSTRUCTIONS = (
    ('Modelo da planilha de ensalamento', None),
    ('Como usar', [
        'Preencha as aulas nas abas de horário e as listas da aba "Validação de Dados". A aba "usuários - sistema" é opcional.',
        'Não renomeie nem exclua as abas "Horário - Graduação", "Horário - Ensino Médio" e "Validação de Dados". '
        'Esta aba de instruções não é lida pela importação.',
        'O semestre e o período letivo são informados na tela de envio, e não na planilha.',
        'Salve no formato XLSX e envie em Ensalamento > Importações > Importar ensalamento.',
    ]),
    ('Abas de horário', [
        'A linha 1 traz o nome do curso, mesclado sobre as colunas das turmas dele.',
        'Cada linha com "DIA" na coluna A abre um bloco de dia. Logo abaixo vem o dia da semana: segunda a sexta, '
        'com ou sem "-feira". Mantenha a última linha "DIA", que fecha o bloco de sexta.',
        'A coluna B traz a faixa de horário no formato 07:20 - 08:10, ou INTERVALO e ALMOÇO nas pausas.',
        'Cada turma ocupa uma coluna a partir da C. O cabeçalho da turma tem o rótulo na primeira linha e o nome curto '
        'do curso na segunda (por exemplo, "2º PERÍODO" e, abaixo, "Sist. de Informação").',
        'Para acrescentar uma turma, insira uma coluna dentro do bloco do curso e preencha o cabeçalho. '
        'Coluna com aula e sem cabeçalho faz a planilha ser recusada.',
    ]),
    ('Célula de aula', [
        'Escreva a disciplina, o docente entre parênteses e a sala entre parênteses: Cálculo III (Ana Souza) (2/6).',
        'Mais de um docente vai no mesmo parêntese, separado por "/", "," ou " e ": Biologia (Ana Souza / João Lima) (1/6).',
        'Duas aulas na mesma célula são separadas por "/" fora dos parênteses, cada uma com os próprios parênteses.',
        'O docente e a sala precisam estar escritos como nas listas da aba "Validação de Dados". '
        'Maiúsculas, minúsculas e espaços repetidos não contam.',
        'Deixe em branco as faixas sem aula.',
    ]),
    ('Validação de Dados', [
        'Coluna A: docentes, um por linha, a partir da linha 2. Coluna B: salas, uma por linha, a partir da linha 2.',
        'Nenhuma das duas listas pode ficar vazia.',
        'O docente fica em vermelho quando não há, na aba "usuários - sistema", um usuário com o mesmo nome de usuário.',
    ]),
    ('usuários - sistema (opcional)', [
        'Colunas E-mail, Nome, Perfil e Nome de usuário, uma pessoa por linha, a partir da linha 2.',
        'Perfil é o código de um perfil cadastrado no sistema, como DOCENTE.',
        'Nome de usuário deve ser igual ao nome do docente na aba "Validação de Dados". '
        'Fica em vermelho quando não está na lista de docentes.',
        'Usuário com e-mail novo é cadastrado; usuário já cadastrado não é alterado.',
    ]),
)


def clear(cell):
    cell.value = None


def clear_schedule(sheet):
    """Apaga as aulas e mantém dias, faixas, pausas, cursos, turmas e toda a formatação."""
    marks = header_rows(sheet)
    if not marks:
        raise CommandError(f'A aba "{sheet.title}" não tem as linhas "DIA".')
    headers = set(marks)
    for row in range(marks[0] + 1, sheet.max_row + 1):
        if row in headers:
            continue
        for column in range(FIRST_GROUP_COLUMN, sheet.max_column + 1):
            clear(sheet.cell(row, column))
    for row in marks:
        for column in range(FIRST_GROUP_COLUMN, sheet.max_column + 1):
            cell = sheet.cell(row, column)
            if isinstance(cell.value, str):
                lines = cell.value.split('\n')
                cell.value = '\n'.join(HEADER_TYPOS.get(line, line) for line in lines)


def clear_columns(sheet, columns, first_row):
    for row in range(first_row, sheet.max_row + 1):
        for column in columns:
            clear(sheet.cell(row, column))


def add_instructions(workbook):
    sheet = workbook.create_sheet(INSTRUCTIONS_SHEET, 0)
    sheet.column_dimensions['A'].width = 120
    sheet.sheet_view.showGridLines = False
    row = 1
    for title, lines in INSTRUCTIONS:
        cell = sheet.cell(row, 1, title)
        cell.font = Font(bold=True, size=12 if lines is None else 10)
        cell.fill = HEADER_FILL if lines is None else SECTION_FILL
        cell.border = BORDER
        cell.alignment = WRAP
        row += 1
        for line in lines or ():
            cell = sheet.cell(row, 1, line)
            cell.font = Font(size=10)
            cell.border = BORDER
            cell.alignment = WRAP
            row += 1
        row += 1
    workbook.active = 0
    for other in workbook.worksheets:
        other.sheet_view.tabSelected = other is sheet


def build(source):
    workbook = load_workbook(source)
    expected = [layout.title for layout in SHEET_LAYOUTS] + [CATALOG_SHEET, USERS_SHEET]
    missing = [title for title in expected if title not in workbook.sheetnames]
    if missing:
        raise CommandError(f'Faltam as abas {", ".join(missing)} em {source}.')
    if INSTRUCTIONS_SHEET in workbook.sheetnames:
        del workbook[INSTRUCTIONS_SHEET]
    for layout in SHEET_LAYOUTS:
        clear_schedule(workbook[layout.title])
    clear_columns(workbook[CATALOG_SHEET], (TEACHER_CATALOG_COLUMN, SPACE_CATALOG_COLUMN), CATALOG_FIRST_ROW)
    clear_columns(workbook[USERS_SHEET], range(1, len(USER_COLUMNS) + 1), USER_HEADER_ROW + 1)
    for (title, coordinate), value in FIXES.items():
        workbook[title][coordinate].value = value
    add_instructions(workbook)
    workbook.calculation.fullCalcOnLoad = True
    return workbook


class Command(BaseCommand):
    """Gera o modelo em branco da importação do ensalamento a partir da planilha sugerida ao campus."""

    help = 'Gera schedule/files/modelo-importacao-ensalamento.xlsx a partir da planilha sugerida.'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=DEFAULT_SOURCE, help='Planilha sugerida usada como base.')

    def handle(self, *args, **options):
        source = Path(options['source'])
        if not source.is_absolute():
            source = Path(settings.BASE_DIR) / source
        if not source.exists():
            raise CommandError(f'Planilha {source} não encontrada.')
        TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        build(source).save(TEMPLATE_FILE)
        self.stdout.write(self.style.SUCCESS(f'Modelo gerado em {TEMPLATE_FILE.relative_to(settings.BASE_DIR)}.'))
