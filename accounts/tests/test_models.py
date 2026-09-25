from allauth.account.models import EmailAddress
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
            {
                'id', 'password', 'last_login', 'email', 'name', 'username',
                'is_active', 'is_superadmin', 'created_at',
            },
        )

    def test_no_default_django_user_attributes(self):
        """O `username` fica fora da lista: ele existe como identificador de domínio, e não

        como a credencial do AbstractUser (D2 da Change identificar-usuario-por-username).
        """
        user = User(email='maria@ifnmg.edu.br', name='Maria')
        for attribute in (
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


class UsernameTests(TestCase):
    def build(self, email='maria@ifnmg.edu.br', name='Maria', username=None):
        user = User(email=email, name=name, username=username)
        user.set_unusable_password()
        return user

    def clean(self, **values):
        user = self.build(**values)
        user.full_clean()
        return user

    def test_keeps_spaces_accents_and_abbreviations(self):
        for value in ('Aldo Gomes', 'João da Silva', 'Érica', 'Gera Jr.', 'Élcio José'):
            with self.subTest(value=value):
                self.assertEqual(self.clean(username=value).username, value)

    def test_strips_and_collapses_spaces(self):
        self.assertEqual(self.clean(username='  Aldo   Gomes  ').username, 'Aldo Gomes')

    def test_blank_becomes_none(self):
        for value in ('', '   ', None):
            with self.subTest(value=value):
                self.assertIsNone(self.clean(username=value).username)

    def test_several_users_without_username(self):
        self.clean().save()
        other = self.build(email='outra@ifnmg.edu.br', name='Outra', username='')
        other.full_clean()
        other.save()
        self.assertEqual(User.objects.filter(username=None).count(), 2)

    def test_validation_rejects_duplicate(self):
        self.clean(username='Aldo Gomes').save()
        other = self.build(email='outro@ifnmg.edu.br', name='Outro', username='Aldo Gomes')
        with self.assertRaises(ValidationError) as context:
            other.full_clean()
        self.assertIn('username', context.exception.message_dict)

    def test_validation_rejects_duplicate_differing_only_in_case(self):
        self.clean(username='Aldo Gomes').save()
        other = self.build(email='outro@ifnmg.edu.br', name='Outro', username='ALDO GOMES')
        with self.assertRaises(ValidationError) as context:
            other.full_clean()
        self.assertIn('username', context.exception.message_dict)

    def test_accents_make_values_distinct(self):
        self.clean(username='Érica').save()
        other = self.clean(email='outra@ifnmg.edu.br', name='Outra', username='Erica')
        other.save()
        self.assertEqual(User.objects.count(), 2)

    def test_own_username_is_not_a_duplicate_of_itself(self):
        user = self.clean(username='Aldo Gomes')
        user.save()
        user.full_clean()

    def test_inactive_user_username_remains_unavailable(self):
        user = self.clean(username='Aldo Gomes')
        user.is_active = False
        user.save()
        other = self.build(email='outro@ifnmg.edu.br', name='Outro', username='Aldo Gomes')
        with self.assertRaises(ValidationError) as context:
            other.full_clean()
        self.assertIn('username', context.exception.message_dict)

    def test_database_rejects_duplicate_differing_only_in_case(self):
        User.objects.create(email='aldo@ifnmg.edu.br', name='Aldo', username='Aldo Gomes')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email='outro@ifnmg.edu.br', name='Outro', username='aldo gomes')
        self.assertEqual(User.objects.count(), 1)


class RoleTests(TestCase):
    def test_is_system_false_by_default(self):
        role = Role.objects.create(code='COORDENACAO', name='Coordenação')
        self.assertFalse(role.is_system)
        self.assertEqual(role.description, '')

    def test_valid_codes(self):
        for code in ('COORDENACAO', 'COORDENACAO_GERAL', 'A_B_C'):
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
        count = Role.objects.count()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Role.objects.create(code='COORDENACAO_GERAL', name='coordenação')
        self.assertEqual(Role.objects.count(), count)


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
        Permission.objects.create(code='TESTE.CRIAR', description='Criar teste')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Permission.objects.create(code='TESTE.CRIAR', description='Outra')


class UserRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')

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
        cls.permission = Permission.objects.create(code='TESTE.VISUALIZAR', description='Consultar teste')

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
        self.assertFalse(RolePermission.objects.filter(permission=self.permission).exists())
        self.assertTrue(Permission.objects.filter(pk=self.permission.pk).exists())

    def test_deleting_permission_removes_grants(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        self.permission.delete()
        self.assertFalse(RolePermission.objects.filter(role=self.role).exists())
        self.assertTrue(Role.objects.filter(pk=self.role.pk).exists())


class RegisterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')

    def test_register_creates_active_user_with_one_role_and_unusable_password(self):
        user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Souza', role=self.teacher)
        user = User.objects.get(pk=user.pk)
        self.assertEqual((user.email, user.name), ('maria@ifnmg.edu.br', 'Maria Souza'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superadmin)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(list(user.roles.all()), [self.teacher])
        self.assertEqual(user.role, self.teacher)

    def test_register_normalizes_email_and_name(self):
        user = User.objects.register(email=' Maria@IFNMG.edu.br ', name='  Maria  ', role=self.teacher)
        self.assertEqual(User.objects.get(pk=user.pk).email, 'maria@ifnmg.edu.br')
        self.assertEqual(User.objects.get(pk=user.pk).name, 'Maria')

    def test_register_does_not_accept_superadmin_or_password(self):
        with self.assertRaises(TypeError):
            User.objects.register(
                email='maria@ifnmg.edu.br', name='Maria', role=self.teacher, is_superadmin=True,
            )
        with self.assertRaises(TypeError):
            User.objects.register(
                email='maria@ifnmg.edu.br', name='Maria', role=self.teacher, password='Senha-forte-123',
            )
        self.assertFalse(User.objects.exists())

    def test_register_refuses_invalid_data_without_creating_anything(self):
        cases = {
            'name': dict(email='maria@ifnmg.edu.br', name='  ', role=self.teacher),
            'email': dict(email='', name='Maria', role=self.teacher),
            'invalid email': dict(email='maria.ifnmg.edu.br', name='Maria', role=self.teacher),
            'other domain email': dict(email='maria@gmail.com', name='Maria', role=self.teacher),
            'similar domain email': dict(email='maria@ifnmg.edu.br.com', name='Maria', role=self.teacher),
            'role': dict(email='maria@ifnmg.edu.br', name='Maria', role=None),
        }
        for label, data in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValidationError) as raised:
                    User.objects.register(**data)
                self.assertIn(label.split()[-1], raised.exception.message_dict)
        self.assertFalse(User.objects.exists())
        self.assertFalse(UserRole.objects.exists())

    def test_register_refuses_email_in_use_ignoring_case_and_status(self):
        User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=self.teacher)
        User.objects.filter(email='maria@ifnmg.edu.br').update(is_active=False)
        with self.assertRaises(ValidationError) as raised:
            User.objects.register(email='MARIA@ifnmg.edu.br', name='Outra', role=self.administrator)
        self.assertTrue(raised.exception.messages)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserRole.objects.count(), 1)

    def test_register_leaves_no_user_without_role_when_link_fails(self):
        unsaved_role = Role(code='INEXISTENTE', name='Inexistente')
        with self.assertRaises(ValueError):
            User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=unsaved_role)
        self.assertFalse(User.objects.exists())


class UpdateDetailsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.executor = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.teacher)

    def setUp(self):
        self.user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=self.teacher)
        self.user.set_password('Senha-forte-123')
        self.user.save()

    def test_changes_name_and_email_only(self):
        password = self.user.password
        self.user.update_details(self.executor, name='Maria Souza', email=' Maria.Souza@IFNMG.edu.br ')
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual((user.name, user.email), ('Maria Souza', 'maria.souza@ifnmg.edu.br'))
        self.assertEqual(user.password, password)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superadmin)
        self.assertEqual(user.role, self.teacher)

    def test_removes_email_addresses_other_than_the_new_one(self):
        EmailAddress.objects.create(user=self.user, email='maria@ifnmg.edu.br')
        EmailAddress.objects.create(user=self.user, email='maria.souza@ifnmg.edu.br')
        self.user.update_details(self.executor, name='Maria Souza', email='Maria.Souza@ifnmg.edu.br')
        self.assertEqual(
            list(EmailAddress.objects.filter(user=self.user).values_list('email', flat=True)),
            ['maria.souza@ifnmg.edu.br'],
        )

    def test_keeps_email_addresses_when_the_change_is_refused(self):
        EmailAddress.objects.create(user=self.user, email='maria@ifnmg.edu.br')
        with self.assertRaises(ValidationError):
            self.user.update_details(self.executor, name='Maria', email='admin@ifnmg.edu.br')
        self.assertTrue(EmailAddress.objects.filter(user=self.user, email='maria@ifnmg.edu.br').exists())

    def test_does_not_overwrite_status_changed_elsewhere(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.user.update_details(self.executor, name='Maria Souza', email=self.user.email)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.name, 'Maria Souza')
        self.assertFalse(user.is_active)

    def test_inactive_user_can_be_edited(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        user = User.objects.get(pk=self.user.pk)
        user.update_details(self.executor, name='Maria Souza', email=user.email)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.name, 'Maria Souza')
        self.assertFalse(user.is_active)

    def test_refuses_invalid_data_and_keeps_previous_values(self):
        cases = {
            'name': dict(name='', email='maria@ifnmg.edu.br'),
            'email': dict(name='Maria', email='maria.ifnmg.edu.br'),
        }
        for field, data in cases.items():
            with self.subTest(field):
                with self.assertRaises(ValidationError) as raised:
                    self.user.update_details(self.executor, **data)
                self.assertIn(field, raised.exception.message_dict)
                self.assertEqual((self.user.name, self.user.email), ('Maria Sousa', 'maria@ifnmg.edu.br'))
                user = User.objects.get(pk=self.user.pk)
                self.assertEqual((user.name, user.email), ('Maria Sousa', 'maria@ifnmg.edu.br'))

    def test_refuses_email_of_another_user_ignoring_case(self):
        with self.assertRaises(ValidationError):
            self.user.update_details(self.executor, name='Maria', email='Admin@ifnmg.edu.br')
        self.assertEqual(User.objects.get(pk=self.user.pk).email, 'maria@ifnmg.edu.br')
        self.assertEqual(User.objects.get(pk=self.executor.pk).email, 'admin@ifnmg.edu.br')
