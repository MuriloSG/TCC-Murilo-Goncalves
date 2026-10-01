from importlib import import_module

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from accounts import permissions
from accounts.models import Permission, Role, RolePermission, User

USER_CODES = {
    'USUARIO.VISUALIZAR',
    'USUARIO.CRIAR',
    'USUARIO.EDITAR',
    'USUARIO.ALTERAR_PERFIL',
    'USUARIO.ALTERAR_SITUACAO',
}
IMPORT_CODE = 'USUARIO.IMPORTAR'
IMPORT_DELETE_CODE = 'USUARIO.EXCLUIR_IMPORTACAO'
AUDIT_CODE = 'AUDITORIA.VISUALIZAR'
NOTICE_CODE = 'NOTIFICACAO.PUBLICAR'
SPACE_ALLOCATION_VIEW_CODE = 'ENSALAMENTO.VISUALIZAR'
SPACE_ALLOCATION_CODE = 'ENSALAMENTO.IMPORTAR'
SPACE_ALLOCATION_DELETE_CODE = 'ENSALAMENTO.EXCLUIR_IMPORTACAO'
SPACE_ALLOCATION_CANCEL_CODE = 'ENSALAMENTO.CANCELAR_OCORRENCIA'
SPACE_ALLOCATION_CHANGE_CODE = 'ENSALAMENTO.ALTERAR_RECORRENCIA'
SPACE_ALLOCATION_CREATE_CODE = 'ENSALAMENTO.CRIAR_RECORRENCIA'
NEW_CODES = [SPACE_ALLOCATION_VIEW_CODE, IMPORT_DELETE_CODE, SPACE_ALLOCATION_DELETE_CODE]
SPACE_CODES = {'ESPACO.VISUALIZAR', 'ESPACO.CRIAR', 'ESPACO.EDITAR', 'ESPACO.ALTERAR_SITUACAO', 'ESPACO.EXCLUIR'}
BOOKING_CODES = {'AGENDA.VISUALIZAR', 'AGENDA.SOLICITAR', 'AGENDA.ANALISAR'}
BOOKING_CREATE_CODE = 'AGENDA.CRIAR'
ACADEMIC_CODES = {
    'DISCIPLINA.VISUALIZAR', 'DISCIPLINA.CRIAR', 'DISCIPLINA.EDITAR', 'DISCIPLINA.EXCLUIR',
    'TURMA.VISUALIZAR', 'TURMA.CRIAR', 'TURMA.EDITAR', 'TURMA.EXCLUIR',
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
    def test_constant_codes(self):
        self.assertEqual(permissions.USER_VIEW, 'USUARIO.VISUALIZAR')
        self.assertEqual(permissions.USER_CREATE, 'USUARIO.CRIAR')
        self.assertEqual(permissions.USER_EDIT, 'USUARIO.EDITAR')
        self.assertEqual(permissions.USER_CHANGE_ROLE, 'USUARIO.ALTERAR_PERFIL')
        self.assertEqual(permissions.USER_CHANGE_STATUS, 'USUARIO.ALTERAR_SITUACAO')
        self.assertEqual(permissions.USER_IMPORT, 'USUARIO.IMPORTAR')
        self.assertEqual(permissions.USER_IMPORT_DELETE, 'USUARIO.EXCLUIR_IMPORTACAO')
        self.assertEqual(permissions.ROLE_VIEW, 'PERFIL.VISUALIZAR')
        self.assertEqual(permissions.ROLE_CREATE, 'PERFIL.CRIAR')
        self.assertEqual(permissions.ROLE_EDIT, 'PERFIL.EDITAR')
        self.assertEqual(permissions.ROLE_CHANGE_PERMISSIONS, 'PERFIL.ALTERAR_PERMISSOES')
        self.assertEqual(permissions.ROLE_DELETE, 'PERFIL.EXCLUIR')
        self.assertEqual(permissions.AUDIT_VIEW, 'AUDITORIA.VISUALIZAR')
        self.assertEqual(permissions.NOTICE_PUBLISH, 'NOTIFICACAO.PUBLICAR')
        self.assertEqual(permissions.SPACE_ALLOCATION_VIEW, 'ENSALAMENTO.VISUALIZAR')
        self.assertEqual(permissions.SPACE_ALLOCATION_IMPORT, 'ENSALAMENTO.IMPORTAR')
        self.assertEqual(permissions.SPACE_ALLOCATION_IMPORT_DELETE, 'ENSALAMENTO.EXCLUIR_IMPORTACAO')
        self.assertEqual(permissions.SPACE_VIEW, 'ESPACO.VISUALIZAR')
        self.assertEqual(permissions.SPACE_CREATE, 'ESPACO.CRIAR')
        self.assertEqual(permissions.SPACE_EDIT, 'ESPACO.EDITAR')
        self.assertEqual(permissions.SPACE_CHANGE_STATUS, 'ESPACO.ALTERAR_SITUACAO')
        self.assertEqual(permissions.SPACE_DELETE, 'ESPACO.EXCLUIR')
        self.assertEqual(permissions.BOOKING_CREATE, 'AGENDA.CRIAR')

    def test_all_permissions_has_every_code(self):
        self.assertEqual(
            permissions.ALL_PERMISSIONS,
            USER_CODES | {IMPORT_CODE, IMPORT_DELETE_CODE, AUDIT_CODE, NOTICE_CODE, SPACE_ALLOCATION_VIEW_CODE, SPACE_ALLOCATION_CODE, SPACE_ALLOCATION_DELETE_CODE, SPACE_ALLOCATION_CANCEL_CODE, SPACE_ALLOCATION_CHANGE_CODE, SPACE_ALLOCATION_CREATE_CODE} | SPACE_CODES | BOOKING_CODES | {BOOKING_CREATE_CODE} | ACADEMIC_CODES | ROLE_CODES,
        )
        self.assertEqual(len(permissions.ALL_PERMISSIONS), 37)

    def test_codes_follow_the_format(self):
        for code in permissions.ALL_PERMISSIONS:
            with self.subTest(code=code):
                Permission(code=code, description='Teste').clean_fields()

    def test_administrative_capability_is_user_management_without_import(self):
        self.assertEqual(permissions.ADMINISTRATIVE_CAPABILITY, USER_CODES)
        self.assertNotIn(IMPORT_CODE, permissions.ADMINISTRATIVE_CAPABILITY)
        self.assertNotIn(IMPORT_CODE, permissions.SUPERADMIN_RESERVED_PERMISSIONS)
        self.assertNotIn(AUDIT_CODE, permissions.ADMINISTRATIVE_CAPABILITY)
        self.assertNotIn(AUDIT_CODE, permissions.SUPERADMIN_RESERVED_PERMISSIONS)
        self.assertNotIn(NOTICE_CODE, permissions.ADMINISTRATIVE_CAPABILITY)
        self.assertNotIn(NOTICE_CODE, permissions.SUPERADMIN_RESERVED_PERMISSIONS)

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
    def test_database_codes_match_constants(self):
        codes = set(Permission.objects.values_list('code', flat=True))
        self.assertEqual(codes, set(permissions.ALL_PERMISSIONS))
        self.assertEqual(Permission.objects.count(), 37)

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

    def test_administrator_grants_administrative_capability_import_audit_notice_and_space_allocation(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertEqual(
            codes,
            set(permissions.ADMINISTRATIVE_CAPABILITY)
            | {IMPORT_CODE, IMPORT_DELETE_CODE, AUDIT_CODE, NOTICE_CODE, SPACE_ALLOCATION_VIEW_CODE, SPACE_ALLOCATION_CODE, SPACE_ALLOCATION_DELETE_CODE, SPACE_ALLOCATION_CANCEL_CODE, SPACE_ALLOCATION_CHANGE_CODE, SPACE_ALLOCATION_CREATE_CODE}
            | SPACE_CODES
            | BOOKING_CODES
            | {BOOKING_CREATE_CODE}
            | ACADEMIC_CODES,
        )

    def test_teacher_grants_only_the_booking_request(self):
        teacher = Role.objects.get(code='DOCENTE')
        self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)

    def test_no_role_grants_reserved_permission(self):
        self.assertFalse(
            RolePermission.objects.filter(
                permission__code__in=permissions.SUPERADMIN_RESERVED_PERMISSIONS
            ).exists()
        )


class ImportPermissionMigrationTests(TestCase):
    def test_grants_import_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0003_user_import_permission')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code=IMPORT_CODE).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_import_permission(apps, None)
        migration.add_import_permission(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertIn(IMPORT_CODE, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code=IMPORT_CODE).count(), 1)


class AuditPermissionMigrationTests(TestCase):
    def test_grants_audit_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0004_audit_permission')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code=AUDIT_CODE).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_audit_permission(apps, None)
        migration.add_audit_permission(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertIn(AUDIT_CODE, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code=AUDIT_CODE).count(), 1)


class NoticePermissionMigrationTests(TestCase):
    def test_grants_notice_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0005_notice_permission')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code=NOTICE_CODE).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_notice_permission(apps, None)
        migration.add_notice_permission(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertIn(NOTICE_CODE, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code=NOTICE_CODE).count(), 1)


class SpaceAllocationPermissionsMigrationTests(TestCase):
    def test_grants_the_deletion_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0008_space_allocation_permissions')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code__in=NEW_CODES).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_permissions(apps, None)
        migration.add_permissions(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertLessEqual(set(NEW_CODES), administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code__in=NEW_CODES).count(), 3)


class SpacePermissionsMigrationTests(TestCase):
    def test_grants_the_space_permissions_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0009_space_permissions')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code__in=SPACE_CODES).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_permissions(apps, None)
        migration.add_permissions(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertLessEqual(SPACE_CODES, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code__in=SPACE_CODES).count(), 5)

    def test_space_permissions_can_be_granted_to_a_custom_role(self):
        superadmin = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
        coordination = Role.objects.create_role('COORDENACAO', 'Coordenação')
        coordination.set_permissions([Permission.objects.get(code='ESPACO.CRIAR')])
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'ESPACO.CRIAR'})


class BookingPermissionsMigrationTests(TestCase):
    def test_grants_the_booking_permissions_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0010_booking_permissions')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        teacher = Role.objects.get(code='DOCENTE')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code__in=BOOKING_CODES).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_permissions(apps, None)
        migration.add_permissions(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertLessEqual(BOOKING_CODES, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code__in=BOOKING_CODES).count(), 3)

    def test_no_generic_booking_permission(self):
        self.assertFalse(Permission.objects.filter(code='AGENDA.GERENCIAR').exists())
        self.assertNotIn('AGENDA.GERENCIAR', permissions.ALL_PERMISSIONS)

    def test_booking_permissions_are_not_reserved(self):
        self.assertFalse(BOOKING_CODES & permissions.SUPERADMIN_RESERVED_PERMISSIONS)
        coordination = Role.objects.create_role('COORDENACAO', 'Coordenação')
        coordination.set_permissions([Permission.objects.get(code='AGENDA.ANALISAR')])
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'AGENDA.ANALISAR'})


class BookingCreatePermissionMigrationTests(TestCase):
    def test_grants_the_create_permission_only_to_administrator_keeping_other_grants(self):
        migration = import_module('accounts.migrations.0014_booking_create_permission')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        teacher = Role.objects.get(code='DOCENTE')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code=BOOKING_CREATE_CODE).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        migration.add_permissions(apps, None)
        migration.add_permissions(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertIn(BOOKING_CREATE_CODE, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code=BOOKING_CREATE_CODE).count(), 1)

    def test_create_permission_is_not_reserved(self):
        self.assertNotIn(BOOKING_CREATE_CODE, permissions.SUPERADMIN_RESERVED_PERMISSIONS)
        superadmin = User.objects.create_superadmin('super@ifnmg.edu.br', 'Super', 'Senha-forte-123')
        self.assertTrue(superadmin.has_perm(BOOKING_CREATE_CODE))
