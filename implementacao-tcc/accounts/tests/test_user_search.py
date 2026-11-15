import re

from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User
from config.testing import IsolatedCasesMixin
from accounts.tests.roles import requester_role
from ui.pagination import PAGE_SIZE

HTMX = {'HX-Request': 'true'}


class SearchTestCase(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        teacher = requester_role()
        cls.admin_role = Role.objects.create_role(
            code='SECRETARIA', name='Secretaria',
            permissions=sorted(permissions.ADMINISTRATIVE_CAPABILITY),
        )
        cls.ana = User.objects.register(email='ana.souza@ifnmg.edu.br', name='Ana Souza', role=cls.admin_role)
        cls.bruno = User.objects.register(email='bruno.lima@ifnmg.edu.br', name='Bruno Lima', role=teacher)
        cls.carla = User.objects.register(email='carla.mendes@ifnmg.edu.br', name='Carla Mendes', role=teacher)
        cls.carla.deactivate()

    def names(self, queryset):
        return list(queryset.order_by('name').values_list('name', flat=True))


class ManagerSearchTests(SearchTestCase):
    def test_search_by_part_of_name_email_or_username(self):
        with self.case('nome'):
            self.assertEqual(self.names(User.objects.search('sou')), ['Ana Souza'])
        with self.case('e-mail'):
            self.assertEqual(self.names(User.objects.search('bruno.lima')), ['Bruno Lima'])
        with self.case('nome de usuário'):
            aldo = User.objects.register(
                email='aldo@ifnmg.edu.br', name='Aldo Gomes da Silva',
                role=self.admin_role, username='Aldo Gomes',
            )
            self.assertEqual(self.names(User.objects.search('aldo gomes')), [aldo.name])
            self.assertEqual(self.names(User.objects.search('ALDO GOMES')), [aldo.name])
        with self.case('ignora maiúsculas'):
            self.assertEqual(self.names(User.objects.search('CARLA')), ['Carla Mendes'])
            self.assertEqual(self.names(User.objects.search('IFNMG.EDU')), ['Ana Souza', 'Bruno Lima', 'Carla Mendes'])

    def test_status_combination_and_empty_term(self):
        with self.case('nome de usuário e situação'):
            User.objects.register(
                email='aldo@ifnmg.edu.br', name='Aldo Gomes da Silva',
                role=self.admin_role, username='Aldo Gomes',
            ).deactivate()
            self.assertEqual(self.names(User.objects.search('aldo gomes', 'ativos')), [])
            self.assertEqual(self.names(User.objects.search('aldo gomes', 'inativos')), ['Aldo Gomes da Silva'])
        with self.case('situação'):
            self.assertEqual(self.names(User.objects.search('', 'ativos')), ['Ana Souza', 'Bruno Lima'])
            self.assertEqual(self.names(User.objects.search('', 'inativos')), ['Carla Mendes'])
            self.assertEqual(len(User.objects.search('', 'todos')), 3)
            self.assertEqual(len(User.objects.search('', 'qualquer')), 3)
        with self.case('combinação'):
            User.objects.register(email='ana.clara@ifnmg.edu.br', name='Ana Clara', role=self.admin_role).deactivate()
            self.assertEqual(self.names(User.objects.search('ana', 'ativos')), ['Ana Souza'])
            self.assertEqual(self.names(User.objects.search('ana', 'inativos')), ['Ana Clara'])
        with self.case('termo vazio'):
            self.assertEqual(len(User.objects.search('')), 3)
            self.assertEqual(len(User.objects.search()), 3)


class ListSearchViewTests(SearchTestCase):
    def setUp(self):
        self.client.force_login(self.ana)

    def listed(self, response):
        return re.findall(r'<span class="person-name">([^<(]+?)(?: \(superadmin\))?</span>', response.content.decode())

    def test_list_search(self):
        with self.case('por trecho do nome'):
            response = self.client.get('/usuarios/', {'busca': 'SOU'})
            self.assertEqual(self.listed(response), ['ana.souza@ifnmg.edu.br'])
            self.assertContains(response, 'Todos os usuários <span class="count">3</span>')
            self.assertContains(response, 'Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário</p>')
        with self.case('sem resultado'):
            response = self.client.get('/usuarios/', {'busca': 'zzz'})
            self.assertEqual(self.listed(response), [])
            self.assertContains(response, 'Nenhum usuário encontrado para a busca.')
            self.assertContains(response, 'Limpar busca')
            self.assertNotContains(response, 'Exibindo')
        with self.case('sem busca'):
            response = self.client.get('/usuarios/', {'busca': ''})
            self.assertNotContains(response, 'Limpar busca')
        with self.case('formulário com o estado atual'):
            response = self.client.get('/usuarios/', {'busca': 'ana', 'situacao': 'inativos'})
            self.assertRegex(response.content.decode(), r'<input type="search" name="busca" value="ana"')
            self.assertContains(response, '<option value="inativos" selected>Inativos</option>')

    def test_htmx_answers_the_table_only_for_its_target(self):
        with self.case('alvo da tabela'):
            response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'tabela-usuarios'})
            content = response.content.decode()
            self.assertTrue(content.startswith('<table class="data-table compact-rows">'), content[:80])
            self.assertNotIn('<html', content)
            self.assertNotIn('role="search"', content)
            self.assertEqual(self.listed(response), ['ana.souza@ifnmg.edu.br'])
            self.assertIn('Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário', content)
        with self.case('outro alvo'):
            response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'outro'})
            self.assertContains(response, '<html')
