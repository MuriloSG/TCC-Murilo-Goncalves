import json
import re

from django.test import Client, TestCase

from accounts import permissions
from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from ui.pagination import OPTIONS_PAGE_SIZE

OPTIONS_URL = '/auditoria/opcoes/usuarios/'


class UserOptionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        cls.plain = User.objects.register(email='docente@ifnmg.edu.br', name='Docente', role=cls.teacher)
        for number in range(15):
            User.objects.register(
                email=f'pessoa{number:02d}@ifnmg.edu.br',
                name=f'Pessoa {number:02d}' if number % 3 else f'Silva {number:02d}',
                role=cls.teacher,
            )

    def setUp(self):
        self.client.force_login(self.admin)

    def options(self, query=''):
        response = self.client.get(f'{OPTIONS_URL}{query}')
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)

    def test_user_with_permission_is_allowed(self):
        self.teacher.set_permissions([permissions.AUDIT_VIEW])
        client = Client()
        client.force_login(self.plain)
        self.assertEqual(client.get(OPTIONS_URL).status_code, 200)

    def test_label_has_name_and_email(self):
        option = self.options('?busca=admin')['opcoes'][0]
        self.assertEqual(option['valor'], str(self.admin.pk))
        self.assertEqual(option['rotulo'], 'Admin (admin@ifnmg.edu.br)')

    def test_search_covers_the_whole_source(self):
        data = self.options('?busca=silva')
        self.assertEqual(len(data['opcoes']), 5)
        for option in data['opcoes']:
            with self.subTest(option=option):
                self.assertIn('Silva', option['rotulo'])

    def test_search_by_email_ignores_case(self):
        self.assertEqual(len(self.options('?busca=PESSOA01')['opcoes']), 1)


class PaginatedFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.admin = User.objects.register(email='admin@ifnmg.edu.br', name='Admin', role=cls.administrator)
        for number in range(15):
            User.objects.register(
                email=f'pessoa{number:02d}@ifnmg.edu.br', name=f'Pessoa {number:02d}', role=cls.administrator,
            )

    def setUp(self):
        self.client.force_login(self.admin)

    def content(self, query=''):
        return self.client.get(f'/auditoria/{query}').content.decode()

    def user_select(self, query=''):
        content = self.content(query)
        start = content.index('<select name="usuario"')
        return content[start:content.index('</select>', start)]

    def user_options(self, query=''):
        return re.findall(r'<option value="(\d+)"', self.user_select(query))

    def test_page_renders_only_the_first_page_of_options(self):
        self.assertEqual(len(self.user_options()), OPTIONS_PAGE_SIZE)
        field = self.user_select()
        self.assertIn('data-select-source="/auditoria/opcoes/usuarios/"', field)
        self.assertIn('Todos os usuários', field)

    def test_chosen_option_is_rendered_even_outside_the_first_page(self):
        last = User.objects.order_by('name', 'email').last()
        options = self.user_options(f'?usuario={last.pk}')
        self.assertIn(f'<option value="{last.pk}" selected>', self.user_select(f'?usuario={last.pk}'))
        self.assertEqual(len(options), OPTIONS_PAGE_SIZE + 1)

    def test_filter_still_works_with_an_option_outside_the_first_page(self):
        last = User.objects.order_by('name', 'email').last()
        response = self.client.get('/auditoria/', {'usuario': last.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filters'].criteria()['user'], last)
