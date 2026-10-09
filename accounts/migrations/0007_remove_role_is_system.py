"""Remove a marca de perfil do sistema: os perfis da carga inicial passam a ser perfis comuns.

Os perfis, os vínculos e as concessões existentes ficam como estão. A reversão recria a coluna e
marca de novo ADMINISTRADOR e DOCENTE, como a 0002 deixou, para que a reversão dela continue funcionando.
"""

from django.db import migrations, models

INITIAL_ROLES = ['ADMINISTRADOR', 'DOCENTE']


def mark_initial_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Role.objects.filter(code__in=INITIAL_ROLES).update(is_system=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_academic_scope_permissions'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, mark_initial_roles),
        migrations.RemoveField(
            model_name='role',
            name='is_system',
        ),
    ]
