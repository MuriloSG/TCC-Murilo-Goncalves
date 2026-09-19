import re

from django.test import Client, TestCase

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
        self.assertEqual(self.listed(response), ['Ana Souza'])
        self.assertContains(response, 'Todos os usuários <span class="count">3</span>')
        self.assertContains(response, 'Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário</p>')

    def test_busca_por_trecho_do_email(self):
        self.assertEqual(self.listed(self.client.get('/usuarios/', {'busca': 'bruno.lima'})), ['Bruno Lima'])

    def test_filtro_por_situacao(self):
        self.assertEqual(self.listed(self.client.get('/usuarios/', {'situacao': 'inativos'})), ['Carla Mendes'])
        self.assertEqual(self.listed(self.client.get('/usuarios/', {'situacao': 'ativos'})), ['Ana Souza', 'Bruno Lima'])

    def test_busca_e_filtro_combinados(self):
        User.objects.register(email='ana.clara@ifnmg.edu.br', name='Ana Clara', role=self.admin_role).deactivate()
        response = self.client.get('/usuarios/', {'busca': 'ana', 'situacao': 'ativos'})
        self.assertEqual(self.listed(response), ['Ana Souza'])

    def test_situacao_invalida_mostra_todos(self):
        response = self.client.get('/usuarios/', {'situacao': 'qualquer'})
        self.assertEqual(self.listed(response), ['Ana Souza', 'Bruno Lima', 'Carla Mendes'])
        self.assertNotContains(response, 'class="error"')

    def test_ordem_por_nome(self):
        self.assertEqual(self.listed(self.client.get('/usuarios/', {'busca': 'ifnmg'})), ['Ana Souza', 'Bruno Lima', 'Carla Mendes'])

    def test_busca_sem_resultado(self):
        response = self.client.get('/usuarios/', {'busca': 'zzz'})
        self.assertEqual(self.listed(response), [])
        self.assertContains(response, '<p>Nenhum usuário encontrado para a busca.</p>', html=True)
        self.assertContains(response, '<a class="link" href="/usuarios/">Limpar busca</a>', html=True)
        self.assertNotContains(response, 'Exibindo')

    def test_lista_sem_busca_mantem_o_estado_vazio_original(self):
        response = self.client.get('/usuarios/', {'busca': ''})
        self.assertNotContains(response, 'Limpar busca')

    def test_formulario_mostra_o_estado_atual(self):
        response = self.client.get('/usuarios/', {'busca': 'ana', 'situacao': 'inativos'})
        content = response.content.decode()
        self.assertRegex(content, r'<form class="filters" method="get" action="/usuarios/" role="search" hx-get="/usuarios/"')
        self.assertIn('hx-push-url="true" hx-history="false"', content)
        self.assertRegex(content, r'<input type="search" name="busca" value="ana"')
        self.assertIn('<option value="inativos" selected>Inativos</option>', content)
        self.assertIn('<label class="sr-only" for="id_busca">Buscar por nome ou e-mail</label>', content)
        self.assertIn('<label class="sr-only" for="id_situacao">Situação</label>', content)
        self.assertRegex(content, r'(?s)<noscript><button class="btn-secondary" type="submit">.*Buscar</button></noscript>')

    def test_atualizacao_pelo_htmx_responde_so_a_tabela(self):
        response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'tabela-usuarios'})
        content = response.content.decode()
        self.assertTrue(content.startswith('<table class="data-table compact-rows">'), content[:80])
        self.assertNotIn('<html', content)
        self.assertNotIn('role="search"', content)
        self.assertEqual(self.listed(response), ['Ana Souza'])
        self.assertIn('Exibindo <strong>1</strong> a <strong>1</strong> de <strong>1</strong> usuário', content)

    def test_htmx_com_outro_alvo_responde_a_pagina(self):
        response = self.client.get('/usuarios/', {'busca': 'ana'}, headers=HTMX | {'HX-Target': 'outro'})
        self.assertContains(response, '<html')

    def test_busca_sem_a_permissao(self):
        client = Client()
        client.force_login(self.bruno)
        self.assertEqual(client.get('/usuarios/', {'busca': 'ana'}).status_code, 403)

    def test_busca_nao_altera_dados(self):
        before = list(User.objects.order_by('pk').values_list('name', 'email', 'is_active'))
        self.client.get('/usuarios/', {'busca': 'ana', 'situacao': 'inativos'})
        self.assertEqual(list(User.objects.order_by('pk').values_list('name', 'email', 'is_active')), before)

    def test_desativacao_pelo_htmx_volta_para_a_lista_filtrada(self):
        response = self.client.post(
            f'/usuarios/{self.bruno.pk}/desativar/',
            headers=HTMX | {'HX-Current-URL': 'http://testserver/usuarios/?busca=ana'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Redirect'], '/usuarios/?busca=ana')
        self.assertFalse(User.objects.get(pk=self.bruno.pk).is_active)


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
        self.assertIn(f'Pessoa Silva {PAGE_SIZE:03d}', content)
        self.assertNotIn(f'Pessoa Silva {PAGE_SIZE - 1:03d}', content)
        self.assertIn('href="/usuarios/?busca=silva&amp;pagina=3"', content)
        self.assertIn('href="/usuarios/?busca=silva"', content)
        self.assertIn('hx-target="#tabela-usuarios"', content)

    def test_navegacao_pelo_htmx_responde_so_a_tabela(self):
        response = self.client.get('/usuarios/', {'pagina': '2'}, headers=HTMX | {'HX-Target': 'tabela-usuarios'})
        self.assertTrue(response.content.decode().startswith('<table class="data-table compact-rows">'))
