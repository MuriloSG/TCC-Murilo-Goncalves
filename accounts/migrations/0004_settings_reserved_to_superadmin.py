"""Retira dos perfis a CONFIGURACAO.EDITAR, que passou a ser reservada ao superadmin.

O código é escrito literalmente, como na 0002. A reversão devolve a permissão ao ADMINISTRADOR.
"""

from django.db import migrations

CODE = 'CONFIGURACAO.EDITAR'
GRANTED_ROLE = 'ADMINISTRADOR'


def revoke(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.filter(permission__code=CODE).delete()


def restore(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')
    role = Role.objects.filter(code=GRANTED_ROLE).first()
    permission = Permission.objects.filter(code=CODE).first()
    if role is not None and permission is not None:
        RolePermission.objects.get_or_create(role=role, permission=permission)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_course_permissions'),
    ]

    operations = [
        migrations.RunPython(revoke, restore),
    ]
