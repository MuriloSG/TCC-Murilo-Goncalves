"""Permissões de consulta do ensalamento e de exclusão das importações, concedidas ao ADMINISTRADOR.

ENSALAMENTO.VISUALIZAR, USUARIO.EXCLUIR_IMPORTACAO e ENSALAMENTO.EXCLUIR_IMPORTACAO seguem a D9 da Change
gerenciar-usuarios-e-controle-de-acesso: códigos literais, idempotente e concessão só ao
perfil do sistema, sem alterar as demais permissões concedidas pelos perfis existentes.
"""

from django.db import migrations

PERMISSIONS = {
    'ENSALAMENTO.VISUALIZAR': 'Consultar a grade do ensalamento confirmado',
    'USUARIO.EXCLUIR_IMPORTACAO': 'Excluir importações de usuários descartadas ou com erros',
    'ENSALAMENTO.EXCLUIR_IMPORTACAO': 'Excluir importações de ensalamento descartadas ou com erros',
}


def add_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    for code, description in PERMISSIONS.items():
        permission, _ = Permission.objects.get_or_create(code=code, defaults={'description': description})
        for role in Role.objects.filter(code='ADMINISTRADOR', is_system=True):
            RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_permissions(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_space_allocation_permission'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
