import json

from django.test import TestCase
from config.testing import IsolatedCasesMixin

from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from ui.pagination import OPTIONS_PAGE_SIZE

OPTIONS_URL = '/notificacoes/opcoes/usuarios/'


class UserOptionsTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator = management_role()
        cls.teacher = requester_role()
        cls.admin = User.objects.register('admin@ifnmg.edu.br', 'Admin', cls.administrator)
        cls.plain = User.objects.register('docente@ifnmg.edu.br', 'Docente', cls.teacher)
        for number in range(15):
            User.objects.register(
                f'pessoa{number:02d}@ifnmg.edu.br',
                f'Pessoa {number:02d}' if number % 3 else f'Silva {number:02d}',
                cls.teacher,
            )

    def setUp(self):
        self.client.force_login(self.admin)

    def options(self, query=''):
        response = self.client.get(f'{OPTIONS_URL}{query}')
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)

    def test_options_are_paged_and_searched_on_the_server(self):
        with self.case('primeira página'):
            data = self.options()
            self.assertEqual(len(data['opcoes']), OPTIONS_PAGE_SIZE)
            self.assertTrue(data['tem_mais'])
            self.assertEqual(data['opcoes'][0]['rotulo'], 'Admin (admin@ifnmg.edu.br)')
        with self.case('segunda página'):
            first = self.options()
            second = self.options('?pagina=2')
            self.assertEqual(len(second['opcoes']), 7)
            self.assertFalse(second['tem_mais'])
            self.assertTrue(set(o['valor'] for o in first['opcoes']).isdisjoint(o['valor'] for o in second['opcoes']))
        with self.case('busca'):
            data = self.options('?busca=silva')
            self.assertEqual(len(data['opcoes']), 5)
            for option in data['opcoes']:
                self.assertIn('Silva', option['rotulo'])
        with self.case('busca por e-mail'):
            data = self.options('?busca=pessoa01')
            self.assertEqual([option['rotulo'] for option in data['opcoes']], ['Pessoa 01 (pessoa01@ifnmg.edu.br)'])
        with self.case('inativos fora'):
            self.plain.deactivate()
            labels = [option['rotulo'] for option in self.options('?busca=docente')['opcoes']]
            self.assertEqual(labels, [])

    def test_form_carries_only_the_chosen_users(self):
        with self.case('não leva todos'):
            content = self.client.get('/notificacoes/nova/').content.decode()
            options = content[content.index('<select name="users"'):]
            options = options[:options.index('</select>')]
            self.assertEqual(options.count('<option'), OPTIONS_PAGE_SIZE)
            self.assertIn('data-select-source="/notificacoes/opcoes/usuarios/"', content)
        with self.case('escolhidos depois de um erro'):
            chosen = User.objects.get(email='pessoa14@ifnmg.edu.br')
            response = self.client.post(
                '/notificacoes/nova/',
                {'title': '', 'message': 'Mensagem.', 'type': 'INFORMACAO', 'destination': 'USUARIOS', 'users': [chosen.pk]},
            )
            content = response.content.decode()
            options = content[content.index('<select name="users"'):]
            options = options[:options.index('</select>')]
            self.assertIn(f'value="{chosen.pk}" selected', options)
            self.assertEqual(options.count('<option'), OPTIONS_PAGE_SIZE + 1)
