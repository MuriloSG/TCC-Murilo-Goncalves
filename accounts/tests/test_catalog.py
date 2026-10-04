from importlib import import_module

from django.apps import apps
from django.db import transaction
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
PERMISSION_MIGRATIONS = [
    ('0003_user_import_permission', 'add_import_permission', {'USUARIO.IMPORTAR'}),
    ('0004_audit_permission', 'add_audit_permission', {'AUDITORIA.VISUALIZAR'}),
    ('0005_notice_permission', 'add_notice_permission', {'NOTIFICACAO.PUBLICAR'}),
    (
        '0008_space_allocation_permissions',
        'add_permissions',
        {'ENSALAMENTO.VISUALIZAR', 'USUARIO.EXCLUIR_IMPORTACAO', 'ENSALAMENTO.EXCLUIR_IMPORTACAO'},
    ),
    (
        '0009_space_permissions',
        'add_permissions',
        {'ESPACO.VISUALIZAR', 'ESPACO.CRIAR', 'ESPACO.EDITAR', 'ESPACO.ALTERAR_SITUACAO', 'ESPACO.EXCLUIR'},
    ),
    ('0010_booking_permissions', 'add_permissions', {'AGENDA.VISUALIZAR', 'AGENDA.SOLICITAR', 'AGENDA.ANALISAR'}),
    ('0014_booking_create_permission', 'add_permissions', {'AGENDA.CRIAR'}),
    ('0017_panel_permission', 'add_permission', {'PAINEL.VISUALIZAR'}),
    ('0019_settings_permission', 'add_permission', {'CONFIGURACAO.EDITAR'}),
]


class PermissionConstantsTests(SimpleTestCase):
    def test_codes_follow_the_format(self):
        for code in permissions.ALL_PERMISSIONS:
            with self.subTest(code=code):
                Permission(code=code, description='Teste').clean_fields()

    def test_administrative_capability_is_user_management_without_import(self):
        self.assertEqual(permissions.ADMINISTRATIVE_CAPABILITY, USER_CODES)

    def test_reserved_permissions_are_exactly_role_permissions(self):
        self.assertEqual(permissions.SUPERADMIN_RESERVED_PERMISSIONS, ROLE_CODES)


class InitialCatalogTests(TestCase):
    def test_database_codes_match_constants(self):
        codes = set(Permission.objects.values_list('code', flat=True))
        self.assertEqual(codes, set(permissions.ALL_PERMISSIONS))

    def test_every_permission_has_a_description(self):
        self.assertFalse(Permission.objects.filter(description='').exists())

    def test_system_roles_exist_and_are_marked_as_system(self):
        self.assertEqual(
            set(Role.objects.values_list('code', 'is_system')), {('ADMINISTRADOR', True), ('DOCENTE', True)},
        )

    def test_administrator_grants_every_permission_not_reserved(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        self.assertEqual(
            set(administrator.permissions.values_list('code', flat=True)),
            permissions.ALL_PERMISSIONS - permissions.SUPERADMIN_RESERVED_PERMISSIONS,
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


class PermissionMigrationTests(TestCase):
    def test_grants_the_new_permissions_to_administrator_keeping_other_grants(self):
        for module, function, codes in PERMISSION_MIGRATIONS:
            with self.subTest(module), transaction.atomic():
                self.check_migration(getattr(import_module(f'accounts.migrations.{module}'), function), codes)
                transaction.set_rollback(True)

    def check_migration(self, add_permissions, codes):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        teacher = Role.objects.get(code='DOCENTE')
        coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')
        Permission.objects.filter(code__in=codes).delete()
        RolePermission.objects.filter(role=administrator, permission__code='USUARIO.EDITAR').delete()
        RolePermission.objects.create(role=coordination, permission=Permission.objects.get(code='USUARIO.VISUALIZAR'))

        add_permissions(apps, None)
        add_permissions(apps, None)

        administrator_codes = set(administrator.permissions.values_list('code', flat=True))
        self.assertLessEqual(codes, administrator_codes)
        self.assertNotIn('USUARIO.EDITAR', administrator_codes)
        self.assertEqual(set(teacher.permissions.values_list('code', flat=True)), TEACHER_CODES)
        self.assertEqual(set(coordination.permissions.values_list('code', flat=True)), {'USUARIO.VISUALIZAR'})
        self.assertEqual(Permission.objects.filter(code__in=codes).count(), len(codes))
