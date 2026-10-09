"""Perfis de teste definidos só pelas permissões, sem depender dos perfis criados pela carga inicial."""

from accounts import permissions
from accounts.models import Permission, Role

MANAGEMENT_PERMISSIONS = (
    permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS - permissions.ACADEMIC_SCOPE_PERMISSIONS
)
REQUESTER_PERMISSIONS = frozenset({permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST})
MANAGEMENT = 'GESTAO'
REQUESTER = 'SOLICITACAO'


def role_with(code, *codes, name=None):
    """Perfil pelo código, criado na primeira chamada com as permissões informadas."""
    role, created = Role.objects.get_or_create(code=code, defaults={'name': name or code.capitalize()})
    if created:
        role.permissions.set(Permission.objects.filter(code__in=codes))
    return role


def management_role():
    return role_with(MANAGEMENT, *MANAGEMENT_PERMISSIONS, name='Gestão')


def requester_role():
    return role_with(REQUESTER, *REQUESTER_PERMISSIONS, name='Solicitação')
