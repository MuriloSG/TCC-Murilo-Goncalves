"""Solicitação de agendamento e agendamento, o uso eventual dos espaços.

A solicitação é o pedido do usuário e passa pela máquina de estados da D4 da Change
agendar-uso-eventual-dos-espacos. O agendamento é o uso aprovado, avulso e numa única data,
ligado à solicitação que o originou. A alocação do ensalamento não é tocada: são três
conceitos em três tabelas (D3).

Toda transição é uma operação do model, numa transação, com a solicitação relida e travada
por `select_for_update`; a aprovação e o aceite travam também o espaço, para que a
verificação dos conflitos e a criação do agendamento aconteçam sem outra decisão do mesmo
espaço no meio (D6). A ausência de sobreposição entre agendamentos é garantida pela
`ExclusionConstraint` do banco (D5).
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models import Func, Q
from django.utils import timezone
from django.utils.formats import date_format

from accounts import permissions
from audit import catalog
from audit.models import AuditLog
from bookings import notifications
from bookings.occupancy import conflict_message, find_conflict
from notices.events import announce
from schedule.models import Space, TeachingAssignment, teacher_of

DESCRIPTION_MAX_LENGTH = 500
REASON_MAX_LENGTH = 500
STUDENT_COUNT_MAX = 999
CANCEL_DEADLINE = timedelta(hours=1)

DESCRIPTION_REQUIRED_MESSAGE = 'Informe a descrição do uso do espaço.'
STUDENT_COUNT_REQUIRED_MESSAGE = 'Informe a quantidade de alunos.'
STUDENT_COUNT_RANGE_MESSAGE = f'Informe uma quantidade de alunos entre 1 e {STUDENT_COUNT_MAX}.'
REASON_REQUIRED_MESSAGE = 'Informe o motivo da rejeição.'
END_BEFORE_START_MESSAGE = 'O fim deve ser posterior ao início.'
PAST_MESSAGE = 'Este horário já passou. Escolha um horário futuro.'
SAME_SUGGESTION_MESSAGE = 'A alternativa deve mudar o espaço, a data ou o horário da solicitação.'
OWNER_ONLY_MESSAGE = 'Só quem solicitou pode responder à alternativa.'
PERMISSION_MESSAGE = 'Sem permissão para esta ação na Agenda.'
SEMESTER_REQUIRED_MESSAGE = 'Escolha o semestre.'
SUBJECT_REQUIRED_MESSAGE = 'Escolha a disciplina.'
ASSIGNMENT_REQUIRED_MESSAGE = 'Escolha a turma.'
NOT_A_TEACHER_MESSAGE = 'O seu usuário não corresponde a um docente do ensalamento. Só docentes solicitam agendamento.'
REQUESTER_REQUIRED_MESSAGE = 'Escolha o usuário.'
COURSE_REQUIRED_MESSAGE = 'Escolha o curso.'
SUBJECT_OUTSIDE_COURSE_MESSAGE = 'Esta disciplina não está entre as disciplinas do usuário no curso escolhido. Escolha outra disciplina.'
CANCEL_DEADLINE_MESSAGE = 'O agendamento só pode ser cancelado até 1 hora antes do início.'
CANCEL_PERMISSION_MESSAGE = 'Só quem solicitou ou quem analisa a Agenda pode cancelar este agendamento.'
ASSIGNMENT_OUTSIDE_SUBJECT_MESSAGE = 'Esta turma não está entre as turmas do usuário na disciplina escolhida. Escolha outra turma.'


def not_a_teacher_message(user):
    return f'O usuário {user.username or user.email} não corresponde a um docente do ensalamento. Escolha outro usuário.'


class TsTzRange(Func):
    """Intervalo `[início, fim)` de duas colunas de data e hora, para a restrição de exclusão."""

    function = 'TSTZRANGE'
    output_field = DateTimeRangeField()


def moment(day, at):
    """Data e hora locais do campus, com o fuso, para comparar e gravar o intervalo."""
    return timezone.make_aware(datetime.combine(day, at))


def inactive_message(space):
    return f'O espaço {space.name} está desativado. Escolha outro espaço.'


class InvalidTransition(ValidationError):
    """Recusa de uma ação que o estado atual da solicitação não admite (D4)."""

    def __init__(self, status):
        label = BookingRequest.Status(status).label.lower()
        super().__init__(f'Esta solicitação está {label} e não aceita esta ação.', code='invalid_transition')


class SlotUnavailable(ValidationError):
    """Recusa por conflito com o ensalamento ou com outro agendamento aprovado (D5)."""

    def __init__(self, message):
        super().__init__(message, code='unavailable')


def hours(start, end):
    return f'{start:%H:%M} às {end:%H:%M}'


def record_transition(action, request, previous, **values):
    """Registra a mudança de estado da solicitação, com o estado anterior e o posterior (D9)."""
    AuditLog.objects.record(
        action,
        catalog.BOOKING_REQUEST,
        resource_id=request.pk,
        old_values={'situacao': previous},
        new_values={'situacao': request.status, **values},
    )


def require(user, code):
    if not user.has_perm(code):
        raise ValidationError(PERMISSION_MESSAGE, code='permission')


def check_slot(space, day, start, end, prefix='', exclude_request=None):
    """Valida o espaço, a data e o horário de uma solicitação ou alternativa.

    As mesmas regras valem na criação, na sugestão, na aprovação e no aceite. O conflito
    é verificado por último, só com os dados válidos.
    """
    errors = {}
    if space is not None and not space.is_active:
        errors[f'{prefix}space'] = ValidationError(inactive_message(space), code='inactive')
    if start is not None and end is not None and not start < end:
        errors[f'{prefix}end_time'] = ValidationError(END_BEFORE_START_MESSAGE, code='invalid_range')
    elif day is not None and start is not None and moment(day, start) <= timezone.now():
        errors[f'{prefix}start_time'] = ValidationError(PAST_MESSAGE, code='past')
    if errors:
        raise ValidationError(errors)
    conflict = find_conflict(space, day, start, end)
    if conflict is not None:
        raise SlotUnavailable(conflict_message(conflict))


def check_assignment(requester, semester, assignment, course=None, subject=None, on_behalf=False):
    """Recusa a turma que não é um vínculo atual do docente do solicitante no semestre.

    É a única conferência da cadeia usuário, curso, disciplina e turma, usada pelos dois fluxos
    de criação. O solicitante é reconhecido como docente pelo `username` (`teacher_of`), e a
    turma escolhida precisa ser um vínculo atual dele, criado pela importação do ensalamento
    (Change relacionar-professor-disciplina-turma). Quando informados, a disciplina precisa ser
    a da oferta do vínculo e o curso, o da turma dela: o vínculo é a fonte de verdade, e o curso
    e a disciplina são conferidos a partir dele (D1 e D3 da Change
    criar-agendamento-para-outro-usuario). Um ID de outro docente, de outro semestre, de outra
    disciplina, de outro curso ou de um vínculo histórico é recusado, venha de onde vier.
    """
    teacher = teacher_of(requester)
    if teacher is None:
        if on_behalf:
            raise ValidationError({'requested_for': ValidationError(not_a_teacher_message(requester), code='not_a_teacher')})
        raise ValidationError(NOT_A_TEACHER_MESSAGE, code='not_a_teacher')
    missing = {}
    if semester is None:
        missing['semester'] = ValidationError(SEMESTER_REQUIRED_MESSAGE, code='required')
    if assignment is None:
        missing['teaching_assignment'] = ValidationError(ASSIGNMENT_REQUIRED_MESSAGE, code='required')
    if missing:
        raise ValidationError(missing)
    offering = assignment.offering
    if (
        assignment.teacher_id != teacher.pk
        or not assignment.is_current
        or offering.semester_id != semester.pk
    ):
        text = (
            f'Esta turma não está entre as turmas do usuário no ensalamento de {semester.code}. Escolha outra turma.'
            if on_behalf
            else f'Esta turma não está entre as suas turmas do ensalamento de {semester.code}. Escolha uma das suas turmas.'
        )
        raise ValidationError({'teaching_assignment': ValidationError(text, code='not_available')})
    if course is not None and offering.class_group.course_id != course.pk:
        raise ValidationError({'subject': ValidationError(SUBJECT_OUTSIDE_COURSE_MESSAGE, code='not_available')})
    if subject is not None and offering.subject_id != subject.pk:
        raise ValidationError({'teaching_assignment': ValidationError(ASSIGNMENT_OUTSIDE_SUBJECT_MESSAGE, code='not_available')})


def check_period(semester, day):
    """Recusa o semestre sem período e a data fora dele."""
    if not semester.has_period:
        raise ValidationError({'semester': ValidationError(
            f'O semestre {semester.code} não tem período definido. Escolha outro semestre.', code='without_period',
        )})
    if day is not None and not semester.contains(day):
        raise ValidationError({'date': ValidationError(
            f'A data {date_format(day, "SHORT_DATE_FORMAT")} está fora do período do semestre {semester.code}. '
            'Escolha outra data.',
            code='outside',
        )})


class BookingRequestManager(models.Manager):
    def prepare(
        self, user, space, day, start, end, description, student_count=None, semester=None, assignment=None,
        requester=None, course=None, subject=None,
    ):
        """Confere a solicitação e a devolve sem gravar.

        Confere a permissão, a cadeia do vínculo, o período do semestre, os campos, o espaço,
        o horário e os conflitos, nesta ordem. É a mesma conferência do envio, usada para a
        revisão mostrada antes da confirmação. O ID da turma vale só como vínculo atual do
        docente que é o solicitante, no semestre.

        O solicitante é o próprio usuário, com `AGENDA.SOLICITAR`, ou outro usuário ativo,
        escolhido por quem tem `AGENDA.CRIAR`; nesse caso `created_by` guarda quem criou
        (D3 e D7 da Change criar-agendamento-para-outro-usuario).
        """
        requester = requester or user
        on_behalf = requester.pk != user.pk
        require(user, permissions.BOOKING_CREATE if on_behalf else permissions.BOOKING_REQUEST)
        check_assignment(requester, semester, assignment, course, subject, on_behalf=on_behalf)
        check_period(semester, day)
        request = self.model(
            requested_by=requester, created_by=user if on_behalf else None, space=space, date=day,
            start_time=start, end_time=end, description=(description or '').strip(), student_count=student_count,
            status=self.model.Status.PENDING, teaching_assignment=assignment,
        )
        if student_count is None:
            raise ValidationError({'student_count': ValidationError(STUDENT_COUNT_REQUIRED_MESSAGE, code='required')})
        request.full_clean(
            exclude=['requested_by', 'created_by', 'space', 'teaching_assignment'], validate_constraints=False,
        )
        check_slot(space, day, start, end)
        return request

    def submit(
        self, user, space, day, start, end, description, student_count=None, semester=None, assignment=None,
        requester=None, course=None, subject=None,
    ):
        """Cria a solicitação `PENDENTE`, sem criar agendamento nem ocupar o horário.

        Tudo numa transação: uma recusa ou uma falha não deixa solicitação, auditoria nem
        notificação gravadas. O ensalamento não é tocado.
        """
        with transaction.atomic():
            request = self.prepare(
                user, space, day, start, end, description, student_count, semester, assignment, requester, course, subject,
            )
            request.save()
            offering = request.teaching_assignment.offering
            values = {
                'situacao': request.status,
                'semestre': semester.code,
                'docente': request.teaching_assignment.teacher.name,
                'disciplina': offering.subject.name,
                'turma': str(offering.class_group),
                'espaco': space.name,
                'data': day.isoformat(),
                'horario': hours(start, end),
                'description': request.description,
                'quantidade_alunos': request.student_count,
            }
            if request.created_by_id:
                values['solicitante'] = request.requested_by.username
                values['criada_por'] = user.username or user.email
            AuditLog.objects.record(catalog.CREATE, catalog.BOOKING_REQUEST, resource_id=request.pk, new_values=values)
            announce(notifications.REQUESTED, request=request)
        return request


class BookingRequest(models.Model):
    """Pedido de uso eventual de um espaço, com a decisão e a alternativa sugerida.

    Os campos originais nunca mudam depois da criação: a alternativa fica nos campos
    `suggested_*`, para que o original e o sugerido apareçam lado a lado (D3).

    `teaching_assignment` é o vínculo do docente com a disciplina e a turma no semestre, de
    onde vêm os quatro dados acadêmicos, sem cópia deles na solicitação. Fica vazio só nas
    solicitações criadas antes da Change solicitar-agendamento-com-vinculo-academico.

    `requested_by` é o dono da solicitação em todas as regras. `created_by` fica preenchido só
    quando outro usuário, com `AGENDA.CRIAR`, a criou em nome dele (Change
    criar-agendamento-para-outro-usuario).
    """

    class Status(models.TextChoices):
        PENDING = 'PENDENTE', 'Pendente'
        APPROVED = 'APROVADA', 'Aprovada'
        REJECTED = 'REJEITADA', 'Rejeitada'
        SUGGESTED = 'ALTERNATIVA_SUGERIDA', 'Alternativa sugerida'
        DECLINED = 'ALTERNATIVA_RECUSADA', 'Alternativa recusada'
        CANCELLED = 'CANCELADA', 'Cancelada'

    OPEN = (Status.PENDING, Status.SUGGESTED)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='booking_requests', verbose_name='solicitante',
    )
    teaching_assignment = models.ForeignKey(
        TeachingAssignment,
        on_delete=models.PROTECT,
        related_name='booking_requests',
        null=True,
        blank=True,
        verbose_name='docente da oferta',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
        verbose_name='criada por',
    )
    space = models.ForeignKey(Space, on_delete=models.PROTECT, related_name='booking_requests', verbose_name='espaço')
    date = models.DateField('data')
    start_time = models.TimeField('início')
    end_time = models.TimeField('fim')
    description = models.CharField(
        'descrição',
        max_length=DESCRIPTION_MAX_LENGTH,
        error_messages={'blank': DESCRIPTION_REQUIRED_MESSAGE, 'required': DESCRIPTION_REQUIRED_MESSAGE},
    )
    student_count = models.PositiveSmallIntegerField(
        'quantidade de alunos',
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1, STUDENT_COUNT_RANGE_MESSAGE), MaxValueValidator(STUDENT_COUNT_MAX, STUDENT_COUNT_RANGE_MESSAGE),
        ],
    )
    status = models.CharField('situação', max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.CharField('motivo da rejeição', max_length=REASON_MAX_LENGTH, blank=True)
    suggested_space = models.ForeignKey(
        Space, on_delete=models.PROTECT, related_name='+', null=True, blank=True, verbose_name='espaço sugerido',
    )
    suggested_date = models.DateField('data sugerida', null=True, blank=True)
    suggested_start_time = models.TimeField('início sugerido', null=True, blank=True)
    suggested_end_time = models.TimeField('fim sugerido', null=True, blank=True)
    suggestion_message = models.CharField('mensagem da alternativa', max_length=REASON_MAX_LENGTH, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True, verbose_name='decidida por',
    )
    decided_at = models.DateTimeField('decidida em', null=True, blank=True)
    responded_at = models.DateTimeField('respondida em', null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True, verbose_name='cancelada por',
    )
    cancelled_at = models.DateTimeField('cancelada em', null=True, blank=True)
    cancellation_reason = models.CharField('motivo do cancelamento', max_length=REASON_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField('criada em', auto_now_add=True)

    objects = BookingRequestManager()

    class Meta:
        verbose_name = 'solicitação de agendamento'
        verbose_name_plural = 'solicitações de agendamento'
        ordering = ['-created_at', '-pk']
        indexes = [
            models.Index(fields=['requested_by', '-created_at'], name='booking_request_owner_idx'),
            models.Index(fields=['status', 'date'], name='booking_request_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_time__lt=models.F('end_time')),
                name='booking_request_range_valid',
                violation_error_message=END_BEFORE_START_MESSAGE,
            ),
            models.CheckConstraint(
                condition=(
                    Q(suggested_start_time__isnull=True, suggested_end_time__isnull=True)
                    | Q(suggested_start_time__lt=models.F('suggested_end_time'))
                ),
                name='booking_request_suggestion_range_valid',
                violation_error_message=END_BEFORE_START_MESSAGE,
            ),
        ]

    def __str__(self):
        return f'{self.space} {self.date} {self.start_time}-{self.end_time}'

    @property
    def has_suggestion(self):
        return self.suggested_space_id is not None

    @property
    def is_open(self):
        return self.status in self.OPEN

    @property
    def awaits_response(self):
        return self.status == self.Status.SUGGESTED

    def locked(self):
        return type(self).objects.select_for_update(of=('self',)).select_related('space', 'suggested_space').get(pk=self.pk)

    def snapshot(self):
        return {'situacao': self.status}

    def approve(self, user):
        """Aprova a solicitação pendente e cria o agendamento com o horário original."""
        require(user, permissions.BOOKING_REVIEW)
        with transaction.atomic():
            current = self.locked()
            if current.status != self.Status.PENDING:
                raise InvalidTransition(current.status)
            space = Space.objects.select_for_update().get(pk=current.space_id)
            check_slot(space, current.date, current.start_time, current.end_time)
            current.status = self.Status.APPROVED
            current.decided_by = user
            current.decided_at = timezone.now()
            current.save(update_fields=['status', 'decided_by', 'decided_at'])
            record_transition(catalog.APPROVE, current, self.Status.PENDING)
            Booking.objects.book(current, space, current.date, current.start_time, current.end_time, user)
            announce(notifications.APPROVED, request=current)
        self.refresh_from_db()

    def reject(self, user, reason):
        """Rejeita a solicitação pendente ou com alternativa, com o motivo obrigatório."""
        require(user, permissions.BOOKING_REVIEW)
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError({'rejection_reason': ValidationError(REASON_REQUIRED_MESSAGE, code='required')})
        with transaction.atomic():
            current = self.locked()
            if current.status not in self.OPEN:
                raise InvalidTransition(current.status)
            previous = current.status
            current.status = self.Status.REJECTED
            current.rejection_reason = reason[:REASON_MAX_LENGTH]
            current.decided_by = user
            current.decided_at = timezone.now()
            current.save(update_fields=['status', 'rejection_reason', 'decided_by', 'decided_at'])
            record_transition(catalog.REJECT, current, previous, motivo=current.rejection_reason)
            announce(notifications.REJECTED, request=current)
        self.refresh_from_db()

    def suggest(self, user, space, day, start, end, message=''):
        """Devolve a solicitação com outra combinação de espaço, data e horário, disponível agora.

        A alternativa não ocupa o horário: o aceite verifica de novo (D4).
        """
        require(user, permissions.BOOKING_REVIEW)
        with transaction.atomic():
            current = self.locked()
            if current.status not in self.OPEN:
                raise InvalidTransition(current.status)
            if (space.pk, day, start, end) == (current.space_id, current.date, current.start_time, current.end_time):
                raise ValidationError(SAME_SUGGESTION_MESSAGE, code='same')
            check_slot(space, day, start, end, prefix='suggested_')
            previous = current.status
            current.status = self.Status.SUGGESTED
            current.suggested_space = space
            current.suggested_date = day
            current.suggested_start_time = start
            current.suggested_end_time = end
            current.suggestion_message = (message or '').strip()[:REASON_MAX_LENGTH]
            current.decided_by = user
            current.decided_at = timezone.now()
            current.save()
            record_transition(
                catalog.SUGGEST, current, previous,
                espaco_sugerido=space.name, data_sugerida=day.isoformat(), horario_sugerido=hours(start, end),
                mensagem=current.suggestion_message,
            )
            announce(notifications.SUGGESTED, request=current)
        self.refresh_from_db()

    def check_owner(self, user):
        require(user, permissions.BOOKING_REQUEST)
        if self.requested_by_id != user.pk:
            raise ValidationError(OWNER_ONLY_MESSAGE, code='owner')

    def accept_suggestion(self, user):
        """Aceite do solicitante: verifica de novo a alternativa e cria o agendamento com ela."""
        with transaction.atomic():
            current = self.locked()
            current.check_owner(user)
            if current.status != self.Status.SUGGESTED:
                raise InvalidTransition(current.status)
            space = Space.objects.select_for_update().get(pk=current.suggested_space_id)
            check_slot(space, current.suggested_date, current.suggested_start_time, current.suggested_end_time)
            current.status = self.Status.APPROVED
            current.responded_at = timezone.now()
            current.save(update_fields=['status', 'responded_at'])
            record_transition(catalog.ACCEPT, current, self.Status.SUGGESTED)
            Booking.objects.book(
                current, space, current.suggested_date, current.suggested_start_time, current.suggested_end_time,
                current.decided_by,
            )
            announce(notifications.ACCEPTED, request=current)
        self.refresh_from_db()

    def decline_suggestion(self, user):
        """Recusa do solicitante: encerra a solicitação sem agendamento."""
        with transaction.atomic():
            current = self.locked()
            current.check_owner(user)
            if current.status != self.Status.SUGGESTED:
                raise InvalidTransition(current.status)
            current.status = self.Status.DECLINED
            current.responded_at = timezone.now()
            current.save(update_fields=['status', 'responded_at'])
            record_transition(catalog.DECLINE, current, self.Status.SUGGESTED)
            announce(notifications.DECLINED, request=current)
        self.refresh_from_db()

    def may_cancel(self, user):
        return user.has_perm(permissions.BOOKING_REVIEW) or (
            self.requested_by_id == user.pk and user.has_perm(permissions.BOOKING_REQUEST)
        )

    def within_cancel_deadline(self):
        booking = Booking.objects.filter(request=self).values_list('starts_at', flat=True).first()
        return booking is not None and timezone.now() < booking - CANCEL_DEADLINE

    def can_cancel(self, user):
        """Diz se o botão "Cancelar agendamento" aparece para o usuário; a operação confere de novo."""
        return self.status == self.Status.APPROVED and self.may_cancel(user) and self.within_cancel_deadline()

    def cancel(self, user, reason=''):
        """Cancela a solicitação aprovada até 1 hora antes do início e exclui o agendamento.

        Cancelam quem solicitou e quem analisa. Excluir o agendamento libera o espaço em todas
        as leituras de ocupação sem filtro novo; o histórico fica na solicitação e na auditoria
        (D1 a D3 da Change cancelar-agendamento-aprovado).
        """
        with transaction.atomic():
            current = self.locked()
            if not current.may_cancel(user):
                raise ValidationError(CANCEL_PERMISSION_MESSAGE, code='permission')
            if current.status != self.Status.APPROVED:
                raise InvalidTransition(current.status)
            booking = Booking.objects.select_for_update().select_related('space').get(request=current)
            if timezone.now() >= booking.starts_at - CANCEL_DEADLINE:
                raise ValidationError(CANCEL_DEADLINE_MESSAGE, code='deadline')
            current.status = self.Status.CANCELLED
            current.cancelled_by = user
            current.cancelled_at = timezone.now()
            current.cancellation_reason = (reason or '').strip()[:REASON_MAX_LENGTH]
            current.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])
            record_transition(catalog.CANCEL, current, self.Status.APPROVED, motivo=current.cancellation_reason)
            starts_at, ends_at = timezone.localtime(booking.starts_at), timezone.localtime(booking.ends_at)
            AuditLog.objects.record(
                catalog.DELETE,
                catalog.BOOKING,
                resource_id=booking.pk,
                old_values={
                    'espaco': booking.space.name,
                    'data': starts_at.date().isoformat(),
                    'horario': hours(starts_at.time(), ends_at.time()),
                    'solicitacao': current.pk,
                },
            )
            booking.delete()
            announce(notifications.CANCELLED, request=current)
        self.refresh_from_db()

    @property
    def booked_space(self):
        """Espaço do agendamento: o sugerido, quando a alternativa foi aceita, ou o original."""
        return self.suggested_space if self.has_suggestion else self.space

    def booked_schedule_text(self):
        return self.suggested_schedule_text() if self.has_suggestion else self.schedule_text()

    def schedule_text(self):
        return slot_text(self.date, self.start_time, self.end_time)

    def suggested_schedule_text(self):
        return slot_text(self.suggested_date, self.suggested_start_time, self.suggested_end_time) if self.has_suggestion else ''


def slot_text(day, start, end):
    """Data e intervalo como aparecem na interface: `15/10/2026, das 14:00 às 16:00`."""
    return f'{date_format(day, "SHORT_DATE_FORMAT")}, das {start:%H:%M} às {end:%H:%M}'


class BookingManager(models.Manager):
    def book(self, request, space, day, start, end, approved_by):
        """Cria o agendamento da solicitação aprovada; a restrição do banco é a garantia final."""
        try:
            with transaction.atomic():
                booking = self.create(
                    request=request,
                    space=space,
                    starts_at=moment(day, start),
                    ends_at=moment(day, end),
                    description=request.description,
                    student_count=request.student_count,
                    requested_by_id=request.requested_by_id,
                    approved_by=approved_by,
                )
        except IntegrityError as error:
            raise SlotUnavailable('Este espaço está ocupado nesse horário. Escolha outro horário.') from error
        AuditLog.objects.record(
            catalog.CREATE,
            catalog.BOOKING,
            resource_id=booking.pk,
            new_values={'espaco': space.name, 'data': day.isoformat(), 'horario': hours(start, end), 'solicitacao': request.pk},
        )
        return booking


class Booking(models.Model):
    """Uso eventual aprovado de um espaço, avulso, não recorrente, numa única data."""

    request = models.OneToOneField(
        BookingRequest, on_delete=models.PROTECT, related_name='booking', verbose_name='solicitação',
    )
    space = models.ForeignKey(Space, on_delete=models.PROTECT, related_name='bookings', verbose_name='espaço')
    starts_at = models.DateTimeField('início')
    ends_at = models.DateTimeField('fim')
    description = models.CharField('descrição', max_length=DESCRIPTION_MAX_LENGTH)
    student_count = models.PositiveSmallIntegerField('quantidade de alunos', null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', verbose_name='solicitante',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', verbose_name='aprovado por',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)

    objects = BookingManager()

    class Meta:
        verbose_name = 'agendamento'
        verbose_name_plural = 'agendamentos'
        ordering = ['starts_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__lt=models.F('ends_at')),
                name='booking_range_valid',
                violation_error_message=END_BEFORE_START_MESSAGE,
            ),
            ExclusionConstraint(
                name='booking_no_overlap',
                expressions=[
                    ('space', RangeOperators.EQUAL),
                    (TsTzRange('starts_at', 'ends_at', RangeBoundary()), RangeOperators.OVERLAPS),
                ],
                violation_error_message='Este espaço está ocupado nesse horário.',
            ),
        ]

    def __str__(self):
        return f'{self.space} {self.starts_at:%Y-%m-%d %H:%M}'
