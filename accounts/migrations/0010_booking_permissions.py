"""Permissões da Agenda, com as concessões iniciais aos perfis de sistema.

Seguem a D2 da Change agendar-uso-eventual-dos-espacos: códigos literais, idempotente,
`ADMINISTRADOR` com as três e `DOCENTE` com visualizar e solicitar, sem alterar as demais
permissões concedidas pelos perfis existentes.
"""

from django.db import migrations

PERMISSIONS = {
    'AGENDA.VISUALIZAR': 'Consultar a Grade da Agenda',
    'AGENDA.SOLICITAR': 'Solicitar agendamento, consultar as próprias solicitações e responder à alternativa sugerida',
    'AGENDA.ANALISAR': 'Consultar as solicitações de agendamento, aprovar, rejeitar e sugerir alternativa',
}

GRANTS = {
    'ADMINISTRADOR': ('AGENDA.VISUALIZAR', 'AGENDA.SOLICITAR', 'AGENDA.ANALISAR'),
    'DOCENTE': ('AGENDA.VISUALIZAR', 'AGENDA.SOLICITAR'),
}


def add_permissions(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    created = {
        code: Permission.objects.get_or_create(code=code, defaults={'description': description})[0]
        for code, description in PERMISSIONS.items()
    }
    for role_code, codes in GRANTS.items():
        for role in Role.objects.filter(code=role_code, is_system=True):
            for code in codes:
                RolePermission.objects.get_or_create(role=role, permission=created[code])


def remove_permissions(apps, schema_editor):
    """As concessões saem por CASCADE."""
    apps.get_model('accounts', 'Permission').objects.filter(code__in=PERMISSIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_space_permissions'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
