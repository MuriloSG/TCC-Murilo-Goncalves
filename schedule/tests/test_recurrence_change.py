"""Alteração da recorrência de uma aula a partir de uma data (Change alterar-recorrencia-do-ensalamento)."""

import re
from datetime import date, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts import permissions
from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from bookings.occupancy import find_conflict
from bookings.tests.base import submit
from schedule.imports import RECURRENCE_CHANGED, SpaceAllocationImport
from schedule.models import Allocation, AllocationException, ClassGroup, Course, Origin, Semester, Space, Stage, Teacher, Weekday
from schedule.occupancy import AllocationSource, occupancy
from schedule.tests.test_occurrence_cancel import user_with
from schedule.tests.test_timetable import allocate

TODAY = date(2026, 9, 1)
MONDAY = date(2026, 9, 28)
CUT = date(2026, 10, 5)
AFTER = date(2026, 10, 12)
GRID = reverse('space_allocation_grid')
CHANGE = reverse('space_allocation_recurrence_change')
PUBLIC = reverse('public_calendar')


class RecurrenceTestCase(TestCase):
    """Cálculo III às segundas, das 10:00 às 12:00 em duas faixas na Sala 5, e Química às
    segundas, das 08:00 às 10:00 na Sala 7. A Sala 9 está disponível."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        cls.other_group, _ = ClassGroup.objects.resolve(course, '4º PERÍODO')
        cls.first = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(10, 0), time(11, 0), 'Sala 5', ['Viviane'])
        cls.second = allocate(cls.semester, cls.group, 'Cálculo III', Weekday.MONDAY, time(11, 0), time(12, 0), 'Sala 5', ['Viviane'])
        cls.chemistry = [
            allocate(cls.semester, cls.other_group, 'Química', Weekday.MONDAY, time(8, 0), time(9, 0), 'Sala 7', ['Érica']),
            allocate(cls.semester, cls.other_group, 'Química', Weekday.MONDAY, time(9, 0), time(10, 0), 'Sala 7', ['Érica']),
        ]
        cls.room = Space.objects.get(name='Sala 5')
        cls.lab = Space.objects.get(name='Sala 7')
        cls.new_room = Space.objects.register('Sala 9')
        cls.viviane_teacher = Teacher.objects.get(name='Viviane')
        cls.otavio, _ = Teacher.objects.resolve('Otávio')
        view = permissions.SPACE_ALLOCATION_VIEW
        cls.changer = user_with('coord@ifnmg.edu.br', 'coord', view, permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE)
        cls.canceller = user_with('gestor@ifnmg.edu.br', 'gestor', view, permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE)
        cls.viviane = user_with('viviane@ifnmg.edu.br', 'VIVIANE', view)
        cls.reviewer = user_with(
            'analista@ifnmg.edu.br', 'analista', permissions.BOOKING_VIEW, permissions.BOOKING_REQUEST, permissions.BOOKING_REVIEW,
        )
        cls.superadmin = user_with('super@ifnmg.edu.br', 'super')
        User.objects.filter(pk=cls.superadmin.pk).update(is_superadmin=True)
        cls.superadmin.refresh_from_db()

    def setUp(self):
        patcher = mock.patch('django.utils.timezone.localdate', return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def change(self, user=None, cut=CUT, weekday=Weekday.MONDAY, start=time(10, 0), space=None, teachers=None, allocations=None):
        allocations = allocations or (self.first, self.second)
        return Allocation.objects.change_recurrence(
            [allocation.pk for allocation in allocations],
            cut,
            user or self.superadmin,
            weekday,
            start,
            self.new_room if space is None else space,
            [self.viviane_teacher] if teachers is None else teachers,
        )

    def versions_of(self, allocation):
        return Allocation.objects.filter(
            class_group=allocation.class_group, subject=allocation.subject, valid_from__isnull=False,
        ).order_by('time_slot__start_time')

    def url(self, day=CUT):
        return f'{CHANGE}?data={day.isoformat()}&alocacao={self.first.pk}&alocacao={self.second.pk}'

    def form_data(self, **overrides):
        return {
            'data': CUT.isoformat(), 'dia': Weekday.MONDAY, 'horario': '10:00',
            'espaco': str(self.new_room.pk), 'docentes': [str(self.viviane_teacher.pk)], **overrides,
        }

    def lessons(self, space, start, end, subject='Cálculo III'):
        return sorted({item.date for item in occupancy(space, start, end) if item.entry.subject == subject})

    def text(self, response):
        return re.sub(r'\s+', ' ', response.content.decode())


class VersioningTests(RecurrenceTestCase):
    def test_the_original_ends_the_day_before_and_the_new_one_starts_on_the_date(self):
        plan = self.change()
        for allocation in (self.first, self.second):
            allocation.refresh_from_db()
            self.assertIsNone(allocation.valid_from)
            self.assertEqual(allocation.valid_until, date(2026, 10, 4))
            self.assertEqual(allocation.space, self.room)
        versions = [change.version for change in plan.changes]
        self.assertEqual([version.valid_from for version in versions], [CUT, CUT])
        self.assertEqual([version.valid_until for version in versions], [None, None])
        self.assertEqual({version.space for version in versions}, {self.new_room})
        self.assertEqual(Allocation.objects.count(), 6)

    def test_unchanged_data_is_preserved(self):
        plan = self.change()
        for allocation, change in zip((self.first, self.second), plan.changes):
            version = Allocation.objects.get(pk=change.version.pk)
            self.assertEqual(
                (version.semester, version.class_group, version.subject, version.weekday, version.time_slot),
                (allocation.semester, allocation.class_group, allocation.subject, allocation.weekday, allocation.time_slot),
            )
            self.assertEqual([teacher.name for teacher in version.teachers.all()], ['Viviane'])
            self.assertEqual(version.origin, Origin.MANUAL)

    def test_room_change_splits_the_history(self):
        self.change()
        self.assertEqual(self.lessons(self.room, date(2026, 9, 21), date(2026, 10, 30)), [date(2026, 9, 21), MONDAY])
        self.assertEqual(
            self.lessons(self.new_room, date(2026, 9, 21), date(2026, 10, 30)),
            [CUT, AFTER, date(2026, 10, 19), date(2026, 10, 26)],
        )

    def test_no_duplicate_occurrence_on_any_date(self):
        self.change(space=self.room, start=time(8, 0))
        found = [item for item in occupancy(self.room, date(2026, 8, 3), date(2026, 12, 18)) if item.entry.subject == 'Cálculo III']
        per_day = {}
        for item in found:
            per_day.setdefault(item.date, []).append((item.start, item.end))
        self.assertEqual(per_day[MONDAY], [(time(10, 0), time(11, 0)), (time(11, 0), time(12, 0))])
        self.assertEqual(per_day[CUT], [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))])
        self.assertTrue(all(len(slots) == 2 for slots in per_day.values()))

    def test_time_change_moves_the_whole_block(self):
        plan = self.change(start=time(8, 0))
        self.assertEqual(
            [(change.version.time_slot.start_time, change.version.time_slot.end_time) for change in plan.changes],
            [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))],
        )
        self.assertEqual(plan.after.text, 'Segunda-feira, das 08:00 às 10:00, Sala 9')
        self.assertEqual(plan.before.text, 'Segunda-feira, das 10:00 às 12:00, Sala 5')

    def test_time_without_consecutive_slots_is_refused(self):
        with self.assertRaisesMessage(ValidationError, 'Escolha um horário do semestre.'):
            self.change(start=time(11, 0))

    def test_teacher_change(self):
        plan = self.change(space=self.room, teachers=[self.otavio])
        version = Allocation.objects.get(pk=plan.changes[0].version.pk)
        self.assertEqual([teacher.name for teacher in version.teachers.all()], ['Otávio'])
        self.first.refresh_from_db()
        self.assertEqual([teacher.name for teacher in self.first.teachers.all()], ['Viviane'])

    def test_weekday_change(self):
        self.change(weekday=Weekday.WEDNESDAY)
        self.assertEqual(self.lessons(self.new_room, CUT, date(2026, 10, 9)), [date(2026, 10, 7)])
        self.assertEqual(self.lessons(self.room, CUT, date(2026, 10, 9)), [])
        self.assertEqual(self.lessons(self.room, MONDAY, MONDAY), [MONDAY])

    def test_a_second_change_versions_the_new_rule(self):
        self.change()
        versions = list(self.versions_of(self.first))
        later = date(2026, 11, 2)
        Allocation.objects.change_recurrence([item.pk for item in versions], later, self.superadmin, Weekday.MONDAY, time(10, 0), self.room, [self.viviane_teacher])
        self.assertEqual(self.lessons(self.new_room, CUT, date(2026, 11, 30)), [CUT, AFTER, date(2026, 10, 19), date(2026, 10, 26)])
        self.assertEqual(self.lessons(self.room, CUT, date(2026, 11, 30)), [later, date(2026, 11, 9), date(2026, 11, 16), date(2026, 11, 23), date(2026, 11, 30)])


class ValidationTests(RecurrenceTestCase):
    def assert_refused(self, message, **kwargs):
        with self.assertRaisesMessage(ValidationError, message):
            self.change(**kwargs)
        self.assertEqual(Allocation.objects.count(), 4)
        self.assertFalse(Allocation.objects.filter(valid_until__isnull=False).exists())

    def test_past_date(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 10)):
            self.assert_refused('Escolha uma data a partir de hoje.')

    def test_date_outside_the_semester(self):
        self.assert_refused('está fora do período do semestre 2026/2', cut=date(2026, 12, 21))

    def test_date_that_is_not_an_occurrence(self):
        self.assert_refused('A aula não acontece em 06/10/2026.', cut=date(2026, 10, 6))

    def test_first_date_of_the_recurrence(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 7, 1)):
            self.assert_refused('A recorrência começa em 03/08/2026.', cut=date(2026, 8, 3))

    def test_nothing_changed(self):
        self.assert_refused('Altere ao menos um dado da recorrência.', space=self.room)

    def test_missing_allocation(self):
        with self.assertRaises(ValidationError):
            Allocation.objects.change_recurrence([self.first.pk, 999999], CUT, self.superadmin, Weekday.MONDAY, time(10, 0), self.new_room, [])

    def test_mixing_lessons_is_refused(self):
        with self.assertRaisesMessage(ValidationError, 'A aula informada não existe.'):
            self.change(allocations=(self.first, self.chemistry[0]))

    def test_inactive_space(self):
        self.new_room.deactivate()
        self.assert_refused('O espaço Sala 9 está desativado.')

    def test_date_after_a_previous_end(self):
        self.change()
        self.first.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, 'A aula não acontece em 12/10/2026.'):
            Allocation.objects.change_recurrence([self.first.pk], AFTER, self.superadmin, Weekday.MONDAY, time(10, 0), self.lab, [])


class PermissionTests(RecurrenceTestCase):
    def test_superadmin_changes(self):
        self.change(self.superadmin)
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_user_with_the_permission_changes(self):
        self.change(self.changer)
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_users_without_the_permission_cannot(self):
        for user in (self.canceller, self.viviane):
            with self.subTest(user.username), self.assertRaisesMessage(ValidationError, 'Só quem tem permissão altera'):
                self.change(user)
        self.assertEqual(Allocation.objects.count(), 4)


class ConflictTests(RecurrenceTestCase):
    def test_clash_with_another_lesson_is_refused(self):
        with self.assertRaisesMessage(
            ValidationError,
            'O espaço Sala 7 está ocupado pela aula de Química (Engenharia de Alimentos, 4º período) em 05/10/2026, das 08:00 às 09:00.',
        ):
            self.change(space=self.lab, start=time(8, 0))
        self.assertEqual(Allocation.objects.count(), 4)

    def test_joint_lesson_is_accepted(self):
        allocate(self.semester, self.other_group, 'Cálculo III', Weekday.MONDAY, time(10, 0), time(11, 0), 'Sala 9', ['Viviane'])
        self.change()
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_the_old_rule_itself_is_not_a_conflict(self):
        self.change(space=self.room, teachers=[self.otavio])
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_cancelled_and_ended_occurrences_do_not_conflict(self):
        chemistry = self.chemistry
        Allocation.objects.filter(pk__in=[item.pk for item in chemistry]).update(valid_until=AFTER)
        for day in (CUT, AFTER):
            AllocationException.objects.cancel([item.pk for item in chemistry], day, self.superadmin)
        self.change(space=self.lab, start=time(8, 0))
        self.assertEqual(self.lessons(self.lab, CUT, date(2026, 10, 30)), [CUT, AFTER, date(2026, 10, 19), date(2026, 10, 26)])

    def test_approved_booking_is_a_conflict(self):
        request = submit(self.reviewer, self.new_room, AFTER, time(10, 30), time(11, 0))
        request.approve(self.reviewer)
        with self.assertRaisesMessage(
            ValidationError, 'O espaço Sala 9 tem um agendamento aprovado em 12/10/2026, das 10:30 às 11:00.',
        ):
            self.change()
        self.assertEqual(Allocation.objects.count(), 4)

    def test_booking_on_another_time_is_not_a_conflict(self):
        request = submit(self.reviewer, self.new_room, AFTER, time(14, 0), time(15, 0))
        request.approve(self.reviewer)
        self.change()
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_same_lesson_twice_is_refused(self):
        allocate(self.semester, self.group, 'Cálculo III', Weekday.WEDNESDAY, time(10, 0), time(11, 0), 'Sala 7', ['Viviane'])
        with self.assertRaisesMessage(ValidationError, 'já tem Cálculo III neste horário deste dia'):
            self.change(weekday=Weekday.WEDNESDAY)


class ExceptionTests(RecurrenceTestCase):
    def cancel(self, day):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], day, self.superadmin)

    def test_exceptions_before_stay_and_after_move(self):
        self.cancel(MONDAY)
        self.cancel(AFTER)
        plan = self.change()
        self.assertEqual(plan.moved_dates, [AFTER])
        versions = {change.current.pk: change.version.pk for change in plan.changes}
        self.assertEqual(
            set(AllocationException.objects.filter(date=MONDAY).values_list('allocation_id', flat=True)),
            {self.first.pk, self.second.pk},
        )
        self.assertEqual(
            set(AllocationException.objects.filter(date=AFTER).values_list('allocation_id', flat=True)),
            set(versions.values()),
        )
        self.assertEqual(AllocationException.objects.count(), 4)
        self.assertEqual(self.lessons(self.room, MONDAY, MONDAY), [])
        self.assertEqual(self.lessons(self.new_room, CUT, date(2026, 10, 19)), [CUT, date(2026, 10, 19)])

    def test_exception_that_does_not_fit_the_new_rule_refuses(self):
        self.cancel(AFTER)
        with self.assertRaisesMessage(ValidationError, 'As ocorrências canceladas de 12/10/2026 não são datas da nova recorrência.'):
            self.change(weekday=Weekday.WEDNESDAY)
        self.assertEqual(set(AllocationException.objects.values_list('allocation_id', flat=True)), {self.first.pk, self.second.pk})

    def test_new_version_can_be_cancelled(self):
        plan = self.change()
        AllocationException.objects.cancel([change.version.pk for change in plan.changes], date(2026, 10, 19), self.superadmin)
        self.assertEqual(self.lessons(self.new_room, CUT, date(2026, 10, 26)), [CUT, AFTER, date(2026, 10, 26)])


class TransactionTests(RecurrenceTestCase):
    def test_failure_after_ending_the_rule_rolls_everything_back(self):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], AFTER, self.superadmin)
        with mock.patch.object(AuditLog.objects, 'record', side_effect=RuntimeError('falha')), self.assertRaises(RuntimeError):
            self.change()
        self.assertFalse(Allocation.objects.filter(valid_until__isnull=False).exists())
        self.assertEqual(Allocation.objects.count(), 4)
        self.assertEqual(
            set(AllocationException.objects.values_list('allocation_id', flat=True)), {self.first.pk, self.second.pk},
        )
        self.assertEqual(self.lessons(self.room, CUT, CUT), [CUT])


class AuditTests(RecurrenceTestCase):
    def test_each_allocation_is_audited_with_the_cut_and_the_new_one(self):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], AFTER, self.superadmin)
        plan = self.change()
        records = AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION).order_by('resource_id')
        self.assertEqual(len(records), 2)
        record = records.get(resource_id=str(self.first.pk))
        self.assertEqual(record.action, catalog.UPDATE)
        self.assertEqual(record.old_values, {'espaco': 'Sala 5'})
        self.assertEqual(record.new_values, {'espaco': 'Sala 9'})
        self.assertEqual(record.metadata['a_partir_de'], '2026-10-05')
        self.assertEqual(record.metadata['vigente_ate'], '2026-10-04')
        self.assertEqual(record.metadata['nova_alocacao'], plan.changes[0].version.pk)
        self.assertEqual(record.metadata['excecoes_transferidas'], ['2026-10-12'])
        self.assertEqual(record.metadata['disciplina'], 'Cálculo III')
        moved = AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION_EXCEPTION, action=catalog.UPDATE)
        self.assertEqual(moved.count(), 2)

    def test_refusal_is_not_audited(self):
        with self.assertRaises(ValidationError):
            self.change(space=self.room)
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION).exists())

    def test_view_records_the_user(self):
        self.client.force_login(self.changer)
        self.client.post(self.url(), self.form_data() | {'confirmar': '1'})
        record = AuditLog.objects.get(resource=catalog.SPACE_ALLOCATION, resource_id=str(self.first.pk))
        self.assertEqual(record.user, self.changer)



class ViewTests(RecurrenceTestCase):
    def test_anonymous_goes_to_login(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=', response['Location'])

    def test_without_the_permission_is_403(self):
        for user in (self.viviane, self.canceller):
            self.client.force_login(user)
            with self.subTest(user.username):
                self.assertEqual(self.client.get(self.url()).status_code, 403)
                self.assertEqual(self.client.post(self.url(), self.form_data() | {'confirmar': '1'}).status_code, 403)
        self.assertEqual(Allocation.objects.count(), 4)

    def test_form_explains_that_the_whole_recurrence_changes(self):
        self.client.force_login(self.changer)
        response = self.client.get(self.url(), headers={'HX-Request': 'true'})
        text = self.text(response)
        self.assertIn('Alterar recorrência', text)
        self.assertIn('As ocorrências anteriores permanecem no histórico.', text)
        self.assertIn('A partir de', text)
        self.assertIn('value="2026-10-05"', text)
        self.assertIn('Das 08:00 às 10:00', text)

    def test_first_post_shows_the_summary_without_saving(self):
        self.client.force_login(self.changer)
        response = self.client.post(self.url(), self.form_data(), headers={'HX-Request': 'true'})
        text = self.text(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Alterar a recorrência de Cálculo III?', text)
        self.assertIn('<dt>Antes</dt><dd>Segunda-feira, das 10:00 às 12:00, Sala 5', text)
        self.assertIn('<dt>A partir de</dt><dd>05/10/2026</dd>', text)
        self.assertIn('<dt>Depois</dt><dd>Segunda-feira, das 10:00 às 12:00, Sala 9', text)
        self.assertIn('name="confirmar" value="1"', text)
        self.assertEqual(Allocation.objects.count(), 4)

    def test_confirmation_executes_and_returns_to_the_grid(self):
        self.client.force_login(self.changer)
        response = self.client.post(self.url(), self.form_data() | {'confirmar': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('sala=Sala+9', response['Location'])
        self.assertIn('semana=2026-10-05', response['Location'])
        self.assertEqual(Allocation.objects.filter(valid_from=CUT, space=self.new_room).count(), 2)

    def test_htmx_confirmation_opens_the_new_room(self):
        self.client.force_login(self.changer)
        response = self.client.post(
            self.url(), self.form_data() | {'confirmar': '1'},
            headers={'HX-Request': 'true', 'HX-Current-URL': 'http://testserver/ensalamento/?sala=Sala+5&semana=2026-10-05'},
        )
        self.assertIn('sala=Sala+9', response['HX-Redirect'])

    def test_superadmin_executes(self):
        self.client.force_login(self.superadmin)
        self.client.post(self.url(), self.form_data() | {'confirmar': '1'})
        self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)

    def test_refusal_appears_in_the_form(self):
        self.client.force_login(self.changer)
        response = self.client.post(self.url(), self.form_data(data='2026-10-06', confirmar='1'))
        self.assertContains(response, 'A aula não acontece em 06/10/2026.')
        self.assertEqual(Allocation.objects.count(), 4)

    def test_conflict_appears_in_the_summary_step(self):
        self.client.force_login(self.changer)
        response = self.client.post(self.url(), self.form_data(espaco=str(self.lab.pk), horario='08:00'))
        self.assertContains(response, 'O espaço Sala 7 está ocupado pela aula de Química')
        self.assertNotContains(response, 'name="confirmar"')

    def test_manipulated_parameters_get_404(self):
        self.client.force_login(self.changer)
        for query in ('', '?data=2026-10-05', f'?data=2026-10-06&alocacao={self.first.pk}', '?data=x&alocacao=1', '?data=2026-10-05&alocacao=999999'):
            with self.subTest(query):
                self.assertEqual(self.client.get(f'{CHANGE}{query}').status_code, 404)

    def test_post_without_csrf_is_403(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.changer)
        self.assertEqual(client.post(self.url(), self.form_data() | {'confirmar': '1'}).status_code, 403)
        self.assertEqual(Allocation.objects.count(), 4)


class GridTests(RecurrenceTestCase):
    def grid(self, user, sala='Sala 5', **params):
        self.client.force_login(user)
        return self.client.get(GRID, {'semestre': '2026/2', 'sala': sala, **params})

    def test_action_only_for_who_has_the_permission(self):
        self.assertContains(self.grid(self.changer, semana='2026-10-05'), 'aria-label="Alterar recorrência"')
        self.assertContains(self.grid(self.superadmin, semana='2026-10-05'), 'aria-label="Alterar recorrência"')
        for user in (self.canceller, self.viviane):
            with self.subTest(user.username):
                self.assertNotContains(self.grid(user, semana='2026-10-05'), 'Alterar recorrência')

    def test_action_carries_the_block_and_the_date(self):
        response = self.grid(self.changer, semana='2026-10-05')
        self.assertContains(response, f'recorrencias/alterar/?data=2026-10-05&amp;alocacao={self.first.pk}&amp;alocacao={self.second.pk}')

    def test_no_action_on_past_dates(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 7)):
            response = self.grid(self.changer, semana='2026-10-05')
        self.assertNotContains(response, 'Alterar recorrência')

    def test_week_before_and_after_the_cut(self):
        self.change()
        self.assertContains(self.grid(self.changer, semana='2026-09-28'), 'Cálculo III')
        self.assertNotContains(self.grid(self.changer, semana='2026-10-05'), 'Cálculo III')
        self.assertContains(self.grid(self.changer, sala='Sala 9', semana='2026-10-05'), 'Cálculo III')
        self.assertNotContains(self.grid(self.changer, sala='Sala 9', semana='2026-09-28'), 'Cálculo III')

    def test_month_splits_on_the_cut(self):
        self.change()
        old = self.grid(self.changer, visao='mes', mes='2026-10').content.decode()
        self.assertNotIn('data=2026-10-05', old)
        new = self.grid(self.changer, sala='Sala 9', visao='mes', mes='2026-10').content.decode()
        for day in ('2026-10-05', '2026-10-12', '2026-10-19', '2026-10-26'):
            self.assertIn(f'data={day}', new)
        september = self.grid(self.changer, visao='mes', mes='2026-09').content.decode()
        self.assertIn('data=2026-09-28', september)

    def test_versioning_adds_no_query(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                AllocationSource().occurrences(self.room, date(2026, 8, 3), date(2026, 12, 18))
            return len(queries)

        before = count()
        self.change(space=self.room, start=time(8, 0))
        self.assertEqual(count(), before)


class PublicCalendarTests(RecurrenceTestCase):
    def test_room_before_and_after_the_cut(self):
        self.change()
        before = self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-09-28', 'fim': '2026-10-02'})
        self.assertContains(before, 'Cálculo III')
        after = self.client.get(PUBLIC, {'sala': 'Sala 5', 'inicio': '2026-10-05', 'fim': '2026-10-09'})
        self.assertNotContains(after, 'Cálculo III')
        moved = self.client.get(PUBLIC, {'sala': 'Sala 9', 'inicio': '2026-10-05', 'fim': '2026-10-09'})
        self.assertContains(moved, 'Cálculo III')

    def test_teacher_sees_one_lesson_per_date(self):
        self.change()
        text = self.text(self.client.get(PUBLIC, {'docente': 'Viviane', 'inicio': '2026-10-05', 'fim': '2026-10-09'}))
        grid = text[text.index('<table'):]
        self.assertEqual(grid.count('Cálculo III'), 1)
        self.assertIn('Sala 9', grid)
        self.assertNotIn('Sala 5', grid)

    def test_nothing_administrative_is_exposed(self):
        self.change()
        text = self.text(self.client.get(PUBLIC, {'sala': 'Sala 9', 'inicio': '2026-10-05', 'fim': '2026-10-09'})).casefold()
        for word in ('recorrência', 'vigente', 'super', 'alterad'):
            self.assertNotIn(word, text)


class AgendaTests(RecurrenceTestCase):
    def test_availability_follows_the_new_rule(self):
        self.change()
        self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNone(find_conflict(self.room, CUT, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.new_room, CUT, time(10, 0), time(12, 0)))
        self.assertIsNone(find_conflict(self.new_room, MONDAY, time(10, 0), time(12, 0)))

    def test_agenda_grid_follows_the_new_rule(self):
        self.change()
        self.client.force_login(self.reviewer)
        old = self.client.get(reverse('agenda_grid'), {'sala': 'Sala 5', 'semana': '2026-10-05'})
        new = self.client.get(reverse('agenda_grid'), {'sala': 'Sala 9', 'semana': '2026-10-05'})
        self.assertNotContains(old, 'Cálculo III')
        self.assertContains(new, 'Cálculo III')

    def test_booking_request_on_the_new_room_is_refused(self):
        self.change()
        with self.assertRaises(ValidationError):
            submit(self.reviewer, self.new_room, AFTER, time(10, 0), time(11, 0))
        submit(self.reviewer, self.room, AFTER, time(10, 0), time(11, 0))


class ReimportTests(RecurrenceTestCase):
    def apply(self, allocation, space):
        return Allocation.objects.apply(
            self.semester, self.group, allocation.subject, allocation.weekday, allocation.time_slot,
            space=space, teachers=[self.viviane_teacher],
        )

    def test_reimport_does_not_rewrite_the_versions(self):
        self.change()
        before = list(Allocation.objects.order_by('pk').values())
        for space in (self.room, self.lab, self.new_room):
            with self.subTest(space.name):
                allocation, action, changes = self.apply(self.first, space)
                self.assertEqual((action, changes), ('unchanged', {}))
                self.assertTrue(allocation.is_versioned)
        self.assertEqual(list(Allocation.objects.order_by('pk').values()), before)

    def test_reimport_does_not_recreate_the_old_rule_after_a_day_change(self):
        self.change(weekday=Weekday.WEDNESDAY)
        count = Allocation.objects.count()
        _, action, _ = self.apply(self.first, self.room)
        self.assertEqual(action, 'unchanged')
        self.assertEqual(Allocation.objects.count(), count)
        self.assertEqual(self.lessons(self.room, CUT, CUT), [])

    def test_the_import_row_warns_about_the_change(self):
        self.assertIn(RECURRENCE_CHANGED, SpaceAllocationImport.warning_labels)
        self.assertEqual(
            SpaceAllocationImport.warning_labels[RECURRENCE_CHANGED],
            'Esta aula teve a recorrência alterada no sistema e não foi atualizada pela planilha.',
        )

    def test_lesson_without_versions_still_updates(self):
        self.change()
        allocation, action, _ = Allocation.objects.apply(
            self.semester, self.other_group, self.chemistry[0].subject, Weekday.MONDAY, self.chemistry[0].time_slot,
            space=self.new_room, teachers=[],
        )
        self.assertEqual((allocation.pk, action), (self.chemistry[0].pk, 'update'))
