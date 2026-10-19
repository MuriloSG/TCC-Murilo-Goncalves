"""Contrato das importações; linha com pendência não é aplicada e deixa a importação `PENDENTE`."""

from contextlib import nullcontext
from dataclasses import dataclass, field

from django.core.exceptions import NON_FIELD_ERRORS


@dataclass(frozen=True)
class Column:
    """`required` vale para a célula; a coluna é sempre exigida no cabeçalho."""

    label: str
    required: bool = True


@dataclass(frozen=True)
class RowFilter:
    """Recorte das linhas da prévia; `columns` vazio mantém todas as colunas."""

    slug: str
    label: str
    column: str
    value: str
    columns: tuple = ()


@dataclass(frozen=True)
class RowError:
    column: str | None
    code: str
    message: str


@dataclass
class RowPlan:
    """`created` fica fora da comparação, porque a chave gerada na prévia some no rollback."""

    action: str | None = None
    target: str | None = None
    changes: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    created: str | None = None
    pending: list = field(default_factory=list)


class ImportDefinition:
    """Importação específica; `optional_sheets` são abas que a planilha pode não ter."""

    kind = ''
    audit_resource = ''
    columns = ()
    identifier = ''
    columns_by_field = {}
    action_labels = {}
    field_labels = {}
    warning_labels = {}
    pending_labels = {}
    upload_fields = {}
    row_filters = ()
    optional_sheets = ()
    max_file_size = None
    max_rows = None
    has_template = True

    def source(self):
        """Leitor do arquivo, CSV por padrão; o import é local para evitar o ciclo."""
        from imports.reader import CsvSource

        return CsvSource()

    def file_columns(self):
        """Colunas que vêm do arquivo, sem as colunas lógicas preenchidas pelo envio."""
        return tuple(column for column in self.columns if column.label not in self.upload_fields)

    def normalize_identifier(self, value):
        return value.strip()

    def execution(self, importation=None):
        """Contexto em volta das linhas; recebe a importação em curso, salvo na primeira prévia."""
        return nullcontext()

    def lock(self, rows, executor):
        """Trava o que a execução vai ler, antes da primeira linha."""

    def execute_row(self, values, executor):
        """Executa a linha com as operações reais do domínio e devolve o RowPlan."""
        raise NotImplementedError

    def clean_upload(self, values):
        """Validação conjunta dos campos próprios do envio, antes da leitura do arquivo."""

    def upload_display(self, label, value):
        """Valor de um campo próprio como aparece no resumo; o gravado nas linhas não muda."""
        return value

    def finish(self, executor):
        """Etapa final na transação das linhas; um erro do banco aqui sobe como erro inesperado, e não de linha."""

    def check_file(self, executor):
        """Verificações do arquivo inteiro, depois de todas as linhas; devolve RowError sem coluna."""
        return []

    def check_confirmation(self, importation, executor):
        """Recusa a confirmação com `ValidationError`, antes de reexecutar as linhas e sem alterar dados."""

    def pending_label(self, code, key):
        """Texto de uma pendência da linha, a partir do rótulo declarado para o código."""
        return self.pending_labels.get(code, code).format(key=key)

    def audit_metadata(self, rows):
        """Metadados próprios da importação nos registros de auditoria, em valores canônicos."""
        return {}


def errors_from_validation(error, columns_by_field):
    """Traduz a ValidationError do model em erros de coluna; o que não mapeia fica sem coluna."""
    if hasattr(error, 'error_dict'):
        groups = error.error_dict.items()
    else:
        groups = [(NON_FIELD_ERRORS, error.error_list)]
    errors = []
    for name, items in groups:
        column = columns_by_field.get(name)
        for item in items:
            for message in item.messages:
                errors.append(RowError(column, item.code or 'invalid', message))
    return errors
