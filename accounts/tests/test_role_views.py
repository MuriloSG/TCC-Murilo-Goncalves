from django.test import Client, TestCase

from accounts import permissions
from accounts.models import Permission, Role, User
from ui.pagination import PAGE_SIZE

ROUTES = {
    'list': '/perfis/',
    'create': '/perfis/novo/',
    'detail': '/perfis/{pk}/',
    'update': '/perfis/{pk}/editar/',
    'permissions': '/perfis/{pk}/permissoes/',
    'delete': '/perfis/{pk}/excluir/',
}


class RoleViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = Role.objects.get(code='ADMINISTRADOR')
        cls.teacher = Role.objects.get(code='DOCENTE')
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


class AccessTests(RoleViewsTestCase):
    def test_anonymous_is_redirected_to_login_with_next(self):
        client = Client()
        for route in ROUTES:
            with self.subTest(route):
                url = self.url(route)
                for method in (client.get, client.post):
                    response = method(url)
                    self.assertRedirects(response, f'/contas/login/?next={url}', fetch_redirect_response=False)
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())

    def test_user_with_all_user_permissions_gets_403(self):
        client = Client()
        client.force_login(self.admin)
        for route in ROUTES:
            with self.subTest(route):
                self.assertEqual(client.get(self.url(route)).status_code, 403)
                self.assertEqual(client.post(self.url(route), {'code': 'NOVO', 'name': 'Novo'}).status_code, 403)
        self.assertFalse(Role.objects.filter(code='NOVO').exists())
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())

    def test_denial_comes_before_the_business_rules(self):
        client = Client()
        client.force_login(self.admin)
        response = client.post(self.url('delete', self.teacher))
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'Perfis do sistema', status_code=403)

    def test_regular_user_cannot_grant_permissions(self):
        client = Client()
        client.force_login(self.admin)
        response = client.post(self.url('permissions', self.teacher), {'permissions': [permissions.USER_CREATE]})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.codes(self.teacher), set())

    def test_active_superadmin_with_teacher_role_has_access(self):
        for route in ROUTES:
            with self.subTest(route):
                self.assertEqual(self.client.get(self.url(route)).status_code, 200)

    def test_inactive_superadmin_changes_nothing(self):
        User.objects.filter(pk=self.superadmin.pk).update(is_active=False)
        response = self.client.post(self.url('delete'))
        self.assertRedirects(response, f'/contas/login/?next={self.url("delete")}', fetch_redirect_response=False)
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())

    def test_home_shows_the_roles_shortcut_only_to_the_superadmin(self):
        self.assertContains(self.client.get('/inicio/'), 'href="/perfis/"')
        client = Client()
        client.force_login(self.admin)
        self.assertNotContains(client.get('/inicio/'), 'href="/perfis/"')

    def test_post_without_csrf_is_refused(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.superadmin)
        cases = [
            (self.url('create'), {'code': 'SECRETARIA', 'name': 'Secretaria'}),
            (self.url('permissions'), {'permissions': [permissions.USER_CREATE]}),
            (self.url('delete'), {}),
        ]
        for url, data in cases:
            with self.subTest(url):
                self.assertEqual(client.post(url, data).status_code, 403)
        self.assertFalse(Role.objects.filter(code='SECRETARIA').exists())
        self.assertEqual(self.codes(self.coordination), {permissions.USER_VIEW})


class ListAndDetailTests(RoleViewsTestCase):
    def test_list_shows_all_roles_with_type_and_linked_users(self):
        User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
        inactive = User.objects.register(email='b@ifnmg.edu.br', name='B', role=self.coordination)
        User.objects.filter(pk=inactive.pk).update(is_active=False)
        response = self.client.get('/perfis/')
        roles = {role.code: role for role in response.context['roles']}
        self.assertEqual(set(roles), {'ADMINISTRADOR', 'DOCENTE', 'COORDENACAO'})
        self.assertTrue(roles['ADMINISTRADOR'].is_system)
        self.assertTrue(roles['DOCENTE'].is_system)
        self.assertFalse(roles['COORDENACAO'].is_system)
        self.assertEqual(roles['COORDENACAO'].user_count, 2)

    def test_detail_shows_exactly_the_granted_permissions_by_resource(self):
        self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT])
        response = self.client.get(self.url('detail'))
        self.assertEqual(
            [permission.code for permission in response.context['permissions']],
            [permissions.USER_EDIT, permissions.USER_VIEW],
        )
        self.assertContains(response, '<span class="perm-group-name">Usuários</span>', html=True)
        self.assertNotContains(response, 'USUARIO.CRIAR')

    def test_there_is_no_route_to_manage_the_catalog(self):
        for url in ['/permissoes/', '/perfis/permissoes/', '/permissoes/novo/']:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 404)


class CreateTests(RoleViewsTestCase):
    def post(self, **data):
        return self.client.post('/perfis/novo/', {'code': 'SECRETARIA', 'name': 'Secretaria'} | data)

    def test_form_offers_only_grantable_permissions_and_no_system_flag(self):
        response = self.client.get('/perfis/novo/')
        self.assertEqual(set(response.context['form'].fields), {'code', 'name', 'description', 'permissions'})
        self.assertNotContains(response, 'type="checkbox"')
        self.assertNotContains(response, 'is_system')
        self.post()
        response = self.client.get(f'/perfis/{Role.objects.get(code="SECRETARIA").pk}/permissoes/?etapa=2')
        for code in permissions.ADMINISTRATIVE_CAPABILITY:
            self.assertContains(response, f'value="{code}"')
        for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
            self.assertNotContains(response, f'value="{code}"')
        self.assertNotContains(response, 'is_system')

    def test_creates_custom_role_without_permissions(self):
        response = self.post(is_system='on')
        role = Role.objects.get(code='SECRETARIA')
        self.assertRedirects(response, f'/perfis/{role.pk}/permissoes/?etapa=2')
        self.assertFalse(role.is_system)
        self.assertEqual(self.codes(role), set())

    def test_creates_role_with_chosen_permissions(self):
        self.post(permissions=[permissions.USER_VIEW, permissions.USER_EDIT])
        role = Role.objects.get(code='SECRETARIA')
        self.assertEqual(self.codes(role), {permissions.USER_VIEW, permissions.USER_EDIT})

    def test_refuses_invalid_data(self):
        cases = {
            'missing code': ('code', {'code': ''}),
            'lowercase code': ('code', {'code': 'secretaria'}),
            'code with digits': ('code', {'code': 'COORD-1'}),
            'repeated code': ('code', {'code': 'COORDENACAO'}),
            'missing name': ('name', {'name': ''}),
        }
        for case, (field, data) in cases.items():
            with self.subTest(case):
                response = self.post(**data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
        self.assertEqual(Role.objects.count(), 3)

    def test_refuses_name_that_differs_only_in_case(self):
        response = self.post(code='COORDENACAO_GERAL', name='COORDENAÇÃO')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Já existe um perfil com este nome')
        self.assertFalse(Role.objects.filter(code='COORDENACAO_GERAL').exists())

    def test_reserved_permission_is_refused_with_the_reason(self):
        response = self.post(permissions=[permissions.USER_VIEW, permissions.ROLE_CHANGE_PERMISSIONS])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Permissões reservadas ao superadmin não podem ser concedidas')
        self.assertFalse(Role.objects.filter(code='SECRETARIA').exists())

    def test_unknown_permission_is_refused(self):
        response = self.post(permissions=['RESERVA.APROVAR'])
        self.assertIn('permissions', response.context['form'].errors)
        self.assertFalse(Role.objects.filter(code='SECRETARIA').exists())
        self.assertFalse(Permission.objects.filter(code='RESERVA.APROVAR').exists())


class UpdateTests(RoleViewsTestCase):
    def test_code_is_shown_but_not_editable(self):
        response = self.client.get(self.url('update'))
        self.assertEqual(set(response.context['form'].fields), {'name', 'description'})
        self.assertContains(response, 'COORDENACAO')

    def test_changes_name_and_description_only(self):
        response = self.client.post(
            self.url('update'),
            {'name': 'Coordenação de Curso', 'description': 'Coordena o curso.', 'code': 'SECRETARIA', 'is_system': 'on'},
        )
        self.assertRedirects(response, self.url('detail'))
        role = Role.objects.get(pk=self.coordination.pk)
        self.assertEqual((role.code, role.name, role.description), ('COORDENACAO', 'Coordenação de Curso', 'Coordena o curso.'))
        self.assertFalse(role.is_system)
        self.assertEqual(self.codes(role), {permissions.USER_VIEW})

    def test_system_role_keeps_its_code(self):
        self.client.post(self.url('update', self.administrator), {'name': 'Administração', 'description': ''})
        role = Role.objects.get(pk=self.administrator.pk)
        self.assertEqual((role.code, role.name), ('ADMINISTRADOR', 'Administração'))

    def test_refuses_empty_name_and_name_of_another_role(self):
        for name in ['', 'docente']:
            with self.subTest(name):
                response = self.client.post(self.url('update'), {'name': name, 'description': ''})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(Role.objects.get(pk=self.coordination.pk).name, 'Coordenação')
        self.assertEqual(Role.objects.get(pk=self.teacher.pk).name, 'Docente')


class PermissionsTests(RoleViewsTestCase):
    def post(self, role=None, codes=()):
        return self.client.post(self.url('permissions', role), {'permissions': list(codes)})

    def test_form_offers_only_grantable_permissions_and_shows_linked_users(self):
        User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
        response = self.client.get(self.url('permissions'))
        self.assertEqual(set(response.context['form'].fields), {'permissions'})
        for code in permissions.SUPERADMIN_RESERVED_PERMISSIONS:
            self.assertNotContains(response, f'value="{code}"')
        self.assertContains(response, f'value="{permissions.USER_CREATE}"')
        self.assertContains(response, '1 usuário vinculado')

    def test_grants_and_revokes_in_the_same_request(self):
        self.coordination.set_permissions([permissions.USER_VIEW, permissions.USER_EDIT])
        response = self.post(codes=[permissions.USER_VIEW, permissions.USER_CREATE])
        self.assertRedirects(response, self.url('detail'))
        self.assertEqual(self.codes(self.coordination), {permissions.USER_VIEW, permissions.USER_CREATE})

    def test_system_role_can_receive_permissions(self):
        self.post(self.teacher, [permissions.USER_VIEW])
        self.assertEqual(self.codes(self.teacher), {permissions.USER_VIEW})
        self.assertTrue(Role.objects.get(pk=self.teacher.pk).is_system)

    def test_accepts_the_empty_set(self):
        self.post(codes=[])
        self.assertEqual(self.codes(self.coordination), set())

    def test_reserved_permission_is_refused_with_the_reason(self):
        for role in (self.coordination, self.administrator):
            with self.subTest(role.code):
                before = self.codes(role)
                response = self.post(role, [permissions.USER_CREATE, permissions.ROLE_DELETE])
                self.assertContains(response, 'Permissões reservadas ao superadmin não podem ser concedidas')
                self.assertEqual(self.codes(role), before)

    def test_unknown_permission_is_refused(self):
        response = self.post(codes=['RESERVA.APROVAR'])
        self.assertIn('permissions', response.context['form'].errors)
        self.assertEqual(self.codes(self.coordination), {permissions.USER_VIEW})

    def test_superadmin_removes_a_capability_permission_from_administrator(self):
        remaining = permissions.ADMINISTRATIVE_CAPABILITY - {permissions.USER_EDIT}
        self.assertRedirects(self.post(self.administrator, remaining), self.url('detail', self.administrator))
        self.assertFalse(User.objects.get(pk=self.admin.pk).has_administrative_capability())

    def test_change_applies_on_the_next_request_of_linked_users(self):
        member = User.objects.register(email='membro@ifnmg.edu.br', name='Membro', role=self.coordination)
        client = Client()
        client.force_login(member)
        self.assertEqual(client.get('/usuarios/').status_code, 200)
        self.post(codes=[])
        self.assertEqual(client.get('/usuarios/').status_code, 403)
        self.post(codes=[permissions.USER_VIEW])
        self.assertEqual(client.get('/usuarios/').status_code, 200)


class DeleteTests(RoleViewsTestCase):
    def test_get_only_asks_for_confirmation(self):
        response = self.client.get(self.url('delete'))
        self.assertContains(response, 'O perfil COORDENACAO é excluído')
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())

    def test_deletes_custom_role_without_users_keeping_the_catalog(self):
        response = self.client.post(self.url('delete'))
        self.assertRedirects(response, '/perfis/')
        self.assertFalse(Role.objects.filter(pk=self.coordination.pk).exists())
        self.assertTrue(Permission.objects.filter(code=permissions.USER_VIEW).exists())

    def test_system_role_is_protected(self):
        response = self.client.post(self.url('delete', self.teacher), follow=True)
        self.assertRedirects(response, self.url('detail', self.teacher))
        self.assertContains(response, 'Perfis do sistema não podem ser excluídos')
        self.assertTrue(Role.objects.filter(pk=self.teacher.pk).exists())

    def test_role_in_use_reports_how_many_users_are_linked(self):
        inactive = User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
        User.objects.filter(pk=inactive.pk).update(is_active=False)
        response = self.client.post(self.url('delete'), follow=True)
        self.assertContains(response, '1 usuário vinculado')
        self.assertTrue(Role.objects.filter(pk=self.coordination.pk).exists())
        self.assertEqual(User.objects.get(pk=inactive.pk).role, self.coordination)

    def test_deletes_after_changing_the_role_of_its_users(self):
        member = User.objects.register(email='a@ifnmg.edu.br', name='A', role=self.coordination)
        member.change_role(self.teacher)
        self.assertRedirects(self.client.post(self.url('delete')), '/perfis/')
        self.assertFalse(Role.objects.filter(pk=self.coordination.pk).exists())
        self.assertEqual(list(User.objects.get(pk=member.pk).roles.all()), [self.teacher])

    def test_system_role_has_no_delete_link(self):
        self.assertNotContains(self.client.get(self.url('detail', self.teacher)), '/excluir/')
        self.assertContains(self.client.get(self.url('detail')), '/excluir/')


class RoleListPaginationTests(TestCase):
    def test_roles_are_paginated(self):
        total = PAGE_SIZE * 2 + 1
        for index in range(total - Role.objects.count()):
            code = f'PERFIL_{chr(65 + index // 26)}{chr(65 + index % 26)}'
            Role.objects.create_role(code=code, name=f'Perfil {index:02d}')
        superadmin = User.objects.create_superadmin(email='super@ifnmg.edu.br', name='Super', password='Senha-forte-123')
        self.client.force_login(superadmin)
        response = self.client.get('/perfis/')
        self.assertContains(
            response, f'Exibindo <strong>1</strong> a <strong>{PAGE_SIZE}</strong> de <strong>{total}</strong> perfis',
        )
        self.assertContains(response, 'Página 1 de 3')
        response = self.client.get('/perfis/', {'pagina': '3'})
        self.assertContains(
            response, f'Exibindo <strong>{total}</strong> a <strong>{total}</strong> de <strong>{total}</strong> perfis',
        )
