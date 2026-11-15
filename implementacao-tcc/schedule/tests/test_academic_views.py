from datetime import time

from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from config.testing import IsolatedCasesMixin
from schedule.models import (
    Allocation,
    ClassGroup,
    ClassOffering,
    Course,
    Semester,
    Stage,
    Subject,
    Teacher,
    TeachingAssignment,
    Weekday,
)
from schedule.tests.test_timetable import allocate


def user_with(email, *codes, username=None):
    code = email.partition('@')[0].upper()
    role = Role.objects.create_role(code=code, name=code, permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role, username=username)


def link(teacher_name, semester, subject, group, current=False):
    """Oferta com vínculo do docente, sem aula, como o histórico que a importação preserva."""
    offering, _ = ClassOffering.objects.get_or_create(semester=semester, subject=subject, class_group=group)
    teacher, _ = Teacher.objects.resolve(teacher_name)
    TeachingAssignment.objects.get_or_create(offering=offering, teacher=teacher, defaults={'is_current': current})
    return offering


ALL_ACADEMIC = (*permissions.SUBJECT_PERMISSIONS, *permissions.CLASS_GROUP_PERMISSIONS)


class AcademicTestCase(IsolatedCasesMixin, TestCase):
    def setUp(self):
        self.semester, _ = Semester.objects.resolve('2026/2')
        self.agro, _ = Course.objects.resolve('Agronomia', stage=Stage.UNDERGRADUATE)
        self.info, _ = Course.objects.resolve('Informática', stage=Stage.SECONDARY)
        self.second, _ = ClassGroup.objects.resolve(self.agro, '2º período')
        self.third, _ = ClassGroup.objects.resolve(self.info, '3º ano')
        self.math = allocate(self.semester, self.second, 'Matemática', Weekday.MONDAY, time(7, 20), time(8, 10), teachers=['joao']).subject
        ClassOffering.objects.record(self.semester, self.math, self.second)
        self.chemistry, _ = Subject.objects.resolve('Química')
        link('joao', self.semester, self.chemistry, self.second)
        self.physics = allocate(self.semester, self.third, 'Física', Weekday.TUESDAY, time(7, 20), time(8, 10), teachers=['maria']).subject
        ClassOffering.objects.record(self.semester, self.physics, self.third)
        self.free_subject, _ = Subject.objects.resolve('Robótica')
        self.free_group, _ = ClassGroup.objects.resolve(self.info, '1º ano')
        self.joao = user_with('joao@ifnmg.edu.br', *ALL_ACADEMIC, permissions.AUDIT_VIEW, username='joao')
        self.outsider = user_with('semdocente@ifnmg.edu.br', *ALL_ACADEMIC, username='semdocente')
        self.stranger = user_with('outro@ifnmg.edu.br', permissions.SPACE_VIEW)
        self.superadmin = User.objects.create_superadmin('admin@ifnmg.edu.br', 'Admin', 'senha-forte-123')


class ScopeTests(AcademicTestCase):
    def test_scope_follows_the_teacher_of_the_user(self):
        self.assertEqual(set(Subject.objects.visible_to(self.joao)), {self.math, self.chemistry})
        self.assertEqual(list(ClassGroup.objects.visible_to(self.joao)), [self.second])
        self.assertFalse(Subject.objects.visible_to(self.outsider).exists())
        self.assertFalse(ClassGroup.objects.visible_to(self.outsider).exists())

    def test_superadmin_and_scope_permissions_reach_every_record(self):
        self.assertEqual(Subject.objects.visible_to(self.superadmin).count(), Subject.objects.count())
        self.assertEqual(ClassGroup.objects.visible_to(self.superadmin).count(), ClassGroup.objects.count())
        subjects = user_with('disciplinas@ifnmg.edu.br', *ALL_ACADEMIC, permissions.SUBJECT_ALL)
        groups = user_with('turmas@ifnmg.edu.br', *ALL_ACADEMIC, permissions.CLASS_GROUP_ALL, username='maria')
        self.assertEqual(set(Subject.objects.visible_to(subjects)), set(Subject.objects.all()))
        self.assertFalse(ClassGroup.objects.visible_to(subjects).exists())
        self.assertEqual(set(ClassGroup.objects.visible_to(groups)), set(ClassGroup.objects.all()))
        self.assertEqual(set(Subject.objects.visible_to(groups)), {self.physics})
        both = user_with('alcance@ifnmg.edu.br', *ALL_ACADEMIC, permissions.SUBJECT_ALL, permissions.CLASS_GROUP_ALL)
        self.client.force_login(both)
        for url in (reverse('subjects_detail', args=[self.physics.pk]), reverse('class_groups_detail', args=[self.third.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        User.objects.filter(pk=both.pk).update(is_active=False)
        inactive = User.objects.get(pk=both.pk)
        self.assertFalse(Subject.objects.visible_to(inactive).exists())
        self.assertFalse(ClassGroup.objects.visible_to(inactive).exists())

    def test_each_route_opens_with_its_own_permission(self):
        routes = {
            reverse('subjects_list'): permissions.SUBJECT_VIEW,
            reverse('subjects_create'): permissions.SUBJECT_CREATE,
            reverse('subjects_detail', args=[self.math.pk]): permissions.SUBJECT_VIEW,
            reverse('subjects_update', args=[self.math.pk]): permissions.SUBJECT_EDIT,
            reverse('subjects_delete', args=[self.chemistry.pk]): permissions.SUBJECT_DELETE,
            reverse('class_groups_list'): permissions.CLASS_GROUP_VIEW,
            reverse('class_groups_create'): permissions.CLASS_GROUP_CREATE,
            reverse('class_groups_detail', args=[self.second.pk]): permissions.CLASS_GROUP_VIEW,
            reverse('class_groups_update', args=[self.second.pk]): permissions.CLASS_GROUP_EDIT,
            reverse('class_groups_delete', args=[self.second.pk]): permissions.CLASS_GROUP_DELETE,
        }
        for position, (url, code) in enumerate(routes.items()):
            with self.subTest(url=url):
                name = f'rota{"abcdefghij"[position]}'
                link(name, self.semester, self.math, self.second)
                link(name, self.semester, self.chemistry, self.second)
                self.client.force_login(user_with(f'{name}@ifnmg.edu.br', code, username=name))
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_records_out_of_scope_are_not_found_and_stay_untouched(self):
        self.client.force_login(self.joao)
        for url in (reverse('subjects_detail', args=[self.physics.pk]), reverse('class_groups_detail', args=[self.third.pk])):
            self.assertEqual(self.client.get(url).status_code, 404)
        forged = [
            (reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'Robótica II'}),
            (reverse('class_groups_update', args=[self.free_group.pk]), {'course': self.info.pk, 'label': '1º ano B'}),
            (reverse('subjects_delete', args=[self.free_subject.pk]), {}),
            (reverse('class_groups_delete', args=[self.free_group.pk]), {}),
        ]
        for url, data in forged:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, data).status_code, 404)
        self.assertEqual(Subject.objects.get(pk=self.free_subject.pk).name, 'Robótica')
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).label, '1º ano')


class ScreenTests(AcademicTestCase):
    def test_lists_show_the_scope_with_counts_search_and_filters(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('subjects_list'))
        for name, shown in (('Matemática', True), ('Química', True), ('Física', False), ('Robótica', False)):
            (self.assertContains if shown else self.assertNotContains)(response, name)
        math = next(item for item in response.context['subjects'] if item.pk == self.math.pk)
        self.assertEqual((math.offering_count, math.lesson_count), (1, 1))
        response = self.client.get(reverse('class_groups_list'))
        self.assertContains(response, '2º período')
        self.assertNotContains(response, '3º ano')
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(reverse('subjects_list')), 'Nenhuma disciplina cadastrada.')
        self.assertContains(self.client.get(reverse('class_groups_list')), 'Nenhuma turma cadastrada.')
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('class_groups_list'), {'busca': 'agro'})
        self.assertEqual(list(response.context['class_groups']), [self.second])
        response = self.client.get(reverse('class_groups_list'), {'curso': self.info.pk})
        self.assertEqual({group.label for group in response.context['class_groups']}, {'1º ano', '3º ano'})
        self.assertContains(self.client.get(reverse('subjects_list'), {'busca': 'zzz'}), 'Nenhuma disciplina encontrada.')

    def test_detail_shows_offerings_teachers_and_history(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('subjects_detail', args=[self.math.pk]))
        self.assertContains(response, '2026/2')
        self.assertContains(response, '<span class="person-detail">joao</span>', html=True)
        self.assertNotContains(response, 'atual')
        self.assertContains(self.client.get(reverse('class_groups_detail', args=[self.second.pk])), 'joao, histórico')

    def test_create_registers_and_audits_without_offerings(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_create'), {'name': '  Artes   Visuais '})
        self.assertRedirects(response, reverse('subjects_list'), fetch_redirect_response=False)
        subject = Subject.objects.get(name='Artes Visuais')
        log = AuditLog.objects.get(resource=catalog.SUBJECT, action=catalog.CREATE)
        self.assertEqual((log.resource_id, log.user, log.new_values), (str(subject.pk), self.joao, {'name': 'Artes Visuais'}))
        self.assertFalse(subject.offerings.exists())
        self.client.post(reverse('class_groups_create'), {'course': self.agro.pk, 'label': '4º período'})
        group = ClassGroup.objects.get(course=self.agro, label='4º período')
        log = AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.CREATE)
        self.assertEqual(log.new_values, {'curso': 'Agronomia', 'rotulo': '4º período'})
        self.assertFalse(group.offerings.exists())
        self.assertContains(self.client.post(reverse('subjects_create'), {'name': 'matemática'}), 'Já existe disciplina com este nome.')
        self.assertEqual(Subject.objects.filter(name__iexact='matemática').count(), 1)
        response = self.client.post(reverse('class_groups_create'), {'course': self.agro.pk, 'label': '2º PERÍODO'})
        self.assertContains(response, 'Já existe uma turma com este rótulo neste curso.')

    def test_update_renames_only_unused_records(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_update', args=[self.math.pk]), {'name': 'Matemática'})
        self.assertRedirects(response, reverse('subjects_list'), fetch_redirect_response=False)
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SUBJECT).exists())
        self.client.force_login(self.superadmin)
        self.client.post(reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'Robótica I'})
        self.assertEqual(Subject.objects.get(pk=self.free_subject.pk).name, 'Robótica I')
        log = AuditLog.objects.get(resource=catalog.SUBJECT, action=catalog.UPDATE)
        self.assertEqual((log.old_values, log.new_values), ({'name': 'Robótica'}, {'name': 'Robótica I'}))
        self.client.post(reverse('class_groups_update', args=[self.free_group.pk]), {'course': self.info.pk, 'label': '1º ano A'})
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).label, '1º ano A')
        self.assertEqual(AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.UPDATE).new_values, {'rotulo': '1º ano A'})

    def test_update_refusals(self):
        offering_only = ClassGroup.objects.resolve(self.agro, '5º período')[0]
        link('joao', self.semester, self.chemistry, offering_only)
        cases = [
            ('disciplina usada no ensalamento', self.joao, reverse('subjects_update', args=[self.math.pk]), {'name': 'Matemática I'}, 'não pode ser renomeada'),
            (
                'turma só com oferta', self.superadmin, reverse('class_groups_update', args=[offering_only.pk]),
                {'course': self.agro.pk, 'label': '5º período B'}, 'não pode ser renomeada',
            ),
            (
                'curso trocado', self.superadmin, reverse('class_groups_update', args=[self.free_group.pk]),
                {'course': self.agro.pk, 'label': '1º ano'}, 'O curso da turma não pode ser alterado.',
            ),
            ('nome já usado', self.superadmin, reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'química'}, 'Já existe disciplina com este nome.'),
        ]
        for label, user, url, data, message in cases:
            with self.subTest(label):
                self.client.force_login(user)
                self.assertContains(self.client.post(url, data), message)
        self.assertEqual(Subject.objects.get(pk=self.math.pk).name, 'Matemática')
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).course, self.info)
        self.assertFalse(AuditLog.objects.filter(resource__in=[catalog.SUBJECT, catalog.CLASS_GROUP]).exists())

    def test_delete_only_unused_records(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('subjects_list'))
        self.assertContains(response, reverse('subjects_delete', args=[self.free_subject.pk]))
        self.assertNotContains(response, reverse('subjects_delete', args=[self.math.pk]))
        response = self.client.post(reverse('subjects_delete', args=[self.physics.pk]), follow=True)
        self.assertContains(response, 'A disciplina Física tem ofertas ou aulas no ensalamento e não pode ser excluída.')
        self.client.force_login(self.joao)
        self.client.post(reverse('subjects_delete', args=[self.chemistry.pk]))
        self.client.post(reverse('class_groups_delete', args=[self.second.pk]))
        for model, pk in ((Subject, self.physics.pk), (Subject, self.chemistry.pk), (ClassGroup, self.second.pk)):
            self.assertTrue(model.objects.filter(pk=pk).exists())
        self.assertFalse(AuditLog.objects.filter(action=catalog.DELETE).exists())
        self.client.force_login(self.superadmin)
        self.client.post(reverse('subjects_delete', args=[self.free_subject.pk]))
        self.client.post(reverse('class_groups_delete', args=[self.free_group.pk]))
        self.assertFalse(Subject.objects.filter(pk=self.free_subject.pk).exists())
        self.assertFalse(ClassGroup.objects.filter(pk=self.free_group.pk).exists())
        log = AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.DELETE)
        self.assertEqual(log.old_values, {'curso': 'Informática', 'rotulo': '1º ano'})
        self.assertTrue(AuditLog.objects.filter(resource=catalog.SUBJECT, action=catalog.DELETE).exists())


class ImportRegressionTests(AcademicTestCase):
    def test_manual_registration_offers_nothing_to_the_agenda(self):
        Subject.objects.register('Artes')
        ClassGroup.objects.register(self.agro, '6º período')
        teacher = Teacher.objects.get(name='joao')
        subjects = {item.offering.subject.name for item in TeachingAssignment.objects.available(self.semester, teacher)}
        self.assertEqual(subjects, {'Matemática'})
        self.assertEqual(Allocation.objects.count(), 2)
