"""Permissões do cadastro de espaços, concedidas ao perfil de sistema ADMINISTRADOR.

Seguem a D9 da Change gerenciar-usuarios-e-controle-de-acesso e a D11 da Change
manipulacao-dos-espacos: códigos literais, idempotente e concessão só ao perfil do sistema,
sem alterar as demais permissões concedidas pelos perfis existentes.
"""

from django.db import migrations

PERMISSIONS = {
    'ESPACO.VISUALIZAR': 'Consultar a lista de espaços',
    'ESPACO.CRIAR': 'Cadastrar espaço, inclusive pela confirmação da importação de ensalamento',
    'ESPACO.EDITAR': 'Alterar o nome e os outros nomes de um espaço, inclusive pela importação de ensalamento',
    'ESPACO.ALTERAR_SITUACAO': 'Desativar e reativar espaço, inclusive pela importação de ensalamento',
    'ESPACO.EXCLUIR': 'Excluir espaço sem aulas no ensalamento',
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
        ('accounts', '0008_space_allocation_permissions'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
