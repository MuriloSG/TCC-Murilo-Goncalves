"""Permissão ENSALAMENTO.IMPORTAR, concedida ao perfil de sistema ADMINISTRADOR.

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: códigos literais,
idempotente e concessão só ao perfil do sistema, sem alterar as demais permissões
concedidas pelos perfis existentes.
"""

from django.db import migrations

CODE = 'ENSALAMENTO.IMPORTAR'
DESCRIPTION = 'Importar o ensalamento de um semestre pela planilha institucional'


def add_space_allocation_permission(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    permission, _ = Permission.objects.get_or_create(code=CODE, defaults={'description': DESCRIPTION})
    for role in Role.objects.filter(code='ADMINISTRADOR', is_system=True):
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_space_allocation_permission(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code=CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_username'),
    ]

    operations = [
        migrations.RunPython(add_space_allocation_permission, remove_space_allocation_permission),
    ]
