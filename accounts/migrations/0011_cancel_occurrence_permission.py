"""Permissão ENSALAMENTO.CANCELAR_OCORRENCIA, concedida ao perfil de sistema ADMINISTRADOR.

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: código literal, idempotente
e concessão só ao perfil do sistema, sem alterar as demais permissões dos perfis existentes.
O docente da aula cancela as ocorrências dela sem esta permissão (Change
cancelar-ocorrencia-do-ensalamento).
"""

from django.db import migrations

CODE = 'ENSALAMENTO.CANCELAR_OCORRENCIA'
DESCRIPTION = 'Cancelar a ocorrência de qualquer aula do ensalamento numa data'


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
        ('accounts', '0010_booking_permissions'),
    ]

    operations = [
        migrations.RunPython(add_permission, remove_permission),
    ]
