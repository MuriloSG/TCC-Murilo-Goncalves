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
    """Coluna declarada. Nesta versão toda coluna é obrigatória (D1)."""

    label: str


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
