"""Leitura do CSV: recusas do arquivo lançam FileRejected, e problemas de linha viram erros dela."""

import csv
import io
import unicodedata
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.formats import number_format

from imports.definitions import RowError

DELIMITER = ';'


class FileRejected(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


@dataclass
class SourceRow:
    line_number: int
    values: dict
    errors: list = field(default_factory=list)


def normalize_header(text):
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in decomposed if not unicodedata.combining(char)).casefold().strip()


def quantity(value):
    return number_format(value, force_grouping=True)


def listing(items):
    items = [str(item) for item in items]
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' e ' + items[-1]


def expected_columns(definition):
    return ', '.join(column.label for column in definition.file_columns())


def file_size_limit(definition):
    """Tamanho máximo declarado pela importação, ou o da configuração."""
    return definition.max_file_size or settings.IMPORT_MAX_FILE_SIZE


def row_limit(definition):
    """Quantidade máxima de linhas declarada pela importação, ou a da configuração."""
    return definition.max_rows or settings.IMPORT_MAX_ROWS


def check_file_size(uploaded_file, definition):
    limit = file_size_limit(definition)
    if uploaded_file.size > limit:
        raise FileRejected(
            f'O arquivo tem {quantity(-(-uploaded_file.size // 1024))} KB. '
            f'O limite é {quantity(limit // 1024)} KB. '
            'Divida o arquivo e importe em partes.'
        )


def check_row_count(rows, definition):
    limit = row_limit(definition)
    if len(rows) > limit:
        raise FileRejected(
            f'O arquivo tem {quantity(len(rows))} linhas. O limite é {quantity(limit)}. '
            'Divida o arquivo e importe em partes.'
        )


def decode(uploaded_file, definition):
    check_file_size(uploaded_file, definition)
    try:
        return uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        raise FileRejected(
            'O arquivo não está em UTF-8. No Excel, salve como "CSV UTF-8 (delimitado por vírgulas)".'
        ) from None


def records(text):
    """Registros do CSV com o número da linha física em que cada um começa."""
    reader = csv.reader(io.StringIO(text, newline=''), delimiter=DELIMITER)
    while True:
        start = reader.line_num + 1
        try:
            cells = next(reader)
        except StopIteration:
            return
        except csv.Error:
            raise FileRejected(
                f'O arquivo não pôde ser lido a partir da linha {start}. Confira as aspas dessa linha.'
            ) from None
        yield start, cells


def header_positions(header, definition):
    labels = {normalize_header(column.label): column.label for column in definition.file_columns()}
    if len(header) == 1 and len(header[0].split(',')) > 1:
        if {normalize_header(cell) for cell in header[0].split(',')} & labels.keys():
            raise FileRejected(
                'O arquivo usa "," como separador. Salve o arquivo com ";" como separador, como no modelo.'
            )
    positions, unknown, repeated = {}, [], []
    for index, cell in enumerate(header):
        label = labels.get(normalize_header(cell))
        if label is None:
            unknown.append(f'"{cell.strip()}"')
        elif label in positions:
            repeated.append(f'"{label}"')
        else:
            positions[label] = index
    if unknown:
        noun = 'Coluna' if len(unknown) == 1 else 'Colunas'
        adjective = 'reconhecida' if len(unknown) == 1 else 'reconhecidas'
        raise FileRejected(
            f'{noun} {listing(unknown)} não {adjective}. Use as colunas do modelo: {expected_columns(definition)}.'
        )
    if repeated:
        raise FileRejected(f'A coluna {listing(repeated)} aparece mais de uma vez. Deixe só uma.')
    missing = [f'"{column.label}"' for column in definition.file_columns() if column.label not in positions]
    if missing:
        noun = 'a coluna' if len(missing) == 1 else 'as colunas'
        raise FileRejected(
            f'Falta {noun} {listing(missing)}. Use as colunas do modelo: {expected_columns(definition)}.'
        )
    return positions


def check_identifiers(rows, definition):
    lines_by_identifier = {}
    for row in rows:
        value = row.values[definition.identifier]
        if value.strip():
            identifier = definition.normalize_identifier(value)
            lines_by_identifier.setdefault(identifier, []).append(row)
    for repeated in lines_by_identifier.values():
        if len(repeated) > 1:
            lines = listing(row.line_number for row in repeated)
            for row in repeated:
                row.errors.append(RowError(
                    definition.identifier, 'duplicate', f'{definition.identifier} repetido nas linhas {lines}.',
                ))


def read_csv(uploaded_file, definition):
    """Lê as linhas com os erros de estrutura; lança FileRejected quando o arquivo inteiro é recusado."""
    text = decode(uploaded_file, definition)
    source = records(text)
    header = next(source, None)
    if header is None:
        raise FileRejected('O arquivo não tem linhas de dados.')
    positions = header_positions(header[1], definition)
    width = len(header[1])
    rows = []
    for line_number, cells in source:
        if not any(cell.strip() for cell in cells):
            continue
        values = {label: cells[index] if index < len(cells) else '' for label, index in positions.items()}
        row = SourceRow(line_number, values)
        if len(cells) > width and any(cell.strip() for cell in cells[width:]):
            row.errors.append(RowError(
                None, 'extra_cells', 'A linha tem mais colunas que o cabeçalho. Confira se há ";" sobrando.',
            ))
        for column in definition.file_columns():
            if column.required and not values[column.label].strip():
                row.errors.append(RowError(column.label, 'required', f'Preencha a coluna {column.label}.'))
        rows.append(row)
    if not rows:
        raise FileRejected('O arquivo não tem linhas de dados.')
    check_row_count(rows, definition)
    check_identifiers(rows, definition)
    return rows


class CsvSource:
    """Fonte de CSV: um arquivo em UTF-8, separado por ";", com cabeçalho na primeira linha."""

    file_label = 'Arquivo CSV'
    accept = '.csv,text/csv'
    missing_message = 'Escolha o arquivo CSV.'

    def help_text(self, definition):
        labels = listing([column.label for column in definition.file_columns()])
        return f'CSV em UTF-8, separado por ";", com as colunas {labels}.'

    def read(self, uploaded_file, definition):
        return read_csv(uploaded_file, definition)
