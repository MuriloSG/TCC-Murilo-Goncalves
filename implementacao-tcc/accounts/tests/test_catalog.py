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

    def test_capability_and_reserved_sets(self):
        with self.subTest('capacidade administrativa'):
            self.assertEqual(permissions.ADMINISTRATIVE_CAPABILITY, USER_CODES)
        with self.subTest('reservadas'):
            self.assertEqual(permissions.SUPERADMIN_RESERVED_PERMISSIONS, ROLE_CODES | {permissions.SETTINGS_EDIT})


class InitialCatalogTests(TestCase):
    def test_database_catalog_matches_the_constants(self):
        with self.subTest('códigos'):
            codes = set(Permission.objects.values_list('code', flat=True))
            self.assertEqual(codes, set(permissions.ALL_PERMISSIONS))
        with self.subTest('descrições'):
            self.assertFalse(Permission.objects.filter(description='').exists())

    def test_initial_roles_exist(self):
        self.assertEqual(set(Role.objects.values_list('code', flat=True)), {'ADMINISTRADOR', 'DOCENTE'})

    def test_initial_roles_grant_their_permissions(self):
        with self.subTest('administrador'):
            administrator = Role.objects.get(code='ADMINISTRADOR')
            self.assertEqual(
                set(administrator.permissions.values_list('code', flat=True)),
                permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS - permissions.ACADEMIC_SCOPE_PERMISSIONS,
            )
        with self.subTest('docente'):
            teacher = Role.objects.get(code='DOCENTE')
            self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)

    def test_no_role_grants_reserved_or_academic_scope_permissions(self):
        with self.subTest('alcance acadêmico'):
            self.assertFalse(
                RolePermission.objects.filter(permission__code__in=permissions.ACADEMIC_SCOPE_PERMISSIONS).exists()
            )
        with self.subTest('reservada'):
            self.assertFalse(
                RolePermission.objects.filter(
                    permission__code__in=permissions.SUPERADMIN_RESERVED_PERMISSIONS
                ).exists()
            )
