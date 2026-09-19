from django.test import TestCase

from accounts import permissions
from accounts.models import Role, User


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

