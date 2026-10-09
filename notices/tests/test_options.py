import json

from django.test import TestCase

from accounts.models import User
from accounts.tests.roles import management_role, requester_role
from ui.pagination import OPTIONS_PAGE_SIZE

OPTIONS_URL = '/notificacoes/opcoes/usuarios/'


class UserOptionsTests(TestCase):
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

    def test_first_page_has_ten_options(self):
        data = self.options()
        self.assertEqual(len(data['opcoes']), OPTIONS_PAGE_SIZE)
        self.assertTrue(data['tem_mais'])
        self.assertEqual(data['opcoes'][0]['rotulo'], 'Admin (admin@ifnmg.edu.br)')

    def test_second_page_continues_the_list(self):
        first = self.options()
        second = self.options('?pagina=2')
        self.assertEqual(len(second['opcoes']), 7)
        self.assertFalse(second['tem_mais'])
        self.assertTrue(set(o['valor'] for o in first['opcoes']).isdisjoint(o['valor'] for o in second['opcoes']))

    def test_search_runs_on_the_server_over_every_user(self):
        data = self.options('?busca=silva')
        self.assertEqual(len(data['opcoes']), 5)
        for option in data['opcoes']:
            self.assertIn('Silva', option['rotulo'])

    def test_search_by_email(self):
        data = self.options('?busca=pessoa01')
        self.assertEqual([option['rotulo'] for option in data['opcoes']], ['Pessoa 01 (pessoa01@ifnmg.edu.br)'])

    def test_inactive_users_are_left_out(self):
        self.plain.deactivate()
        labels = [option['rotulo'] for option in self.options('?busca=docente')['opcoes']]
        self.assertEqual(labels, [])

    def test_form_does_not_carry_every_user(self):
        content = self.client.get('/notificacoes/nova/').content.decode()
        options = content[content.index('<select name="users"'):]
        options = options[:options.index('</select>')]
        self.assertEqual(options.count('<option'), OPTIONS_PAGE_SIZE)
        self.assertIn('data-select-source="/notificacoes/opcoes/usuarios/"', content)

    def test_chosen_users_stay_in_the_form_after_an_error(self):
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
