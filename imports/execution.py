"""Execução das linhas e comparação de planos (D7, D8).

A execução roda as operações reais do domínio na transação de quem chama, que
decide se as mantém (confirmação com plano idêntico) ou as desfaz (prévia e
divergência). Cada linha roda num savepoint próprio: a recusa de uma linha,
inclusive por erro do banco, desfaz só aquela linha e vira erro no plano.
"""

import json
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from imports.definitions import RowError, RowPlan, errors_from_validation

DATABASE_ERROR = RowError(
    None, 'database', 'Os dados desta linha foram recusados pelo banco de dados. Confira os valores da linha.',
)


@dataclass
class Plan:
    rows: list = field(default_factory=list)
    file_errors: list = field(default_factory=list)

    @property
    def has_errors(self):
        return bool(self.file_errors) or any(row_plan.errors for _, row_plan in self.rows)

    def file_errors_data(self):
        return [{'code': error.code, 'message': error.message} for error in self.file_errors]

    def comparable(self):
        return comparable(
            [
                (
                    row.line_number, row_plan.action, row_plan.target, row_plan.changes, row_plan.warnings,
                    [{'column': error.column, 'code': error.code} for error in row_plan.errors],
                )
                for row, row_plan in self.rows
            ],
            self.file_errors_data(),
        )


def canonical(value):
    return json.loads(json.dumps(value))


def comparable(rows, file_errors):
    """Estrutura comparada entre prévia e confirmação (D8).

    Entram ação, alvo, mudanças, avisos e os pares de coluna e código dos erros de
    cada linha, e os códigos dos erros do arquivo. Mensagens e valores lidos ficam
    de fora. A normalização por JSON e a ordenação tornam o resultado determinístico.
    """
    return canonical({
        'rows': [
            {
                'line': line_number,
                'action': action,
                'target': None if target is None else str(target),
                'changes': changes,
                'warnings': sorted(warnings),
                'errors': sorted(
                    ((error.get('column') or '', error['code']) for error in errors),
                ),
            }
            for line_number, action, target, changes, warnings, errors in rows
        ],
        'file_errors': sorted(error['code'] for error in file_errors),
    })


def execute_row(definition, row, executor):
    if row.errors:
        return RowPlan(errors=list(row.errors))
    try:
        with transaction.atomic():
            row_plan = definition.execute_row(row.values, executor)
            if row_plan.errors:
                transaction.set_rollback(True)
    except ValidationError as error:
        return RowPlan(errors=errors_from_validation(error, definition.columns_by_field))
    except DatabaseError:
        return RowPlan(errors=[DATABASE_ERROR])
    if row_plan.target is not None:
        row_plan.target = str(row_plan.target)
    return row_plan


def run(definition, rows, executor):
    """Trava, executa cada linha e as verificações do arquivo, e devolve o Plan."""
    with definition.execution():
        definition.lock(rows, executor)
        plan = Plan(rows=[(row, execute_row(definition, row, executor)) for row in rows])
        plan.file_errors = list(definition.check_file(executor))
    return plan
