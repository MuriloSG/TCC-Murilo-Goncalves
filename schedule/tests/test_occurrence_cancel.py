"""Cancelamento de uma ocorrência do ensalamento (Change cancelar-ocorrencia-do-ensalamento)."""

import re
from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts import permissions
from accounts.models import Role, User
from audit import catalog
from audit.models import AuditLog
from bookings.occupancy import find_conflict
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


class CancelTestCase(TestCase):
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
    def test_cancels_each_allocation_of_the_block_on_the_date(self):
        created = self.cancel(self.viviane)
        self.assertEqual(len(created), 2)
        self.assertEqual({(item.allocation_id, item.date, item.kind) for item in created}, {
            (self.first.pk, MONDAY, AllocationException.Kind.CANCELLED),
            (self.second.pk, MONDAY, AllocationException.Kind.CANCELLED),
        })
        self.assertEqual({item.created_by for item in created}, {self.viviane})

    def test_the_weekly_rule_is_untouched(self):
        before = Allocation.objects.filter(pk=self.first.pk).values().get()
        self.cancel(self.viviane)
        self.assertEqual(Allocation.objects.filter(pk=self.first.pk).values().get(), before)
        self.assertEqual([teacher.name for teacher in self.first.teachers.all()], ['Viviane'])

    def test_occurs_on(self):
        self.assertTrue(self.first.occurs_on(MONDAY))
        self.assertFalse(self.first.occurs_on(date(2026, 9, 29)))
        self.assertFalse(self.first.occurs_on(date(2026, 7, 27)))
        self.assertFalse(self.first.occurs_on(date(2026, 12, 21)))
        self.assertFalse(self.first.occurs_on(date(2026, 10, 3)))

    def test_refuses_dates_that_are_not_occurrences(self):
        for day in (date(2026, 9, 29), date(2026, 7, 27), date(2026, 12, 21), date(2026, 10, 3)):
            with self.subTest(day), self.assertRaises(ValidationError):
                self.cancel(self.viviane, day)
        self.assertFalse(AllocationException.objects.exists())

    def test_refuses_the_same_occurrence_twice(self):
        self.cancel(self.viviane)
        with self.assertRaisesMessage(ValidationError, 'A ocorrência de 28/09/2026 já está cancelada.'):
            self.cancel(self.manager)
        with self.assertRaises(ValidationError):
            self.cancel(self.manager, MONDAY, self.second)
        self.assertEqual(AllocationException.objects.count(), 2)

    def test_refuses_a_missing_allocation(self):
        with self.assertRaises(ValidationError):
            AllocationException.objects.cancel([self.first.pk, 999999], MONDAY, self.viviane)
        self.assertFalse(AllocationException.objects.exists())

    def test_refusal_of_one_allocation_cancels_none(self):
        with self.assertRaises(ValidationError):
            AllocationException.objects.cancel([self.first.pk, self.other.pk], MONDAY, self.manager)
        self.assertFalse(AllocationException.objects.exists())


class AuthorizationTests(CancelTestCase):
    def test_teacher_of_the_lesson_cancels_without_the_permission(self):
        self.assertEqual(len(self.cancel(self.viviane)), 2)

    def test_teacher_of_another_lesson_cannot_cancel(self):
        with self.assertRaises(ValidationError):
            self.cancel(self.erica)

    def test_permission_cancels_any_lesson(self):
        self.cancel(self.manager)
        self.cancel(self.manager, date(2026, 9, 29), self.other)
        self.assertEqual(AllocationException.objects.count(), 3)

    def test_superadmin_cancels_any_lesson(self):
        self.assertEqual(len(self.cancel(self.superadmin)), 2)

    def test_user_without_link_or_permission_cannot_cancel(self):
        for user in (self.plain, self.outsider):
            with self.subTest(user=user.email), self.assertRaises(ValidationError):
                self.cancel(user)

    def test_lesson_without_teacher_only_with_the_permission(self):
        lonely = allocate(self.semester, self.group, 'Estágio', Weekday.MONDAY, time(14, 0), time(15, 0), 'Sala 5')
        for user in (self.viviane, self.plain):
            with self.subTest(user=user.email), self.assertRaises(ValidationError):
                self.cancel(user, MONDAY, lonely)
        self.assertEqual(len(self.cancel(self.manager, MONDAY, lonely)), 1)

    def test_inactive_teacher_cannot_cancel(self):
        User.objects.filter(pk=self.viviane.pk).update(is_active=False)
        self.viviane.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.cancel(self.viviane)


class CancelViewTests(CancelTestCase):
    def test_anonymous_goes_to_login(self):
        url = self.cancel_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('account_login')))

    def test_without_the_module_permission_is_403(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.cancel_url()).status_code, 403)
        self.assertEqual(self.client.post(self.cancel_url()).status_code, 403)

    def test_confirmation_names_the_date_and_keeps_the_recurrence(self):
        self.client.force_login(self.viviane)
        response = self.client.get(self.cancel_url())
        self.assertEqual(response.status_code, 200)
        text = self.text(response)
        self.assertIn('Cancelar a ocorrência de 28/09/2026?', text)
        self.assertIn('das 10:00 às 12:00 em Sala 5', text)
        self.assertIn('A recorrência continua normalmente nas próximas datas.', text)
        self.assertFalse(AllocationException.objects.exists())

    def test_teacher_cancels_by_post(self):
        self.client.force_login(self.viviane)
        response = self.client.post(self.cancel_url())
        self.assertRedirects(response, GRID, fetch_redirect_response=False)
        self.assertEqual(AllocationException.objects.filter(date=MONDAY).count(), 2)

    def test_htmx_keeps_the_grid_week(self):
        self.client.force_login(self.viviane)
        current = f'http://testserver{GRID}?semestre=2026/2&sala=Sala+5&semana=2026-09-28'
        response = self.client.post(self.cancel_url(), HTTP_HX_REQUEST='true', HTTP_HX_CURRENT_URL=current)
        self.assertEqual(response['HX-Redirect'], f'{GRID}?semestre=2026/2&sala=Sala+5&semana=2026-09-28')

    def test_other_teacher_gets_404_on_get_and_post(self):
        self.client.force_login(self.erica)
        self.assertEqual(self.client.get(self.cancel_url()).status_code, 404)
        self.assertEqual(self.client.post(self.cancel_url()).status_code, 404)
        self.assertFalse(AllocationException.objects.exists())

    def test_manipulated_parameters_get_404(self):
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

    def test_second_cancel_shows_the_refusal(self):
        self.cancel(self.viviane)
        self.client.force_login(self.manager)
        response = self.client.post(self.cancel_url(), follow=True)
        self.assertContains(response, 'A ocorrência de 28/09/2026 já está cancelada.')
        self.assertEqual(AllocationException.objects.count(), 2)

    def test_post_without_csrf_is_403(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.viviane)
        self.assertEqual(client.post(self.cancel_url()).status_code, 403)
        self.assertFalse(AllocationException.objects.exists())


class GridTests(CancelTestCase):
    def grid(self, user, **params):
        self.client.force_login(user)
        return self.client.get(GRID, {'semestre': '2026/2', 'sala': 'Sala 5', **params})

    def test_cancelled_occurrence_leaves_the_week(self):
        self.cancel(self.viviane)
        self.assertNotContains(self.grid(self.manager, semana='2026-09-28'), 'Cálculo III')
        self.assertContains(self.grid(self.manager, semana='2026-10-05'), 'Cálculo III')

    def test_cancelled_occurrence_leaves_the_month(self):
        self.cancel(self.viviane)
        found = occupancy(self.room, date(2026, 9, 1), date(2026, 9, 30))
        mondays = sorted({item.date for item in found if item.entry.subject == 'Cálculo III'})
        self.assertEqual(mondays, [date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21)])
        response = self.grid(self.viviane, visao='mes', mes='2026-09')
        self.assertContains(response, 'data=2026-09-21')
        self.assertNotContains(response, 'data=2026-09-28')

    def test_cancelled_occurrence_leaves_every_source_for_the_week(self):
        self.cancel(self.viviane)
        self.assertEqual([item for item in occupancy(self.room, MONDAY, MONDAY) if item.entry.subject == 'Cálculo III'], [])
        self.assertEqual(len([item for item in occupancy(self.room, NEXT_MONDAY, NEXT_MONDAY)]), 2)

    def test_the_block_action_carries_both_allocations(self):
        response = self.grid(self.viviane, semana='2026-09-28')
        self.assertContains(response, f'data=2026-09-28&amp;alocacao={self.first.pk}&amp;alocacao={self.second.pk}')
        self.assertContains(response, 'aria-label="Cancelar esta ocorrência"')

    def test_action_only_for_who_manages_the_lesson(self):
        viviane = self.grid(self.viviane, semana='2026-09-28').content.decode()
        self.assertIn(f'alocacao={self.first.pk}', viviane)
        self.assertNotIn(f'alocacao={self.other.pk}', viviane)
        self.assertNotContains(self.grid(self.plain, semana='2026-09-28'), 'Cancelar esta ocorrência')
        self.assertContains(self.grid(self.manager, semana='2026-09-28'), f'alocacao={self.other.pk}')

    def test_no_new_query_per_exception(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                self.grid(self.viviane, visao='mes', mes='2026-10')
            return len(queries)

        count()
        before = count()
        for day in (date(2026, 10, 5), date(2026, 10, 12), date(2026, 10, 19)):
            self.cancel(self.manager, day)
        self.cancel(self.manager, date(2026, 10, 6), self.other)
        self.assertEqual(count(), before)


class PublicCalendarTests(CancelTestCase):
    def test_cancelled_occurrence_is_absent_for_visitors(self):
        self.cancel(self.viviane)
        week = self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-09-28', 'fim': '2026-10-02'})
        self.assertEqual(week.status_code, 200)
        self.assertNotContains(week, 'Cálculo III')
        self.assertContains(week, 'Física')
        following = self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-10-05', 'fim': '2026-10-09'})
        self.assertContains(following, 'Cálculo III')

    def test_teacher_filter_also_hides_it(self):
        self.cancel(self.viviane)
        week = self.client.get(PUBLIC, {'docente': 'Viviane', 'inicio': '2026-09-28', 'fim': '2026-10-02'})
        self.assertNotContains(week, 'Cálculo III')

    def test_exception_is_not_exposed(self):
        self.cancel(self.viviane)
        text = self.text(self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-09-28', 'fim': '2026-10-02'})).casefold()
        for word in ('cancelad', 'exceç', 'ocorrência'):
            self.assertNotIn(word, text)


class AgendaTests(CancelTestCase):
    def test_cancelled_occurrence_frees_the_space(self):
        self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.cancel(self.viviane)
        self.assertIsNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))

    def test_other_occurrences_keep_blocking(self):
        self.cancel(self.viviane)
        self.assertIsNotNone(find_conflict(self.room, NEXT_MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.room, date(2026, 9, 29), time(10, 0), time(11, 0)))

    def test_cancelling_one_slot_keeps_the_other(self):
        self.cancel(self.viviane, MONDAY, self.first)
        self.assertIsNone(find_conflict(self.room, MONDAY, time(10, 0), time(11, 0)))
        self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))


class ExceptionListTests(CancelTestCase):
    def setUp(self):
        self.cancel(self.viviane)
        self.cancel(self.manager, date(2026, 9, 29), self.other)

    def list_of(self, user):
        self.client.force_login(user)
        return self.client.get(LIST)

    def test_without_the_module_permission_is_403(self):
        self.assertEqual(self.list_of(self.outsider).status_code, 403)

    def test_anonymous_goes_to_login(self):
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, 302)

    def test_permission_sees_every_exception(self):
        response = self.list_of(self.manager)
        self.assertEqual(response.context['page'].paginator.count, 3)
        text = self.text(response)
        self.assertIn('28/09/2026, das 10:00 às 11:00', text)
        self.assertIn('29/09/2026, das 10:00 às 11:00', text)
        self.assertIn('Cancelada', text)
        self.assertIn('Cálculo III', text)
        self.assertIn('Sala 5', text)
        self.assertIn('Segunda-feira, 10:00 - 11:00, semestre 2026/2', text)
        self.assertIn(self.viviane.name, text)

    def test_teacher_sees_only_the_own_lessons(self):
        response = self.list_of(self.viviane)
        self.assertEqual(response.context['page'].paginator.count, 2)
        self.assertNotContains(response, 'Física')

    def test_user_without_lessons_sees_none(self):
        response = self.list_of(self.plain)
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertContains(response, 'Nenhuma exceção registrada.')

    def test_old_exceptions_stay_listed(self):
        AllocationException.objects.cancel([self.first.pk], date(2026, 8, 3), self.manager)
        self.assertContains(self.list_of(self.manager), '03/08/2026')

    def test_grid_links_to_the_list(self):
        self.client.force_login(self.plain)
        self.assertContains(self.client.get(GRID), LIST)


class AuditTests(CancelTestCase):
    def test_each_cancelled_allocation_is_audited(self):
        created = self.cancel(self.viviane)
        logs = AuditLog.objects.filter(action=catalog.CANCEL, resource=catalog.SPACE_ALLOCATION_EXCEPTION).order_by('pk')
        self.assertEqual(len(logs), 2)
        for log, exception in zip(logs, created):
            self.assertEqual(log.resource_id, str(exception.pk))
            self.assertEqual(log.new_values, {'tipo': 'CANCELADA', 'data': '2026-09-28'})
            self.assertEqual(log.metadata['alocacao'], exception.allocation_id)
            self.assertEqual(log.metadata['disciplina'], 'Cálculo III')
            self.assertEqual(log.metadata['espaco'], 'Sala 5')
            self.assertEqual(log.metadata['docentes'], ['Viviane'])

    def test_view_records_the_user(self):
        self.client.force_login(self.viviane)
        self.client.post(self.cancel_url())
        users = set(AuditLog.objects.filter(action=catalog.CANCEL).values_list('user', flat=True))
        self.assertEqual(users, {self.viviane.pk})

    def test_refusal_is_not_audited(self):
        with self.assertRaises(ValidationError):
            self.cancel(self.erica)
        self.client.force_login(self.erica)
        self.client.post(self.cancel_url())
        self.assertFalse(AuditLog.objects.filter(action=catalog.CANCEL).exists())


class ReimportTests(CancelTestCase):
    def test_exception_survives_a_new_import_of_the_same_lesson(self):
        self.cancel(self.viviane)
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

    def test_unchanged_import_keeps_the_exception(self):
        self.cancel(self.viviane)
        _, action, _ = Allocation.objects.apply(
            self.semester, self.group, self.first.subject, Weekday.MONDAY, self.first.time_slot,
            space=self.room, teachers=list(self.first.teachers.all()),
        )
        self.assertEqual(action, 'unchanged')
        self.assertEqual(AllocationException.objects.count(), 2)


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

    def test_agenda_shows_the_action_only_on_the_own_lessons(self):
        page = self.agenda(self.teacher).content.decode()
        self.assertIn(f'{reverse("agenda_occurrence_cancel")}?data=2026-09-28&amp;alocacao={self.first.pk}', page)
        self.assertNotIn(f'alocacao={self.other.pk}', page)
        self.assertNotContains(self.agenda(self.colleague), 'Cancelar esta ocorrência')

    def test_teacher_cancels_by_the_agenda(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.agenda_cancel_url()).status_code, 200)
        response = self.client.post(self.agenda_cancel_url())
        self.assertRedirects(response, reverse('agenda_grid'), fetch_redirect_response=False)
        self.assertEqual(AllocationException.objects.filter(date=MONDAY).count(), 2)
        self.assertNotContains(self.agenda(self.teacher), 'Cálculo III')

    def test_view_refuses_a_lesson_of_another_teacher(self):
        self.client.force_login(self.colleague)
        url = self.agenda_cancel_url()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertFalse(AllocationException.objects.exists())

    def test_view_refuses_mixing_own_and_other_lessons(self):
        self.client.force_login(self.teacher)
        url = self.agenda_cancel_url(self.first, self.other)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertFalse(AllocationException.objects.exists())

    def test_agenda_route_requires_the_agenda_permission(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(self.agenda_cancel_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse('agenda_exception_list')).status_code, 403)

    def test_ensalamento_route_stays_closed_to_the_agenda_teacher(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.cancel_url()).status_code, 403)
        self.assertFalse(AllocationException.objects.exists())

    def test_agenda_list_shows_only_the_own_exceptions(self):
        self.cancel(self.teacher)
        self.cancel(self.manager, date(2026, 9, 29), self.other)
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('agenda_exception_list'))
        self.assertEqual(response.context['page'].paginator.count, 2)
        self.assertNotContains(response, 'Física')
        self.assertContains(self.agenda(self.teacher), reverse('agenda_exception_list'))
