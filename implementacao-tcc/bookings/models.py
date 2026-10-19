"""Solicitação e agendamento; as transições travam a solicitação e o espaço, e a ExclusionConstraint barra a sobreposição."""

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
from schedule.models import Space, TeachingAssignment

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
WEEKEND_MESSAGE = 'Agendamentos só podem ser feitos de segunda a sexta. Escolha outra data.'
SAME_SUGGESTION_MESSAGE = 'A alternativa deve mudar o espaço, a data ou o horário da solicitação.'
OWNER_ONLY_MESSAGE = 'Só quem solicitou pode responder à alternativa.'
PERMISSION_MESSAGE = 'Sem permissão para esta ação na Agenda.'
SEMESTER_REQUIRED_MESSAGE = 'Escolha o semestre.'
REQUESTER_REQUIRED_MESSAGE = 'Escolha o usuário.'
SUBJECT_OUTSIDE_COURSE_MESSAGE = 'Esta disciplina não é do curso escolhido. Escolha outra disciplina.'
CANCEL_DEADLINE_MESSAGE = 'O agendamento só pode ser cancelado até 1 hora antes do início.'
CANCEL_PERMISSION_MESSAGE = 'Só quem solicitou ou quem analisa a Agenda pode cancelar este agendamento.'
ASSIGNMENT_OUTSIDE_SUBJECT_MESSAGE = 'Esta turma não é da disciplina escolhida. Escolha outra turma.'


def without_permission_message(user):
    return f'O usuário {user.username or user.email} não tem permissão para solicitar agendamento. Escolha outro usuário.'


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
    """Recusa de uma ação que o estado atual da solicitação não admite."""

    def __init__(self, status):
        label = BookingRequest.Status(status).label.lower()
        super().__init__(f'Esta solicitação está {label} e não aceita esta ação.', code='invalid_transition')


class SlotUnavailable(ValidationError):
    """Recusa por conflito com o ensalamento ou com outro agendamento aprovado."""

    def __init__(self, message):
        super().__init__(message, code='unavailable')


def hours(start, end):
    return f'{start:%H:%M} às {end:%H:%M}'


def record_transition(action, request, previous, **values):
    """Registra a mudança de estado da solicitação, com o estado anterior e o posterior."""
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
    """Valida espaço, data e horário, deixando o conflito por último."""
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
    """Turma opcional; quando informada, precisa ser vínculo atual do semestre e combinar com curso e disciplina."""
    if on_behalf and not requester.has_perm(permissions.BOOKING_REQUEST):
        raise ValidationError({'requested_for': ValidationError(without_permission_message(requester), code='permission')})
    if semester is None:
        raise ValidationError({'semester': ValidationError(SEMESTER_REQUIRED_MESSAGE, code='required')})
    if assignment is None:
        return
    offering = assignment.offering
    if not assignment.is_current or offering.semester_id != semester.pk:
        raise ValidationError({'teaching_assignment': ValidationError(
            f'Esta turma não está entre as turmas do ensalamento de {semester.code}. Escolha outra turma.', code='not_available',
        )})
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


def check_weekday(day, field='date'):
    """Recusa fim de semana; aprovação e aceite não conferem de novo, para não travar solicitações antigas."""
    if day is not None and day.weekday() >= 5:
        raise ValidationError({field: ValidationError(WEEKEND_MESSAGE, code='weekend')})


class BookingRequestManager(models.Manager):
    def prepare(
        self, user, space, day, start, end, description, student_count=None, semester=None, assignment=None,
        requester=None, course=None, subject=None,
    ):
        """Faz a conferência do envio sem gravar, para a revisão antes da confirmação."""
        requester = requester or user
        on_behalf = requester.pk != user.pk
        require(user, permissions.BOOKING_CREATE if on_behalf else permissions.BOOKING_REQUEST)
        check_assignment(requester, semester, assignment, course, subject, on_behalf=on_behalf)
        check_period(semester, day)
        check_weekday(day)
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
        """Cria a solicitação `PENDENTE` sem ocupar o horário."""
        with transaction.atomic():
            request = self.prepare(
                user, space, day, start, end, description, student_count, semester, assignment, requester, course, subject,
            )
            request.save()
            values = {'situacao': request.status, 'semestre': semester.code}
            if assignment is not None:
                values |= {
                    'docente': assignment.teacher.name,
                    'disciplina': assignment.offering.subject.name,
                    'turma': str(assignment.offering.class_group),
                }
            values |= {
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
    """Os campos originais nunca mudam; a alternativa fica em `suggested_*`, e `created_by` só no pedido em nome de outro."""

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
        """Devolve a solicitação com outra combinação disponível; o aceite verifica de novo."""
        require(user, permissions.BOOKING_REVIEW)
        with transaction.atomic():
            current = self.locked()
            if current.status not in self.OPEN:
                raise InvalidTransition(current.status)
            if (space.pk, day, start, end) == (current.space_id, current.date, current.start_time, current.end_time):
                raise ValidationError(SAME_SUGGESTION_MESSAGE, code='same')
            check_weekday(day, field='suggested_date')
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
        """Cancela até 1 hora antes do início, excluindo o agendamento para liberar o espaço."""
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
