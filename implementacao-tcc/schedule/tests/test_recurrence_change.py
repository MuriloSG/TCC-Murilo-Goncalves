"""Alteração da recorrência de uma aula a partir de uma data."""

import re
from datetime import date, datetime, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts import permissions
from accounts.models import User
from audit import catalog
from audit.models import AuditLog
from bookings.occupancy import find_conflict
from bookings.tests.base import submit
from config.testing import IsolatedCasesMixin
from schedule.models import Allocation, AllocationException, ClassGroup, ClassOffering, Course, Origin, Semester, Space, Stage, Teacher, Weekday
from schedule.occupancy import occupancy
from schedule.tests.test_occurrence_cancel import user_with
from schedule.tests.test_timetable import allocate

TODAY = date(2026, 9, 1)
MONDAY = date(2026, 9, 28)
CUT = date(2026, 10, 5)
AFTER = date(2026, 10, 12)
GRID = reverse('space_allocation_grid')
CHANGE = reverse('space_allocation_recurrence_change')


class RecurrenceTestCase(IsolatedCasesMixin, TestCase):
    """Cálculo III às segundas na Sala 5 em duas faixas, Química às segundas na Sala 7 e a Sala 9 livre."""

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
        for name, value in (('localdate', TODAY), ('now', timezone.make_aware(datetime.combine(TODAY, time(8, 0))))):
            patcher = mock.patch(f'django.utils.timezone.{name}', return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def change(self, user=None, cut=CUT, weekday=Weekday.MONDAY, start=time(10, 0), space=None, teachers=None, allocations=None, slot_count=None):
        allocations = allocations or (self.first, self.second)
        return Allocation.objects.change_recurrence(
            [allocation.pk for allocation in allocations],
            cut,
            user or self.superadmin,
            weekday,
            start,
            self.new_room if space is None else space,
            [self.viviane_teacher] if teachers is None else teachers,
            slot_count,
        )

    def versions_of(self, allocation):
        return Allocation.objects.filter(
            class_group=allocation.class_group, subject=allocation.subject, valid_from__isnull=False,
        ).order_by('time_slot__start_time')

    def url(self, day=CUT):
        return f'{CHANGE}?data={day.isoformat()}&alocacao={self.first.pk}&alocacao={self.second.pk}'

    def form_data(self, **overrides):
        return {
            'data': CUT.isoformat(), 'dia': Weekday.MONDAY, 'horario': '10:00', 'duracao': '2',
            'espaco': str(self.new_room.pk), 'docentes': [str(self.viviane_teacher.pk)], **overrides,
        }

    def lessons(self, space, start, end, subject='Cálculo III'):
        return sorted({item.date for item in occupancy(space, start, end) if item.entry.subject == subject})

    def text(self, response):
        return re.sub(r'\s+', ' ', response.content.decode())


class VersioningTests(RecurrenceTestCase):
    def test_change_ends_the_original_and_starts_a_version_with_the_same_data(self):
        plan = self.change()
        for allocation in (self.first, self.second):
            allocation.refresh_from_db()
            self.assertIsNone(allocation.valid_from)
            self.assertEqual(allocation.valid_until, date(2026, 10, 4))
            self.assertEqual(allocation.space, self.room)
        versions = [change.version for change in plan.changes]
        self.assertEqual([(version.valid_from, version.valid_until) for version in versions], [(CUT, None), (CUT, None)])
        self.assertEqual({version.space for version in versions}, {self.new_room})
        self.assertEqual(Allocation.objects.count(), 6)
        for allocation, change in zip((self.first, self.second), plan.changes):
            version = Allocation.objects.get(pk=change.version.pk)
            self.assertEqual(
                (version.semester, version.class_group, version.subject, version.weekday, version.time_slot),
                (allocation.semester, allocation.class_group, allocation.subject, allocation.weekday, allocation.time_slot),
            )
            self.assertEqual([teacher.name for teacher in version.teachers.all()], ['Viviane'])
            self.assertEqual(version.origin, Origin.MANUAL)

    def test_room_change_splits_the_history_without_duplicates(self):
        with self.case('troca de sala'):
            self.change()
            self.assertEqual(self.lessons(self.room, date(2026, 9, 21), date(2026, 10, 30)), [date(2026, 9, 21), MONDAY])
            self.assertEqual(
                self.lessons(self.new_room, date(2026, 9, 21), date(2026, 10, 30)),
                [CUT, AFTER, date(2026, 10, 19), date(2026, 10, 26)],
            )
        with self.case('mesma sala em outro horário'):
            self.change(space=self.room, start=time(8, 0))
            per_day = {}
            for item in occupancy(self.room, date(2026, 8, 3), date(2026, 12, 18)):
                if item.entry.subject == 'Cálculo III':
                    per_day.setdefault(item.date, []).append((item.start, item.end))
            self.assertEqual(per_day[MONDAY], [(time(10, 0), time(11, 0)), (time(11, 0), time(12, 0))])
            self.assertEqual(per_day[CUT], [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))])
            self.assertTrue(all(len(slots) == 2 for slots in per_day.values()))

    def test_time_teacher_and_weekday_changes(self):
        with self.case('horário move o bloco inteiro'):
            plan = self.change(start=time(8, 0))
            self.assertEqual(
                [(change.version.time_slot.start_time, change.version.time_slot.end_time) for change in plan.changes],
                [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))],
            )
            self.assertEqual(plan.after.text, 'Segunda-feira, das 08:00 às 10:00, Sala 9')
            self.assertEqual(plan.before.text, 'Segunda-feira, das 10:00 às 12:00, Sala 5')
        with self.case('docente'):
            plan = self.change(space=self.room, teachers=[self.otavio])
            version = Allocation.objects.get(pk=plan.changes[0].version.pk)
            self.assertEqual([teacher.name for teacher in version.teachers.all()], ['Otávio'])
            self.assertEqual([teacher.name for teacher in Allocation.objects.get(pk=self.first.pk).teachers.all()], ['Viviane'])
        with self.case('dia da semana'):
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
    def test_invalid_change_is_refused_and_leaves_nothing(self):
        offering = ClassOffering.objects.record(self.semester, self.first.subject, self.group)
        cases = [
            ('data passada', 'Escolha uma data a partir de hoje.', date(2026, 10, 10), {}),
            ('fora do semestre', 'está fora do período do semestre 2026/2', None, {'cut': date(2026, 12, 21)}),
            ('dia sem aula', 'A aula não acontece em 06/10/2026.', None, {'cut': date(2026, 10, 6)}),
            ('primeira data da recorrência', 'A recorrência começa em 03/08/2026.', date(2026, 7, 1), {'cut': date(2026, 8, 3)}),
            ('nada alterado', 'Altere ao menos um dado da recorrência.', None, {'space': self.room}),
            ('aulas misturadas', 'A aula informada não existe.', None, {'allocations': (self.first, self.chemistry[0])}),
            ('horário sem faixas seguintes', 'Escolha um horário do semestre.', None, {'start': time(11, 0)}),
            ('faixas além do semestre', 'Escolha um horário do semestre.', None, {'start': time(10, 0), 'slot_count': 3}),
            ('docente novo na data recusada', 'A recorrência começa em 03/08/2026.', date(2026, 7, 1), {'cut': date(2026, 8, 3), 'teachers': [self.otavio]}),
            ('sem permissão: quem cancela', 'Só quem tem permissão altera', None, {'user': self.canceller}),
            ('sem permissão: docente', 'Só quem tem permissão altera', None, {'user': self.viviane}),
        ]
        for label, message, today, kwargs in cases:
            with self.case(label):
                with mock.patch('django.utils.timezone.localdate', return_value=today or TODAY):
                    with self.assertRaisesMessage(ValidationError, message):
                        self.change(**kwargs)
                self.assertEqual(Allocation.objects.count(), 4)
                self.assertFalse(Allocation.objects.filter(valid_until__isnull=False).exists())
                self.assertFalse(AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION).exists())
                self.assertEqual([item.teacher.name for item in offering.assignments.select_related('teacher')], ['Viviane'])
        with self.case('alocação inexistente'), self.assertRaises(ValidationError):
            Allocation.objects.change_recurrence([self.first.pk, 999999], CUT, self.superadmin, Weekday.MONDAY, time(10, 0), self.new_room, [])
        with self.case('espaço desativado'):
            inactive = Space.objects.get(pk=self.new_room.pk)
            inactive.deactivate()
            with self.assertRaisesMessage(ValidationError, 'O espaço Sala 9 está desativado.'):
                self.change(space=inactive)
        with self.case('data depois de um fim anterior'):
            self.change()
            with self.assertRaisesMessage(ValidationError, 'A aula não acontece em 12/10/2026.'):
                Allocation.objects.change_recurrence([self.first.pk], AFTER, self.superadmin, Weekday.MONDAY, time(10, 0), self.lab, [])


class ConflictTests(RecurrenceTestCase):
    def test_conflicts_are_refused(self):
        with self.case('outra aula no espaço'):
            with self.assertRaisesMessage(
                ValidationError,
                'O espaço Sala 7 está ocupado pela aula de Química (Engenharia de Alimentos, 4º período) em 05/10/2026, das 08:00 às 09:00.',
            ):
                self.change(space=self.lab, start=time(8, 0))
        with self.case('agendamento aprovado'):
            submit(self.reviewer, self.new_room, AFTER, time(10, 30), time(11, 0)).approve(self.reviewer)
            with self.assertRaisesMessage(
                ValidationError, 'O espaço Sala 9 tem um agendamento aprovado em 12/10/2026, das 10:30 às 11:00.',
            ):
                self.change()
        with self.case('mesma disciplina da turma no horário'):
            allocate(self.semester, self.group, 'Cálculo III', Weekday.WEDNESDAY, time(10, 0), time(11, 0), 'Sala 7', ['Viviane'])
            with self.assertRaisesMessage(ValidationError, 'já tem Cálculo III neste horário deste dia'):
                self.change(weekday=Weekday.WEDNESDAY)

    def test_what_is_not_a_conflict_is_accepted(self):
        with self.case('turma conjunta'):
            allocate(self.semester, self.other_group, 'Cálculo III', Weekday.MONDAY, time(10, 0), time(11, 0), 'Sala 9', ['Viviane'])
            self.change()
            self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)
        with self.case('a própria regra antiga'):
            self.change(space=self.room, teachers=[self.otavio])
            self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)
        with self.case('agendamento em outro horário'):
            submit(self.reviewer, self.new_room, AFTER, time(14, 0), time(15, 0)).approve(self.reviewer)
            self.change()
            self.assertEqual(Allocation.objects.filter(valid_from=CUT).count(), 2)
        with self.case('ocorrências canceladas e encerradas'):
            chemistry = [item.pk for item in self.chemistry]
            Allocation.objects.filter(pk__in=chemistry).update(valid_until=AFTER)
            for day in (CUT, AFTER):
                AllocationException.objects.cancel(chemistry, day, self.superadmin)
            self.change(space=self.lab, start=time(8, 0))
            self.assertEqual(self.lessons(self.lab, CUT, date(2026, 10, 30)), [CUT, AFTER, date(2026, 10, 19), date(2026, 10, 26)])


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
        self.assertEqual(
            {key: record.metadata[key] for key in ('a_partir_de', 'vigente_ate', 'nova_alocacao', 'excecoes_transferidas', 'disciplina')},
            {
                'a_partir_de': '2026-10-05',
                'vigente_ate': '2026-10-04',
                'nova_alocacao': plan.changes[0].version.pk,
                'excecoes_transferidas': ['2026-10-12'],
                'disciplina': 'Cálculo III',
            },
        )
        moved = AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION_EXCEPTION, action=catalog.UPDATE)
        self.assertEqual(moved.count(), 2)


class ViewTests(RecurrenceTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.changer)

    def test_form_and_summary_step(self):
        text = self.text(self.client.get(self.url(), headers={'HX-Request': 'true'}))
        for expected in ('Alterar recorrência', 'A partir de', 'value="2026-10-05"', 'A partir das 08:00', '<option value="2" selected>2 faixas seguidas</option>'):
            self.assertIn(expected, text)
        response = self.client.post(self.url(), self.form_data(), headers={'HX-Request': 'true'})
        text = self.text(response)
        self.assertEqual(response.status_code, 200)
        for expected in (
            'Alterar a recorrência de Cálculo III?', 'Segunda-feira, das 10:00 às 12:00, Sala 5', '05/10/2026',
            'Segunda-feira, das 10:00 às 12:00, Sala 9', 'name="confirmar" value="1"',
        ):
            self.assertIn(expected, text)
        self.assertEqual(Allocation.objects.count(), 4)
        response = self.client.post(self.url(), self.form_data(espaco=str(self.lab.pk), horario='08:00'))
        self.assertContains(response, 'O espaço Sala 7 está ocupado pela aula de Química')
        self.assertNotContains(response, 'name="confirmar"')

    def test_confirmation_executes_and_returns_to_the_grid(self):
        with self.case('página inteira'):
            response = self.client.post(self.url(), self.form_data() | {'confirmar': '1'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('sala=Sala+9', response['Location'])
            self.assertIn('semana=2026-10-05', response['Location'])
            self.assertEqual(Allocation.objects.filter(valid_from=CUT, space=self.new_room).count(), 2)
            record = AuditLog.objects.get(resource=catalog.SPACE_ALLOCATION, resource_id=str(self.first.pk))
            self.assertEqual(record.user, self.changer)
        with self.case('htmx abre a sala nova'):
            response = self.client.post(
                self.url(), self.form_data() | {'confirmar': '1'},
                headers={'HX-Request': 'true', 'HX-Current-URL': 'http://testserver/ensalamento/?sala=Sala+5&semana=2026-10-05'},
            )
            self.assertIn('sala=Sala+9', response['HX-Redirect'])
        with self.case('duração enviada pelo formulário'):
            self.client.post(self.url(), self.form_data(horario='09:00', duracao='3', confirmar='1'))
            self.assertEqual(Allocation.objects.filter(subject=self.first.subject, valid_from=CUT).count(), 3)
        with self.case('recusa aparece no formulário'):
            response = self.client.post(self.url(), self.form_data(data='2026-10-06', confirmar='1'))
            self.assertContains(response, 'A aula não acontece em 06/10/2026.')
            self.assertEqual(Allocation.objects.count(), 4)

    def test_manipulated_parameters_get_404(self):
        for query in ('', '?data=2026-10-05', f'?data=2026-10-06&alocacao={self.first.pk}', '?data=x&alocacao=1', '?data=2026-10-05&alocacao=999999'):
            with self.subTest(query):
                self.assertEqual(self.client.get(f'{CHANGE}{query}').status_code, 404)


class GridTests(RecurrenceTestCase):
    def grid(self, user, sala='Sala 5', **params):
        self.client.force_login(user)
        return self.client.get(GRID, {'semestre': '2026/2', 'sala': sala, **params})

    def test_action_only_with_the_permission_and_on_future_dates(self):
        for user in (self.changer, self.superadmin):
            with self.subTest(user.username):
                self.assertContains(self.grid(user, semana='2026-10-05'), 'aria-label="Alterar recorrência"')
        for user in (self.canceller, self.viviane):
            with self.subTest(user.username):
                self.assertNotContains(self.grid(user, semana='2026-10-05'), 'Alterar recorrência')
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 7)):
            self.assertNotContains(self.grid(self.changer, semana='2026-10-05'), 'Alterar recorrência')


class AgendaTests(RecurrenceTestCase):
    def test_availability_follows_the_new_rule(self):
        self.change()
        self.assertIsNotNone(find_conflict(self.room, MONDAY, time(10, 0), time(12, 0)))
        self.assertIsNone(find_conflict(self.room, CUT, time(10, 0), time(12, 0)))
        self.assertIsNotNone(find_conflict(self.new_room, CUT, time(10, 0), time(12, 0)))
        self.assertIsNone(find_conflict(self.new_room, MONDAY, time(10, 0), time(12, 0)))


class ReimportTests(RecurrenceTestCase):
    def apply(self, allocation, space):
        return Allocation.objects.apply(
            self.semester, self.group, allocation.subject, allocation.weekday, allocation.time_slot,
            space=space, teachers=[self.viviane_teacher],
        )

    def test_reimport_does_not_rewrite_the_versions(self):
        with self.case('troca de sala'):
            self.change()
            before = list(Allocation.objects.order_by('pk').values())
            for space in (self.room, self.lab, self.new_room):
                allocation, action, changes = self.apply(self.first, space)
                self.assertEqual((action, changes), ('unchanged', {}), space.name)
                self.assertTrue(allocation.is_versioned)
            self.assertEqual(list(Allocation.objects.order_by('pk').values()), before)
        with self.case('troca de dia não recria a regra antiga'):
            self.change(weekday=Weekday.WEDNESDAY)
            count = Allocation.objects.count()
            self.assertEqual(self.apply(self.first, self.room)[1], 'unchanged')
            self.assertEqual(Allocation.objects.count(), count)
            self.assertEqual(self.lessons(self.room, CUT, CUT), [])


class AcademicLinkTests(RecurrenceTestCase):
    """A alteração da recorrência preserva os docentes da oferta."""

    def test_offering_teachers_survive_the_change(self):
        offering = ClassOffering.objects.record(self.semester, self.first.subject, self.group)
        with self.case('dia, horário e sala'):
            before = sorted(offering.assignments.values_list('pk', 'teacher', 'is_current'))
            self.change(weekday=Weekday.TUESDAY, start=time(8, 0))
            self.assertEqual(sorted(offering.assignments.values_list('pk', 'teacher', 'is_current')), before)
            self.assertEqual(ClassOffering.objects.filter(subject=self.first.subject, class_group=self.group).count(), 1)
        with self.case('docente trocado fica no histórico'):
            self.change(teachers=[self.otavio])
            self.assertEqual(
                {item.teacher.name: item.is_current for item in offering.assignments.select_related('teacher')},
                {'Viviane': False, 'Otávio': True},
            )


class DurationTests(RecurrenceTestCase):
    """A alteração aumenta ou diminui a quantidade de faixas seguidas da aula."""

    def active_slots(self, day):
        return sorted(
            (item.time_slot.start_time, item.time_slot.end_time)
            for item in Allocation.objects.filter(subject=self.first.subject)
            if item.occurs_on(day)
        )

    def test_duration_change_adds_or_ends_slots(self):
        with self.case('aula mais longa ganha uma alocação'):
            plan = self.change(start=time(9, 0), slot_count=3)
            self.assertEqual(self.active_slots(CUT), [(time(9, 0), time(10, 0)), (time(10, 0), time(11, 0)), (time(11, 0), time(12, 0))])
            self.assertEqual(self.active_slots(MONDAY), [(time(10, 0), time(11, 0)), (time(11, 0), time(12, 0))])
            self.assertEqual(plan.after.text, 'Segunda-feira, das 09:00 às 12:00, Sala 9')
            added = plan.changes[-1].version
            self.assertEqual(AuditLog.objects.filter(action=catalog.CREATE, resource=catalog.SPACE_ALLOCATION, resource_id=str(added.pk)).count(), 1)
        with self.case('aula mais curta encerra a faixa que sobra'):
            plan = self.change(slot_count=1)
            self.assertEqual(self.active_slots(CUT), [(time(10, 0), time(11, 0))])
            self.assertEqual(Allocation.objects.get(pk=self.second.pk).valid_until, date(2026, 10, 4))
            self.assertEqual(plan.after.text, 'Segunda-feira, das 10:00 às 11:00, Sala 9')
            record = AuditLog.objects.get(resource=catalog.SPACE_ALLOCATION, resource_id=str(self.second.pk))
            self.assertEqual(record.new_values, {'vigente_ate': '2026-10-04'})
        with self.case('só a duração conta como alteração'):
            self.assertEqual(len(self.change(space=self.room, slot_count=1).changes), 1)

    def test_extra_slot_keeps_the_cancelled_occurrences(self):
        AllocationException.objects.cancel([self.first.pk, self.second.pk], AFTER, self.superadmin)
        plan = self.change(start=time(9, 0), slot_count=3)
        added = plan.changes[-1].version
        self.assertEqual(list(added.exceptions.values_list('date', flat=True)), [AFTER])
        self.assertNotIn(AFTER, self.lessons(self.new_room, CUT, date(2026, 10, 31)))
