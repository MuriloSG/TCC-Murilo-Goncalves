"""Importação de teste sobre auth.Group, para testar o motor sem depender de um app de domínio."""

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection

from imports.definitions import Column, ImportDefinition, RowError, RowPlan

FORBIDDEN = 'PROIBIDO'


class GroupImport(ImportDefinition):
    """Cria o grupo do nome da linha ou o deixa como está.

    "ERRO" recusa a linha pelo model, "BANCO" provoca erro do banco, "FALHA" lança
    uma exceção inesperada e um grupo "PROIBIDO" ao fim reprova o arquivo.
    """

    kind = 'GRUPO'
    columns = (Column('Nome'),)
    identifier = 'Nome'
    columns_by_field = {'name': 'Nome'}
    locked = None

    def lock(self, rows, executor):
        self.locked = [row.line_number for row in rows]

    def execute_row(self, values, executor):
        name = values['Nome'].strip()
        if name == 'ERRO':
            raise ValidationError({'name': ValidationError('Nome recusado.', code='refused')})
        if name == 'BANCO':
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM tabela_inexistente')
        if name == 'FALHA':
            raise RuntimeError('falha inesperada')
        group = Group.objects.filter(name=name).first()
        if group is not None:
            return RowPlan(action='unchanged', target=group.pk)
        if name.startswith('AVISO'):
            group = Group.objects.create(name=name)
            return RowPlan(action='create', changes={'name': [None, name]}, warnings=['aviso'], created=group.pk)
        group = Group.objects.create(name=name)
        return RowPlan(action='create', changes={'name': [None, name]}, created=group.pk)

    def check_file(self, executor):
        if Group.objects.filter(name=FORBIDDEN).exists():
            return [RowError(None, 'forbidden', 'Grupo proibido.')]
        return []
