"""Catalog of the permission codes defined by the accounts app.

The database records are created only by data migrations, which write the
codes literally. ``accounts/tests/test_catalog.py`` keeps both in sync.
"""

USER_VIEW = 'USUARIO.VISUALIZAR'
USER_CREATE = 'USUARIO.CRIAR'
USER_EDIT = 'USUARIO.EDITAR'
USER_CHANGE_ROLE = 'USUARIO.ALTERAR_PERFIL'
USER_CHANGE_STATUS = 'USUARIO.ALTERAR_SITUACAO'

ROLE_VIEW = 'PERFIL.VISUALIZAR'
ROLE_CREATE = 'PERFIL.CRIAR'
ROLE_EDIT = 'PERFIL.EDITAR'
ROLE_CHANGE_PERMISSIONS = 'PERFIL.ALTERAR_PERMISSOES'
ROLE_DELETE = 'PERFIL.EXCLUIR'

# Permissions a user must hold, all of them, to count as administrative
# capability (D10).
ADMINISTRATIVE_CAPABILITY = frozenset({
    USER_VIEW,
    USER_CREATE,
    USER_EDIT,
    USER_CHANGE_ROLE,
    USER_CHANGE_STATUS,
})

# Permissions held only by an active superadmin and never granted to a role
# (D21).
SUPERADMIN_RESERVED_PERMISSIONS = frozenset({
    ROLE_VIEW,
    ROLE_CREATE,
    ROLE_EDIT,
    ROLE_CHANGE_PERMISSIONS,
    ROLE_DELETE,
})

ALL_PERMISSIONS = ADMINISTRATIVE_CAPABILITY | SUPERADMIN_RESERVED_PERMISSIONS
