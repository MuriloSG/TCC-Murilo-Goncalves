"""Importação de teste sobre auth.Group, para testar o motor sem depender de um app de domínio."""

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection

from audit import catalog
from imports.definitions import Column, ImportDefinition, RowError, RowPlan

FORBIDDEN = 'PROIBIDO'


class GroupImport(ImportDefinition):
    """"ERRO", "BANCO", "FALHA", "PROIBIDO" e "DECIDIR" provocam cada tipo de recusa do motor."""

    kind = 'GRUPO'
    audit_resource = catalog.USER_IMPORT
    columns = (Column('Nome'),)
    identifier = 'Nome'
    columns_by_field = {'name': 'Nome'}
    locked = None
    refusal = None
    received = None
    pending_labels = {'decidir': 'Decida o grupo {key}.'}

    def execution(self, importation=None):
        self.received = importation
        return super().execution(importation)

    def lock(self, rows, executor):
        self.locked = [row.line_number for row in rows]

    def check_confirmation(self, importation, executor):
        if self.refusal:
            raise ValidationError(self.refusal)

    def execute_row(self, values, executor):
        name = values['Nome'].strip()
        if name == 'ERRO':
            raise ValidationError({'name': ValidationError('Nome recusado.', code='refused')})
        if name == 'BANCO':
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM tabela_inexistente')
        if name == 'FALHA':
            raise RuntimeError('falha inesperada')
        if name == 'DECIDIR' and not Group.objects.filter(name='DECIDIDO').exists():
            Group.objects.create(name='DECIDIR')
            return RowPlan(pending=[{'code': 'decidir', 'key': name}])
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
