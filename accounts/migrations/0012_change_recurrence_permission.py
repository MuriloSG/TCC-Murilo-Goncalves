"""Permissão ENSALAMENTO.ALTERAR_RECORRENCIA, concedida ao perfil de sistema ADMINISTRADOR.

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: código literal, idempotente
e concessão só ao perfil do sistema, sem alterar as demais permissões dos perfis existentes.
Diferente do cancelamento de uma ocorrência, o docente da aula não altera a recorrência sem
esta permissão (Change alterar-recorrencia-do-ensalamento).
"""

from django.db import migrations

CODE = 'ENSALAMENTO.ALTERAR_RECORRENCIA'
DESCRIPTION = 'Alterar a recorrência de uma aula do ensalamento a partir de uma data'


def add_permission(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    permission, _ = Permission.objects.get_or_create(code=CODE, defaults={'description': DESCRIPTION})
    for role in Role.objects.filter(code='ADMINISTRADOR', is_system=True):
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_permission(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code=CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_cancel_occurrence_permission'),
    ]

    operations = [
        migrations.RunPython(add_permission, remove_permission),
    ]
