import threading
import time

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from accounts import permissions
from accounts.models import (
    AdministrativeContinuityViolation,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    administrative_continuity,
    deferred_administrative_continuity,
    ensure_administrative_continuity,
)


def create_user(email, role, **fields):
    user = User.objects.create(email=email, name=email.partition('@')[0], **fields)
    UserRole.objects.create(user=user, role=role)
    return User.objects.get(pk=user.pk)


def capable_emails():
    return set(User.objects.with_administrative_capability().values_list('email', flat=True))


class ContinuityTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')


class AdministrativeCapabilityTests(ContinuityTestCase):
    def assertCapable(self, user, expected):
        user = User.objects.get(pk=user.pk)
        self.assertIs(user.has_administrative_capability(), expected)
        self.assertIs(user.email in capable_emails(), expected)

    def test_active_superadmin(self):
        self.assertCapable(create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True), True)

    def test_inactive_superadmin(self):
        user = create_user(
            'super@ifnmg.edu.br', self.administrator, is_superadmin=True, is_active=False,
        )
        self.assertCapable(user, False)

    def test_active_administrator_by_role(self):
        self.assertCapable(create_user('admin@ifnmg.edu.br', self.administrator), True)

    def test_inactive_administrator_by_role(self):
        self.assertCapable(create_user('admin@ifnmg.edu.br', self.administrator, is_active=False), False)

    def test_role_without_permissions(self):
        self.assertCapable(create_user('docente@ifnmg.edu.br', self.teacher), False)

    def test_role_missing_one_permission(self):
        for code in permissions.ADMINISTRATIVE_CAPABILITY:
            with self.subTest(missing=code):
                RolePermission.objects.filter(role=self.coordination).delete()
                for granted in permissions.ADMINISTRATIVE_CAPABILITY - {code}:
                    RolePermission.objects.create(
                        role=self.coordination, permission=Permission.objects.get(code=granted),
                    )
                user = create_user(f'coord.{code.lower()}@ifnmg.edu.br', self.coordination)
                self.assertCapable(user, False)

    def test_administrator_role_after_losing_a_permission(self):
        user = create_user('admin@ifnmg.edu.br', self.administrator)
        RolePermission.objects.filter(
            role=self.administrator, permission__code=permissions.USER_EDIT,
        ).delete()
        self.assertCapable(user, False)

    def test_custom_role_with_the_same_permissions(self):
        for code in permissions.ADMINISTRATIVE_CAPABILITY:
            RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
        self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), True)

    def test_renamed_role(self):
        self.administrator.name = 'Gestão de pessoas'
        self.administrator.save()
        self.assertCapable(create_user('admin@ifnmg.edu.br', self.administrator), True)

    def test_reserved_permissions_do_not_count(self):
        for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
            RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
        self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), False)

    def test_extra_permissions_do_not_matter(self):
        for code in permissions.ADMINISTRATIVE_CAPABILITY:
            RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
        extra = Permission.objects.create(code='RESERVA.APROVAR', description='Aprovar reserva')
        RolePermission.objects.create(role=self.coordination, permission=extra)
        self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), True)


class DeactivationTests(ContinuityTestCase):
    def test_last_capable_user_cannot_be_deactivated(self):
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertRaises(AdministrativeContinuityViolation) as raised:
            admin.deactivate()
        self.assertIsInstance(raised.exception, ValidationError)
        self.assertTrue(raised.exception.messages)
        self.assertTrue(admin.is_active)
        self.assertTrue(User.objects.get(pk=admin.pk).is_active)

    def test_last_capable_superadmin_cannot_be_deactivated(self):
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        with self.assertRaises(AdministrativeContinuityViolation):
            superadmin.deactivate()
        self.assertTrue(User.objects.get(pk=superadmin.pk).is_active)

    def test_deactivation_allowed_when_another_user_is_capable(self):
        first = create_user('um@ifnmg.edu.br', self.administrator)
        second = create_user('dois@ifnmg.edu.br', self.administrator)
        first.deactivate()
        self.assertFalse(first.is_active)
        self.assertFalse(User.objects.get(pk=first.pk).is_active)
        self.assertEqual(capable_emails(), {second.email})

    def test_capable_user_can_deactivate_a_regular_user(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        teacher = create_user('docente@ifnmg.edu.br', self.teacher)
        teacher.deactivate()
        self.assertFalse(User.objects.get(pk=teacher.pk).is_active)

    def test_inactive_superadmin_does_not_count(self):
        create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True, is_active=False)
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertRaises(AdministrativeContinuityViolation):
            admin.deactivate()
        self.assertTrue(User.objects.get(pk=admin.pk).is_active)

    def test_capability_by_custom_role_counts(self):
        for code in permissions.ADMINISTRATIVE_CAPABILITY:
            RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
        create_user('coord@ifnmg.edu.br', self.coordination)
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        superadmin.deactivate()
        self.assertFalse(User.objects.get(pk=superadmin.pk).is_active)

    def test_deactivation_keeps_the_user_data(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        user = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        user.set_password('Senha-forte-123')
        user.save()
        before = User.objects.get(pk=user.pk)

        user.deactivate()

        after = User.objects.get(pk=user.pk)
        self.assertFalse(after.is_active)
        self.assertEqual(
            (after.name, after.email, after.password, after.is_superadmin),
            (before.name, before.email, before.password, before.is_superadmin),
        )
        self.assertEqual(list(after.roles.all()), [self.teacher])

    def test_deactivation_does_not_overwrite_other_fields(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        User.objects.filter(pk=user.pk).update(name='Nome atualizado')
        user.deactivate()
        self.assertEqual(User.objects.get(pk=user.pk).name, 'Nome atualizado')

    def test_deactivated_user_loses_permissions_on_the_same_instance(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        self.assertTrue(admin.has_perm(permissions.USER_VIEW))
        admin.deactivate()
        self.assertFalse(admin.has_perm(permissions.USER_VIEW))


class ReactivationTests(ContinuityTestCase):
    def test_reactivation_restores_role_password_and_superadmin(self):
        user = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True, is_active=False)
        user.set_password('Senha-forte-123')
        user.save()

        user.reactivate()

        reloaded = User.objects.get(pk=user.pk)
        self.assertTrue(reloaded.is_active)
        self.assertTrue(reloaded.is_superadmin)
        self.assertTrue(reloaded.check_password('Senha-forte-123'))
        self.assertEqual(list(reloaded.roles.all()), [self.teacher])
        self.assertEqual(capable_emails(), {user.email})

    def test_reactivation_is_not_guarded(self):
        user = create_user('docente@ifnmg.edu.br', self.teacher, is_active=False)
        self.assertEqual(capable_emails(), set())
        user.reactivate()
        self.assertTrue(User.objects.get(pk=user.pk).is_active)


class SuperadminStatusTests(ContinuityTestCase):
    def test_grant_superadmin(self):
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        user.set_superadmin(True)
        self.assertTrue(user.is_superadmin)
        reloaded = User.objects.get(pk=user.pk)
        self.assertTrue(reloaded.is_superadmin)
        self.assertTrue(reloaded.has_administrative_capability())

    def test_grant_superadmin_refreshes_the_instance_permissions(self):
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        self.assertFalse(user.has_perm(permissions.ROLE_VIEW))
        user.set_superadmin(True)
        self.assertTrue(user.has_perm(permissions.ROLE_VIEW))
        self.assertIn(permissions.ROLE_VIEW, user.effective_permissions())

    def test_removing_last_capable_superadmin_is_refused(self):
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        with self.assertRaises(AdministrativeContinuityViolation):
            superadmin.set_superadmin(False)
        self.assertTrue(superadmin.is_superadmin)
        self.assertTrue(User.objects.get(pk=superadmin.pk).is_superadmin)

    def test_removing_superadmin_allowed_when_another_user_is_capable(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        superadmin.set_superadmin(False)
        self.assertFalse(User.objects.get(pk=superadmin.pk).is_superadmin)

    def test_removing_superadmin_allowed_when_the_user_keeps_capability_by_role(self):
        superadmin = create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True)
        superadmin.set_superadmin(False)
        reloaded = User.objects.get(pk=superadmin.pk)
        self.assertFalse(reloaded.is_superadmin)
        self.assertTrue(reloaded.has_administrative_capability())

    def test_no_rule_requires_an_active_superadmin(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        first = create_user('um@ifnmg.edu.br', self.teacher, is_superadmin=True)
        second = create_user('dois@ifnmg.edu.br', self.teacher, is_superadmin=True)

        first.set_superadmin(False)
        second.deactivate()

        self.assertFalse(User.objects.filter(is_active=True, is_superadmin=True).exists())
        self.assertEqual(capable_emails(), {'admin@ifnmg.edu.br'})


class ChangeRoleTests(ContinuityTestCase):
    def test_change_role_replaces_the_only_role(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        user.change_role(self.administrator)
        self.assertEqual(list(User.objects.get(pk=user.pk).roles.all()), [self.administrator])
        self.assertEqual(UserRole.objects.filter(user=user).count(), 1)

    def test_change_to_custom_role(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        user.change_role(self.coordination)
        self.assertEqual(User.objects.get(pk=user.pk).role, self.coordination)

    def test_change_role_refreshes_the_instance_permissions(self):
        superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        self.assertFalse(user.has_perm(permissions.USER_VIEW))
        user.change_role(self.administrator)
        self.assertTrue(user.has_perm(permissions.USER_VIEW))
        self.assertTrue(superadmin.is_superadmin)

    def test_last_capable_user_by_role_cannot_lose_the_role(self):
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertRaises(AdministrativeContinuityViolation):
            admin.change_role(self.teacher)
        self.assertEqual(list(User.objects.get(pk=admin.pk).roles.all()), [self.administrator])
        self.assertTrue(admin.has_perm(permissions.USER_VIEW))

    def test_last_capable_superadmin_can_change_role(self):
        superadmin = create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True)
        superadmin.change_role(self.teacher)
        reloaded = User.objects.get(pk=superadmin.pk)
        self.assertEqual(reloaded.role, self.teacher)
        self.assertTrue(reloaded.has_administrative_capability())

    def test_change_role_allowed_when_another_user_is_capable(self):
        create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        admin.change_role(self.teacher)
        self.assertEqual(User.objects.get(pk=admin.pk).role, self.teacher)

    def test_change_role_requires_a_role(self):
        create_user('admin@ifnmg.edu.br', self.administrator)
        user = create_user('docente@ifnmg.edu.br', self.teacher)
        with self.assertRaises(ValidationError):
            user.change_role(None)
        self.assertEqual(list(User.objects.get(pk=user.pk).roles.all()), [self.teacher])


class ContinuityGuardTests(ContinuityTestCase):
    def test_guard_checks_the_final_state_and_rolls_back(self):
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertRaises(AdministrativeContinuityViolation):
            with administrative_continuity():
                RolePermission.objects.filter(role=self.administrator).delete()
        self.assertEqual(
            set(self.administrator.permissions.values_list('code', flat=True)),
            permissions.ADMINISTRATIVE_CAPABILITY
            | {
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
            }
            | permissions.SPACE_PERMISSIONS
            | permissions.BOOKING_PERMISSIONS
            | permissions.SUBJECT_PERMISSIONS
            | permissions.CLASS_GROUP_PERMISSIONS,
        )
        self.assertTrue(User.objects.get(pk=admin.pk).has_administrative_capability())

    def test_guard_accepts_a_change_that_keeps_capability_in_the_end(self):
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        teacher = create_user('docente@ifnmg.edu.br', self.teacher)
        with administrative_continuity():
            User.objects.filter(pk=admin.pk).update(is_active=False)
            User.objects.filter(pk=teacher.pk).update(is_superadmin=True)
        self.assertEqual(capable_emails(), {teacher.email})

    def test_guard_locks_active_users_in_pk_order(self):
        create_user('b@ifnmg.edu.br', self.administrator)
        create_user('a@ifnmg.edu.br', self.administrator)
        with CaptureQueriesContext(connection) as queries:
            with administrative_continuity():
                pass
        lock = next(q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql'])
        self.assertIn('"is_active"', lock)
        self.assertRegex(lock, r'^SELECT "accounts_user"\."id"( AS "pk")? FROM')
        self.assertRegex(lock, r'ORDER BY (1|"accounts_user"\."id") ASC FOR UPDATE$')


class ConcurrentDeactivationTests(TransactionTestCase):
    serialized_rollback = True

    def test_simultaneous_deactivations_keep_one_capable_user(self):
        administrator = Role.objects.get(code='ADMINISTRADOR')
        first = create_user('um@ifnmg.edu.br', administrator)
        second = create_user('dois@ifnmg.edu.br', administrator)

        result = {}
        started = threading.Event()

        def deactivate_second():
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    result['pid'] = cursor.fetchone()[0]
                started.set()
                User.objects.get(pk=second.pk).deactivate()
                result['outcome'] = 'deactivated'
            except AdministrativeContinuityViolation:
                result['outcome'] = 'refused'
            except Exception as error:
                result['outcome'] = error
            finally:
                started.set()
                connection.close()

        with transaction.atomic():
            first.deactivate()

            worker = threading.Thread(target=deactivate_second)
            worker.start()
            self.assertTrue(started.wait(10))
            self.assertIn('pid', result, result.get('outcome'))
            self.assertTrue(self.wait_until_blocked(result['pid']), 'second operation did not wait for the lock')

        worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result['outcome'], 'refused')
        self.assertFalse(User.objects.get(pk=first.pk).is_active)
        self.assertTrue(User.objects.get(pk=second.pk).is_active)
        self.assertEqual(capable_emails(), {second.email})

    def wait_until_blocked(self, pid, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute('SELECT cardinality(pg_blocking_pids(%s))', [pid])
                if cursor.fetchone()[0]:
                    return True
            time.sleep(0.05)
        return False


class DeferredContinuityTests(ContinuityTestCase):
    def setUp(self):
        self.admin = create_user('admin@ifnmg.edu.br', self.administrator)
        self.other = create_user('outro@ifnmg.edu.br', self.teacher)

    def test_intermediate_state_is_not_checked_inside_the_block(self):
        with transaction.atomic(), deferred_administrative_continuity():
            self.admin.change_role(self.teacher)
            self.other.change_role(self.administrator)
            ensure_administrative_continuity()
        self.assertEqual(capable_emails(), {'outro@ifnmg.edu.br'})

    def test_final_check_refuses_system_without_administrator(self):
        with self.assertRaises(AdministrativeContinuityViolation):
            with transaction.atomic(), deferred_administrative_continuity():
                self.admin.change_role(self.teacher)
                ensure_administrative_continuity()
        self.assertEqual(User.objects.get(pk=self.admin.pk).role, self.administrator)

    def test_outside_the_block_each_operation_is_checked(self):
        with transaction.atomic(), deferred_administrative_continuity():
            pass
        with self.assertRaises(AdministrativeContinuityViolation):
            self.admin.change_role(self.teacher)

    def test_block_is_closed_even_after_an_exception(self):
        with self.assertRaises(RuntimeError), deferred_administrative_continuity():
            raise RuntimeError
        with self.assertRaises(AdministrativeContinuityViolation):
            self.admin.deactivate()
