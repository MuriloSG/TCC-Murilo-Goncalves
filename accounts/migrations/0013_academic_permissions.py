"""Permissões das áreas de disciplinas e turmas, concedidas ao perfil de sistema ADMINISTRADOR.

Seguem a D3 da Change gerenciar-disciplinas-e-turmas, no mesmo formato da migration das
permissões de espaço: códigos literais, idempotente e concessão só ao perfil do sistema, sem
alterar as demais permissões concedidas pelos perfis existentes.
"""

from django.db import migrations

PERMISSIONS = {
    'DISCIPLINA.VISUALIZAR': 'Consultar as disciplinas do próprio escopo',
    'DISCIPLINA.CRIAR': 'Cadastrar disciplina',
    'DISCIPLINA.EDITAR': 'Alterar o nome de uma disciplina do próprio escopo sem uso no ensalamento',
    'DISCIPLINA.EXCLUIR': 'Excluir disciplina do próprio escopo sem uso no ensalamento',
    'TURMA.VISUALIZAR': 'Consultar as turmas do próprio escopo',
    'TURMA.CRIAR': 'Cadastrar turma de um curso',
    'TURMA.EDITAR': 'Alterar o rótulo de uma turma do próprio escopo sem uso no ensalamento',
    'TURMA.EXCLUIR': 'Excluir turma do próprio escopo sem uso no ensalamento',
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
        ('accounts', '0012_change_recurrence_permission'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
