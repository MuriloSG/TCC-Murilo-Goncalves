from django.db import migrations

# Codes are written literally, without importing accounts.permissions, so the
# migration stays reproducible if the constants change later (D8).
PERMISSIONS = [
    ('USUARIO.VISUALIZAR', 'Listar e consultar usuários'),
    ('USUARIO.CRIAR', 'Cadastrar usuário'),
    ('USUARIO.EDITAR', 'Alterar nome e e-mail de usuário'),
    ('USUARIO.ALTERAR_PERFIL', 'Trocar o perfil de um usuário'),
    ('USUARIO.ALTERAR_SITUACAO', 'Desativar e reativar usuário'),
    ('PERFIL.VISUALIZAR', 'Listar e consultar perfis e as permissões que concedem'),
    ('PERFIL.CRIAR', 'Criar perfil personalizado'),
    ('PERFIL.EDITAR', 'Alterar nome e descrição de um perfil'),
    ('PERFIL.ALTERAR_PERMISSOES', 'Definir as permissões concedidas por um perfil'),
    ('PERFIL.EXCLUIR', 'Excluir perfil personalizado sem usuários'),
]

SYSTEM_ROLES = [
    ('ADMINISTRADOR', 'Administrador'),
    ('DOCENTE', 'Docente'),
]

# Initial grants. DOCENTE receives nothing and no PERFIL.* is granted (D9).
INITIAL_GRANTS = {
    'ADMINISTRADOR': [
        'USUARIO.VISUALIZAR',
        'USUARIO.CRIAR',
        'USUARIO.EDITAR',
        'USUARIO.ALTERAR_PERFIL',
        'USUARIO.ALTERAR_SITUACAO',
    ],
}


def create_catalog(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    for code, description in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={'description': description})

    for code, name in SYSTEM_ROLES:
        Role.objects.get_or_create(code=code, defaults={'name': name, 'is_system': True})

    for role_code, permission_codes in INITIAL_GRANTS.items():
        role = Role.objects.get(code=role_code)
        for permission in Permission.objects.filter(code__in=permission_codes):
            RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_catalog(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')

    # Grants go away by CASCADE. Roles still linked to users fail by PROTECT.
    Role.objects.filter(code__in=[code for code, _ in SYSTEM_ROLES], is_system=True).delete()
    Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_catalog, remove_catalog),
    ]
