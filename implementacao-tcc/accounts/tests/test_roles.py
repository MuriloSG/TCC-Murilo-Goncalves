import threading
import time

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase

from accounts import permissions
from accounts.models import (
    AdministrativeContinuityViolation,
    Permission,
    ReservedPermissionNotGrantable,
    Role,
    RoleInUse,
    RolePermission,
    User,
    UserRole,
)
from accounts.tests.roles import management_role, requester_role


def codes(role):
    return set(Role.objects.get(pk=role.pk).permissions.values_list('code', flat=True))


def create_user(email, role, **fields):
    user = User.objects.create(email=email, name=email.partition('@')[0], **fields)
    UserRole.objects.create(user=user, role=role)
    return User.objects.get(pk=user.pk)


class CreateRoleTests(TestCase):
    def test_creates_custom_role_without_permissions(self):
        role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', description='Cursos')
        role = Role.objects.get(pk=role.pk)
        self.assertEqual((role.code, role.name, role.description), ('COORDENACAO', 'Coordenação', 'Cursos'))
        self.assertEqual(codes(role), set())

    def test_creates_role_with_chosen_permissions(self):
        role = Role.objects.create_role(
            code='COORDENACAO',
            name='Coordenação',
            permissions=[permissions.USER_VIEW, Permission.objects.get(code=permissions.USER_EDIT)],
        )
        self.assertEqual(codes(role), {permissions.USER_VIEW, permissions.USER_EDIT})

    def test_refuses_invalid_data_without_creating_anything(self):
        Role.objects.create_role(code='COORDENACAO', name='Coordenação')
        cases = {
            'missing code': dict(code='', name='Secretaria'),
            'lowercase code': dict(code='secretaria', name='Secretaria'),
            'code with dash': dict(code='COORD-1', name='Secretaria'),
            'repeated code': dict(code='COORDENACAO', name='Secretaria'),
            'missing name': dict(code='SECRETARIA', name='   '),
            'name differing in case': dict(code='COORDENACAO_GERAL', name='COORDENAÇÃO'),
        }
        for label, data in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValidationError):
                    Role.objects.create_role(**data)
        self.assertEqual(Role.objects.count(), 3)

    def test_refuses_reserved_permission_without_creating_anything(self):
        with self.assertRaises(ReservedPermissionNotGrantable) as raised:
            Role.objects.create_role(
                code='COORDENACAO',
                name='Coordenação',
                permissions=[permissions.USER_VIEW, permissions.ROLE_CHANGE_PERMISSIONS],
            )
        self.assertIn(permissions.ROLE_CHANGE_PERMISSIONS, raised.exception.messages[0])
        self.assertFalse(Role.objects.filter(code='COORDENACAO').exists())
        self.assertFalse(RolePermission.objects.filter(role__code='COORDENACAO').exists())

    def test_refuses_permission_outside_catalog_without_creating_anything(self):
        with self.assertRaises(ValidationError):
            Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=['RESERVA.APROVAR'])
        self.assertFalse(Role.objects.filter(code='COORDENACAO').exists())
        self.assertFalse(Permission.objects.filter(code='RESERVA.APROVAR').exists())


class UpdateRoleDetailsTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', permissions=[permissions.USER_VIEW],
        )
        self.user = create_user('coord@ifnmg.edu.br', self.role)

    def test_changes_name_and_description_only(self):
        self.role.update_details(name='Coordenação de Curso', description='Nova descrição')
        role = Role.objects.get(pk=self.role.pk)
        self.assertEqual((role.name, role.description), ('Coordenação de Curso', 'Nova descrição'))
        self.assertEqual(role.code, 'COORDENACAO')
        self.assertEqual(codes(role), {permissions.USER_VIEW})
        self.assertEqual(User.objects.get(pk=self.user.pk).role, role)
        self.assertTrue(User.objects.get(pk=self.user.pk).has_perm(permissions.USER_VIEW))

    def test_does_not_accept_code(self):
        with self.assertRaises(TypeError):
            self.role.update_details(name='Secretaria', description='', code='SECRETARIA')

    def test_initial_role_name_can_change_and_code_stays(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        administrator.update_details(name='Administração', description='')
        administrator = Role.objects.get(pk=administrator.pk)
        self.assertEqual((administrator.code, administrator.name), ('ADMINISTRADOR', 'Administração'))

    def test_refuses_empty_or_repeated_name_and_keeps_values(self):
        for name in ('', '   ', 'docente'):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    self.role.update_details(name=name, description='Outra')
                self.assertEqual((self.role.name, self.role.description), ('Coordenação', ''))
                role = Role.objects.get(pk=self.role.pk)
                self.assertEqual((role.name, role.description), ('Coordenação', ''))
        self.assertEqual(Role.objects.get(code='DOCENTE').name, 'Docente')


class SetPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()

    def setUp(self):
        self.coordination = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', permissions=[permissions.USER_VIEW, permissions.USER_EDIT],
        )

    def test_grants_and_removes_in_the_same_call(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_CREATE])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW, permissions.USER_CREATE})

    def test_initial_role_permissions_can_change(self):
        teacher = Role.objects.get(code='DOCENTE')
        teacher.set_permissions([permissions.USER_VIEW])
        self.assertEqual(codes(teacher), {permissions.USER_VIEW})

    def test_empty_set_is_accepted(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        self.coordination.set_permissions([])
        self.assertEqual(codes(self.coordination), set())

    def test_change_reaches_every_user_of_the_role(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        first = create_user('um@ifnmg.edu.br', self.coordination)
        second = create_user('dois@ifnmg.edu.br', self.coordination)
        inactive = create_user('tres@ifnmg.edu.br', self.coordination, is_active=False)
        self.coordination.set_permissions([permissions.USER_CREATE])
        for user in (first, second):
            with self.subTest(user=user.email):
                self.assertEqual(User.objects.get(pk=user.pk).effective_permissions(), {permissions.USER_CREATE})
        self.assertFalse(User.objects.get(pk=inactive.pk).has_perm(permissions.USER_CREATE))

    def test_refuses_reserved_permission_entirely(self):
        with self.assertRaises(ReservedPermissionNotGrantable):
            self.coordination.set_permissions([permissions.USER_CREATE, permissions.ROLE_CREATE])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW, permissions.USER_EDIT})

    def test_refuses_reserved_permission_on_role_with_capability(self):
        with self.assertRaises(ReservedPermissionNotGrantable):
            self.administrator.set_permissions(
                set(permissions.ADMINISTRATIVE_CAPABILITY) | {permissions.ROLE_DELETE},
            )
        self.assertNotIn(permissions.ROLE_DELETE, codes(self.administrator))

    def test_refuses_permission_outside_catalog(self):
        with self.assertRaises(ValidationError):
            self.coordination.set_permissions([permissions.USER_VIEW, 'RESERVA.APROVAR'])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW, permissions.USER_EDIT})
        self.assertFalse(Permission.objects.filter(code='RESERVA.APROVAR').exists())

    def test_removal_allowed_because_active_superadmin_keeps_capability(self):
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        self.administrator.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_EDIT})
        self.assertFalse(User.objects.get(pk=admin.pk).has_administrative_capability())
        self.assertTrue(User.objects.get(pk=superadmin.pk).has_administrative_capability())

    def test_removal_refused_without_another_capable_user(self):
        self.coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY)
        create_user('coord@ifnmg.edu.br', self.coordination)
        with self.assertRaises(AdministrativeContinuityViolation):
            self.coordination.set_permissions(
                permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_CHANGE_STATUS},
            )
        self.assertEqual(codes(self.coordination), set(permissions.ADMINISTRATIVE_CAPABILITY))

    def test_removal_refused_when_only_superadmin_is_inactive(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True, is_active=False)
        self.coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY)
        create_user('coord@ifnmg.edu.br', self.coordination)
        with self.assertRaises(AdministrativeContinuityViolation):
            self.coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_CREATE})
        self.assertIn(permissions.USER_CREATE, codes(self.coordination))

    def test_removal_allowed_with_capable_user_by_another_role(self):
        self.coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY)
        create_user('coord@ifnmg.edu.br', self.coordination)
        create_user('admin@ifnmg.edu.br', self.administrator)
        self.coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_EDIT})
        self.assertNotIn(permissions.USER_EDIT, codes(self.coordination))

    def test_additions_and_other_removals_are_not_checked(self):
        self.assertFalse(User.objects.with_administrative_capability().exists())
        other = Permission.objects.create(code='RESERVA.APROVAR', description='Aprovar reserva')
        self.teacher.set_permissions([permissions.USER_VIEW])
        self.teacher.set_permissions([permissions.USER_VIEW, other])
        self.teacher.set_permissions([permissions.USER_VIEW])
        self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT, other])
        self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW, permissions.USER_EDIT})

    def test_removal_of_capability_permission_is_checked(self):
        self.assertFalse(User.objects.with_administrative_capability().exists())
        with self.assertRaises(AdministrativeContinuityViolation):
            self.coordination.set_permissions([permissions.USER_VIEW])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW, permissions.USER_EDIT})


class DeleteRoleTests(TestCase):
    def setUp(self):
        self.coordination = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', permissions=[permissions.USER_VIEW],
        )

    def test_deletes_custom_role_without_users_and_its_grants(self):
        self.coordination.delete_role()
        self.assertFalse(Role.objects.filter(code='COORDENACAO').exists())
        self.assertFalse(RolePermission.objects.filter(role_id=self.coordination.pk).exists())
        self.assertTrue(Permission.objects.filter(code=permissions.USER_VIEW).exists())

    def test_initial_roles_without_users_are_deleted_like_any_other(self):
        for code in ('ADMINISTRADOR', 'DOCENTE'):
            with self.subTest(code=code):
                role = Role.objects.get(code=code)
                role.delete_role()
                self.assertFalse(Role.objects.filter(code=code).exists())
                self.assertFalse(RolePermission.objects.filter(role_id=role.pk).exists())

    def test_initial_role_with_user_cannot_be_deleted(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        create_user('admin@ifnmg.edu.br', administrator)
        with self.assertRaises(RoleInUse):
            administrator.delete_role()
        self.assertTrue(Role.objects.filter(pk=administrator.pk).exists())

    def test_role_with_active_user_cannot_be_deleted(self):
        user = create_user('coord@ifnmg.edu.br', self.coordination)
        with self.assertRaises(RoleInUse) as raised:
            self.coordination.delete_role()
        self.assertIn('1 usuário vinculado', raised.exception.messages[0])
        self.assertEqual(codes(self.coordination), {permissions.USER_VIEW})
        self.assertEqual(User.objects.get(pk=user.pk).role, self.coordination)

    def test_role_with_only_inactive_users_cannot_be_deleted(self):
        create_user('um@ifnmg.edu.br', self.coordination, is_active=False)
        create_user('dois@ifnmg.edu.br', self.coordination, is_active=False)
        with self.assertRaises(RoleInUse) as raised:
            self.coordination.delete_role()
        self.assertIn('2 usuários vinculados', raised.exception.messages[0])
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())

    def test_role_can_be_deleted_after_users_change_role(self):
        create_user('admin@ifnmg.edu.br', management_role())
        user = create_user('coord@ifnmg.edu.br', self.coordination)
        user.change_role(requester_role())
        self.coordination.delete_role()
        self.assertFalse(Role.objects.filter(pk=self.coordination.pk).exists())
        self.assertEqual(list(User.objects.get(pk=user.pk).roles.values_list('code', flat=True)), ['SOLICITACAO'])


class ConcurrentPermissionChangeTests(TransactionTestCase):
    serialized_rollback = True

    def test_permission_removal_and_deactivation_keep_one_capable_user(self):
        administrator = management_role()
        coordination = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', permissions=permissions.ADMINISTRATIVE_CAPABILITY,
        )
        admin = create_user('admin@ifnmg.edu.br', administrator)
        coordinator = create_user('coord@ifnmg.edu.br', coordination)

        result = {}
        started = threading.Event()

        def deactivate_admin():
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    result['pid'] = cursor.fetchone()[0]
                started.set()
                User.objects.get(pk=admin.pk).deactivate()
                result['outcome'] = 'deactivated'
            except AdministrativeContinuityViolation:
                result['outcome'] = 'refused'
            except Exception as error:
                result['outcome'] = error
            finally:
                started.set()
                connection.close()

        with transaction.atomic():
            coordination.set_permissions(permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_EDIT})

            worker = threading.Thread(target=deactivate_admin)
            worker.start()
            self.assertTrue(started.wait(10))
            self.assertIn('pid', result, result.get('outcome'))
            self.assertTrue(self.wait_until_blocked(result['pid']), 'deactivation did not wait for the lock')

        worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result['outcome'], 'refused')
        self.assertTrue(User.objects.get(pk=admin.pk).is_active)
        self.assertFalse(User.objects.get(pk=coordinator.pk).has_administrative_capability())
        self.assertEqual(
            set(User.objects.with_administrative_capability().values_list('email', flat=True)),
            {admin.email},
        )

    def wait_until_blocked(self, pid, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute('SELECT cardinality(pg_blocking_pids(%s))', [pid])
                if cursor.fetchone()[0]:
                    return True
            time.sleep(0.05)
        return False
