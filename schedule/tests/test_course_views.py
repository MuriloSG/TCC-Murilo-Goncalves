"""Telas de Cursos: acesso por permissão, menu e operações pela interface."""

from datetime import time

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from schedule.models import ClassGroup, Course, Semester, Stage, Weekday
from schedule.tests.test_timetable import allocate


def user_with(email, *codes):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role)


class CourseTestCase(TestCase):
    def setUp(self):
        self.agro = Course.objects.register('Agronomia', Stage.UNDERGRADUATE)
        self.info = Course.objects.register('Informática', Stage.SECONDARY)
        self.free = Course.objects.register('Zootecnia', Stage.UNDERGRADUATE)
        self.group = ClassGroup.objects.register(self.info, '1º ano')
        semester, _ = Semester.objects.resolve('2026/2')
        allocate(semester, ClassGroup.objects.register(self.agro, '2º período'), 'Matemática', Weekday.MONDAY, time(7, 20), time(8, 10))
        self.manager = user_with('gestor@ifnmg.edu.br', *permissions.COURSE_PERMISSIONS, permissions.AUDIT_VIEW)
        self.stranger = user_with('outro@ifnmg.edu.br', permissions.SPACE_VIEW)

    def messages_of(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]


class AccessTests(CourseTestCase):
    def test_routes_refuse_a_user_without_the_permission(self):
        self.client.force_login(self.stranger)
        for url in (
            reverse('courses_list'),
            reverse('courses_create'),
            reverse('courses_detail', args=[self.agro.pk]),
            reverse('courses_update', args=[self.agro.pk]),
            reverse('courses_delete', args=[self.free.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_menu_item_follows_the_view_permission(self):
        self.client.force_login(user_with('leitor@ifnmg.edu.br', permissions.COURSE_VIEW))
        self.assertContains(self.client.get(reverse('home'), follow=True), reverse('courses_list'))
        self.client.force_login(self.stranger)
        self.assertNotContains(self.client.get(reverse('home'), follow=True), reverse('courses_list'))


class OperationTests(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def test_create_registers_audits_and_returns_to_the_list(self):
        response = self.client.post(reverse('courses_create'), {'name': ' Eng.  Pesca ', 'stage': Stage.UNDERGRADUATE})
        self.assertRedirects(response, reverse('courses_list'), fetch_redirect_response=False)
        course = Course.objects.get(name='Eng. Pesca')
        self.assertEqual(course.stage, Stage.UNDERGRADUATE)
        self.assertEqual(self.messages_of(response), ['Curso Eng. Pesca cadastrado.'])
        entry = AuditLog.objects.get(resource=catalog.COURSE, action=catalog.CREATE, resource_id=str(course.pk))
        self.assertEqual(entry.user, self.manager)

    def test_update_of_a_course_without_use_changes_it(self):
        response = self.client.post(
            reverse('courses_update', args=[self.info.pk]), {'name': 'Técnico em Informática', 'stage': Stage.SECONDARY},
        )
        self.assertRedirects(response, reverse('courses_list'), fetch_redirect_response=False)
        self.info.refresh_from_db()
        self.assertEqual(self.info.name, 'Técnico em Informática')
        self.assertEqual(self.messages_of(response), ['Curso Técnico em Informática atualizado.'])

    def test_delete_of_a_course_without_class_groups(self):
        response = self.client.post(reverse('courses_delete', args=[self.free.pk]))
        self.assertRedirects(response, reverse('courses_list'), fetch_redirect_response=False)
        self.assertFalse(Course.objects.filter(pk=self.free.pk).exists())
        self.assertEqual(self.messages_of(response), ['Curso Zootecnia excluído.'])

    def test_delete_of_a_course_with_class_groups_is_refused_with_a_message(self):
        response = self.client.post(reverse('courses_delete', args=[self.info.pk]))
        self.assertRedirects(response, reverse('courses_list'), fetch_redirect_response=False)
        self.assertTrue(Course.objects.filter(pk=self.info.pk).exists())
        self.assertEqual(
            self.messages_of(response),
            ['O curso Informática tem turmas cadastradas e não pode ser excluído. Exclua as turmas antes.'],
        )


class ScreenTests(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def listed(self, query=''):
        return [course.name for course in self.client.get(reverse('courses_list') + query).context['courses']]

    def test_each_route_opens_with_its_own_permission(self):
        routes = {
            reverse('courses_list'): permissions.COURSE_VIEW,
            reverse('courses_create'): permissions.COURSE_CREATE,
            reverse('courses_detail', args=[self.agro.pk]): permissions.COURSE_VIEW,
            reverse('courses_update', args=[self.agro.pk]): permissions.COURSE_EDIT,
            reverse('courses_delete', args=[self.free.pk]): permissions.COURSE_DELETE,
        }
        for position, (url, code) in enumerate(routes.items()):
            with self.subTest(url=url):
                self.client.force_login(user_with(f'rota{"abcde"[position]}@ifnmg.edu.br', code))
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_list_searches_by_name_and_filters_by_stage(self):
        self.assertEqual(self.listed(), ['Agronomia', 'Informática', 'Zootecnia'])
        self.assertEqual(self.listed('?busca=inform'), ['Informática'])
        self.assertEqual(self.listed(f'?etapa={Stage.UNDERGRADUATE}'), ['Agronomia', 'Zootecnia'])
        self.assertEqual(self.listed('?etapa=DOUTORADO'), ['Agronomia', 'Informática', 'Zootecnia'])

    def test_delete_action_only_for_courses_without_class_groups(self):
        courses = self.client.get(reverse('courses_list')).context['courses']
        self.assertEqual({course.name: course.deletable for course in courses}, {'Agronomia': False, 'Informática': False, 'Zootecnia': True})
        self.assertEqual({course.name: course.class_group_count for course in courses}, {'Agronomia': 1, 'Informática': 1, 'Zootecnia': 0})

    def test_filter_request_by_htmx_returns_only_the_table(self):
        response = self.client.get(reverse('courses_list'), headers={'HX-Request': 'true', 'HX-Target': 'tabela-cursos'})
        self.assertTemplateUsed(response, 'schedule/partials/course_table.html')
        self.assertTemplateNotUsed(response, 'schedule/course_list.html')

    def test_detail_shows_the_class_groups_with_their_use(self):
        response = self.client.get(reverse('courses_detail', args=[self.agro.pk]))
        groups = {group.label: (group.offering_count, group.lesson_count) for group in response.context['class_groups']}
        self.assertEqual(groups, {'2º período': (0, 1)})
        self.assertTrue(response.context['in_use'])
        self.assertIsNotNone(response.context['history'])

    def test_refusals_appear_as_form_errors(self):
        cases = (
            ('courses_create', [], {'name': 'agronomia', 'stage': Stage.UNDERGRADUATE}, 'Já existe curso com este nome.'),
            ('courses_update', [self.agro.pk], {'name': 'Agronomia', 'stage': Stage.SECONDARY}, 'não pode ser alterado'),
        )
        for name, args, data, message in cases:
            with self.subTest(route=name):
                response = self.client.post(reverse(name, args=args), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(message, ' '.join(response.context['form'].non_field_errors() + response.context['form'].errors.get('name', [])))
        self.agro.refresh_from_db()
        self.assertEqual(self.agro.stage, Stage.UNDERGRADUATE)
