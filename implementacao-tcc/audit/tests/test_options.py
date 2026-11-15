import json
import re

from config.testing import IsolatedCasesMixin
from django.test import Client, TestCase

from accounts import permissions
from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from ui.pagination import OPTIONS_PAGE_SIZE

OPTIONS_URL = '/auditoria/opcoes/usuarios/'


class PaginatedFieldTests(IsolatedCasesMixin, TestCase):
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

    def test_chosen_option_outside_the_first_page(self):
        with self.case('opção escolhida'):
            last = User.objects.order_by('name', 'email').last()
            options = self.user_options(f'?usuario={last.pk}')
            self.assertIn(f'<option value="{last.pk}" selected>', self.user_select(f'?usuario={last.pk}'))
            self.assertEqual(len(options), OPTIONS_PAGE_SIZE + 1)
        with self.case('filtro'):
            last = User.objects.order_by('name', 'email').last()
            response = self.client.get('/auditoria/', {'usuario': last.pk})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['filters'].criteria()['user'], last)
