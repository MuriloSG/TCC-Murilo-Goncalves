from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import (
    Permission,
    Role,
    User,
    UserRole,
)
from accounts.tests.roles import management_role, requester_role
from audit import catalog
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin
from schedule.models import Teacher


class UserDatabaseTests(IsolatedCasesMixin, TestCase):
    def test_email_is_normalized_and_unique_ignoring_case(self):
        with self.case('normaliza'):
            user = User(email='Maria@IFNMG.edu.br', name='Maria')
            user.set_unusable_password()
            user.full_clean()
            self.assertEqual(user.email, 'maria@ifnmg.edu.br')
        with self.case('validação recusa outra caixa'):
            User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
            other = User(email='MARIA@ifnmg.edu.br', name='Outra Maria')
            other.set_unusable_password()
            with self.assertRaises(ValidationError):
                other.full_clean()
        with self.case('banco recusa outra caixa'):
            User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
            with self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create(email='Maria@ifnmg.edu.br', name='Outra Maria')
            self.assertEqual(User.objects.count(), 1)


class UsernameTests(IsolatedCasesMixin, TestCase):
    def build(self, email='maria@ifnmg.edu.br', name='Maria', username=None):
        user = User(email=email, name=name, username=username)
        user.set_unusable_password()
        return user

    def clean(self, **values):
        user = self.build(**values)
        user.full_clean()
        return user

    def test_username_is_normalized(self):
        with self.case('mantém espaços, acentos e abreviações'):
            for value in ('Aldo Gomes', 'João da Silva', 'Érica', 'Gera Jr.', 'Élcio José'):
                with self.subTest(value=value):
                    self.assertEqual(self.clean(username=value).username, value)
        with self.case('apara e junta espaços'):
            self.assertEqual(self.clean(username='  Aldo   Gomes  ').username, 'Aldo Gomes')
        with self.case('em branco vira nulo'):
            for value in ('', '   ', None):
                with self.subTest(value=value):
                    self.assertIsNone(self.clean(username=value).username)
        with self.case('vários usuários sem nome de usuário'):
            self.clean().save()
            other = self.build(email='outra@ifnmg.edu.br', name='Outra', username='')
            other.full_clean()
            other.save()
            self.assertEqual(User.objects.filter(username=None).count(), 2)

    def test_username_is_unique_ignoring_case(self):
        with self.case('validação recusa outra caixa'):
            self.clean(username='Aldo Gomes').save()
            for value in ('Aldo Gomes', 'ALDO GOMES'):
                with self.subTest(value=value):
                    other = self.build(email='outro@ifnmg.edu.br', name='Outro', username=value)
                    with self.assertRaises(ValidationError) as context:
                        other.full_clean()
                    self.assertIn('username', context.exception.message_dict)
        with self.case('acentos distinguem'):
            self.clean(username='Érica').save()
            other = self.clean(email='outra@ifnmg.edu.br', name='Outra', username='Erica')
            other.save()
            self.assertEqual(User.objects.count(), 2)
        with self.case('o próprio não é repetido'):
            user = self.clean(username='Aldo Gomes')
            user.save()
            user.full_clean()
        with self.case('de usuário inativo continua indisponível'):
            user = self.clean(username='Aldo Gomes')
            user.is_active = False
            user.save()
            other = self.build(email='outro@ifnmg.edu.br', name='Outro', username='Aldo Gomes')
            with self.assertRaises(ValidationError) as context:
                other.full_clean()
            self.assertIn('username', context.exception.message_dict)
        with self.case('banco recusa outra caixa'):
            User.objects.create(email='aldo@ifnmg.edu.br', name='Aldo', username='Aldo Gomes')
            with self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create(email='outro@ifnmg.edu.br', name='Outro', username='aldo gomes')
            self.assertEqual(User.objects.count(), 1)


class RoleTests(IsolatedCasesMixin, TestCase):
    def test_role_code_format(self):
        with self.case('códigos válidos'):
            for code in ('COORDENACAO', 'COORDENACAO_GERAL', 'A_B_C'):
                with self.subTest(code=code):
                    Role(code=code, name=code.title()).full_clean()
        with self.case('validação recusa código malformado'):
            for code in ('', 'coordenacao', 'COORD-1', 'COORD_', '_COORD', 'COORD__GERAL', 'COORDENAÇÃO'):
                with self.subTest(code=code):
                    with self.assertRaises(ValidationError) as context:
                        Role(code=code, name='Coordenação').full_clean()
                    self.assertIn('code', context.exception.message_dict)
        with self.case('banco recusa código malformado'):
            for code in ('', 'coordenacao', 'COORD-1'):
                with self.subTest(code=code):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        Role.objects.create(code=code, name='Coordenação')

    def test_role_name_is_unique_ignoring_case(self):
        with self.case('apara o nome'):
            role = Role(code='COORDENACAO', name='  Coordenação  ')
            role.full_clean()
            self.assertEqual(role.name, 'Coordenação')
        with self.case('validação recusa outra caixa'):
            Role.objects.create(code='COORDENACAO', name='Coordenação')
            with self.assertRaises(ValidationError):
                Role(code='COORDENACAO_GERAL', name='COORDENAÇÃO').full_clean()
        with self.case('banco recusa outra caixa'):
            Role.objects.create(code='COORDENACAO', name='Coordenação')
            count = Role.objects.count()
            with self.assertRaises(IntegrityError), transaction.atomic():
                Role.objects.create(code='COORDENACAO_GERAL', name='coordenação')
            self.assertEqual(Role.objects.count(), count)


class PermissionTests(IsolatedCasesMixin, TestCase):
    def test_permission_code_gives_resource_and_action(self):
        with self.case('recurso e ação'):
            permission = Permission(code='USUARIO.ALTERAR_PERFIL', description='Trocar o perfil')
            self.assertEqual(permission.resource, 'USUARIO')
            self.assertEqual(permission.action, 'ALTERAR_PERFIL')
        with self.case('validação recusa código malformado'):
            for code in ('usuario.criar', 'USUARIO', 'USUARIO.', '.CRIAR', 'USUARIO.CRIAR.TUDO', 'USUARIO-CRIAR'):
                with self.subTest(code=code):
                    with self.assertRaises(ValidationError) as context:
                        Permission(code=code, description='Teste').full_clean()
                    self.assertIn('code', context.exception.message_dict)
        with self.case('banco recusa código malformado'):
            for code in ('usuario.criar', 'USUARIO', 'USUARIO.CRIAR.TUDO'):
                with self.subTest(code=code):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        Permission.objects.create(code=code, description='Teste')


class UserRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email='maria@ifnmg.edu.br', name='Maria')
        cls.teacher = requester_role()
        cls.administrator = management_role()

    def test_database_rejects_second_role(self):
        UserRole.objects.create(user=self.user, role=self.teacher)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserRole.objects.create(user=self.user, role=self.administrator)
        self.assertEqual(list(self.user.roles.all()), [self.teacher])


class RegisterTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()
        cls.administrator = management_role()

    def test_register_creates_an_active_user_with_one_role(self):
        with self.case('usuário ativo, um perfil e sem senha'):
            user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Souza', role=self.teacher)
            user = User.objects.get(pk=user.pk)
            self.assertEqual((user.email, user.name), ('maria@ifnmg.edu.br', 'Maria Souza'))
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_superadmin)
            self.assertFalse(user.has_usable_password())
            self.assertEqual(list(user.roles.all()), [self.teacher])
            self.assertEqual(user.role, self.teacher)
        with self.case('normaliza e-mail e nome'):
            user = User.objects.register(email=' Maria@IFNMG.edu.br ', name='  Maria  ', role=self.teacher)
            self.assertEqual(User.objects.get(pk=user.pk).email, 'maria@ifnmg.edu.br')
            self.assertEqual(User.objects.get(pk=user.pk).name, 'Maria')
        with self.case('não aceita superadmin nem senha'):
            with self.assertRaises(TypeError):
                User.objects.register(
                    email='maria@ifnmg.edu.br', name='Maria', role=self.teacher, is_superadmin=True,
                )
            with self.assertRaises(TypeError):
                User.objects.register(
                    email='maria@ifnmg.edu.br', name='Maria', role=self.teacher, password='Senha-forte-123',
                )
            self.assertFalse(User.objects.exists())

    def test_register_with_username_ensures_the_teacher(self):
        with self.case('cria o docente e registra o vínculo'):
            user = User.objects.register(
                email='ana@ifnmg.edu.br', name='Ana', role=self.teacher, username='Ana  Lima',
            )
            self.assertEqual(list(Teacher.objects.values_list('name', flat=True)), ['Ana Lima'])
            log = AuditLog.objects.get(resource=catalog.USER, resource_id=str(user.pk))
            self.assertEqual(log.metadata, {'docente_ligado': 'Ana Lima', 'docente_criado': True})
        with self.case('reaproveita o docente de outra caixa'):
            Teacher.objects.resolve('Ana Lima')
            User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher, username='ana lima')
            self.assertEqual(list(Teacher.objects.values_list('name', flat=True)), ['Ana Lima'])
        with self.case('sem nome de usuário não cria docente'):
            User.objects.register(email='ana@ifnmg.edu.br', name='Ana', role=self.teacher)
            self.assertFalse(Teacher.objects.exists())

    def test_register_refuses_invalid_data_without_creating_anything(self):
        with self.case('dados inválidos'):
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
        with self.case('e-mail em uso'):
            User.objects.register(email='maria@ifnmg.edu.br', name='Maria', role=self.teacher)
            User.objects.filter(email='maria@ifnmg.edu.br').update(is_active=False)
            with self.assertRaises(ValidationError) as raised:
                User.objects.register(email='MARIA@ifnmg.edu.br', name='Outra', role=self.administrator)
            self.assertTrue(raised.exception.messages)
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(UserRole.objects.count(), 1)


class UpdateDetailsTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = requester_role()
        cls.executor = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.teacher)

    def setUp(self):
        self.user = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=self.teacher)
        self.user.set_password('Senha-forte-123')
        self.user.save()

    def test_changes_name_and_email_only(self):
        with self.case('nome e e-mail'):
            password = self.user.password
            self.user.update_details(self.executor, name='Maria Souza', email=' Maria.Souza@IFNMG.edu.br ')
            user = User.objects.get(pk=self.user.pk)
            self.assertEqual((user.name, user.email), ('Maria Souza', 'maria.souza@ifnmg.edu.br'))
            self.assertEqual(user.password, password)
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_superadmin)
            self.assertEqual(user.role, self.teacher)
        with self.case('retira os outros endereços'):
            EmailAddress.objects.create(user=self.user, email='maria@ifnmg.edu.br')
            EmailAddress.objects.create(user=self.user, email='maria.souza@ifnmg.edu.br')
            self.user.update_details(self.executor, name='Maria Souza', email='Maria.Souza@ifnmg.edu.br')
            self.assertEqual(
                list(EmailAddress.objects.filter(user=self.user).values_list('email', flat=True)),
                ['maria.souza@ifnmg.edu.br'],
            )
        with self.case('não sobrescreve a situação'):
            User.objects.filter(pk=self.user.pk).update(is_active=False)
            self.user.update_details(self.executor, name='Maria Souza', email=self.user.email)
            user = User.objects.get(pk=self.user.pk)
            self.assertEqual(user.name, 'Maria Souza')
            self.assertFalse(user.is_active)

    def test_refusals_keep_the_previous_values(self):
        with self.case('mantém os endereços'):
            EmailAddress.objects.create(user=self.user, email='maria@ifnmg.edu.br')
            with self.assertRaises(ValidationError):
                self.user.update_details(self.executor, name='Maria', email='admin@ifnmg.edu.br')
            self.assertTrue(EmailAddress.objects.filter(user=self.user, email='maria@ifnmg.edu.br').exists())
        with self.case('dados inválidos'):
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
        with self.case('e-mail de outro usuário'):
            with self.assertRaises(ValidationError):
                self.user.update_details(self.executor, name='Maria', email='Admin@ifnmg.edu.br')
            self.assertEqual(User.objects.get(pk=self.user.pk).email, 'maria@ifnmg.edu.br')
            self.assertEqual(User.objects.get(pk=self.executor.pk).email, 'admin@ifnmg.edu.br')
