from datetime import time

from django.test import Client, TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
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


class AcademicTestCase(TestCase):
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
    def test_subject_scope_follows_the_teacher_of_the_user(self):
        visible = set(Subject.objects.visible_to(self.joao))
        self.assertEqual(visible, {self.math, self.chemistry})

    def test_class_group_scope_follows_the_teacher_of_the_user(self):
        self.assertEqual(list(ClassGroup.objects.visible_to(self.joao)), [self.second])

    def test_user_without_teacher_has_empty_scope(self):
        self.assertFalse(Subject.objects.visible_to(self.outsider).exists())
        self.assertFalse(ClassGroup.objects.visible_to(self.outsider).exists())

    def test_superadmin_reaches_every_record(self):
        self.assertEqual(Subject.objects.visible_to(self.superadmin).count(), Subject.objects.count())
        self.assertEqual(ClassGroup.objects.visible_to(self.superadmin).count(), ClassGroup.objects.count())


class AccessTests(AcademicTestCase):
    def routes(self):
        return {
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

    def test_anonymous_is_sent_to_the_login_with_next(self):
        for url in self.routes():
            with self.subTest(url=url):
                self.assertRedirects(
                    self.client.get(url), f"{reverse('account_login')}?next={url}", fetch_redirect_response=False,
                )

    def test_each_route_requires_its_own_permission(self):
        for position, (url, code) in enumerate(self.routes().items()):
            with self.subTest(url=url):
                name = f'rota{"abcdefghij"[position]}'
                link(name, self.semester, self.math, self.second)
                link(name, self.semester, self.chemistry, self.second)
                self.client.force_login(user_with(f'{name}@ifnmg.edu.br', code, username=name))
                self.assertEqual(self.client.get(url).status_code, 200)
                self.client.force_login(self.stranger)
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_post_without_the_permission_creates_nothing(self):
        self.client.force_login(user_with('consulta@ifnmg.edu.br', permissions.SUBJECT_VIEW))
        response = self.client.post(reverse('subjects_create'), {'name': 'Artes'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Subject.objects.filter(name='Artes').exists())

    def test_post_without_csrf_is_refused(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.superadmin)
        response = client.post(reverse('class_groups_delete', args=[self.free_group.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ClassGroup.objects.filter(pk=self.free_group.pk).exists())

    def test_menu_items_follow_the_view_permission(self):
        self.client.force_login(self.joao)
        page = self.client.get(reverse('home'))
        self.assertContains(page, reverse('subjects_list'))
        self.assertContains(page, reverse('class_groups_list'))
        self.client.force_login(self.stranger)
        page = self.client.get(reverse('home'))
        self.assertNotContains(page, reverse('subjects_list'))
        self.assertNotContains(page, reverse('class_groups_list'))


class OutOfScopeTests(AcademicTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.joao)

    def test_detail_by_url_is_not_found(self):
        self.assertEqual(self.client.get(reverse('subjects_detail', args=[self.physics.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('class_groups_detail', args=[self.third.pk])).status_code, 404)

    def test_forged_update_is_not_found_and_changes_nothing(self):
        response = self.client.post(reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'Robótica II'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Subject.objects.get(pk=self.free_subject.pk).name, 'Robótica')
        response = self.client.post(
            reverse('class_groups_update', args=[self.free_group.pk]), {'course': self.info.pk, 'label': '1º ano B'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).label, '1º ano')

    def test_forged_delete_is_not_found_and_keeps_the_record(self):
        self.assertEqual(self.client.post(reverse('subjects_delete', args=[self.free_subject.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('class_groups_delete', args=[self.free_group.pk])).status_code, 404)
        self.assertTrue(Subject.objects.filter(pk=self.free_subject.pk).exists())
        self.assertTrue(ClassGroup.objects.filter(pk=self.free_group.pk).exists())


class ListTests(AcademicTestCase):
    def test_teacher_lists_only_his_subjects(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('subjects_list'))
        self.assertContains(response, 'Matemática')
        self.assertContains(response, 'Química')
        self.assertNotContains(response, 'Física')
        self.assertNotContains(response, 'Robótica')

    def test_teacher_lists_only_his_class_groups(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('class_groups_list'))
        self.assertContains(response, '2º período')
        self.assertNotContains(response, '3º ano')

    def test_user_without_teacher_sees_the_empty_state(self):
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(reverse('subjects_list')), 'Nenhuma disciplina cadastrada.')
        self.assertContains(self.client.get(reverse('class_groups_list')), 'Nenhuma turma cadastrada.')

    def test_superadmin_lists_every_record_through_the_pages(self):
        for number in range(30):
            Subject.objects.resolve(f'Disciplina {number:02d}')
        self.client.force_login(self.superadmin)
        seen = set()
        for page in range(1, 10):
            response = self.client.get(reverse('subjects_list'), {'pagina': page})
            seen.update(item.pk for item in response.context['subjects'])
        self.assertEqual(seen, set(Subject.objects.values_list('pk', flat=True)))

    def test_search_and_course_filter(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('class_groups_list'), {'busca': 'agro'})
        self.assertEqual(list(response.context['class_groups']), [self.second])
        response = self.client.get(reverse('class_groups_list'), {'curso': self.info.pk})
        self.assertEqual({group.label for group in response.context['class_groups']}, {'1º ano', '3º ano'})
        response = self.client.get(reverse('subjects_list'), {'busca': 'zzz'})
        self.assertContains(response, 'Nenhuma disciplina encontrada.')

    def test_counts_are_not_multiplied_by_the_scope_join(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('subjects_list'))
        math = next(item for item in response.context['subjects'] if item.pk == self.math.pk)
        self.assertEqual((math.offering_count, math.lesson_count), (1, 1))

    def test_filter_request_by_htmx_returns_only_the_table(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('subjects_list'), headers={'HX-Request': 'true', 'HX-Target': 'tabela-disciplinas'})
        self.assertTemplateUsed(response, 'schedule/partials/subject_table.html')
        self.assertTemplateNotUsed(response, 'schedule/subject_list.html')


class DetailTests(AcademicTestCase):
    def test_subject_detail_shows_offerings_and_teachers(self):
        self.client.force_login(self.joao)
        response = self.client.get(reverse('subjects_detail', args=[self.math.pk]))
        self.assertContains(response, '2026/2')
        self.assertContains(response, '<span class="person-detail">joao</span>', html=True)
        self.assertNotContains(response, 'atual')

    def test_historic_link_is_labelled(self):
        self.client.force_login(self.joao)
        self.assertContains(self.client.get(reverse('class_groups_detail', args=[self.second.pk])), 'joao, histórico')


class CreateTests(AcademicTestCase):
    def test_valid_subject_is_created_and_audited(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_create'), {'name': '  Artes   Visuais '})
        self.assertRedirects(response, reverse('subjects_list'), fetch_redirect_response=False)
        subject = Subject.objects.get(name='Artes Visuais')
        log = AuditLog.objects.get(resource=catalog.SUBJECT, action=catalog.CREATE)
        self.assertEqual((log.resource_id, log.user, log.new_values), (str(subject.pk), self.joao, {'name': 'Artes Visuais'}))
        self.assertFalse(subject.offerings.exists())

    def test_duplicate_subject_is_refused(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_create'), {'name': 'matemática'})
        self.assertContains(response, 'Já existe disciplina com este nome.')
        self.assertEqual(Subject.objects.filter(name__iexact='matemática').count(), 1)

    def test_empty_label_is_refused(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('class_groups_create'), {'course': self.agro.pk, 'label': '   '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClassGroup.objects.filter(course=self.agro).count(), 1)

    def test_valid_class_group_is_created_and_audited(self):
        self.client.force_login(self.joao)
        self.client.post(reverse('class_groups_create'), {'course': self.agro.pk, 'label': '4º período'})
        group = ClassGroup.objects.get(course=self.agro, label='4º período')
        log = AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.CREATE)
        self.assertEqual(log.new_values, {'curso': 'Agronomia', 'rotulo': '4º período'})
        self.assertFalse(group.offerings.exists())

    def test_duplicate_class_group_in_the_course_is_refused(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('class_groups_create'), {'course': self.agro.pk, 'label': '2º PERÍODO'})
        self.assertContains(response, 'Já existe uma turma com este rótulo neste curso.')

    def test_same_label_in_another_course_is_accepted(self):
        self.client.force_login(self.joao)
        self.client.post(reverse('class_groups_create'), {'course': self.info.pk, 'label': '2º período'})
        self.assertTrue(ClassGroup.objects.filter(course=self.info, label='2º período').exists())


class UpdateTests(AcademicTestCase):
    def test_superadmin_renames_an_unused_record_of_any_scope(self):
        self.client.force_login(self.superadmin)
        self.client.post(reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'Robótica I'})
        self.assertEqual(Subject.objects.get(pk=self.free_subject.pk).name, 'Robótica I')
        log = AuditLog.objects.get(resource=catalog.SUBJECT, action=catalog.UPDATE)
        self.assertEqual((log.old_values, log.new_values), ({'name': 'Robótica'}, {'name': 'Robótica I'}))

    def test_rename_of_subject_used_by_the_timetable_is_refused(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_update', args=[self.math.pk]), {'name': 'Matemática I'})
        self.assertContains(response, 'não pode ser renomeada')
        self.assertEqual(Subject.objects.get(pk=self.math.pk).name, 'Matemática')
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SUBJECT).exists())

    def test_rename_of_class_group_with_only_an_offering_is_refused(self):
        self.client.force_login(self.superadmin)
        offering_only = ClassGroup.objects.resolve(self.agro, '5º período')[0]
        link('joao', self.semester, self.chemistry, offering_only)
        response = self.client.post(
            reverse('class_groups_update', args=[offering_only.pk]), {'course': self.agro.pk, 'label': '5º período B'},
        )
        self.assertContains(response, 'não pode ser renomeada')

    def test_saving_the_same_name_changes_nothing(self):
        self.client.force_login(self.joao)
        response = self.client.post(reverse('subjects_update', args=[self.math.pk]), {'name': 'Matemática'})
        self.assertRedirects(response, reverse('subjects_list'), fetch_redirect_response=False)
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SUBJECT).exists())

    def test_forged_course_is_refused(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(
            reverse('class_groups_update', args=[self.free_group.pk]), {'course': self.agro.pk, 'label': '1º ano'},
        )
        self.assertContains(response, 'O curso da turma não pode ser alterado.')
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).course, self.info)

    def test_superadmin_renames_an_unused_class_group(self):
        self.client.force_login(self.superadmin)
        self.client.post(reverse('class_groups_update', args=[self.free_group.pk]), {'course': self.info.pk, 'label': '1º ano A'})
        self.assertEqual(ClassGroup.objects.get(pk=self.free_group.pk).label, '1º ano A')
        log = AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.UPDATE)
        self.assertEqual(log.new_values, {'rotulo': '1º ano A'})

    def test_rename_to_an_existing_name_is_refused(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse('subjects_update', args=[self.free_subject.pk]), {'name': 'química'})
        self.assertContains(response, 'Já existe disciplina com este nome.')


class DeleteTests(AcademicTestCase):
    def test_superadmin_deletes_unused_records_and_audits(self):
        self.client.force_login(self.superadmin)
        self.client.post(reverse('subjects_delete', args=[self.free_subject.pk]))
        self.client.post(reverse('class_groups_delete', args=[self.free_group.pk]))
        self.assertFalse(Subject.objects.filter(pk=self.free_subject.pk).exists())
        self.assertFalse(ClassGroup.objects.filter(pk=self.free_group.pk).exists())
        log = AuditLog.objects.get(resource=catalog.CLASS_GROUP, action=catalog.DELETE)
        self.assertEqual(log.old_values, {'curso': 'Informática', 'rotulo': '1º ano'})
        self.assertTrue(AuditLog.objects.filter(resource=catalog.SUBJECT, action=catalog.DELETE).exists())

    def test_delete_of_a_record_with_lessons_is_refused(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse('subjects_delete', args=[self.physics.pk]), follow=True)
        self.assertContains(response, 'A disciplina Física tem ofertas ou aulas no ensalamento e não pode ser excluída.')
        self.assertTrue(Subject.objects.filter(pk=self.physics.pk).exists())
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SUBJECT, action=catalog.DELETE).exists())

    def test_delete_of_a_record_with_only_an_offering_is_refused(self):
        self.client.force_login(self.joao)
        self.client.post(reverse('subjects_delete', args=[self.chemistry.pk]))
        self.client.post(reverse('class_groups_delete', args=[self.second.pk]))
        self.assertTrue(Subject.objects.filter(pk=self.chemistry.pk).exists())
        self.assertTrue(ClassGroup.objects.filter(pk=self.second.pk).exists())

    def test_confirmation_is_shown_on_get(self):
        self.client.force_login(self.superadmin)
        self.assertContains(self.client.get(reverse('subjects_delete', args=[self.free_subject.pk])), 'Excluir Robótica?')

    def test_delete_action_only_for_unused_records(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse('subjects_list'))
        self.assertContains(response, reverse('subjects_delete', args=[self.free_subject.pk]))
        self.assertNotContains(response, reverse('subjects_delete', args=[self.math.pk]))


class ImportRegressionTests(AcademicTestCase):
    def test_import_reuses_a_manually_registered_subject(self):
        subject = Subject.objects.register('Robótica Educacional')
        allocation = allocate(self.semester, self.free_group, 'robótica educacional', Weekday.FRIDAY, time(7, 20), time(8, 10), teachers=['joao'])
        self.assertEqual(allocation.subject, subject)
        offering = ClassOffering.objects.record(self.semester, subject, self.free_group)
        self.assertTrue(offering.assignments.get(teacher__name='joao').is_current)

    def test_import_keeps_the_historic_link_and_makes_it_current(self):
        allocate(self.semester, self.second, 'Química', Weekday.FRIDAY, time(7, 20), time(8, 10), teachers=['joao'])
        offering = ClassOffering.objects.record(self.semester, self.chemistry, self.second)
        self.assertEqual(offering.assignments.count(), 1)
        self.assertTrue(offering.assignments.get().is_current)

    def test_manual_registration_offers_nothing_to_the_agenda(self):
        Subject.objects.register('Artes')
        ClassGroup.objects.register(self.agro, '6º período')
        teacher = Teacher.objects.get(name='joao')
        subjects = {item.offering.subject.name for item in TeachingAssignment.objects.available(self.semester, teacher)}
        self.assertEqual(subjects, {'Matemática'})
        self.assertEqual(Allocation.objects.count(), 2)
