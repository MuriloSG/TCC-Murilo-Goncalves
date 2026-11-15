from datetime import time

from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin
from schedule.models import ClassGroup, Course, Semester, Space, Stage, Weekday
from schedule.tests.test_timetable import allocate


def user_with(email, *codes):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role)


def with_lessons(space):
    semester, _ = Semester.objects.resolve('2026/2')
    course, _ = Course.objects.resolve('Eng. Florestal', stage=Stage.UNDERGRADUATE)
    group, _ = ClassGroup.objects.resolve(course, '6º período')
    allocate(semester, group, 'Patologia Florestal', Weekday.MONDAY, time(7, 20), time(8, 10), space=space.name)
    return space


class SpaceScreenTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.manager = user_with('gestor@ifnmg.edu.br', *permissions.SPACE_PERMISSIONS, permissions.AUDIT_VIEW)
        self.viewer = user_with('consulta@ifnmg.edu.br', permissions.SPACE_VIEW)
        self.importer = user_with('importador@ifnmg.edu.br', permissions.SPACE_ALLOCATION_IMPORT)
        self.space = Space.objects.register('HV 5', other_names=['HV5'])

    def routes(self):
        return {
            reverse('spaces_list'): permissions.SPACE_VIEW,
            reverse('spaces_create'): permissions.SPACE_CREATE,
            reverse('spaces_update', args=[self.space.pk]): permissions.SPACE_EDIT,
            reverse('spaces_deactivate', args=[self.space.pk]): permissions.SPACE_CHANGE_STATUS,
            reverse('spaces_reactivate', args=[self.space.pk]): permissions.SPACE_CHANGE_STATUS,
            reverse('spaces_delete', args=[self.space.pk]): permissions.SPACE_DELETE,
        }


class SpaceScreenTests(SpaceScreenTestCase):
    def list(self, user=None, **query):
        self.client.force_login(user or self.manager)
        return self.client.get(reverse('spaces_list'), query)

    def test_each_route_opens_with_its_own_permission(self):
        for position, (url, code) in enumerate(self.routes().items()):
            with self.subTest(url=url):
                self.client.force_login(user_with(f'rota_{"abcdef"[position]}@ifnmg.edu.br', code))
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_list_shows_names_origin_status_order_and_search(self):
        with self.case('nomes, origem e situação'):
            response = self.list()
            self.assertContains(response, 'HV 5')
            self.assertContains(response, 'HV5')
            self.assertContains(response, 'Manual')
            self.assertContains(response, 'Ativo')
        with self.case('busca pelo outro nome e filtros'):
            Space.objects.register('HV 4')
            Space.objects.register('Zoo I', origin='PLANILHA')
            self.assertEqual([space.name for space in self.list(busca='hv5').context['spaces']], ['HV 5'])
            self.assertEqual([space.name for space in self.list(origem='PLANILHA').context['spaces']], ['Zoo I'])
            self.assertEqual(len(self.list(situacao='qualquer').context['spaces']), 3)
        with self.case('ordem natural dos nomes'):
            for name in ('1/10', '1/4', '1/13'):
                Space.objects.register(name)
            names = [space.name for space in self.list().context['spaces']]
            self.assertEqual(names[:3], ['1/4', '1/10', '1/13'])
        with self.case('busca sem resultado'):
            response = self.list(busca='inexistente')
            self.assertContains(response, 'Nenhum espaço encontrado para a busca.')
            self.assertContains(response, 'Limpar busca')

    def test_list_controls_follow_the_permissions_and_the_lessons(self):
        with self.case('só a consulta não mostra ações'):
            response = self.list(self.viewer)
            for url in list(self.routes())[1:]:
                with self.subTest(url=url):
                    self.assertNotContains(response, url)
        with self.case('excluir só sem aulas'):
            used = with_lessons(Space.objects.register('1/10'))
            response = self.list()
            self.assertContains(response, reverse('spaces_delete', args=[self.space.pk]))
            self.assertNotContains(response, reverse('spaces_delete', args=[used.pk]))
        with self.case('auditoria para quem a consulta'):
            self.assertContains(self.list(), f'recurso={catalog.SPACE}&amp;registro={self.space.pk}')
            self.assertNotContains(self.list(self.viewer), 'Ver auditoria')

    def test_operations_with_their_messages(self):
        self.client.force_login(self.manager)
        with self.case('cadastro com outros nomes'):
            response = self.client.post(reverse('spaces_create'), {'name': 'Sala 101', 'other_names': 'S101\n\ns-101'}, follow=True)
            self.assertContains(response, 'Espaço Sala 101 cadastrado.')
            space = Space.objects.get(name='Sala 101')
            self.assertEqual((space.origin, space.is_active, space.other_names), ('MANUAL', True, ['s-101', 'S101']))
        with self.case('atualização mantém o nome anterior'):
            url = reverse('spaces_update', args=[self.space.pk])
            page = self.client.get(url)
            self.assertContains(page, 'HV5')
            response = self.client.post(url, {'name': 'Sala HV 05', 'other_names': 'HV5', 'origin': 'PLANILHA'}, follow=True)
            self.assertContains(response, 'Espaço Sala HV 05 atualizado.')
            self.space.refresh_from_db()
            self.assertEqual((self.space.name, self.space.other_names, self.space.origin), ('Sala HV 05', ['HV 5', 'HV5'], 'MANUAL'))
        with self.case('desativação e reativação'):
            confirmation = self.client.get(reverse('spaces_deactivate', args=[self.space.pk]))
            self.assertContains(confirmation, 'Desativar HV 5?')
            response = self.client.post(reverse('spaces_deactivate', args=[self.space.pk]), follow=True)
            self.assertContains(response, 'Espaço HV 5 desativado.')
            self.assertFalse(Space.objects.get(pk=self.space.pk).is_active)
            response = self.client.post(reverse('spaces_reactivate', args=[self.space.pk]), follow=True)
            self.assertContains(response, 'Espaço HV 5 reativado.')
            self.assertTrue(Space.objects.get(pk=self.space.pk).is_active)
        with self.case('exclusão sem aulas'):
            response = self.client.post(reverse('spaces_delete', args=[self.space.pk]), follow=True)
            self.assertContains(response, 'Espaço HV 5 excluído.')
            self.assertFalse(Space.objects.exists())
            self.assertTrue(AuditLog.objects.filter(resource=catalog.SPACE, action=catalog.DELETE).exists())

    def test_refusals_appear_on_the_screen(self):
        self.client.force_login(self.manager)
        with self.case('nome já usado'):
            response = self.client.post(reverse('spaces_create'), {'name': 'hv5'})
            self.assertEqual(response.status_code, 200)
            self.assertFormError(response.context['form'], 'name', 'Já existe um espaço com este nome.')
            self.assertEqual(Space.objects.count(), 1)
        with self.case('exclusão com aulas'):
            with_lessons(self.space)
            response = self.client.post(reverse('spaces_delete', args=[self.space.pk]), follow=True)
            self.assertContains(response, 'O espaço HV 5 tem aulas no ensalamento e não pode ser excluído. Desative o espaço.')
            self.assertTrue(Space.objects.filter(pk=self.space.pk).exists())
