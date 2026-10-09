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
TEACHER_CODES = {'AGENDA.VISUALIZAR', 'AGENDA.SOLICITAR'}
ROLE_CODES = {
    'PERFIL.VISUALIZAR',
    'PERFIL.CRIAR',
    'PERFIL.EDITAR',
    'PERFIL.ALTERAR_PERMISSOES',
    'PERFIL.EXCLUIR',
}


class PermissionConstantsTests(SimpleTestCase):
    def test_codes_follow_the_format(self):
        for code in permissions.ALL_PERMISSIONS:
            with self.subTest(code=code):
                Permission(code=code, description='Teste').clean_fields()

    def test_administrative_capability_is_user_management_without_import(self):
        self.assertEqual(permissions.ADMINISTRATIVE_CAPABILITY, USER_CODES)

    def test_reserved_permissions_are_role_and_settings_permissions(self):
        self.assertEqual(permissions.SUPERADMIN_RESERVED_PERMISSIONS, ROLE_CODES | {permissions.SETTINGS_EDIT})


class InitialCatalogTests(TestCase):
    def test_database_codes_match_constants(self):
        codes = set(Permission.objects.values_list('code', flat=True))
        self.assertEqual(codes, set(permissions.ALL_PERMISSIONS))

    def test_every_permission_has_a_description(self):
        self.assertFalse(Permission.objects.filter(description='').exists())

    def test_initial_roles_exist(self):
        self.assertEqual(set(Role.objects.values_list('code', flat=True)), {'ADMINISTRADOR', 'DOCENTE'})

    def test_administrator_grants_every_permission_not_reserved(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        self.assertEqual(
            set(administrator.permissions.values_list('code', flat=True)),
            permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS - permissions.ACADEMIC_SCOPE_PERMISSIONS,
        )

    def test_teacher_grants_only_the_booking_request(self):
        teacher = Role.objects.get(code='DOCENTE')
        self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)

    def test_no_role_grants_academic_scope_permission(self):
        self.assertFalse(
            RolePermission.objects.filter(permission__code__in=permissions.ACADEMIC_SCOPE_PERMISSIONS).exists()
        )

    def test_no_role_grants_reserved_permission(self):
        self.assertFalse(
            RolePermission.objects.filter(
                permission__code__in=permissions.SUPERADMIN_RESERVED_PERMISSIONS
            ).exists()
        )

