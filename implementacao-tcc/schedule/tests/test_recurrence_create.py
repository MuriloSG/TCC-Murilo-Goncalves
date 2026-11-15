"""Cadastro de uma aula recorrente pela interface."""

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
from bookings.tests.base import academic, submit
from config.testing import IsolatedCasesMixin
from schedule.models import Allocation, ClassGroup, ClassOffering, Course, Origin, Semester, Space, Stage, Subject, Teacher, TimeSlot, Weekday
from schedule.tests.test_occurrence_cancel import user_with
from schedule.tests.test_timetable import allocate

TODAY = date(2026, 9, 1)
TUESDAY = date(2026, 10, 6)
MONDAY = date(2026, 10, 5)
SATURDAY = date(2026, 10, 10)
GRID = reverse('space_allocation_grid')
CREATE = reverse('space_allocation_recurrence_create')
KEEP = object()


class CreateTestCase(IsolatedCasesMixin, TestCase):
    """Quatro faixas seguidas, Cálculo às terças das 10:00 às 12:00 na Sala 5 e a Sala 9 livre."""

    @classmethod
    def setUpTestData(cls):
        cls.semester, _ = Semester.objects.resolve('2026/2')
        cls.semester.define_period(date(2026, 8, 3), date(2026, 12, 18))
        course, _ = Course.objects.resolve('ENGENHARIA DE ALIMENTOS', stage=Stage.UNDERGRADUATE)
        cls.group, _ = ClassGroup.objects.resolve(course, '2º PERÍODO')
        cls.other_group, _ = ClassGroup.objects.resolve(course, '4º PERÍODO')
        cls.taken = [
            allocate(cls.semester, cls.other_group, 'Cálculo III', Weekday.TUESDAY, time(10, 0), time(11, 0), 'Sala 5', ['Viviane']),
            allocate(cls.semester, cls.other_group, 'Cálculo III', Weekday.TUESDAY, time(11, 0), time(12, 0), 'Sala 5', ['Viviane']),
        ]
        TimeSlot.objects.resolve(cls.semester, time(13, 20), time(14, 10))
        TimeSlot.objects.resolve(cls.semester, time(14, 10), time(15, 0))
        cls.room = Space.objects.get(name='Sala 5')
        cls.free_room = Space.objects.register('Sala 9')
        cls.chemistry, _ = Subject.objects.resolve('Química Orgânica')
        cls.calculus, _ = Subject.objects.resolve('Cálculo III')
        cls.erica, _ = Teacher.objects.resolve('Érica')
        cls.viviane = Teacher.objects.get(name='Viviane')
        view = permissions.SPACE_ALLOCATION_VIEW
        cls.creator = user_with('coord@ifnmg.edu.br', 'coord', view, permissions.SPACE_ALLOCATION_CREATE_RECURRENCE)
        cls.changer = user_with('gestor@ifnmg.edu.br', 'gestor', view, permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE)
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

    def create(self, user=None, start=TUESDAY, end=None, start_time=time(13, 20), count=1, space=KEEP, teachers=None, subject=None, group=None):
        return Allocation.objects.create_recurrence(
            self.semester,
            group or self.group,
            subject or self.chemistry,
            start,
            end,
            user or self.creator,
            start_time,
            count,
            self.free_room if space is KEEP else space,
            [self.erica] if teachers is None else teachers,
        )

    def created(self):
        return Allocation.objects.filter(origin=Origin.MANUAL).order_by('time_slot__start_time')

    def payload(self, **changes):
        data = {
            'turma': self.group.pk,
            'disciplina': self.chemistry.pk,
            'docentes': [self.erica.pk],
            'espaco': self.free_room.pk,
            'data': TUESDAY.isoformat(),
            'fim': '',
            'horario': '13:20',
            'duracao': '1',
        }
        return data | changes

    def url(self, **params):
        query = '&'.join(f'{key}={value}' for key, value in ({'semestre': '2026/2'} | params).items())
        return f'{CREATE}?{query}'


class CreateModelTests(CreateTestCase):
    def test_creates_one_allocation_per_slot_of_the_block(self):
        with self.case('uma faixa'):
            plan = self.create()
            allocation = self.created().get()
            self.assertEqual(
                (allocation.weekday, allocation.valid_from, allocation.valid_until, allocation.origin, allocation.space),
                (Weekday.TUESDAY, TUESDAY, None, Origin.MANUAL, self.free_room),
            )
            self.assertEqual(list(allocation.teachers.all()), [self.erica])
            self.assertEqual(plan.cut, TUESDAY)
        with self.case('bloco de duas faixas'):
            self.create(count=2)
            allocations = list(self.created())
            self.assertEqual([item.time_slot.start_time for item in allocations], [time(13, 20), time(14, 10)])
            self.assertEqual({item.valid_from for item in allocations}, {TUESDAY})
        with self.case('fim da vigência'):
            self.create(end=date(2026, 11, 3))
            self.assertEqual(self.created().get().valid_until, date(2026, 11, 3))
        with self.case('sem espaço'):
            self.create(space=None)
            self.assertIsNone(self.created().get().space)
        with self.case('superadmin sem a permissão no perfil'):
            self.assertFalse(self.superadmin.role.permissions.filter(code=permissions.SPACE_ALLOCATION_CREATE_RECURRENCE).exists())
            self.create(user=self.superadmin)
            self.assertTrue(self.created().exists())

    def test_invalid_creation_is_refused_with_the_reason(self):
        inactive = Space.objects.register('Sala 10')
        inactive.deactivate()
        cases = [
            ('Escolha um horário do semestre.', {'count': 4}),
            ('Escolha uma data a partir de hoje.', {'start': date(2026, 8, 25)}),
            ('A data 02/02/2027 está fora do período do semestre', {'start': date(2027, 2, 2)}),
            ('A aula acontece de segunda a sexta-feira.', {'start': SATURDAY}),
            ('A última aula não pode ser anterior à primeira.', {'end': date(2026, 9, 29)}),
            ('A data 05/01/2027 está fora do período do semestre', {'end': date(2027, 1, 5)}),
            ('O espaço Sala 10 está desativado.', {'space': inactive}),
            ('', {'user': self.changer}),
        ]
        for message, arguments in cases:
            with self.subTest(message or 'sem a permissão'), self.assertRaisesMessage(ValidationError, message):
                self.create(**arguments)
        self.assertFalse(self.created().exists())
        self.assertFalse(AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION).exists())

    def test_records_the_offering_and_the_audit(self):
        with self.case('uma faixa'):
            self.create()
            allocation = self.created().get()
            self.assertTrue(
                ClassOffering.objects.filter(semester=self.semester, subject=self.chemistry, class_group=self.group).exists(),
            )
            log = AuditLog.objects.get(resource=catalog.SPACE_ALLOCATION, action=catalog.CREATE)
            self.assertEqual(log.resource_id, str(allocation.pk))
            self.assertEqual((log.new_values['disciplina'], log.new_values['espaco']), ('Química Orgânica', 'Sala 9'))
            self.assertEqual((log.metadata['vigente_desde'], log.metadata['origem']), (TUESDAY.isoformat(), Origin.MANUAL))
        with self.case('as entradas do bloco apontam uma para a outra'):
            self.create(count=2)
            first, second = list(self.created())
            logs = {int(log.resource_id): log for log in AuditLog.objects.filter(resource=catalog.SPACE_ALLOCATION)}
            self.assertEqual(logs[first.pk].metadata['outras_alocacoes'], [second.pk])
            self.assertEqual(logs[second.pk].metadata['outras_alocacoes'], [first.pk])


class CreateConflictTests(CreateTestCase):
    def test_conflicts_are_refused(self):
        with self.case('espaço ocupado por outra aula'):
            with self.assertRaisesMessage(ValidationError, 'Cálculo III'):
                self.create(space=self.room, start_time=time(10, 0))
        with self.case('agendamento aprovado'):
            submit(
                user_with('erica@ifnmg.edu.br', 'Érica', permissions.BOOKING_REQUEST, permissions.BOOKING_VIEW),
                self.free_room, day=TUESDAY, start=time(13, 0), end=time(14, 0), assignment=academic(teacher='Érica'),
            ).approve(self.reviewer)
            with self.assertRaisesMessage(ValidationError, 'agendamento aprovado'):
                self.create()
        with self.case('mesma disciplina da turma na faixa'), self.assertRaises(ValidationError):
            self.create(group=self.other_group, subject=self.calculus, start_time=time(10, 0), teachers=[self.viviane], space=None)
        self.assertFalse(self.created().exists())

    def test_joint_group_and_conflict_outside_the_validity_are_accepted(self):
        with self.case('turma conjunta'):
            self.create(space=self.room, start_time=time(10, 0), subject=self.calculus, teachers=[self.viviane])
            self.assertTrue(self.created().exists())
        with self.case('conflito fora da vigência'):
            Allocation.objects.filter(pk__in=[item.pk for item in self.taken]).update(valid_until=date(2026, 9, 30))
            self.create(space=self.room, start_time=time(10, 0))
            self.assertTrue(self.created().exists())


class CreateScreenTests(CreateTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.creator)

    def test_form_summary_and_confirmation(self):
        self.assertEqual(self.client.get(f'{CREATE}?semestre=2030/1').status_code, 404)
        response = self.client.get(self.url(sala='Sala 9', data=TUESDAY.isoformat(), horario='13:20'))
        self.assertContains(response, TUESDAY.isoformat())
        self.assertContains(response, 'Cadastrar aula')
        response = self.client.post(self.url(), self.payload())
        self.assertContains(response, 'Química Orgânica')
        self.assertContains(response, 'confirmar')
        self.assertFalse(self.created().exists())
        response = self.client.post(self.url(), self.payload() | {'espaco': self.room.pk, 'horario': '10:00', 'confirmar': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cálculo III')
        self.assertFalse(self.created().exists())
        response = self.client.post(self.url(), self.payload() | {'confirmar': '1'})
        self.assertTrue(self.created().exists())
        self.assertEqual(response.status_code, 302)
        self.assertIn(GRID, response['Location'])

    def test_grid_offers_the_action_only_with_the_permission(self):
        url = f'{GRID}?semestre=2026/2&sala=Sala 9&semana={MONDAY.isoformat()}'
        self.assertContains(self.client.get(url), 'timetable-add')
        self.client.force_login(self.changer)
        self.assertNotContains(self.client.get(url), 'timetable-add')


class CreateReimportTests(CreateTestCase):
    def test_reimport_keeps_the_lesson_created_in_the_system(self):
        self.create()
        allocation = self.created().get()
        before = list(Allocation.objects.order_by('pk').values())
        found, action, changes = Allocation.objects.apply(
            self.semester, self.group, self.chemistry, Weekday.TUESDAY, allocation.time_slot,
            space=self.room, teachers=[self.viviane],
        )
        self.assertEqual((found.pk, action, changes), (allocation.pk, 'unchanged', {}))
        self.assertEqual(list(Allocation.objects.order_by('pk').values()), before)
