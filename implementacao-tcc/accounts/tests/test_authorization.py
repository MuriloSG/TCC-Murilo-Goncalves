from django.contrib.auth.context_processors import PermWrapper
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts import permissions
from accounts.models import Permission, Role, RolePermission, User, UserRole
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import MANAGEMENT_PERMISSIONS, management_role, requester_role


def grant(role, *codes):
    for code in codes:
        RolePermission.objects.create(role=role, permission=Permission.objects.get(code=code))


TEACHER_PERMISSIONS = frozenset({permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST})


class AuthorizationTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.coordination = Role.objects.create(code='COORDENACAO', name='Coordenação')

    def create_user(self, email, role, **fields):
        user = User.objects.create(email=email, name=email.partition('@')[0], **fields)
        UserRole.objects.create(user=user, role=role)
        return User.objects.get(pk=user.pk)


class PermissionDecisionTests(AuthorizationTestCase):
    def test_inactive_users_have_no_permission(self):
        with self.case('usuário inativo'):
            with_role = self.create_user('antigo@ifnmg.edu.br', self.administrator, is_active=False)
            without_role = User.objects.create(email='semperfil@ifnmg.edu.br', name='Sem perfil', is_active=False)
            for user in (with_role, without_role):
                with self.subTest(user.email):
                    self.assertEqual(user.effective_permissions(), frozenset())
                    self.assertFalse(user.has_perm(permissions.USER_VIEW))
                    self.assertFalse(user.has_perms([permissions.USER_VIEW]))
                    self.assertFalse(user.has_module_perms('USUARIO'))
        with self.case('superadmin inativo'):
            user = self.create_user(
                'super@ifnmg.edu.br', self.administrator, is_active=False, is_superadmin=True,
            )
            self.assertEqual(user.effective_permissions(), frozenset())
            self.assertFalse(user.has_perm(permissions.USER_VIEW))
            self.assertFalse(user.has_perm(permissions.ROLE_CREATE))
            self.assertFalse(user.has_perm('RESERVA.APROVAR'))
            self.assertFalse(user.has_perms([permissions.USER_VIEW]))
            self.assertFalse(user.has_module_perms('PERFIL'))

    def test_permissions_come_from_the_role(self):
        with self.case('do perfil'):
            grant(self.coordination, permissions.USER_VIEW)
            user = self.create_user('coord@ifnmg.edu.br', self.coordination)
            self.assertEqual(user.effective_permissions(), {permissions.USER_VIEW})
            self.assertTrue(user.has_perm(permissions.USER_VIEW))
            self.assertTrue(user.has_module_perms('USUARIO'))
        with self.case('fora do perfil'):
            grant(self.coordination, permissions.USER_VIEW, permissions.USER_EDIT)
            user = self.create_user('coord@ifnmg.edu.br', self.coordination)
            self.assertFalse(user.has_perm(permissions.USER_CHANGE_STATUS))
            self.assertFalse(user.has_perm('RESERVA.APROVAR'))
            self.assertFalse(user.has_module_perms('PERFIL'))
        with self.case('has_perms exige todas'):
            grant(self.coordination, permissions.USER_VIEW, permissions.USER_EDIT)
            user = self.create_user('coord@ifnmg.edu.br', self.coordination)
            self.assertTrue(user.has_perms([permissions.USER_VIEW, permissions.USER_EDIT]))
            self.assertFalse(user.has_perms([permissions.USER_VIEW, permissions.USER_CREATE]))
        with self.case('módulo pelo recurso inteiro'):
            Permission.objects.create(code='USUARIOS_EXTERNOS.VISUALIZAR', description='Teste')
            grant(self.coordination, 'USUARIOS_EXTERNOS.VISUALIZAR')
            user = self.create_user('coord@ifnmg.edu.br', self.coordination)
            self.assertTrue(user.has_module_perms('USUARIOS_EXTERNOS'))
            self.assertFalse(user.has_module_perms('USUARIO'))

    def test_reserved_permission_written_directly_is_not_granted(self):
        grant(self.coordination, permissions.USER_VIEW, permissions.ROLE_CHANGE_PERMISSIONS)
        user = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.assertEqual(user.effective_permissions(), {permissions.USER_VIEW})
        self.assertFalse(user.has_perm(permissions.ROLE_CHANGE_PERMISSIONS))
        self.assertFalse(user.has_module_perms('PERFIL'))

    def test_effective_permissions_computed_once_per_instance(self):
        user = self.create_user('admin@ifnmg.edu.br', self.administrator)
        with self.assertNumQueries(1):
            user.has_perm(permissions.USER_VIEW)
            user.has_perms([permissions.USER_CREATE, permissions.USER_EDIT])
            user.has_module_perms('USUARIO')
            user.effective_permissions()

    def test_active_superadmin_has_every_permission(self):
        with self.case('qualquer permissão'):
            user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            for code in permissions.ALL_PERMISSIONS:
                with self.subTest(code=code):
                    self.assertTrue(user.has_perm(code))
            self.assertTrue(user.has_perms(list(permissions.ALL_PERMISSIONS)))
            self.assertTrue(user.has_module_perms('USUARIO'))
            self.assertTrue(user.has_module_perms('PERFIL'))
        with self.case('fora do catálogo'):
            user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            with self.assertNumQueries(0):
                self.assertTrue(user.has_perm('RESERVA.APROVAR'))
                self.assertTrue(user.has_perms(['RESERVA.APROVAR', 'ESPACO.CRIAR']))
                self.assertTrue(user.has_module_perms('RESERVA'))
        with self.case('permissões efetivas'):
            user = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            catalog = set(Permission.objects.values_list('code', flat=True))
            self.assertEqual(user.effective_permissions(), catalog)
            self.assertTrue(permissions.SUPERADMIN_RESERVED_PERMISSIONS <= user.effective_permissions())

    def test_perm_wrapper_uses_has_perm_and_has_module_perms(self):
        grant(self.coordination, permissions.USER_VIEW)
        perms = PermWrapper(self.create_user('coord@ifnmg.edu.br', self.coordination))
        self.assertTrue(perms['USUARIO'])
        self.assertTrue(perms['USUARIO']['VISUALIZAR'])
        self.assertFalse(perms['USUARIO']['CRIAR'])
        self.assertFalse(perms['PERFIL'])


class AuthorityTests(AuthorizationTestCase):
    """Quem gere usuários só atribui ou altera o que já cobre com as próprias permissões."""

    def create_user(self, email, role, **fields):
        user = super().create_user(email, role, **fields)
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user

    def setUp(self):
        grant(
            self.coordination, permissions.USER_VIEW, permissions.USER_CREATE, permissions.USER_EDIT,
            permissions.USER_CHANGE_ROLE, permissions.USER_CHANGE_STATUS,
        )
        self.coordinator = self.create_user('coord@ifnmg.edu.br', self.coordination)
        self.colleague = self.create_user('admin@ifnmg.edu.br', self.administrator)
        self.teacher_user = self.create_user('docente@ifnmg.edu.br', self.teacher)

    def assertRefused(self, operation):
        with self.assertRaises(ValidationError) as caught:
            operation()
        error = caught.exception
        items = [item for group in error.error_dict.values() for item in group] if hasattr(error, 'error_dict') else error.error_list
        self.assertEqual([item.code for item in items], ['insufficient_authority'])

    def test_refusals_outside_the_authority(self):
        with self.case('perfil fora do alcance'):
            self.assertRefused(lambda: User.objects.register(
                email='novo@ifnmg.edu.br', name='Novo', role=self.administrator, executor=self.coordinator,
            ))
            self.assertRefused(lambda: self.teacher_user.change_role(self.administrator, executor=self.coordinator))
            self.assertRefused(lambda: self.coordinator.change_role(self.administrator, executor=self.coordinator))
            self.assertFalse(User.objects.filter(email='novo@ifnmg.edu.br').exists())
            self.assertEqual(User.objects.get(pk=self.coordinator.pk).role, self.coordination)
        with self.case('conta fora do alcance'):
            for operation in (
                lambda: self.colleague.update_details(self.coordinator, name='Admin', email='novo@ifnmg.edu.br'),
                lambda: self.colleague.update_details(self.coordinator, name='Admin', email=self.colleague.email, username='Fulano'),
                lambda: self.colleague.change_role(self.teacher, executor=self.coordinator),
                lambda: self.colleague.deactivate(executor=self.coordinator),
            ):
                with self.subTest(operation=operation):
                    self.assertRefused(operation)
            colleague = User.objects.get(pk=self.colleague.pk)
            self.assertEqual((colleague.email, colleague.username, colleague.is_active), ('admin@ifnmg.edu.br', None, True))
        with self.case('conta inativa'):
            self.colleague.deactivate()
            self.assertRefused(lambda: User.objects.get(pk=self.colleague.pk).reactivate(executor=self.coordinator))
        with self.case('o próprio nome de usuário'):
            self.assertRefused(lambda: self.coordinator.update_details(
                self.coordinator, name='coord', email=self.coordinator.email, username='Docente Qualquer',
            ))
            superadmin = self.create_user('super@ifnmg.edu.br', self.teacher, is_superadmin=True)
            superadmin.update_details(superadmin, name='super', email=superadmin.email, username='Super')
            self.assertEqual(User.objects.get(pk=superadmin.pk).username, 'Super')

    def test_allowed_inside_the_authority(self):
        with self.case('perfil e conta no alcance'):
            grant(self.coordination, *TEACHER_PERMISSIONS)
            coordinator = User.objects.get(pk=self.coordinator.pk)
            created = User.objects.register(
                email='novo@ifnmg.edu.br', name='Novo', role=self.teacher, executor=coordinator,
            )
            created.update_details(coordinator, name='Novo', email='outro@ifnmg.edu.br', username='Novo Docente')
            created.deactivate(executor=coordinator)
            created.reactivate(executor=coordinator)
            self.assertEqual(User.objects.get(pk=created.pk).username, 'Novo Docente')
        with self.case('nome de conta fora do alcance'):
            self.colleague.update_details(self.coordinator, name='Admin Novo', email=self.colleague.email)
            self.assertEqual(User.objects.get(pk=self.colleague.pk).name, 'Admin Novo')

    def test_screens_offer_and_accept_only_covered_roles(self):
        with self.case('formulários'):
            from accounts.forms import UserCreateForm

            offered = set(UserCreateForm(executor=self.coordinator).fields['role'].queryset)
            self.assertNotIn(self.administrator, offered)
            self.assertNotIn(self.teacher, offered)
            self.assertIn(self.coordination, offered)
        with self.case('POST forjado'):
            self.client.force_login(self.coordinator)
            response = self.client.post(
                f'/usuarios/{self.teacher_user.pk}/perfil/', {'role': self.administrator.pk},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors['role'])
            self.assertEqual(User.objects.get(pk=self.teacher_user.pk).role, self.teacher)

    def test_username_change_that_moves_a_teacher_link_is_highlighted_in_the_audit(self):
        from audit import catalog
        from audit.models import AuditLog
        from schedule.models import Teacher

        Teacher.objects.create(name='Ana Lima')
        Teacher.objects.create(name='Bruno Reis')
        grant(self.coordination, *TEACHER_PERMISSIONS)
        coordinator = User.objects.get(pk=self.coordinator.pk)
        teacher_user = User.objects.get(pk=self.teacher_user.pk)
        teacher_user.update_details(coordinator, name='docente', email=teacher_user.email, username='ana lima')
        teacher_user.update_details(coordinator, name='docente', email=teacher_user.email, username='Bruno Reis')
        teacher_user.update_details(coordinator, name='docente', email=teacher_user.email, username='Sem Docente')
        entries = AuditLog.objects.filter(resource=catalog.USER, resource_id=str(teacher_user.pk), action=catalog.UPDATE)
        self.assertEqual(
            [entry.metadata for entry in entries.order_by('pk')],
            [
                {'docente_ligado': 'Ana Lima'},
                {'docente_desligado': 'Ana Lima', 'docente_ligado': 'Bruno Reis'},
                {'docente_desligado': 'Bruno Reis'},
            ],
        )
