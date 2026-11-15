from django.test import Client, TestCase

from accounts import permissions
from accounts.models import Permission, Role, User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import management_role, requester_role

ROUTES = {
    'list': '/perfis/',
    'create': '/perfis/novo/',
    'detail': '/perfis/{pk}/',
    'update': '/perfis/{pk}/editar/',
    'permissions': '/perfis/{pk}/permissoes/',
    'delete': '/perfis/{pk}/excluir/',
}


class RoleViewsTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.coordination = Role.objects.create_role(
            code='COORDENACAO', name='Coordenação', permissions=[permissions.USER_VIEW],
        )
        cls.superadmin = User.objects.register(email='super@ifnmg.edu.br', name='Super', role=cls.teacher)
        cls.superadmin.set_superadmin(True)
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)

    def setUp(self):
        self.client.force_login(self.superadmin)

    def url(self, route, role=None):
        return ROUTES[route].format(pk=(role or self.coordination).pk)

    def codes(self, role):
        return set(Role.objects.get(pk=role.pk).permissions.values_list('code', flat=True))


class ListAndDetailTests(RoleViewsTestCase):
    def test_list_and_detail_show_the_roles_and_their_permissions(self):
        with self.case('lista'):
            User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
            inactive = User.objects.register(email='b@ifnmg.edu.br', name='B', role=self.coordination)
            User.objects.filter(pk=inactive.pk).update(is_active=False)
            response = self.client.get('/perfis/')
            roles = {role.code: role for role in response.context['roles']}
            self.assertEqual(set(roles), {'ADMINISTRADOR', 'DOCENTE', 'GESTAO', 'SOLICITACAO', 'COORDENACAO'})
            self.assertEqual(roles['COORDENACAO'].user_count, 2)
        with self.case('detalhe'):
            self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT])
            response = self.client.get(self.url('detail'))
            self.assertEqual(
                [permission.code for permission in response.context['permissions']],
                [permissions.USER_EDIT, permissions.USER_VIEW],
            )
            self.assertContains(response, '<span class="perm-group-name">Usuários</span>', html=True)
            self.assertNotContains(response, 'USUARIO.CRIAR')


class CreateTests(RoleViewsTestCase):
    def post(self, **data):
        return self.client.post('/perfis/novo/', {'code': 'SECRETARIA', 'name': 'Secretaria'} | data)

    def test_creates_role_from_the_grantable_permissions(self):
        with self.case('formulário só com as concedíveis'):
            response = self.client.get('/perfis/novo/')
            self.assertEqual(set(response.context['form'].fields), {'code', 'name', 'description', 'permissions'})
            self.assertNotContains(response, 'type="checkbox"')
            self.post()
            response = self.client.get(f'/perfis/{Role.objects.get(code="SECRETARIA").pk}/permissoes/?etapa=2')
            for code in permissions.ADMINISTRATIVE_CAPABILITY:
                self.assertContains(response, f'value="{code}"')
            for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
                self.assertNotContains(response, f'value="{code}"')
        with self.case('sem permissões'):
            response = self.post()
            role = Role.objects.get(code='SECRETARIA')
            self.assertRedirects(response, f'/perfis/{role.pk}/permissoes/?etapa=2')
            self.assertEqual(self.codes(role), set())
        with self.case('com as escolhidas'):
            self.post(permissions=[permissions.USER_VIEW, permissions.USER_EDIT])
            role = Role.objects.get(code='SECRETARIA')
            self.assertEqual(self.codes(role), {permissions.USER_VIEW, permissions.USER_EDIT})

    def test_refusals_appear_on_the_form(self):
        with self.case('dados inválidos'):
            cases = {
                'missing code': ('code', {'code': ''}),
                'lowercase code': ('code', {'code': 'secretaria'}),
                'code with digits': ('code', {'code': 'COORD-1'}),
                'repeated code': ('code', {'code': 'COORDENACAO'}),
                'missing name': ('name', {'name': ''}),
            }
            count = Role.objects.count()
            for case, (field, data) in cases.items():
                with self.subTest(case):
                    response = self.post(**data)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(field, response.context['form'].errors)
            self.assertEqual(Role.objects.count(), count)
        with self.case('permissão reservada'):
            response = self.post(permissions=[permissions.USER_VIEW, permissions.ROLE_CHANGE_PERMISSIONS])
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Permissões reservadas ao superadmin não podem ser concedidas')
            self.assertFalse(Role.objects.filter(code='SECRETARIA').exists())


class UpdateTests(RoleViewsTestCase):
    def test_changes_name_and_description_only(self):
        with self.case('código visível e não editável'):
            response = self.client.get(self.url('update'))
            self.assertEqual(set(response.context['form'].fields), {'name', 'description'})
        with self.case('nome e descrição'):
            response = self.client.post(
                self.url('update'),
                {'name': 'Coordenação de Curso', 'description': 'Coordena o curso.', 'code': 'SECRETARIA'},
            )
            self.assertRedirects(response, self.url('detail'))
            role = Role.objects.get(pk=self.coordination.pk)
            self.assertEqual((role.code, role.name, role.description), ('COORDENACAO', 'Coordenação de Curso', 'Coordena o curso.'))
            self.assertEqual(self.codes(role), {permissions.USER_VIEW})
        with self.case('nome vazio ou de outro perfil'):
            for name in ['', 'solicitação']:
                with self.subTest(name):
                    response = self.client.post(self.url('update'), {'name': name, 'description': ''})
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.context['form'].errors)
            self.assertEqual(Role.objects.get(pk=self.coordination.pk).name, 'Coordenação')
            self.assertEqual(Role.objects.get(pk=self.teacher.pk).name, 'Solicitação')


class PermissionsTests(RoleViewsTestCase):
    def post(self, role=None, codes=()):
        return self.client.post(self.url('permissions', role), {'permissions': list(codes)})

    def test_permissions_screen_grants_and_revokes(self):
        with self.case('formulário'):
            User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
            response = self.client.get(self.url('permissions'))
            self.assertEqual(set(response.context['form'].fields), {'permissions'})
            for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
                self.assertNotContains(response, f'value="{code}"')
            self.assertContains(response, f'value="{permissions.USER_CREATE}"')
        with self.case('concede e revoga'):
            self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT])
            response = self.post(codes=[permissions.USER_VIEW, permissions.USER_CREATE])
            self.assertRedirects(response, self.url('detail'))
            self.assertEqual(self.codes(self.coordination), {permissions.USER_VIEW, permissions.USER_CREATE})
        with self.case('superadmin retira permissão de capacidade'):
            remaining = permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_EDIT}
            self.assertRedirects(self.post(self.administrator, remaining), self.url('detail', self.administrator))
            self.assertFalse(User.objects.get(pk=self.admin.pk).has_administrative_capability())
        with self.case('vale na próxima requisição'):
            member = User.objects.register(email='membro@ifnmg.edu.br', name='Membro', role=self.coordination)
            client = Client()
            client.force_login(member)
            self.assertEqual(client.get('/usuarios/').status_code, 200)
            self.post(codes=[])
            self.assertEqual(client.get('/usuarios/').status_code, 403)
            self.post(codes=[permissions.USER_VIEW])
            self.assertEqual(client.get('/usuarios/').status_code, 200)

    def test_reserved_permission_is_refused_with_the_reason(self):
        for role in (self.coordination, self.administrator):
            with self.subTest(role.code):
                before = self.codes(role)
                response = self.post(role, [permissions.USER_CREATE, permissions.ROLE_DELETE])
                self.assertContains(response, 'Permissões reservadas ao superadmin não podem ser concedidas')
                self.assertEqual(self.codes(role), before)


class DeleteTests(RoleViewsTestCase):
    def test_delete_confirms_and_removes_only_unused_roles(self):
        with self.case('GET só pede confirmação'):
            response = self.client.get(self.url('delete'))
            self.assertContains(response, 'O perfil COORDENACAO é excluído')
            self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())
        with self.case('perfil próprio sem usuários'):
            response = self.client.post(self.url('delete'))
            self.assertRedirects(response, '/perfis/')
            self.assertFalse(Role.objects.filter(pk=self.coordination.pk).exists())
            self.assertTrue(Permission.objects.filter(code=permissions.USER_VIEW).exists())
        with self.case('perfil inicial sem usuários'):
            teacher = Role.objects.get(code='DOCENTE')
            response = self.client.post(self.url('delete', teacher))
            self.assertRedirects(response, '/perfis/')
            self.assertFalse(Role.objects.filter(pk=teacher.pk).exists())
        with self.case('perfil em uso'):
            inactive = User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
            User.objects.filter(pk=inactive.pk).update(is_active=False)
            response = self.client.post(self.url('delete'), follow=True)
            self.assertContains(response, '1 usuário vinculado')
            self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())
            self.assertEqual(User.objects.get(pk=inactive.pk).role, self.coordination)
