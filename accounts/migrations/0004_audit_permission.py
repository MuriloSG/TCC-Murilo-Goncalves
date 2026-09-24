"""Permissão AUDITORIA.VISUALIZAR, concedida ao perfil de sistema ADMINISTRADOR (D12).

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: códigos literais,
idempotente e concessão só ao perfil do sistema, sem alterar as demais permissões
concedidas pelos perfis existentes.
"""

from django.db import migrations

CODE = 'AUDITORIA.VISUALIZAR'
DESCRIPTION = 'Consultar os registros de auditoria do sistema'


def add_audit_permission(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    permission, _ = Permission.objects.get_or_create(code=CODE, defaults={'description': DESCRIPTION})
    for role in Role.objects.filter(code='ADMINISTRADOR', is_system=True):
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_audit_permission(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code=CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_import_permission'),
    ]

    operations = [
        migrations.RunPython(add_audit_permission, remove_audit_permission),
    ]
