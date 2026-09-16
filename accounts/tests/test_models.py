from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import SimpleTestCase, TestCase

from accounts.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserManager,
    UserRole,
)


class UserModelTests(SimpleTestCase):
    def test_user_is_the_auth_user_model(self):
        self.assertIs(get_user_model(), User)

    def test_email_is_the_login_identifier(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertEqual(User.EMAIL_FIELD, 'email')
        self.assertEqual(User.REQUIRED_FIELDS, ['name'])

    def test_user_fields(self):
        fields = {field.name for field in User._meta.concrete_fields}
        self.assertEqual(
            fields,
            {'id', 'password', 'last_login', 'email', 'name', 'is_active', 'is_superadmin', 'created_at'},
        )

    def test_no_default_django_user_attributes(self):
        user = User(email='maria@ifnmg.edu.br', name='Maria')
        for attribute in (
            'username',
            'first_name',
            'last_name',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        ):
            with self.subTest(attribute=attribute):
                self.assertFalse(hasattr(user, attribute))

    def test_defaults(self):
        user = User(email='maria@ifnmg.edu.br', name='Maria')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superadmin)

    def test_normalize_email_strips_and_lowercases(self):
        self.assertEqual(
            UserManager.normalize_email(' Maria@IFNMG.edu.br '),
            'maria@ifnmg.edu.br',
        )


class UserDatabaseTests(TestCase):
    def test_created_at_filled_on_creation(self):
        user = User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        self.assertIsNotNone(user.created_at)

    def test_validation_normalizes_email(self):
        user = User(email='Maria@IFNMG.edu.br', name='Maria')
        user.set_unusable_password()
        user.full_clean()
        self.assertEqual(user.email, 'maria@ifnmg.edu.br')

    def test_validation_rejects_email_differing_only_in_case(self):
        User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        other = User(email='MARIA@ifnmg.edu.br', name='Outra Maria')
        other.set_unusable_password()
        with self.assertRaises(ValidationError):
            other.full_clean()

    def test_database_rejects_email_differing_only_in_case(self):
        User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='Maria@ifnmg.edu.br', name='Outra Maria')
        self.assertEqual(User.objects.count(), 1)

    def test_inactive_user_email_remains_unavailable(self):
        User.objects.create(email='antigo@ifnmg.edu.br', name='Antigo', is_active=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='ANTIGO@ifnmg.edu.br', name='Novo')


class RoleTests(TestCase):
    def test_is_system_false_by_default(self):
        role = Role.objects.create(code='COORDENACAO', name='Coordenação')
        self.assertFalse(role.is_system)
        self.assertEqual(role.description, '')

    def test_valid_codes(self):
        for code in ('DOCENTE', 'COORDENACAO_GERAL', 'A_B_C'):
            with self.subTest(code=code):
                Role(code=code, name=code.title()).full_clean()

    def test_validation_rejects_malformed_code(self):
        for code in ('', 'coordenacao', 'COORD-1', 'COORD_', '_COORD', 'COORD__GERAL', 'COORDENAÇÃO'):
            with self.subTest(code=code):
                with self.assertRaises(ValidationError) as context:
                    Role(code=code, name='Coordenação').full_clean()
                self.assertIn('code', context.exception.message_dict)

    def test_database_rejects_malformed_code(self):
        for code in ('', 'coordenacao', 'COORD-1'):
            with self.subTest(code=code):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Role.objects.create(code=code, name='Coordenação')

    def test_database_rejects_duplicate_code(self):
        Role.objects.create(code='COORDENACAO', name='Coordenação')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Role.objects.create(code='COORDENACAO', name='Outra coordenação')

    def test_validation_requires_name(self):
        with self.assertRaises(ValidationError) as context:
            Role(code='COORDENACAO', name='').full_clean()
        self.assertIn('name', context.exception.message_dict)

    def test_validation_strips_name(self):
        role = Role(code='COORDENACAO', name='  Coordenação  ')
        role.full_clean()
        self.assertEqual(role.name, 'Coordenação')

    def test_validation_rejects_name_differing_only_in_case(self):
        Role.objects.create(code='COORDENACAO', name='Coordenação')
        with self.assertRaises(ValidationError):
            Role(code='COORDENACAO_GERAL', name='COORDENAÇÃO').full_clean()

    def test_database_rejects_name_differing_only_in_case(self):
        Role.objects.create(code='COORDENACAO', name='Coordenação')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Role.objects.create(code='COORDENACAO_GERAL', name='coordenação')
        self.assertEqual(Role.objects.count(), 1)


class PermissionTests(TestCase):
    def test_resource_and_action_derived_from_code(self):
        permission = Permission(code='USUARIO.ALTERAR_PERFIL', description='Trocar o perfil')
        self.assertEqual(permission.resource, 'USUARIO')
        self.assertEqual(permission.action, 'ALTERAR_PERFIL')

    def test_resource_and_action_are_not_columns(self):
        fields = {field.name for field in Permission._meta.concrete_fields}
        self.assertEqual(fields, {'id', 'code', 'description'})

    def test_validation_rejects_malformed_code(self):
        for code in ('usuario.criar', 'USUARIO', 'USUARIO.', '.CRIAR', 'USUARIO.CRIAR.TUDO', 'USUARIO-CRIAR'):
            with self.subTest(code=code):
                with self.assertRaises(ValidationError) as context:
                    Permission(code=code, description='Teste').full_clean()
                self.assertIn('code', context.exception.message_dict)

    def test_database_rejects_malformed_code(self):
        for code in ('usuario.criar', 'USUARIO', 'USUARIO.CRIAR.TUDO'):
            with self.subTest(code=code):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Permission.objects.create(code=code, description='Teste')

    def test_database_rejects_duplicate_code(self):
        Permission.objects.create(code='USUARIO.CRIAR', description='Cadastrar usuário')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Permission.objects.create(code='USUARIO.CRIAR', description='Outra')


class UserRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        cls.teacher = Role.objects.create(code='DOCENTE', name='Docente')
        cls.administrator = Role.objects.create(code='ADMINISTRADOR', name='Administrador')

    def test_link_reachable_from_both_sides(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        self.assertEqual(list(self.user.roles.all()), [self.teacher])
        self.assertEqual(list(self.teacher.users.all()), [self.user])

    def test_database_rejects_second_role(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserRole.objects.create(user=self.user, role=self.administrator)
        self.assertEqual(list(self.user.roles.all()), [self.teacher])

    def test_database_rejects_duplicate_link(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserRole.objects.create(user=self.user, role=self.teacher)

    def test_role_with_user_cannot_be_deleted(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.teacher.delete()
        self.assertTrue(Role.objects.filter(pk=self.teacher.pk).exists())
        self.assertEqual(list(self.user.roles.all()), [self.teacher])

    def test_role_with_inactive_user_cannot_be_deleted(self):
        inactive = User.objects.create(email='antigo@ifnmg.edu.br', name='Antigo', is_active=False)
        UserRole.objects.create(user=inactive, role=self.teacher)
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.teacher.delete()
        self.assertTrue(Role.objects.filter(pk=self.teacher.pk).exists())

    def test_role_without_users_can_be_deleted(self):
        self.teacher.delete()
        self.assertFalse(Role.objects.filter(pk=self.teacher.pk).exists())

    def test_deleting_user_removes_link(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        self.user.delete()
        self.assertFalse(UserRole.objects.exists())
        self.assertTrue(Role.objects.filter(pk=self.teacher.pk).exists())


class RolePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Role.objects.create(code='COORDENACAO', name='Coordenação')
        cls.permission = Permission.objects.create(code='USUARIO.VISUALIZAR', description='Listar usuários')

    def test_grant_reachable_from_both_sides(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        self.assertEqual(list(self.role.permissions.all()), [self.permission])
        self.assertEqual(list(self.permission.roles.all()), [self.role])

    def test_database_rejects_duplicate_grant(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RolePermission.objects.create(role=self.role, permission=self.permission)

    def test_deleting_role_removes_grants(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        self.role.delete()
        self.assertFalse(RolePermission.objects.exists())
        self.assertTrue(Permission.objects.filter(pk=self.permission.pk).exists())

    def test_deleting_permission_removes_grants(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        self.permission.delete()
        self.assertFalse(RolePermission.objects.exists())
        self.assertTrue(Role.objects.filter(pk=self.role.pk).exists())
