"""Solicitação de agendamento por quem tem `AGENDA.SOLICITAR`, com a turma opcional."""

from datetime import date, time
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.urls import reverse

from accounts import permissions
from audit.models import AuditLog
from bookings.models import Booking, BookingRequest
from bookings.tests.base import REQUESTER, REVIEWER, THURSDAY, academic, frozen_clock, semester_with_lesson, submit, user_with
from schedule.models import Semester, Space

Status = BookingRequest.Status
CREATE = reverse('agenda_request_create')


class AcademicTestCase(IsolatedCasesMixin, TestCase):
    """Ana dá Redes e Banco de Dados em 2026/2 e deu Física em 2026/1; Érica dá Física em 2026/2."""

    def setUp(self):
        frozen_clock(self)
        semester_with_lesson()
        self.lab = Space.objects.get(name='Laboratório de Informática 2')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.erica = user_with('erica@ifnmg.edu.br', *REQUESTER)
        self.outsider = user_with('secretaria@ifnmg.edu.br', *REQUESTER)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        self.networks = academic(teacher='ana')
        self.databases = academic(teacher='ana', subject='Banco de Dados', label='3º ANO A')
        self.physics = academic(teacher='erica', subject='Física')
        previous, _ = Semester.objects.resolve('2026/1')
        previous.define_period(date(2026, 2, 2), date(2026, 7, 10))
        self.old_physics = academic(teacher='ana', subject='Física', code='2026/1')
        self.semester = self.networks.offering.semester

    def submit_as(self, user, assignment, semester=None, course=None, subject=None, **overrides):
        values = {'day': THURSDAY, 'start': time(16, 0), 'end': time(18, 0), 'description': 'Reunião do projeto.', 'students': 30} | overrides
        return BookingRequest.objects.submit(
            user, self.lab, values['day'], values['start'], values['end'], values['description'],
            values['students'], semester or self.semester, assignment, None, course, subject,
        )

    def refused(self, *arguments, **overrides):
        with self.assertRaises(ValidationError) as caught:
            self.submit_as(*arguments, **overrides)
        self.assertFalse(BookingRequest.objects.exists())
        return caught.exception


class AssignmentTests(AcademicTestCase):
    def test_accepted_academic_links(self):
        with self.case('turma própria'):
            request = self.submit_as(self.ana, self.networks)
            self.assertEqual((request.status, request.teaching_assignment), (Status.PENDING, self.networks))
            self.assertFalse(Booking.objects.exists())
        with self.case('turma de outro docente'):
            request = self.submit_as(self.ana, self.physics)
            self.assertEqual(request.teaching_assignment, self.physics)
        with self.case('sem turma'):
            request = self.submit_as(self.ana, None)
            self.assertEqual((request.status, request.teaching_assignment), (Status.PENDING, None))
            log = AuditLog.objects.filter(resource_id=str(request.pk)).latest('pk')
            self.assertNotIn('turma', log.new_values)
        with self.case('usuário que não é docente'):
            request = self.submit_as(self.outsider, self.networks)
            self.assertEqual(request.requested_by, self.outsider)

    def test_refused_academic_links(self):
        with self.case('turma de outro semestre'):
            error = self.refused(self.ana, self.old_physics)
            self.assertEqual(
                error.message_dict['teaching_assignment'],
                ['Esta turma não está entre as turmas do ensalamento de 2026/2. Escolha outra turma.'],
            )
        with self.case('vínculo histórico'):
            self.networks.is_current = False
            self.networks.save()
            self.assertIn('teaching_assignment', self.refused(self.ana, self.networks).message_dict)
        with self.case('sem semestre'):
            with self.assertRaises(ValidationError) as caught:
                BookingRequest.objects.submit(self.ana, self.lab, THURSDAY, time(16, 0), time(18, 0), 'Reunião.', 30, None, None)
            self.assertEqual(set(caught.exception.message_dict), {'semester'})
        with self.case('semestre sem período'):
            no_period = academic(teacher='ana', subject='Estágio', code='2027/1')
            semester = no_period.offering.semester
            Semester.objects.filter(pk=semester.pk).update(start_date=None, end_date=None)
            semester.refresh_from_db()
            error = self.refused(self.ana, no_period, semester=semester)
            self.assertEqual(error.message_dict['semester'], ['O semestre 2027/1 não tem período definido. Escolha outro semestre.'])


class ScreenTests(AcademicTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.ana)

    def data(self, **values):
        return {
            'course': self.networks.offering.class_group.course_id,
            'subject': self.networks.offering.subject_id,
            'teaching_assignment': self.networks.pk,
            'space': self.lab.pk, 'date': '2026-10-15', 'start_time': '16:00', 'end_time': '18:00',
            'description': 'Reunião do projeto de extensão com os alunos.', 'student_count': '30',
        } | values

    def refresh(self, **query):
        return self.client.get(CREATE, query, headers={'HX-Request': 'true'}).content.decode()

    def options(self, content, field):
        return content.split(f'name="{field}"')[1].split('</select>')[0]

    def test_options_follow_the_permission_to_request_for_others(self):
        """Quem só solicita para si escolhe entre as próprias turmas; quem solicita para outro vê todas."""
        informatics = self.networks.offering.class_group.course_id
        physics = self.physics.offering.subject_id
        with self.case('curso, disciplina e turma só do próprio docente'):
            content = self.refresh(data='2026-10-15', course=informatics, subject=self.networks.offering.subject_id)
            self.assertIn('>Redes</option>', self.options(content, 'subject'))
            self.assertIn('>Banco de Dados</option>', self.options(content, 'subject'))
            self.assertNotIn('Física', self.options(content, 'subject'))
            self.assertIn(f'value="{self.networks.pk}"', self.options(content, 'teaching_assignment'))
            self.assertIn('turma sua no semestre', content)
            groups = self.options(self.refresh(data='2026-10-15', course=informatics, subject=physics), 'teaching_assignment')
            self.assertNotIn(f'value="{self.physics.pk}"', groups)
        with self.case('quem pode solicitar para outro vê todas'):
            self.client.force_login(user_with('direcao@ifnmg.edu.br', *REQUESTER, permissions.BOOKING_CREATE))
            content = self.refresh(data='2026-10-15', course=informatics, subject=physics)
            self.assertIn('>Física</option>', self.options(content, 'subject'))
            self.assertIn(f'value="{self.physics.pk}"', self.options(content, 'teaching_assignment'))
            self.assertNotIn('turma sua no semestre', content)
        with self.case('usuário que não é docente de nenhuma turma'):
            self.client.force_login(self.outsider)
            content = self.refresh(data='2026-10-15')
            self.assertEqual(self.options(content, 'course').count('<option'), 1)
            self.assertIn('Sem turmas suas em 2026/2. Envie a solicitação sem curso.', content)

    def test_subjects_and_class_groups_follow_the_choices(self):
        with self.case('disciplinas do curso'):
            course = self.networks.offering.class_group.course
            content = self.refresh(espaco=self.lab.pk, data='2026-10-15', course=course.pk)
            self.assertIn('>INFORMÁTICA</option>', content)
            self.assertIn('>Redes</option>', content)
            self.assertIn('>Banco de Dados</option>', content)
            self.assertNotIn('>Física</option>', content)
            self.assertNotIn(f'value="{self.networks.pk}"', content)
        with self.case('turmas da disciplina'):
            offering = self.networks.offering
            content = self.refresh(date='2026-10-15', course=offering.class_group.course_id, subject=offering.subject_id)
            self.assertIn(f'<option value="{self.networks.pk}">2º ANO A (INFORMÁTICA) · ana</option>', content)
            self.assertNotIn(f'value="{self.databases.pk}"', content)
            self.assertNotIn(f'value="{self.physics.pk}"', content)
            self.assertIn('hx-get', content.split('name="subject"')[1].split('>')[0])

    def test_date_defines_the_semester_of_the_agenda(self):
        previous = self.old_physics.offering.semester
        Semester.objects.filter(pk=previous.pk).update(start_date=date(2026, 2, 2), end_date=date(2026, 10, 9))
        Semester.objects.filter(pk=self.semester.pk).update(start_date=date(2026, 10, 10))
        offering = self.old_physics.offering
        content = self.refresh(date='2026-10-05', course=offering.class_group.course_id, subject=offering.subject_id)
        self.assertIn('Semestre 2026/1.', content)
        self.assertIn('>Física</option>', content)
        self.assertNotIn('>Redes</option>', content)
        self.assertIn(f'<option value="{self.old_physics.pk}">2º ANO A (INFORMÁTICA) · ana</option>', content)
        self.assertIn('hx-get', content.split('name="date"')[1].split('>')[0])

    def test_review_then_submit(self):
        review = self.client.post(CREATE, self.data(), headers={'HX-Request': 'true'})
        content = review.content.decode()
        self.assertIn('Enviar a solicitação de Laboratório de Informática 2?', content)
        for value in ('2026/2', 'ana', 'Redes', '2º ANO A (INFORMÁTICA)', '15/10/2026, das 16:00 às 18:00'):
            with self.subTest(value=value):
                self.assertIn(value, content)
        self.assertFalse(BookingRequest.objects.exists())
        response = self.client.post(CREATE, self.data(confirmar='1'), headers={'HX-Request': 'true'})
        self.assertIn('HX-Redirect', response.headers)
        self.assertEqual(BookingRequest.objects.get().teaching_assignment, self.networks)

    def test_forged_or_out_of_range_choices_are_refused(self):
        with self.case('turma de outro docente'):
            physics = self.physics.offering
            response = self.client.post(CREATE, self.data(subject=physics.subject_id, teaching_assignment=self.physics.pk, confirmar='1'))
            self.assertContains(response, 'Escolha uma das disciplinas do curso escolhido.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('turma de outro semestre'):
            response = self.client.post(CREATE, self.data(teaching_assignment=self.old_physics.pk, confirmar='1'))
            self.assertContains(response, 'Escolha uma turma da disciplina escolhida.')
        with self.case('turma de outra disciplina'):
            response = self.client.post(CREATE, self.data(teaching_assignment=self.databases.pk, confirmar='1'))
            self.assertContains(response, 'Escolha uma turma da disciplina escolhida.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('disciplina de outro semestre'):
            response = self.client.post(CREATE, self.data(subject=999999, confirmar='1'))
            self.assertContains(response, 'Escolha uma das disciplinas do curso escolhido.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('ids desconhecidos'):
            response = self.client.post(CREATE, self.data(teaching_assignment=999999, space=999999, confirmar='1'))
            self.assertContains(response, 'Escolha uma turma da disciplina escolhida.')
            self.assertContains(response, 'Escolha um espaço ativo.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('data fora de todo semestre'):
            response = self.client.post(CREATE, self.data(date='2027-01-07', confirmar='1'))
            self.assertContains(response, 'A data 07/01/2027 não está no período de nenhum semestre da Agenda. Escolha outra data.')
            self.assertFalse(BookingRequest.objects.exists())

    def test_forged_semester_is_ignored(self):
        response = self.client.post(CREATE, self.data(semester=self.old_physics.offering.semester_id, confirmar='1'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BookingRequest.objects.get().teaching_assignment.offering.semester, self.semester)

    def test_detail_shows_the_academic_link(self):
        request = submit(self.ana, self.lab, assignment=self.networks)
        content = self.client.get(reverse('agenda_my_request', args=[request.pk])).content.decode()
        self.assertIn('Semestre 2026/2', content)
        self.assertIn('2º ANO A (INFORMÁTICA)', content)
        self.assertIn('Redes', content)


class SubjectCheckTests(AcademicTestCase):
    """O model confere curso e disciplina mesmo sem o formulário."""

    def test_forged_subject_is_refused_by_the_model(self):
        with self.assertRaises(ValidationError) as caught:
            BookingRequest.objects.submit(
                self.ana, self.lab, THURSDAY, time(16, 0), time(18, 0), 'Reunião.', 30, self.semester, self.networks,
                subject=self.databases.offering.subject,
            )
        self.assertIn('teaching_assignment', caught.exception.message_dict)
        self.assertFalse(BookingRequest.objects.exists())
