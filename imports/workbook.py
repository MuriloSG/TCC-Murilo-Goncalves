"""Leitura de uma planilha XLSX em grade, como fonte do motor de importação.

A grade não tem linhas no sentido do CSV: a importação específica descreve as abas e
percorre as células, e esta fonte entrega uma linha por célula de dado, numerada em
sequência na ordem de leitura. As fórmulas não são recalculadas: o valor lido é o que
está em cache na planilha, e uma fórmula sem valor chega como célula vazia.

Cabe à importação específica recusar o arquivo cuja estrutura não permita a leitura,
lançando FileRejected de dentro de `read_cells`.
"""

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from imports.reader import (
    FileRejected,
    SourceRow,
    check_file_size,
    check_identifiers,
    check_row_count,
    listing,
)


def cell_reference(sheet_title, row, column):
    """Origem de uma célula no formato `Aba!Célula`, como a planilha a mostra."""
    return f'{sheet_title}!{get_column_letter(column)}{row}'


def open_workbook(uploaded_file):
    try:
        return load_workbook(uploaded_file, data_only=True)
    except Exception:
        raise FileRejected(
            'O arquivo não pôde ser lido como planilha. Envie a planilha no formato XLSX.'
        ) from None


class WorkbookSource:
    """Fonte de planilha em grade, para uma importação que declara abas e percorre células."""

    file_label = 'Arquivo da planilha'
    accept = '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    missing_message = 'Escolha o arquivo da planilha.'

    def help_text(self, definition):
        return f'Planilha em XLSX, com as abas {listing(definition.sheets)}.'

    def read(self, uploaded_file, definition):
        """Lê a planilha e devolve as linhas, uma por célula de dado das abas declaradas."""
        check_file_size(uploaded_file, definition)
        workbook = open_workbook(uploaded_file)
        missing = [f'"{name}"' for name in definition.sheets if name not in workbook.sheetnames]
        if missing:
            noun = 'a aba' if len(missing) == 1 else 'as abas'
            raise FileRejected(f'Falta {noun} {listing(missing)} na planilha. Confira o arquivo enviado.')
        rows = [SourceRow(number, values) for number, values in enumerate(definition.read_cells(workbook), start=1)]
        if not rows:
            raise FileRejected('O arquivo não tem linhas de dados.')
        check_row_count(rows, definition)
        check_identifiers(rows, definition)
        return rows
