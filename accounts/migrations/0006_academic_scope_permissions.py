"""Permissões de alcance de todas as disciplinas e turmas, criadas sem concessão a nenhum perfil.

Os códigos são escritos literalmente, como na 0002. Sem concessão, o escopo de quem já usa o sistema
não muda: só o superadmin continua alcançando todos os registros até que algum perfil as receba.
"""

from django.db import migrations

PERMISSIONS = [
    ('DISCIPLINA.ACESSAR_TODAS', 'Alcançar todas as disciplinas, e não só as do próprio escopo'),
    ('TURMA.ACESSAR_TODAS', 'Alcançar todas as turmas, e não só as do próprio escopo'),
]


def create_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    for code, description in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={'description': description})


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_session_epoch'),
    ]

    operations = [
        migrations.RunPython(create_permissions, remove_permissions),
    ]
