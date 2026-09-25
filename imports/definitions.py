"""Contrato das importações específicas (D4).

Cada app estende ImportDefinition e declara colunas, identificador, travamento,
execução de uma linha, verificações do arquivo e rótulos. O motor trata o plano
como dado e não interpreta o seu conteúdo.
"""

from contextlib import nullcontext
from dataclasses import dataclass, field

from django.core.exceptions import NON_FIELD_ERRORS


@dataclass(frozen=True)
class Column:
    """Coluna declarada.

    A coluna é sempre exigida no cabeçalho. `required` diz respeito à célula: numa
    coluna opcional, a célula vazia é entregue à importação específica como texto
    vazio, em vez de virar erro da linha.
    """

    label: str
    required: bool = True


@dataclass(frozen=True)
class RowFilter:
    """Recorte das linhas oferecido na prévia, por um valor de uma coluna lógica.

    `columns` limita as colunas exibidas enquanto o recorte está escolhido, para que a
    tabela mostre só o que importa naquele recorte. Vazio mantém todas as colunas.
    """

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
    """Decisão sobre uma linha: ação, alvo, mudanças, avisos e erros (D8).

    `created` é a chave do registro criado pela linha. Fica fora da comparação e só
    é gravado na conclusão, porque a chave gerada na prévia desaparece no rollback.
    """

    action: str | None = None
    target: str | None = None
    changes: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    created: str | None = None


class ImportDefinition:
    kind = ''
    audit_resource = ''
    columns = ()
    identifier = ''
    columns_by_field = {}
    action_labels = {}
    field_labels = {}
    warning_labels = {}
    upload_fields = {}
    row_filters = ()
    max_file_size = None
    max_rows = None
    has_template = True

    def source(self):
        """Fonte que lê o arquivo enviado. A leitura de CSV é o padrão.

        O import é local porque o leitor depende deste módulo, e não o contrário.
        """
        from imports.reader import CsvSource

        return CsvSource()

    def file_columns(self):
        """Colunas que vêm do arquivo, sem as colunas lógicas preenchidas pelo envio."""
        return tuple(column for column in self.columns if column.label not in self.upload_fields)

    def normalize_identifier(self, value):
        return value.strip()

    def execution(self):
        """Contexto aberto em volta de todas as linhas e das verificações do arquivo."""
        return nullcontext()

    def lock(self, rows, executor):
        """Trava o que a execução vai ler, antes da primeira linha."""

    def execute_row(self, values, executor):
        """Executa a linha com as operações reais do domínio e devolve o RowPlan."""
        raise NotImplementedError

    def check_file(self, executor):
        """Verificações do arquivo inteiro, depois de todas as linhas. Devolve RowError sem coluna."""
        return []

    def audit_metadata(self, rows):
        """Informações adicionais próprias da importação nos registros de auditoria.

        Recebe as linhas, cada uma com os valores lidos, e devolve valores canônicos.
        """
        return {}


def errors_from_validation(error, columns_by_field):
    """Traduz uma ValidationError do model em erros de coluna, com as mensagens do próprio model.

    Campos fora do mapa e erros gerais ficam sem coluna.
    """
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
