"""Solicitação de agendamento criada em nome de outro usuário."""

import re
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.urls import reverse

from accounts import permissions
from accounts.models import RolePermission, User
from audit import catalog
from audit.models import AuditLog
from bookings.models import Booking, BookingRequest
from bookings.tests.base import (
    CREATOR, REQUESTER, REVIEWER, THURSDAY, academic, frozen_clock, semester_with_lesson, space, user_with,
)
from schedule.models import Course, Semester, Space

Status = BookingRequest.Status
CREATE = reverse('agenda_create')
DESCRIPTION = 'Reunião do projeto de extensão com os alunos.'


class OnBehalfTestCase(IsolatedCasesMixin, TestCase):
    """Ana, Bruno e Érica com vínculos em INFORMÁTICA e AGROPECUÁRIA; a secretaria tem `AGENDA.CRIAR`."""

    def setUp(self):
        frozen_clock(self)
        semester_with_lesson()
        self.lab = Space.objects.get(name='Laboratório de Informática 2')
        self.ana = user_with('ana@ifnmg.edu.br', *REQUESTER)
        self.bruno = user_with('bruno@ifnmg.edu.br', *REQUESTER)
        self.erica = user_with('erica@ifnmg.edu.br', *REQUESTER)
        self.outsider = user_with('sem_docente@ifnmg.edu.br', *REQUESTER)
        self.viewer = user_with('consulta@ifnmg.edu.br', REQUESTER[0])
        self.creator = user_with('secretaria@ifnmg.edu.br', *CREATOR)
        self.reviewer = user_with('analise@ifnmg.edu.br', *REVIEWER)
        self.networks = academic(teacher='ana')
        self.networks_third = academic(teacher='ana', label='3º ANO A')
        self.databases = academic(teacher='ana', subject='Banco de Dados', label='3º ANO A')
        self.chemistry = academic(teacher='ana', subject='Química', label='1º ANO A', course='AGROPECUÁRIA')
        self.bruno_networks = academic(teacher='bruno')
        self.bruno_physics = academic(teacher='bruno', subject='Física', label='1º ANO B', course='AGROPECUÁRIA')
        self.erica_networks = academic(teacher='erica', label='1º ANO A')
        previous, _ = Semester.objects.resolve('2026/1')
        previous.define_period(date(2026, 2, 2), date(2026, 7, 10))
        self.old_physics = academic(teacher='ana', subject='Física', code='2026/1')
        self.semester = self.networks.offering.semester
        self.informatics = Course.objects.get(name='INFORMÁTICA')
        self.agriculture = Course.objects.get(name='AGROPECUÁRIA')
        self.redes = self.networks.offering.subject
        self.chem = self.chemistry.offering.subject

    def submit_for(self, creator, requester, assignment, course=None, subject=None, **overrides):
        values = {'day': THURSDAY, 'start': time(16, 0), 'end': time(18, 0), 'description': DESCRIPTION, 'students': 30} | overrides
        return BookingRequest.objects.submit(
            creator, self.lab, values['day'], values['start'], values['end'], values['description'],
            values['students'], self.semester, assignment, requester,
            course or assignment.offering.class_group.course, subject or assignment.offering.subject,
        )

    def refused(self, *arguments, **overrides):
        with self.assertRaises(ValidationError) as caught:
            self.submit_for(*arguments, **overrides)
        self.assertFalse(BookingRequest.objects.exists())
        return caught.exception

    def data(self, **values):
        return {
            'requested_for': self.ana.pk,
            'course': self.informatics.pk,
            'subject': self.redes.pk,
            'teaching_assignment': self.networks.pk,
            'space': self.lab.pk, 'date': '2026-10-15', 'start_time': '16:00', 'end_time': '18:00',
            'description': DESCRIPTION, 'student_count': '30',
        } | values

    def refresh(self, trigger='', **query):
        headers = {'HX-Request': 'true'}
        if trigger:
            headers['HX-Trigger-Name'] = trigger
        return self.client.get(CREATE, {'date': '2026-10-15'} | query, headers=headers).content.decode()


class AccessTests(OnBehalfTestCase):
    def grid(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('agenda_grid'), {'semestre': '2026/2', 'semana': '2026-10-12'}).content.decode()

    def test_grid_offers_the_creation_to_who_creates(self):
        with self.case('só cria'):
            content = self.grid(self.creator)
            self.assertIn(f'{CREATE}?espaco=', content)
            self.assertNotIn(reverse('agenda_request_create'), content)
        with self.case('cria e solicita'):
            both = user_with('coordenacao@ifnmg.edu.br', *REQUESTER, permissions.BOOKING_CREATE)
            content = self.grid(both)
            self.assertIn(f"{reverse('agenda_request_create')}?espaco=", content)
            self.assertNotIn(f'{CREATE}?espaco=', content)
            modal = self.client.get(reverse('agenda_request_create'), headers={'HX-Request': 'true'}).content.decode()
            self.assertIn('aria-label="Criar para outro usuário"', modal.split('class="modal-foot"')[1])
        with self.case('só solicita'):
            self.client.force_login(self.ana)
            modal = self.client.get(reverse('agenda_request_create'), headers={'HX-Request': 'true'}).content.decode()
            self.assertNotIn('Criar para outro usuário', modal)

    def test_operation_without_the_permission(self):
        error = self.refused(self.bruno, self.ana, self.networks)
        self.assertEqual(error.code, 'permission')


class ChainOptionsTests(OnBehalfTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.creator)

    def options(self, content, name):
        return content.split(f'name="{name}"')[1].split('</select>')[0]

    def chosen(self, content, name):
        """Valor da opção escolhida no campo, ou vazio."""
        found = re.search(r'<option value="([^"]*)" selected>', self.options(content, name))
        return found.group(1) if found else ''

    def test_chain_options(self):
        with self.case('usuários'):
            User.objects.filter(pk=self.erica.pk).update(is_active=False)
            users = self.options(self.refresh(), 'requested_for')
            self.assertIn('Ana (ana)', users)
            self.assertIn('Bruno (bruno)', users)
            self.assertIn('Sem_docente (sem_docente)', users)
            self.assertNotIn('erica', users)
            self.assertNotIn('consulta', users)
            self.assertNotIn('secretaria', users)
        with self.case('cursos'):
            courses = self.options(self.refresh(requested_for=self.erica.pk), 'course')
            self.assertIn('>INFORMÁTICA</option>', courses)
            self.assertIn('>AGROPECUÁRIA</option>', courses)
        with self.case('vínculos históricos e de outro semestre'):
            self.chemistry.is_current = False
            self.chemistry.save()
            subjects = self.options(self.refresh(course=self.agriculture.pk), 'subject')
            self.assertNotIn('Química', subjects)
            self.assertIn('>Física</option>', subjects)
            self.assertNotIn('>Física</option>', self.refresh(course=self.informatics.pk))
        with self.case('disciplinas'):
            subjects = self.options(self.refresh(requested_for=self.erica.pk, course=self.informatics.pk), 'subject')
            self.assertIn('>Redes</option>', subjects)
            self.assertIn('>Banco de Dados</option>', subjects)
            self.assertNotIn('Química', subjects)
            self.assertNotIn('Física', subjects)
        with self.case('turmas'):
            content = self.refresh(requested_for=self.ana.pk, course=self.informatics.pk, subject=self.redes.pk)
            groups = self.options(content, 'teaching_assignment')
            self.assertIn(f'<option value="{self.networks.pk}">2º ANO A (INFORMÁTICA) · ana</option>', groups)
            self.assertIn(f'<option value="{self.bruno_networks.pk}">2º ANO A (INFORMÁTICA) · bruno</option>', groups)
            self.assertIn(f'<option value="{self.networks_third.pk}">3º ANO A (INFORMÁTICA) · ana</option>', groups)
            self.assertIn(f'value="{self.erica_networks.pk}"', groups)
            self.assertNotIn(f'value="{self.databases.pk}"', groups)

    def test_changing_a_field_resets_the_following(self):
        with self.case('usuário'):
            content = self.refresh(
                'requested_for', requested_for=self.bruno.pk, course=self.informatics.pk, subject=self.redes.pk,
                teaching_assignment=self.networks.pk,
            )
            self.assertEqual(self.chosen(content, 'requested_for'), str(self.bruno.pk))
            self.assertEqual(self.chosen(content, 'teaching_assignment'), str(self.networks.pk))
        with self.case('curso'):
            content = self.refresh(
                'course', requested_for=self.ana.pk, course=self.informatics.pk, subject=self.redes.pk,
                teaching_assignment=self.networks.pk,
            )
            self.assertEqual(self.chosen(content, 'requested_for'), str(self.ana.pk))
            self.assertEqual(self.chosen(content, 'course'), str(self.informatics.pk))
            self.assertEqual(self.chosen(content, 'subject'), '')
            self.assertEqual(self.chosen(content, 'teaching_assignment'), '')
        with self.case('disciplina'):
            content = self.refresh(
                'subject', requested_for=self.ana.pk, course=self.informatics.pk, subject=self.redes.pk,
                teaching_assignment=self.networks.pk,
            )
            self.assertEqual(self.chosen(content, 'course'), str(self.informatics.pk))
            self.assertEqual(self.chosen(content, 'subject'), str(self.redes.pk))
            self.assertEqual(self.chosen(content, 'teaching_assignment'), '')
        with self.case('data'):
            previous = self.old_physics.offering.semester
            Semester.objects.filter(pk=previous.pk).update(start_date=date(2026, 2, 2), end_date=date(2026, 10, 9))
            Semester.objects.filter(pk=self.semester.pk).update(start_date=date(2026, 10, 10))
            content = self.refresh('date', date='2026-10-05', requested_for=self.ana.pk, course=self.informatics.pk)
            self.assertIn('Semestre 2026/1.', content)
            self.assertIn('>Física</option>', self.options(content, 'subject'))


class ChainSecurityTests(OnBehalfTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.creator)

    def post(self, **values):
        return self.client.post(CREATE, self.data(confirmar='1', **values))

    def test_server_checks_the_chain(self):
        with self.case('fim de semana'):
            response = self.post(date='2026-10-17')
            self.assertContains(response, 'Agendamentos só podem ser feitos de segunda a sexta. Escolha outra data.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('turma de outro docente'):
            response = self.post(teaching_assignment=self.erica_networks.pk)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(BookingRequest.objects.get().teaching_assignment, self.erica_networks)
        with self.case('sem turma'):
            response = self.post(course='', subject='', teaching_assignment='')
            self.assertEqual(response.status_code, 302)
            request = BookingRequest.objects.get()
            self.assertEqual((request.requested_by, request.teaching_assignment), (self.ana, None))
        with self.case('disciplina de outro curso'):
            response = self.post(subject=self.chem.pk, teaching_assignment=self.chemistry.pk)
            self.assertContains(response, 'Escolha uma das disciplinas do curso escolhido.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('turma de outra disciplina'):
            response = self.post(teaching_assignment=self.databases.pk)
            self.assertContains(response, 'Escolha uma turma da disciplina escolhida.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('usuário que não é docente'):
            response = self.post(requested_for=self.outsider.pk)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(BookingRequest.objects.get().requested_by, self.outsider)
        with self.case('usuário sem a permissão de solicitar'):
            response = self.post(requested_for=self.viewer.pk)
            self.assertContains(response, 'Escolha um dos usuários que solicitam agendamento.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('usuário inativo'):
            User.objects.filter(pk=self.ana.pk).update(is_active=False)
            response = self.post()
            self.assertContains(response, 'Escolha um dos usuários que solicitam agendamento.')
            self.assertFalse(BookingRequest.objects.exists())
        with self.case('ids desconhecidos'):
            response = self.post(requested_for=999999, course=999999, subject=999999, teaching_assignment=999999)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(BookingRequest.objects.exists())


class ChainModelTests(OnBehalfTestCase):
    """A conferência do model, independente do formulário."""

    def test_model_checks_the_chain(self):
        with self.case('curso que não é o da turma'):
            error = self.refused(self.creator, self.ana, self.networks, course=self.agriculture)
            self.assertIn('subject', error.message_dict)
        with self.case('disciplina que não é a da oferta'):
            error = self.refused(self.creator, self.ana, self.networks, subject=self.chem)
            self.assertEqual(
                error.message_dict['teaching_assignment'],
                ['Esta turma não é da disciplina escolhida. Escolha outra turma.'],
            )
        with self.case('turma de outro semestre'):
            error = self.refused(self.creator, self.ana, self.old_physics)
            self.assertIn('teaching_assignment', error.message_dict)
        with self.case('usuário sem a permissão de solicitar'):
            error = self.refused(self.creator, self.viewer, self.networks)
            self.assertEqual(
                error.message_dict['requested_for'],
                ['O usuário consulta não tem permissão para solicitar agendamento. Escolha outro usuário.'],
            )
        with self.case('usuário inativo'):
            User.objects.filter(pk=self.ana.pk).update(is_active=False)
            self.ana.refresh_from_db()
            self.assertIn('requested_for', self.refused(self.creator, self.ana, self.networks).message_dict)


class CreationTests(OnBehalfTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.creator)

    def test_review_then_submit(self):
        review = self.client.post(CREATE, self.data(), headers={'HX-Request': 'true'})
        content = review.content.decode()
        self.assertIn('Enviar a solicitação de Laboratório de Informática 2?', content)
        for value in ('Solicitante', 'Criada por', 'Secretaria', '2026/2', 'Redes', '2º ANO A (INFORMÁTICA)'):
            with self.subTest(value=value):
                self.assertIn(value, content)
        for name in ('requested_for', 'course'):
            with self.subTest(name=name):
                self.assertIn(f'name="{name}"', content)
        self.assertFalse(BookingRequest.objects.exists())
        response = self.client.post(CREATE, self.data(confirmar='1'), headers={'HX-Request': 'true'})
        self.assertIn('HX-Redirect', response.headers)
        request = BookingRequest.objects.get()
        self.assertEqual(
            (request.status, request.requested_by, request.created_by, request.teaching_assignment),
            (Status.PENDING, self.ana, self.creator, self.networks),
        )
        self.assertFalse(Booking.objects.exists())

    def test_request_and_booking_belong_to_the_chosen_user(self):
        with self.case('solicitação'):
            self.client.post(CREATE, self.data(confirmar='1'))
            request = BookingRequest.objects.get()
            self.client.force_login(self.ana)
            self.assertContains(self.client.get(reverse('agenda_my_requests')), 'Laboratório de Informática 2')
            detail = self.client.get(reverse('agenda_my_request', args=[request.pk]))
            self.assertContains(detail, 'Criada por')
            self.assertContains(detail, 'Secretaria')
            self.client.force_login(self.bruno)
            self.assertEqual(self.client.get(reverse('agenda_my_request', args=[request.pk])).status_code, 404)
        with self.case('agendamento'):
            request = self.submit_for(self.creator, self.ana, self.networks)
            request.approve(self.reviewer)
            self.assertEqual(Booking.objects.get().requested_by, self.ana)

    def test_audit_records_the_requester_and_the_creator(self):
        self.client.post(CREATE, self.data(confirmar='1'))
        request = BookingRequest.objects.get()
        log = AuditLog.objects.get(action=catalog.CREATE, resource=catalog.BOOKING_REQUEST, resource_id=str(request.pk))
        self.assertEqual((log.new_values['solicitante'], log.new_values['criada_por']), ('ana', 'secretaria'))
        self.assertEqual(log.user, self.creator)

    def test_creating_for_oneself_needs_the_request_permission(self):
        error = self.refused(self.creator, self.creator, self.networks)
        self.assertEqual(error.code, 'permission')
