"""Permissão RELATORIO.VISUALIZAR, concedida ao perfil de sistema ADMINISTRADOR.

Segue a D9 da Change gerenciar-usuarios-e-controle-de-acesso: código literal, idempotente
e concessão só ao perfil do sistema. Ela libera as rotas dos relatórios, e cada relatório
exige também a permissão do módulo dono dos dados (Change gerar-mapa-de-calor-dos-espacos).
"""

from django.db import migrations

CODE = 'RELATORIO.VISUALIZAR'
DESCRIPTION = 'Visualizar os relatórios'


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
        ('accounts', '0017_panel_permission'),
    ]

    operations = [
        migrations.RunPython(add_permission, remove_permission),
    ]
