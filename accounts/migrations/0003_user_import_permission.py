"""Permissão USUARIO.IMPORTAR, concedida ao perfil de sistema ADMINISTRADOR (D15).

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: códigos literais,
idempotente e concessão só ao perfil do sistema, sem alterar as demais permissões
concedidas pelos perfis existentes.
"""

from django.db import migrations

CODE = 'USUARIO.IMPORTAR'
DESCRIPTION = 'Importar usuários por planilha e consultar o histórico das importações'


def add_import_permission(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    permission, _ = Permission.objects.get_or_create(code=CODE, defaults={'description': DESCRIPTION})
    for role in Role.objects.filter(code='ADMINISTRADOR', is_system=True):
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_import_permission(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code=CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_system_roles_and_permissions'),
    ]

    operations = [
        migrations.RunPython(add_import_permission, remove_import_permission),
    ]
