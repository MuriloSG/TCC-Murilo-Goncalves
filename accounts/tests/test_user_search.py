import re

from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User
from ui.pagination import PAGE_SIZE

HTMX = {'HX-Request': 'true'}


class SearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        teacher = Role.objects.get(code='DOCENTE')
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
    def test_trecho_do_nome(self):
        self.assertEqual(self.names(User.objects.search('sou')), ['Ana Souza'])

    def test_trecho_do_email(self):
        self.assertEqual(self.names(User.objects.search('bruno.lima')), ['Bruno Lima'])

    def test_trecho_do_nome_de_usuario(self):
        aldo = User.objects.register(
            email='aldo@ifnmg.edu.br', name='Aldo Gomes da Silva',
            role=self.admin_role, username='Aldo Gomes',
        )
        self.assertEqual(self.names(User.objects.search('aldo gomes')), [aldo.name])
        self.assertEqual(self.names(User.objects.search('ALDO GOMES')), [aldo.name])

    def test_nome_de_usuario_combinado_com_a_situacao(self):
        User.objects.register(
            email='aldo@ifnmg.edu.br', name='Aldo Gomes da Silva',
            role=self.admin_role, username='Aldo Gomes',
        ).deactivate()
        self.assertEqual(self.names(User.objects.search('aldo gomes', 'ativos')), [])
        self.assertEqual(self.names(User.objects.search('aldo gomes', 'inativos')), ['Aldo Gomes da Silva'])

    def test_ignora_maiusculas(self):
        self.assertEqual(self.names(User.objects.search('CARLA')), ['Carla Mendes'])
        self.assertEqual(self.names(User.objects.search('IFNMG.EDU')), ['Ana Souza', 'Bruno Lima', 'Carla Mendes'])

    def test_situacao(self):
        self.assertEqual(self.names(User.objects.search('', 'ativos')), ['Ana Souza', 'Bruno Lima'])
        self.assertEqual(self.names(User.objects.search('', 'inativos')), ['Carla Mendes'])
        self.assertEqual(len(User.objects.search('', 'todos')), 3)
        self.assertEqual(len(User.objects.search('', 'qualquer')), 3)

    def test_combinacao(self):
        User.objects.register(email='ana.clara@ifnmg.edu.br', name='Ana Clara', role=self.admin_role).deactivate()
        self.assertEqual(self.names(User.objects.search('ana', 'ativos')), ['Ana Souza'])
        self.assertEqual(self.names(User.objects.search('ana', 'inativos')), ['Ana Clara'])

    def test_termo_vazio(self):
        self.assertEqual(len(User.objects.search('')), 3)
        self.assertEqual(len(User.objects.search()), 3)


class ListSearchViewTests(SearchTestCase):
    def setUp(self):
        self.client.force_login(self.ana)

    def listed(self, response):
        return re.findall(r'<span class="person-name">([^<(]+?)(?: \(superadmin\))?</span>', response.content.decode())

    def test_busca_por_trecho_do_nome(self):
        response = self.client.get('/usuarios/', {'busca': 'SOU'})
        self.assertEqual(self.listed(response), ['ana.souza@ifnmg.edu.br'])
        self.assertContains(response, 'Todos os usuários <span class="count">3</span>')
        self.assertContains(response, 'Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário</p>')

    def test_busca_sem_resultado(self):
        response = self.client.get('/usuarios/', {'busca': 'zzz'})
        self.assertEqual(self.listed(response), [])
        self.assertContains(response, 'Nenhum usuário encontrado para a busca.')
        self.assertContains(response, 'Limpar busca')
        self.assertNotContains(response, 'Exibindo')

    def test_lista_sem_busca_mantem_o_estado_vazio_original(self):
        response = self.client.get('/usuarios/', {'busca': ''})
        self.assertNotContains(response, 'Limpar busca')

    def test_formulario_mostra_o_estado_atual(self):
        response = self.client.get('/usuarios/', {'busca': 'ana', 'situacao': 'inativos'})
        self.assertRegex(response.content.decode(), r'<input type="search" name="busca" value="ana"')
        self.assertContains(response, '<option value="inativos" selected>Inativos</option>')

    def test_atualizacao_pelo_htmx_responde_so_a_tabela(self):
        response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'tabela-usuarios'})
        content = response.content.decode()
        self.assertTrue(content.startswith('<table class="data-table compact-rows">'), content[:80])
        self.assertNotIn('<html', content)
        self.assertNotIn('role="search"', content)
        self.assertEqual(self.listed(response), ['ana.souza@ifnmg.edu.br'])
        self.assertIn('Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário', content)

    def test_htmx_com_outro_alvo_responde_a_pagina(self):
        response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'outro'})
        self.assertContains(response, '<html')


class PaginatedSearchTests(SearchTestCase):
    total = PAGE_SIZE * 2 + 1

    def setUp(self):
        self.client.force_login(self.ana)
        for index in range(self.total):
            User.objects.register(
                email=f'silva{index:03d}@ifnmg.edu.br', name=f'Pessoa Silva {index:03d}', role=self.admin_role,
            )

    def test_busca_paginada_mantem_a_busca(self):
        response = self.client.get('/usuarios/', {'busca': 'silva', 'pagina': '2'})
        content = response.content.decode()
        self.assertIn(
            f'Exibindo <strong>{PAGE_SIZE + 1}</strong> a <strong>{PAGE_SIZE * 2}</strong> '
            f'de <strong>{self.total}</strong> usuários',
            content,
        )
        self.assertIn(f'silva{PAGE_SIZE:03d}@ifnmg.edu.br', content)
        self.assertNotIn(f'silva{PAGE_SIZE - 1:03d}@ifnmg.edu.br', content)
        self.assertIn('href="/usuarios/?busca=silva&amp;pagina=3"', content)
        self.assertIn('href="/usuarios/?busca=silva"', content)
        self.assertIn('hx-target="#tabela-usuarios"', content)
