from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('accounts', '0005_user_session_epoch')]
AFTER = [('accounts', '0007_remove_role_is_system')]
SCOPE_CODES = {'DISCIPLINA.ACESSAR_TODAS', 'TURMA.ACESSAR_TODAS'}


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


class InitialRolesMigrationTests(TransactionTestCase):
    serialized_rollback = True

    def tearDown(self):
        migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_forward_keeps_roles_links_and_grants_without_granting_the_scope(self):
        apps = migrate(BEFORE)
        Role = apps.get_model('accounts', 'Role')
        User = apps.get_model('accounts', 'User')
        UserRole = apps.get_model('accounts', 'UserRole')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        self.assertTrue(administrator.is_system)
        user = User.objects.create(email='ana@ifnmg.edu.br', name='Ana')
        UserRole.objects.create(user=user, role=administrator)
        grants = set(administrator.permissions.values_list('code', flat=True))

        apps = migrate(AFTER)
        Role = apps.get_model('accounts', 'Role')
        RolePermission = apps.get_model('accounts', 'RolePermission')
        UserRole = apps.get_model('accounts', 'UserRole')
        administrator = Role.objects.get(code='ADMINISTRADOR')
        self.assertEqual(set(administrator.permissions.values_list('code', flat=True)), grants)
        self.assertEqual(UserRole.objects.get(user__email='ana@ifnmg.edu.br').role, administrator)
        self.assertFalse(RolePermission.objects.filter(permission__code__in=SCOPE_CODES).exists())
        self.assertNotIn('is_system', {field.name for field in Role._meta.get_fields()})

    def test_backward_marks_the_initial_roles_again_and_removes_the_scope(self):
        apps = migrate(AFTER)
        apps.get_model('accounts', 'Role').objects.create(code='COORDENACAO', name='Coordenação')

        apps = migrate(BEFORE)
        Role = apps.get_model('accounts', 'Role')
        Permission = apps.get_model('accounts', 'Permission')
        self.assertEqual(
            dict(Role.objects.values_list('code', 'is_system')),
            {'ADMINISTRADOR': True, 'DOCENTE': True, 'COORDENACAO': False},
        )
        self.assertFalse(Permission.objects.filter(code__in=SCOPE_CODES).exists())
