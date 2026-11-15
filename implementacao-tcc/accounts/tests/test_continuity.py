import threading
import time

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase

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
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import MANAGEMENT_PERMISSIONS, management_role, requester_role


def create_user(email, role, **fields):
    user = User.objects.create(email=email, name=email.partition('@')[0], **fields)
    UserRole.objects.create(user=user, role=role)
    return User.objects.get(pk=user.pk)


def capable_emails():
    return set(User.objects.with_administrative_capability().values_list('email', flat=True))


class ContinuityTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')


class AdministrativeCapabilityTests(ContinuityTestCase):
    def assertCapable(self, user, expected):
        user = User.objects.get(pk=user.pk)
        self.assertIs(user.has_administrative_capability(), expected)
        self.assertIs(user.email in capable_emails(), expected)

    def test_capability_follows_the_active_user_and_the_permissions(self):
        with self.case('superadmin ativo'):
            self.assertCapable(create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True), True)
        with self.case('superadmin inativo'):
            user = create_user(
                'super@ifnmg.edu.br', self.administrator, is_superadmin=True, is_active=False,
            )
            self.assertCapable(user, False)
        with self.case('administrador ativo pelo perfil'):
            self.assertCapable(create_user('admin@ifnmg.edu.br', self.administrator), True)
        with self.case('administrador inativo'):
            self.assertCapable(create_user('admin@ifnmg.edu.br', self.administrator, is_active=False), False)
        with self.case('perfil sem permissões'):
            self.assertCapable(create_user('docente@ifnmg.edu.br', self.teacher), False)
        with self.case('perfil sem uma das permissões'):
            for code in permissions.ADMINISTRATIVE_CAPABILITY:
                with self.subTest(missing=code):
                    RolePermission.objects.filter(role=self.coordination).delete()
                    for granted in permissions.ADMINISTRATIVE_CAPABILITY - {code}:
                        RolePermission.objects.create(
                            role=self.coordination, permission=Permission.objects.get(code=granted),
                        )
                    user = create_user(f'coord.{code.lower()}@ifnmg.edu.br', self.coordination)
                    self.assertCapable(user, False)
        with self.case('perfil próprio com as mesmas permissões'):
            for code in permissions.ADMINISTRATIVE_CAPABILITY:
                RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
            self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), True)
        with self.case('permissões reservadas não contam'):
            for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
                RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
            self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), False)
        with self.case('permissões a mais não importam'):
            for code in permissions.ADMINISTRATIVE_CAPABILITY:
                RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
            extra = Permission.objects.create(code='RESERVA.APROVAR', description='Aprovar reserva')
            RolePermission.objects.create(role=self.coordination, permission=extra)
            self.assertCapable(create_user('coord@ifnmg.edu.br', self.coordination), True)


class DeactivationTests(ContinuityTestCase):
    def test_last_capable_user_cannot_be_deactivated(self):
        with self.case('último administrador'):
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            with self.assertRaises(AdministrativeContinuityViolation) as raised:
                admin.deactivate()
            self.assertIsInstance(raised.exception, ValidationError)
            self.assertTrue(raised.exception.messages)
            self.assertTrue(admin.is_active)
            self.assertTrue(User.objects.get(pk=admin.pk).is_active)
        with self.case('último superadmin'):
            superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            with self.assertRaises(AdministrativeContinuityViolation):
                superadmin.deactivate()
            self.assertTrue(User.objects.get(pk=superadmin.pk).is_active)
        with self.case('superadmin inativo não conta'):
            create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True, is_active=False)
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            with self.assertRaises(AdministrativeContinuityViolation):
                admin.deactivate()
            self.assertTrue(User.objects.get(pk=admin.pk).is_active)

    def test_deactivation_allowed_when_another_user_is_capable(self):
        with self.case('outro administrador'):
            first = create_user('um@ifnmg.edu.br', self.administrator)
            second = create_user('dois@ifnmg.edu.br', self.administrator)
            first.deactivate()
            self.assertFalse(first.is_active)
            self.assertFalse(User.objects.get(pk=first.pk).is_active)
            self.assertEqual(capable_emails(), {second.email})
        with self.case('perfil próprio conta'):
            for code in permissions.ADMINISTRATIVE_CAPABILITY:
                RolePermission.objects.create(role=self.coordination, permission=Permission.objects.get(code=code))
            create_user('coord@ifnmg.edu.br', self.coordination)
            superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            superadmin.deactivate()
            self.assertFalse(User.objects.get(pk=superadmin.pk).is_active)

    def test_deactivation_keeps_the_data_and_drops_the_permissions(self):
        with self.case('mantém os dados'):
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
        with self.case('não sobrescreve outros campos'):
            create_user('admin@ifnmg.edu.br', self.administrator)
            user = create_user('docente@ifnmg.edu.br', self.teacher)
            User.objects.filter(pk=user.pk).update(name='Nome atualizado')
            user.deactivate()
            self.assertEqual(User.objects.get(pk=user.pk).name, 'Nome atualizado')
        with self.case('perde as permissões na mesma instância'):
            create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            self.assertTrue(admin.has_perm(permissions.USER_VIEW))
            admin.deactivate()
            self.assertFalse(admin.has_perm(permissions.USER_VIEW))

    def test_reactivation_restores_everything_without_the_guard(self):
        with self.case('restaura perfil, senha e superadmin'):
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
        with self.case('sem a trava'):
            user = create_user('docente@ifnmg.edu.br', self.teacher, is_active=False)
            self.assertEqual(capable_emails(), set())
            user.reactivate()
            self.assertTrue(User.objects.get(pk=user.pk).is_active)


class SuperadminStatusTests(ContinuityTestCase):
    def test_grant_and_refused_removal_of_the_last_superadmin(self):
        with self.case('conceder'):
            user = create_user('docente@ifnmg.edu.br', self.teacher)
            self.assertFalse(user.has_perm(permissions.ROLE_VIEW))
            user.set_superadmin(True)
            self.assertTrue(user.has_perm(permissions.ROLE_VIEW))
            self.assertTrue(user.is_superadmin)
            reloaded = User.objects.get(pk=user.pk)
            self.assertTrue(reloaded.is_superadmin)
            self.assertTrue(reloaded.has_administrative_capability())
        with self.case('retirar o último'):
            superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            with self.assertRaises(AdministrativeContinuityViolation):
                superadmin.set_superadmin(False)
            self.assertTrue(superadmin.is_superadmin)
            self.assertTrue(User.objects.get(pk=superadmin.pk).is_superadmin)

    def test_removing_superadmin_allowed_while_someone_stays_capable(self):
        with self.case('outro administrador'):
            create_user('admin@ifnmg.edu.br', self.administrator)
            superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            superadmin.set_superadmin(False)
            self.assertFalse(User.objects.get(pk=superadmin.pk).is_superadmin)
        with self.case('continua capaz pelo perfil'):
            superadmin = create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True)
            superadmin.set_superadmin(False)
            reloaded = User.objects.get(pk=superadmin.pk)
            self.assertFalse(reloaded.is_superadmin)
            self.assertTrue(reloaded.has_administrative_capability())
        with self.case('nenhuma regra exige superadmin ativo'):
            create_user('admin@ifnmg.edu.br', self.administrator)
            first = create_user('um@ifnmg.edu.br', self.teacher, is_superadmin=True)
            second = create_user('dois@ifnmg.edu.br', self.teacher, is_superadmin=True)

            first.set_superadmin(False)
            second.deactivate()

            self.assertFalse(User.objects.filter(is_active=True, is_superadmin=True).exists())
            self.assertEqual(capable_emails(), {'admin@ifnmg.edu.br'})


class ChangeRoleTests(ContinuityTestCase):
    def test_change_role_replaces_the_only_role(self):
        with self.case('substitui o perfil'):
            create_user('admin@ifnmg.edu.br', self.administrator)
            user = create_user('docente@ifnmg.edu.br', self.teacher)
            for role in (self.administrator, self.coordination):
                with self.subTest(role.code):
                    user.change_role(role)
                    self.assertEqual(list(User.objects.get(pk=user.pk).roles.all()), [role])
                    self.assertEqual(UserRole.objects.filter(user=user).count(), 1)
        with self.case('atualiza as permissões da instância'):
            superadmin = create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            user = create_user('docente@ifnmg.edu.br', self.teacher)
            self.assertFalse(user.has_perm(permissions.USER_VIEW))
            user.change_role(self.administrator)
            self.assertTrue(user.has_perm(permissions.USER_VIEW))
            self.assertTrue(superadmin.is_superadmin)
        with self.case('exige um perfil'):
            create_user('admin@ifnmg.edu.br', self.administrator)
            user = create_user('docente@ifnmg.edu.br', self.teacher)
            with self.assertRaises(ValidationError):
                user.change_role(None)
            self.assertEqual(list(User.objects.get(pk=user.pk).roles.all()), [self.teacher])

    def test_change_role_keeps_someone_capable(self):
        with self.case('último capaz pelo perfil'):
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            with self.assertRaises(AdministrativeContinuityViolation):
                admin.change_role(self.teacher)
            self.assertEqual(list(User.objects.get(pk=admin.pk).roles.all()), [self.administrator])
            self.assertTrue(admin.has_perm(permissions.USER_VIEW))
        with self.case('último superadmin troca de perfil'):
            superadmin = create_user('super@ifnmg.edu.br', self.administrator, is_superadmin=True)
            superadmin.change_role(self.teacher)
            reloaded = User.objects.get(pk=superadmin.pk)
            self.assertEqual(reloaded.role, self.teacher)
            self.assertTrue(reloaded.has_administrative_capability())
        with self.case('outro capaz'):
            create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            admin.change_role(self.teacher)
            self.assertEqual(User.objects.get(pk=admin.pk).role, self.teacher)


class ContinuityGuardTests(ContinuityTestCase):
    def test_guard_checks_only_the_final_state(self):
        with self.case('estado final recusado e desfeito'):
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            with self.assertRaises(AdministrativeContinuityViolation):
                with administrative_continuity():
                    RolePermission.objects.filter(role=self.administrator).delete()
            self.assertEqual(
                set(self.administrator.permissions.values_list('code', flat=True)),
                MANAGEMENT_PERMISSIONS,
            )
            self.assertTrue(User.objects.get(pk=admin.pk).has_administrative_capability())
        with self.case('estado final aceito'):
            admin = create_user('admin@ifnmg.edu.br', self.administrator)
            teacher = create_user('docente@ifnmg.edu.br', self.teacher)
            with administrative_continuity():
                User.objects.filter(pk=admin.pk).update(is_active=False)
                User.objects.filter(pk=teacher.pk).update(is_superadmin=True)
            self.assertEqual(capable_emails(), {teacher.email})


class ConcurrentDeactivationTests(TransactionTestCase):
    serialized_rollback = True

    def test_simultaneous_deactivations_keep_one_capable_user(self):
        administrator = management_role()
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
    def test_deferred_block_checks_only_at_the_end(self):
        admin = create_user('admin@ifnmg.edu.br', self.administrator)
        other = create_user('outro@ifnmg.edu.br', self.teacher)
        with self.case('estado intermediário não é conferido'):
            with transaction.atomic(), deferred_administrative_continuity():
                User.objects.get(pk=admin.pk).change_role(self.teacher)
                User.objects.get(pk=other.pk).change_role(self.administrator)
                ensure_administrative_continuity()
            self.assertEqual(capable_emails(), {'outro@ifnmg.edu.br'})
        with self.case('conferência final recusa sistema sem administrador'):
            with self.assertRaises(AdministrativeContinuityViolation):
                with transaction.atomic(), deferred_administrative_continuity():
                    User.objects.get(pk=admin.pk).change_role(self.teacher)
                    ensure_administrative_continuity()
            self.assertEqual(User.objects.get(pk=admin.pk).role, self.administrator)
        with self.case('fora do bloco cada operação é conferida'):
            with transaction.atomic(), deferred_administrative_continuity():
                pass
            with self.assertRaises(AdministrativeContinuityViolation):
                User.objects.get(pk=admin.pk).change_role(self.teacher)
        with self.case('o bloco fecha mesmo depois de uma exceção'):
            with self.assertRaises(RuntimeError), deferred_administrative_continuity():
                raise RuntimeError
            with self.assertRaises(AdministrativeContinuityViolation):
                User.objects.get(pk=admin.pk).deactivate()
