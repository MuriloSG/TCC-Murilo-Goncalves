from django.test import SimpleTestCase, TestCase

from accounts import permissions
from accounts.models import Permission, Role, RolePermission

USER_CODES = {
    'USUARIO.VISUALIZAR',
    'USUARIO.CRIAR',
    'USUARIO.EDITAR',
    'USUARIO.ALTERAR_PERFIL',
    'USUARIO.ALTERAR_SITUACAO',
}
ROLE_CODES = {
    'PERFIL.VISUALIZAR',
    'PERFIL.CRIAR',
    'PERFIL.EDITAR',
    'PERFIL.ALTERAR_PERMISSOES',
    'PERFIL.EXCLUIR',
}


class PermissionConstantsTests(SimpleTestCase):
    def test_constant_codes(self):
        self.assertEqual(permissions.USER_VIEW, 'USUARIO.VISUALIZAR')
        self.assertEqual(permissions.USER_CREATE, 'USUARIO.CRIAR')
        self.assertEqual(permissions.USER_EDIT, 'USUARIO.EDITAR')
        self.assertEqual(permissions.USER_CHANGE_ROLE, 'USUARIO.ALTERAR_PERFIL')
        self.assertEqual(permissions.USER_CHANGE_STATUS, 'USUARIO.ALTERAR_SITUACAO')
        self.assertEqual(permissions.ROLE_VIEW, 'PERFIL.VISUALIZAR')
        self.assertEqual(permissions.ROLE_CREATE, 'PERFIL.CRIAR')
        self.assertEqual(permissions.ROLE_EDIT, 'PERFIL.EDITAR')
        self.assertEqual(permissions.ROLE_CHANGE_PERMISSIONS, 'PERFIL.ALTERAR_PERMISSOES')
        self.assertEqual(permissions.ROLE_DELETE, 'PERFIL.EXCLUIR')

    def test_all_permissions_has_the_ten_codes(self):
        self.assertEqual(permissions.ALL_PERMISSIONS, USER_CODES | ROLE_CODES)
        self.assertEqual(len(permissions.ALL_PERMISSIONS), 10)

    def test_codes_follow_the_format(self):
        for code in permissions.ALL_PERMISSIONS:
            with self.subTest(code=code):
                Permission(code=code, description='Teste').clean_fields()

    def test_administrative_capability_is_exactly_user_permissions(self):
        self.assertEqual(permissions.ADMINISTRATIVE_CAPABILITY, USER_CODES)

    def test_reserved_permissions_are_exactly_role_permissions(self):
        self.assertEqual(permissions.SUPERADMIN_RESERVED_PERMISSIONS, ROLE_CODES)

    def test_reserved_permissions_are_disjoint_from_administrative_capability(self):
        self.assertTrue(
            permissions.SUPERADMIN_RESERVED_PERMISSIONS.isdisjoint(permissions.ADMINISTRATIVE_CAPABILITY)
        )

    def test_sets_are_immutable(self):
        self.assertIsInstance(permissions.ADMINISTRATIVE_CAPABILITY, frozenset)
        self.assertIsInstance(permissions.SUPERADMIN_RESERVED_PERMISSIONS, frozenset)


class InitialCatalogTests(TestCase):
    """State left by migration 0002, before any change made by the superadmin."""

    def test_database_codes_match_constants(self):
        codes = set(Permission.objects.values_list('code', flat=True))
        self.assertEqual(codes, set(permissions.ALL_PERMISSIONS))
        self.assertEqual(Permission.objects.count(), 10)

    def test_reserved_permissions_exist_in_database(self):
        codes = set(Permission.objects.values_list('code', flat=True))
        self.assertLessEqual(permissions.SUPERADMIN_RESERVED_PERMISSIONS, codes)

    def test_every_permission_has_a_description(self):
        self.assertFalse(Permission.objects.filter(description='').exists())

    def test_system_roles_exist(self):
        codes = set(Role.objects.values_list('code', flat=True))
        self.assertEqual(codes, {'ADMINISTRADOR', 'DOCENTE'})

    def test_system_roles_are_marked_as_system(self):
        for code in ('ADMINISTRADOR', 'DOCENTE'):
            with self.subTest(code=code):
                self.assertTrue(Role.objects.get(code=code).is_system)

    def test_administrator_grants_administrative_capability(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertEqual(codes, set(permissions.ADMINISTRATIVE_CAPABILITY))

    def test_teacher_grants_no_permission(self):
        teacher = Role.objects.get(code='DOCENTE')
        self.assertFalse(teacher.permissions.exists())

    def test_no_role_grants_reserved_permission(self):
        self.assertFalse(
            RolePermission.objects.filter(
                permission__code__in=permissions.SUPERADMIN_RESERVED_PERMISSIONS
            ).exists()
        )
