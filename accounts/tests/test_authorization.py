from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts import permissions
from accounts.models import Permission, Role, RolePermission, User, UserRole


def grant(role, *codes):
    for code in codes:
        RolePermission.objects.create(role=role, permission=Permission.objects.get(code=code))


TEACHER_PERMISSIONS = frozenset({permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST})

class AuthorizationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')

    def create_user(self, email, role, **fields):
        user = User.objects.create(email=email, name=email.partition('@')[0], **fields)
        UserRole.objects.create(user=user, role=role)
        return User.objects.get(pk=user.pk)


class AnonymousUserTests(TestCase):
    def test_has_no_permission(self):
        user = AnonymousUser()
        self.assertFalse(user.has_perm(permissions.USER_VIEW))
        self.assertFalse(user.has_perm(permissions.ROLE_VIEW))
        self.assertFalse(user.has_perms([permissions.USER_VIEW]))
        self.assertFalse(user.has_module_perms('USUARIO'))


class InactiveUserTests(AuthorizationTestCase):
    def test_inactive_user_with_role_has_no_permission(self):
        user = self.create_user('antigo@ifnmg.edu.br', self.administrator, is_active=False)
        self.assertEqual(user.effective_permissions(), frozenset())
        self.assertFalse(user.has_perm(permissions.USER_VIEW))
        self.assertFalse(user.has_perms([permissions.USER_VIEW]))
        self.assertFalse(user.has_module_perms('USUARIO'))

    def test_inactive_user_without_role_has_no_permission(self):
        user = User.objects.create(email='semperfil@ifnmg.edu.br', name='Sem perfil', is_active=False)
        self.assertEqual(user.effective_permissions(), frozenset())
        self.assertFalse(user.has_perm(permissions.USER_VIEW))

    def test_inactive_superadmin_has_no_permission(self):
        user = self.create_user(
            'super@ifnmg.edu.br', self.administrator, is_active=False, is_superadmin=True,
        )
        self.assertEqual(user.effective_permissions(), frozenset())
        self.assertFalse(user.has_perm(permissions.USER_VIEW))
        self.assertFalse(user.has_perm(permissions.ROLE_CREATE))
        self.assertFalse(user.has_perm('RESERVA.APROVAR'))
        self.assertFalse(user.has_perms([permissions.USER_VIEW]))
        self.assertFalse(user.has_module_perms('PERFIL'))


class RolePermissionsTests(AuthorizationTestCase):
    def test_administrator_holds_user_permissions(self):
        user = self.create_user('admin@ifnmg.edu.br', self.administrator)
        granted = permissions.ADMINISTRATIVE_CAPABILITY | {
            permissions.USER_IMPORT,
            permissions.USER_IMPORT_DELETE,
            permissions.AUDIT_VIEW,
            permissions.NOTICE_PUBLISH,
            permissions.PANEL_VIEW,
            permissions.REPORT_VIEW,
            permissions.SPACE_ALLOCATION_VIEW,
            permissions.SPACE_ALLOCATION_IMPORT,
            permissions.SPACE_ALLOCATION_IMPORT_DELETE,
            permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE,
            permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE,
            permissions.SPACE_ALLOCATION_CREATE_RECURRENCE,
            permissions.SPACE_ALLOCATION_END_RECURRENCE,
        } | permissions.SPACE_PERMISSIONS | permissions.BOOKING_PERMISSIONS | permissions.SUBJECT_PERMISSIONS | permissions.CLASS_GROUP_PERMISSIONS
        self.assertEqual(user.effective_permissions(), granted)
        for code in granted:
            with self.subTest(code=code):
                self.assertTrue(user.has_perm(code))

    def test_teacher_holds_only_the_booking_request(self):
        user = self.create_user('docente@ifnmg.edu.br', self.teacher)
        self.assertEqual(user.effective_permissions(), TEACHER_PERMISSIONS)
        self.assertFalse(user.has_perm(permissions.USER_VIEW))
        self.assertFalse(user.has_module_perms('USUARIO'))

    def test_permission_from_role_is_granted(self):
        grant(self.coordination, permissions.USER_VIEW)
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertEqual(user.effective_permissions(), {permissions.USER_VIEW})
        self.assertTrue(user.has_perm(permissions.USER_VIEW))
        self.assertTrue(user.has_module_perms('USUARIO'))

    def test_permission_outside_role_is_denied(self):
        grant(self.coordination, permissions.USER_VIEW, permissions.USER_EDIT)
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertFalse(user.has_perm(permissions.USER_CHANGE_STATUS))
        self.assertFalse(user.has_perm('RESERVA.APROVAR'))
        self.assertFalse(user.has_module_perms('PERFIL'))

    def test_has_perms_requires_all(self):
        grant(self.coordination, permissions.USER_VIEW, permissions.USER_EDIT)
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertTrue(user.has_perms([permissions.USER_VIEW, permissions.USER_EDIT]))
        self.assertFalse(user.has_perms([permissions.USER_VIEW, permissions.USER_CREATE]))

    def test_module_perms_match_whole_resource(self):
        Permission.objects.create(code='USUARIOS_EXTERNOS.VISUALIZAR', description='Teste')
        grant(self.coordination, 'USUARIOS_EXTERNOS.VISUALIZAR')
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertTrue(user.has_module_perms('USUARIOS_EXTERNOS'))
        self.assertFalse(user.has_module_perms('USUARIO'))

    def test_user_with_all_user_permissions_has_no_role_permission(self):
        user = self.create_user('admin@ifnmg.edu.br', self.administrator)
        for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
            with self.subTest(code=code):
                self.assertFalse(user.has_perm(code))
        self.assertFalse(user.has_module_perms('PERFIL'))

    def test_reserved_permission_written_directly_is_not_granted(self):
        grant(self.coordination, permissions.USER_VIEW, permissions.ROLE_CHANGE_PERMISSIONS)
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertEqual(user.effective_permissions(), {permissions.USER_VIEW})
        self.assertFalse(user.has_perm(permissions.ROLE_CHANGE_PERMISSIONS))
        self.assertFalse(user.has_module_perms('PERFIL'))

    def test_decision_does_not_depend_on_role_code_or_name(self):
        granted = permissions.ADMINISTRATIVE_CAPABILITY | {
            permissions.USER_IMPORT,
            permissions.USER_IMPORT_DELETE,
            permissions.AUDIT_VIEW,
            permissions.NOTICE_PUBLISH,
            permissions.PANEL_VIEW,
            permissions.REPORT_VIEW,
            permissions.SPACE_ALLOCATION_VIEW,
            permissions.SPACE_ALLOCATION_IMPORT,
            permissions.SPACE_ALLOCATION_IMPORT_DELETE,
            permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE,
            permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE,
            permissions.SPACE_ALLOCATION_CREATE_RECURRENCE,
            permissions.SPACE_ALLOCATION_END_RECURRENCE,
        } | permissions.SPACE_PERMISSIONS | permissions.BOOKING_PERMISSIONS | permissions.SUBJECT_PERMISSIONS | permissions.CLASS_GROUP_PERMISSIONS
        grant(self.coordination, *granted)
        administrator = self.create_user('admin@ifnmg.edu.br', self.administrator)
        coordinator = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertEqual(administrator.effective_permissions(), coordinator.effective_permissions())

        self.administrator.name = 'Gestão'
        self.administrator.save()
        renamed = User.objects.get(pk=administrator.pk)
        for code in permissions.ALL_PERMISSIONS | {'RESERVA.APROVAR'}:
            with self.subTest(code=code):
                self.assertEqual(renamed.has_perm(code), coordinator.has_perm(code))
                self.assertEqual(renamed.has_perm(code), code in granted)

    def test_grant_changes_reach_every_user_of_the_role_on_reload(self):
        first = self.create_user('um@ifnmg.edu.br', self.teacher)
        second = self.create_user('dois@ifnmg.edu.br', self.teacher)
        self.assertFalse(first.has_perm(permissions.USER_VIEW))

        grant(self.teacher, permissions.USER_VIEW)

        self.assertFalse(first.has_perm(permissions.USER_VIEW))
        for user in (first, second):
            with self.subTest(user=user.email):
                reloaded = User.objects.get(pk=user.pk)
                self.assertEqual(reloaded.effective_permissions(), {permissions.USER_VIEW} | TEACHER_PERMISSIONS)

    def test_previous_role_permissions_do_not_remain(self):
        user = self.create_user('admin@ifnmg.edu.br', self.administrator)
        UserRole.objects.filter(user=user).update(role=self.teacher)
        reloaded = User.objects.get(pk=user.pk)
        self.assertEqual(reloaded.effective_permissions(), TEACHER_PERMISSIONS)
        self.assertFalse(reloaded.has_perm(permissions.USER_VIEW))

    def test_effective_permissions_computed_once_per_instance(self):
        user = self.create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertNumQueries(1):
            user.has_perm(permissions.USER_VIEW)
            user.has_perms([permissions.USER_CREATE, permissions.USER_EDIT])
            user.has_module_perms('USUARIO')
            user.effective_permissions()


class SuperadminTests(AuthorizationTestCase):
    def test_active_superadmin_has_any_permission(self):
        user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        for code in permissions.ALL_PERMISSIONS:
            with self.subTest(code=code):
                self.assertTrue(user.has_perm(code))
        self.assertTrue(user.has_perms(list(permissions.ALL_PERMISSIONS)))
        self.assertTrue(user.has_module_perms('USUARIO'))
        self.assertTrue(user.has_module_perms('PERFIL'))

    def test_active_superadmin_has_permission_outside_catalog(self):
        user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        with self.assertNumQueries(0):
            self.assertTrue(user.has_perm('RESERVA.APROVAR'))
            self.assertTrue(user.has_perms(['RESERVA.APROVAR', 'ESPACO.CRIAR']))
            self.assertTrue(user.has_module_perms('RESERVA'))

    def test_active_superadmin_effective_permissions_are_the_catalog(self):
        user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        catalog = set(Permission.objects.values_list('code', flat=True))
        self.assertEqual(user.effective_permissions(), catalog)
        self.assertTrue(permissions.SUPERADMIN_RESERVED_PERMISSIONS <= user.effective_permissions())

    def test_superadmin_does_not_rely_on_django_superuser(self):
        user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        self.assertFalse(hasattr(user, 'is_superuser'))


class TemplatePermsTests(AuthorizationTestCase):
    def test_perm_wrapper_uses_has_perm_and_has_module_perms(self):
        grant(self.coordination, permissions.USER_VIEW)
        perms = PermWrapper(self.create_user('coord@ifnmg.edu.br', self.coordination))
        self.assertTrue(perms['USUARIO'])
        self.assertTrue(perms['USUARIO']['VISUALIZAR'])
        self.assertFalse(perms['USUARIO']['CRIAR'])
        self.assertFalse(perms['PERFIL'])
