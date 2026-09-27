"""Permissão de criar solicitação de agendamento em nome de outro usuário, concedida ao perfil ADMINISTRADOR.

Segue a D4 da Change criar-agendamento-para-outro-usuario, no mesmo formato da migration das
permissões de disciplina e turma: código literal, idempotente e concessão só ao perfil do
sistema, sem alterar as demais permissões concedidas pelos perfis existentes.
"""

from django.db import migrations

PERMISSIONS = {
    'AGENDA.CRIAR': 'Criar solicitação de agendamento em nome de outro usuário',
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
        ('accounts', '0013_academic_permissions'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
