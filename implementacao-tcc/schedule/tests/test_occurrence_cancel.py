"""Cancelamento de uma ocorrência do ensalamento."""

import re
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from bookings.occupancy import find_conflict
from config.testing import IsolatedCasesMixin
from schedule.models import Allocation, AllocationException, ClassGroup, Course, Semester, Space, Stage, Teacher, Weekday
from schedule.occupancy import occupancy
from schedule.tests.test_timetable import allocate

MONDAY = date(2026, 9, 28)
NEXT_MONDAY = date(2026, 10, 5)
GRID = reverse('space_allocation_grid')
CANCEL = reverse('space_allocation_occurrence_cancel')
LIST = reverse('space_allocation_exception_list')
PUBLIC = reverse('public_calendar')


def user_with(email, username, *codes):
    code = email.partition('@')[0].upper().replace('.', '_')
    role = Role.objects.create_role(code=code, name=code.capitalize(), permissions=codes)
    return User.objects.register(email=email, name=code.capitalize(), role=role, username=username)


class CancelTestCase(IsolatedCasesMixin, TestCase):
    """Aula de Cálculo às segundas, das 10:00 às 12:00 em duas faixas, e Física às terças."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        cls.first = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(10, 0), time(11, 0), 'Sala 5', ['Viviane'])
        cls.second = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(11, 0), time(12, 0), 'Sala 5', ['Viviane'])
        cls.other = allocate(cls.semester, cls.group, 'Física', Weekday.TUESDAY, time(10, 0), time(11, 0), 'Sala 5', ['Érica'])
        cls.room = Space.objects.get(name='Sala 5')
        view = permissions.SPACE_ALLOCATION_VIEW
        cls.viviane = user_with('viviane@ifnmg.edu.br', 'VIVIANE', view)
        cls.erica = user_with('erica@ifnmg.edu.br', 'Érica', view)
        cls.manager = user_with('gestor@ifnmg.edu.br', 'gestor', view, permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE)
        cls.plain = user_with('leitor@ifnmg.edu.br', 'leitor', view)
        cls.outsider = user_with('fora@ifnmg.edu.br', 'Viviane Fora')
        cls.superadmin = user_with('super@ifnmg.edu.br', 'super')
        User.objects.filter(pk=cls.superadmin.pk).update(is_superadmin=True)
        cls.superadmin.refresh_from_db()

    def cancel_url(self, day=MONDAY, *allocations):
        allocations = allocations or (self.first, self.second)
        ids = '&'.join(f'alocacao={allocation.pk}' for allocation in allocations)
        return f'{CANCEL}?data={day.isoformat()}&{ids}'

    def cancel(self, user, day=MONDAY, *allocations):
        allocations = allocations or (self.first, self.second)
        return AllocationException.objects.cancel([allocation.pk for allocation in allocations], day, user)

    def text(self, response):
        return re.sub(r'\s+', ' ', response.content.decode())


class ModelTests(CancelTestCase):
    def test_cancels_each_allocation_of_the_block_keeping_the_rule(self):
        before = Allocation.objects.filter(pk=self.first.pk).values().get()
        created = self.cancel(self.viviane)
        self.assertEqual({(item.allocation_id, item.date, item.kind, item.created_by) for item in created}, {
            (self.first.pk, MONDAY, AllocationException.Kind.CANCELLED, self.viviane),
            (self.second.pk, MONDAY, AllocationException.Kind.CANCELLED, self.viviane),
        })
        self.assertEqual(Allocation.objects.filter(pk=self.first.pk).values().get(), before)
        self.assertEqual([teacher.name for teacher in self.first.teachers.all()], ['Viviane'])
        logs = AuditLog.objects.filter(action=catalog.CANCEL, resource=catalog.SPACE_ALLOCATION_EXCEPTION).order_by('pk')
        self.assertEqual(len(logs), 2)
        for log, exception in zip(logs, created):
            self.assertEqual(log.resource_id, str(exception.pk))
            self.assertEqual(log.new_values, {'tipo': 'CANCELADA', 'data': '2026-09-28'})
            self.assertEqual(
                {key: log.metadata[key] for key in ('alocacao', 'disciplina', 'espaco', 'docentes')},
                {'alocacao': exception.allocation_id, 'disciplina': 'Cálculo III', 'espaco': 'Sala 5', 'docentes': ['Viviane']},
            )

    def test_invalid_cancellation_is_refused_and_records_nothing(self):
        for day in (date(2026, 9, 29), date(2026, 7, 27), date(2026, 12, 21), date(2026, 10, 3)):
            with self.subTest(day), self.assertRaises(ValidationError):
                self.cancel(self.viviane, day)
        for label, ids in (('alocação inexistente', [self.first.pk, 999999]), ('uma das alocações recusada', [self.first.pk, self.other.pk])):
            with self.subTest(label), self.assertRaises(ValidationError):
                AllocationException.objects.cancel(ids, MONDAY, self.manager)
        self.assertFalse(AllocationException.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action=catalog.CANCEL).exists())
        self.cancel(self.viviane)
        with self.assertRaisesMessage(ValidationError, 'A ocorrência de 28/09/2026 já está cancelada.'):
            self.cancel(self.manager)
        with self.assertRaises(ValidationError):
            self.cancel(self.manager, MONDAY, self.second)
        self.assertEqual(AllocationException.objects.count(), 2)


class AuthorizationTests(CancelTestCase):
    def test_teacher_of_the_lesson_or_the_permission_cancels(self):
        lonely = allocate(self.semester, self.group, 'Estágio', Weekday.MONDAY, time(14, 0), time(15, 0), 'Sala 5')
        allowed = [
            ('docente da aula', self.viviane, (MONDAY,)),
            ('permissão, aula de outro docente', self.manager, (date(2026, 9, 29), self.other)),
            ('permissão, aula sem docente', self.manager, (MONDAY, lonely)),
            ('superadmin', self.superadmin, (MONDAY,)),
        ]
        for label, user, args in allowed:
            with self.case(label):
                self.assertTrue(self.cancel(user, *args))
        refused = [
            ('docente de outra aula', self.erica, (MONDAY,)),
            ('sem vínculo nem permissão', self.plain, (MONDAY,)),
            ('sem perfil', self.outsider, (MONDAY,)),
            ('docente, aula sem docente', self.viviane, (MONDAY, lonely)),
        ]
        for label, user, args in refused:
            with self.case(label), self.assertRaises(ValidationError):
                self.cancel(user, *args)
        User.objects.filter(pk=self.viviane.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.cancel(User.objects.get(pk=self.viviane.pk))


class CancelViewTests(CancelTestCase):
    def test_confirmation_then_cancel_by_post(self):
        self.client.force_login(self.viviane)
        response = self.client.get(self.cancel_url())
        self.assertEqual(response.status_code, 200)
        text = self.text(response)
        for expected in (
            'Cancelar a ocorrência de 28/09/2026?', 'das 10:00 às 12:00 em Sala 5', 'A recorrência continua normalmente nas próximas datas.',
        ):
            self.assertIn(expected, text)
        self.assertFalse(AllocationException.objects.exists())
        with self.case('htmx mantém a semana da grade'):
            current = f'http://testserver{GRID}?semestre=2026/2&sala=Sala+5&semana=2026-09-28'
            response = self.client.post(self.cancel_url(), HTTP_HX_REQUEST='true', HTTP_HX_CURRENT_URL=current)
            self.assertEqual(response['HX-Redirect'], f'{GRID}?semestre=2026/2&sala=Sala+5&semana=2026-09-28')
        response = self.client.post(self.cancel_url())
        self.assertRedirects(response, GRID, fetch_redirect_response=False)
        self.assertEqual(AllocationException.objects.filter(date=MONDAY).count(), 2)
        self.assertEqual(set(AuditLog.objects.filter(action=catalog.CANCEL).values_list('user', flat=True)), {self.viviane.pk})
        self.client.force_login(self.manager)
        response = self.client.post(self.cancel_url(), follow=True)
        self.assertContains(response, 'A ocorrência de 28/09/2026 já está cancelada.')
        self.assertEqual(AllocationException.objects.count(), 2)

    def test_lesson_of_another_teacher_and_manipulated_parameters_get_404(self):
        self.client.force_login(self.erica)
        self.assertEqual(self.client.get(self.cancel_url()).status_code, 404)
        self.assertEqual(self.client.post(self.cancel_url()).status_code, 404)
        self.client.force_login(self.manager)
        for url in (
            f'{CANCEL}?data=2026-09-28',
            f'{CANCEL}?data=28/09/2026&alocacao={self.first.pk}',
            f'{CANCEL}?data=2026-09-28&alocacao=abc',
            f'{CANCEL}?data=2026-09-28&alocacao=999999',
            f'{CANCEL}?data=2026-09-28&alocacao={self.first.pk}&alocacao=999999',
            f'{CANCEL}?data=2026-09-29&alocacao={self.first.pk}',
            f'{CANCEL}?data=2026-12-21&alocacao={self.first.pk}',
            f'{CANCEL}?alocacao={self.first.pk}',
        ):
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertFalse(AllocationException.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action=catalog.CANCEL).exists())


class GridTests(CancelTestCase):
    def grid(self, user, **params):
        self.client.force_login(user)
        return self.client.get(GRID, {'semestre': '2026/2', 'sala': 'Sala 5', **params})

    def test_action_only_for_who_manages_the_lesson(self):
        response = self.grid(self.viviane, semana='2026-09-28')
        self.assertContains(response, f'data=2026-09-28&amp;alocacao={self.first.pk}&amp;alocacao={self.second.pk}')
        self.assertContains(response, 'aria-label="Cancelar esta ocorrência"')
        self.assertNotContains(response, f'alocacao={self.other.pk}')
        self.assertNotContains(self.grid(self.plain, semana='2026-09-28'), 'Cancelar esta ocorrência')
        self.assertContains(self.grid(self.manager, semana='2026-09-28'), f'alocacao={self.other.pk}')

    def test_cancelled_occurrence_leaves_the_grid_and_frees_the_space(self):
        with self.case('uma faixa do bloco'):
            self.cancel(self.viviane, MONDAY, self.first)
            self.assertIsNone(find_conflict(self.room, MONDAY, time(10, 0), time(11, 0)))
            self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.cancel(self.viviane)
        self.assertEqual([item for item in occupancy(self.room, MONDAY, MONDAY) if item.entry.subject == 'Cálculo III'], [])
        self.assertEqual(len(occupancy(self.room, NEXT_MONDAY, NEXT_MONDAY)), 2)
        self.assertIsNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.room, NEXT_MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.room, date(2026, 9, 29), time(10, 0), time(11, 0)))

    def test_exception_is_not_exposed_in_the_public_calendar(self):
        self.cancel(self.viviane)
        text = self.text(self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-09-28', 'fim': '2026-10-02'})).casefold()
        for word in ('cancelad', 'exceç', 'ocorrência'):
            self.assertNotIn(word, text)

    def test_exception_list_follows_who_manages_the_lesson(self):
        self.cancel(self.viviane)
        self.cancel(self.manager, date(2026, 9, 29), self.other)
        for user, count in ((self.manager, 3), (self.viviane, 2), (self.plain, 0)):
            with self.subTest(user.username):
                self.client.force_login(user)
                response = self.client.get(LIST)
                self.assertEqual(response.context['page'].paginator.count, count)
                if user == self.manager:
                    text = self.text(response)
                    self.assertIn('28/09/2026, das 10:00 às 11:00', text)
                    self.assertIn('29/09/2026, das 10:00 às 11:00', text)
                else:
                    self.assertNotContains(response, 'Física')


class ReimportTests(CancelTestCase):
    def test_exception_survives_a_new_import_of_the_same_lesson(self):
        self.cancel(self.viviane)
        with self.case('aula sem alteração'):
            _, action, _ = Allocation.objects.apply(
                self.semester, self.group, self.first.subject, Weekday.MONDAY, self.first.time_slot,
                space=self.room, teachers=list(self.first.teachers.all()),
            )
            self.assertEqual(action, 'unchanged')
            self.assertEqual(AllocationException.objects.count(), 2)
        new_room = Space.objects.register('Sala 9')
        teacher, _ = Teacher.objects.resolve('Otávio')
        allocation, action, _ = Allocation.objects.apply(
            self.semester, self.group, self.first.subject, Weekday.MONDAY, self.first.time_slot,
            space=new_room, teachers=[teacher],
        )
        self.assertEqual((allocation.pk, action), (self.first.pk, 'update'))
        self.assertTrue(AllocationException.objects.filter(allocation=self.first, date=MONDAY).exists())
        self.assertEqual([item for item in occupancy(new_room, MONDAY, MONDAY)], [])
        self.assertEqual(len(occupancy(new_room, NEXT_MONDAY, NEXT_MONDAY)), 1)


class AgendaScreenTests(CancelTestCase):
    """O docente cancela pela Grade da Agenda, sem acesso ao Ensalamento."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User.objects.filter(pk__in=[cls.viviane.pk, cls.erica.pk]).update(username=None)
        agenda = (permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST)
        cls.teacher = user_with('viviane.docente@ifnmg.edu.br', 'Viviane', *agenda)
        cls.colleague = user_with('erica.docente@ifnmg.edu.br', 'erica', *agenda)

    def agenda_cancel_url(self, *allocations):
        return self.cancel_url(MONDAY, *allocations).replace(CANCEL, reverse('agenda_occurrence_cancel'))

    def agenda(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('agenda_grid'), {'semestre': '2026/2', 'sala': 'Sala 5', 'semana': '2026-09-28'})

    def test_teacher_cancels_the_own_lessons_by_the_agenda(self):
        page = self.agenda(self.teacher).content.decode()
        self.assertIn(f'{reverse("agenda_occurrence_cancel")}?data=2026-09-28&amp;alocacao={self.first.pk}', page)
        self.assertNotIn(f'alocacao={self.other.pk}', page)
        self.assertNotContains(self.agenda(self.colleague), 'Cancelar esta ocorrência')
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.agenda_cancel_url()).status_code, 200)
        response = self.client.post(self.agenda_cancel_url())
        self.assertRedirects(response, reverse('agenda_grid'), fetch_redirect_response=False)
        self.assertEqual(AllocationException.objects.filter(date=MONDAY).count(), 2)
        self.assertNotContains(self.agenda(self.teacher), 'Cálculo III')

    def test_agenda_refuses_lessons_of_another_teacher(self):
        self.client.force_login(self.colleague)
        self.assertEqual(self.client.get(self.agenda_cancel_url()).status_code, 404)
        self.assertEqual(self.client.post(self.agenda_cancel_url()).status_code, 404)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.agenda_cancel_url(self.first, self.other)).status_code, 404)
        self.assertFalse(AllocationException.objects.exists())

    def test_agenda_list_shows_only_the_own_exceptions(self):
        self.cancel(self.teacher)
        self.cancel(self.manager, date(2026, 9, 29), self.other)
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('agenda_exception_list'))
        self.assertEqual(response.context['page'].paginator.count, 2)
        self.assertNotContains(response, 'Física')
        self.assertContains(self.agenda(self.teacher), reverse('agenda_exception_list'))
