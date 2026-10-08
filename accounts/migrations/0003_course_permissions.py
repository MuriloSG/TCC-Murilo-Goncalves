"""Permissões do cadastro de cursos, concedidas ao perfil ADMINISTRADOR.

Os códigos são escritos literalmente, sem importar accounts.permissions, como na 0002.
Perfis personalizados não recebem as permissões novas. A reversão apaga só estas
permissões, e as concessões saem por CASCADE.
"""

from django.db import migrations

PERMISSIONS = [
    ('CURSO.CRIAR', 'Cadastrar curso'),
    ('CURSO.EDITAR', 'Alterar o nome e a etapa de um curso sem uso no ensalamento'),
    ('CURSO.EXCLUIR', 'Excluir curso sem turmas'),
    ('CURSO.VISUALIZAR', 'Consultar os cursos'),
]

GRANTED_ROLE = 'ADMINISTRADOR'


def create_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    for code, description in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={'description': description})

    role = Role.objects.filter(code=GRANTED_ROLE).first()
    if role is None:
        return
    for permission in Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]):
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_system_roles_and_permissions'),
    ]

    operations = [
        migrations.RunPython(create_permissions, remove_permissions),
    ]
