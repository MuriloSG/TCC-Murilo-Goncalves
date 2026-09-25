"""Entidades do ensalamento e as operações que a importação aciona.

As regras de identificação, de deduplicação e de atualização são operações destes models
e dos seus managers, conforme o P2 da Constitution: a importação específica só as chama e
traduz as recusas em erros da linha.

A identidade de uma alocação é semestre, turma, dia da semana, faixa de horário e
disciplina. Não existe restrição sobre semestre, espaço, dia e faixa, porque a planilha
institucional tem aulas compartilhadas por turmas diferentes na mesma sala e no mesmo
horário (D8 da Change importar-ensalamento-da-planilha).
"""

from copy import copy

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower

from audit import catalog
from audit.models import AuditLog
from schedule.utils import normalize_name

SEMESTER_CODE_PATTERN = r'^\d{4}/[12]$'
SEMESTER_CODE_MESSAGE = 'Informe o semestre no formato 2026/1.'
NAME_REQUIRED_MESSAGE = 'Informe o nome.'
PERIOD_MAX_DAYS = 366


class Weekday(models.TextChoices):
    MONDAY = 'SEGUNDA', 'Segunda-feira'
    TUESDAY = 'TERCA', 'Terça-feira'
    WEDNESDAY = 'QUARTA', 'Quarta-feira'
    THURSDAY = 'QUINTA', 'Quinta-feira'
    FRIDAY = 'SEXTA', 'Sexta-feira'


class Stage(models.TextChoices):
    UNDERGRADUATE = 'GRADUACAO', 'Graduação'
    SECONDARY = 'ENSINO_MEDIO', 'Ensino médio'


class Origin(models.TextChoices):
    IMPORTED = 'IMPORTADA', 'Importada'
    MANUAL = 'MANUAL', 'Manual'


def iso(day):
    return day.isoformat() if day else None


def taken_message(verbose_name):
    return f'Já existe {verbose_name} com este nome.'


class NamedManager(models.Manager):
    """Manager dos registros identificados pelo nome, sem diferenciar maiúsculas de minúsculas."""

    def resolve(self, name, **defaults):
        """Devolve o registro deste nome, criando-o quando não existir.

        A procura pela identidade antes de criar é o que impede a importação de duplicar
        um registro, e a restrição de unicidade do banco é a garantia (D12).
        """
        normalized = normalize_name(name)
        if normalized is None:
            raise ValidationError({'name': ValidationError(NAME_REQUIRED_MESSAGE, code='required')})
        with transaction.atomic():
            existing = self.filter(name__iexact=normalized).first()
            if existing is not None:
                return existing, False
            record = self.model(name=normalized, **defaults)
            record.full_clean()
            record.save()
            return record, True


class NamedRecord(models.Model):
    """Registro identificado pelo nome, gravado como informado e único sem diferenciar a caixa.

    A unicidade é conferida no `clean()`, e não pelo `unique=True` do campo, porque o valor
    é gravado como foi lido: sem baixar a caixa, a conferência do campo não alcançaria dois
    valores que diferem só nela. A UniqueConstraint de cada model é a garantia do banco.
    """

    name = models.CharField('nome', max_length=200)

    objects = NamedManager()

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = normalize_name(self.name)
        if self.name is None:
            raise ValidationError({'name': ValidationError(NAME_REQUIRED_MESSAGE, code='required')})
        taken = type(self).objects.filter(name__iexact=self.name)
        if self.pk is not None:
            taken = taken.exclude(pk=self.pk)
        if taken.exists():
            message = taken_message(type(self)._meta.verbose_name)
            raise ValidationError({'name': ValidationError(message, code='name_taken')})


class SemesterManager(models.Manager):
    def resolve(self, code):
        """Devolve o semestre deste código, criando-o quando não existir."""
        normalized = (code or '').strip()
        with transaction.atomic():
            existing = self.filter(code=normalized).first()
            if existing is not None:
                return existing, False
            semester = self.model(code=normalized)
            semester.full_clean()
            semester.save()
            return semester, True


class Semester(models.Model):
    """Semestre letivo, recorte a que pertencem as faixas de horário e as alocações.

    O período é opcional: a planilha não o traz, e sem ele a Grade mostra a semana típica.
    Com ele, as alocações do semestre viram ocorrências datadas (D2 da Change
    visualizar-ocupacao-por-semana-e-mes).
    """

    code = models.CharField(
        'código',
        max_length=6,
        unique=True,
        validators=[RegexValidator(SEMESTER_CODE_PATTERN, message=SEMESTER_CODE_MESSAGE)],
        error_messages={'unique': 'Já existe um semestre com este código.'},
    )
    start_date = models.DateField('início', null=True, blank=True)
    end_date = models.DateField('fim', null=True, blank=True)

    objects = SemesterManager()

    class Meta:
        verbose_name = 'semestre'
        verbose_name_plural = 'semestres'
        ordering = ['-code']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(start_date__isnull=True, end_date__isnull=True)
                    | models.Q(start_date__isnull=False, end_date__isnull=False, start_date__lte=models.F('end_date'))
                ),
                name='semester_period_valid',
                violation_error_message='Informe o início e o fim, com o início até o fim.',
            ),
        ]

    def __str__(self):
        return self.code

    @property
    def has_period(self):
        return self.start_date is not None and self.end_date is not None

    def contains(self, day):
        """Diz se a data está no período do semestre; sem período, nenhuma data está."""
        return self.has_period and self.start_date <= day <= self.end_date

    def clean(self):
        super().clean()
        if (self.start_date is None) != (self.end_date is None):
            missing = 'start_date' if self.start_date is None else 'end_date'
            raise ValidationError({missing: ValidationError('Informe o início e o fim do período.', code='required')})
        if self.has_period and self.start_date > self.end_date:
            raise ValidationError(
                {'end_date': ValidationError('O fim deve ser igual ou posterior ao início.', code='invalid_range')},
            )
        if self.has_period and (self.end_date - self.start_date).days >= PERIOD_MAX_DAYS:
            raise ValidationError(
                {'end_date': ValidationError('O período deve ter no máximo 366 dias.', code='too_long')},
            )

    def define_period(self, start_date, end_date):
        """Grava o período do semestre e registra a alteração na auditoria (D3).

        A recusa não altera o semestre: os valores só ficam no objeto depois de validados.
        """
        with transaction.atomic():
            previous = {'inicio': iso(self.start_date), 'fim': iso(self.end_date)}
            candidate = copy(self)
            candidate.start_date, candidate.end_date = start_date, end_date
            candidate.full_clean()
            self.start_date, self.end_date = start_date, end_date
            self.save(update_fields=['start_date', 'end_date'])
            AuditLog.objects.record_changes(
                catalog.SEMESTER, self.code, previous, {'inicio': iso(start_date), 'fim': iso(end_date)},
            )


class Space(NamedRecord):
    """Espaço em que uma turma é ensalada, vindo da lista de salas da planilha."""

    class Meta(NamedRecord.Meta):
        verbose_name = 'espaço'
        verbose_name_plural = 'espaços'
        constraints = [models.UniqueConstraint(Lower('name'), name='space_name_unique_ci')]


class Teacher(NamedRecord):
    """Docente do ensalamento, identificado pelo nome que a planilha usa.

    O nome guarda o mesmo valor que o `User.username`, com a mesma normalização, e é isso
    que torna possível uma correspondência futura exata com um usuário existente. Este
    model não tem vínculo com `User`, e a importação não cria nem consulta usuário (D7).
    """

    class Meta(NamedRecord.Meta):
        verbose_name = 'docente'
        verbose_name_plural = 'docentes'
        constraints = [models.UniqueConstraint(Lower('name'), name='teacher_name_unique_ci')]


class Course(NamedRecord):
    """Curso a que pertencem as turmas de um grupo de colunas da planilha."""

    stage = models.CharField('etapa de ensino', max_length=12, choices=Stage.choices)

    class Meta(NamedRecord.Meta):
        verbose_name = 'curso'
        verbose_name_plural = 'cursos'
        constraints = [models.UniqueConstraint(Lower('name'), name='course_name_unique_ci')]


class Subject(NamedRecord):
    """Disciplina, única pelo nome em todo o sistema.

    Não é por curso porque a planilha mostra a mesma disciplina atendendo turmas de cursos
    diferentes, na mesma sala e no mesmo horário (D12).
    """

    class Meta(NamedRecord.Meta):
        verbose_name = 'disciplina'
        verbose_name_plural = 'disciplinas'
        constraints = [models.UniqueConstraint(Lower('name'), name='subject_name_unique_ci')]


class ClassGroupManager(models.Manager):
    def resolve(self, course, label):
        """Devolve a turma deste curso e rótulo, criando-a quando não existir."""
        normalized = normalize_name(label)
        if normalized is None:
            raise ValidationError({'label': ValidationError('Informe o rótulo da turma.', code='required')})
        with transaction.atomic():
            existing = self.filter(course=course, label__iexact=normalized).first()
            if existing is not None:
                return existing, False
            group = self.model(course=course, label=normalized)
            group.full_clean()
            group.save()
            return group, True


class ClassGroup(models.Model):
    """Turma de um curso, identificada pelo rótulo do cabeçalho da coluna da planilha."""

    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='class_groups', verbose_name='curso')
    label = models.CharField('rótulo', max_length=200)

    objects = ClassGroupManager()

    class Meta:
        verbose_name = 'turma'
        verbose_name_plural = 'turmas'
        ordering = ['course__name', 'label']
        constraints = [
            models.UniqueConstraint(
                'course', Lower('label'), name='class_group_label_unique_ci',
                violation_error_message='Já existe uma turma com este rótulo neste curso.',
            ),
        ]

    def __str__(self):
        return f'{self.label} ({self.course.name})'

    @property
    def stage(self):
        """A etapa da turma é a do curso, e não um dado próprio."""
        return self.course.stage

    def clean(self):
        super().clean()
        self.label = normalize_name(self.label)
        if self.label is None:
            raise ValidationError({'label': ValidationError('Informe o rótulo da turma.', code='required')})
        taken = type(self).objects.filter(course=self.course_id, label__iexact=self.label)
        if self.pk is not None:
            taken = taken.exclude(pk=self.pk)
        if taken.exists():
            raise ValidationError(
                {'label': ValidationError('Já existe uma turma com este rótulo neste curso.', code='label_taken')},
            )


class TimeSlotManager(models.Manager):
    def resolve(self, semester, start_time, end_time):
        """Devolve a faixa de horário deste semestre, criando-a quando não existir."""
        with transaction.atomic():
            existing = self.filter(semester=semester, start_time=start_time, end_time=end_time).first()
            if existing is not None:
                return existing, False
            slot = self.model(semester=semester, start_time=start_time, end_time=end_time)
            slot.full_clean()
            slot.save()
            return slot, True


class TimeSlot(models.Model):
    """Faixa de horário de um semestre, com o início e o fim que a planilha traz."""

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name='time_slots', verbose_name='semestre',
    )
    start_time = models.TimeField('início')
    end_time = models.TimeField('fim')

    objects = TimeSlotManager()

    class Meta:
        verbose_name = 'faixa de horário'
        verbose_name_plural = 'faixas de horário'
        ordering = ['start_time', 'end_time']
        constraints = [
            models.UniqueConstraint(
                fields=['semester', 'start_time', 'end_time'],
                name='time_slot_unique',
                violation_error_message='Já existe esta faixa de horário neste semestre.',
            ),
            models.CheckConstraint(
                condition=models.Q(start_time__lt=models.F('end_time')),
                name='time_slot_start_before_end',
                violation_error_message='O início deve ser anterior ao fim.',
            ),
        ]

    def __str__(self):
        return f'{self.start_time:%H:%M} - {self.end_time:%H:%M}'

    def clean(self):
        super().clean()
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValidationError(
                {'end_time': ValidationError('O início deve ser anterior ao fim.', code='invalid_range')},
            )


def teacher_names(teachers):
    return sorted(teacher.name for teacher in teachers)


class AllocationManager(models.Manager):
    def apply(self, semester, class_group, subject, weekday, time_slot, space=None, teachers=()):
        """Cria a alocação ou atualiza o espaço e os docentes da que já existe.

        Devolve a alocação, a ação (`create`, `update` ou `unchanged`) e as mudanças, com o
        valor anterior e o novo de cada campo alterado, em valores canônicos. Nada é
        excluído: uma alocação que deixou de constar na planilha é preservada (D13).
        """
        teachers = list(teachers)
        names = teacher_names(teachers)
        with transaction.atomic():
            existing = self.filter(
                semester=semester,
                class_group=class_group,
                subject=subject,
                weekday=weekday,
                time_slot=time_slot,
            ).first()
            if existing is None:
                allocation = self.model(
                    semester=semester,
                    class_group=class_group,
                    subject=subject,
                    weekday=weekday,
                    time_slot=time_slot,
                    space=space,
                    origin=Origin.IMPORTED,
                )
                allocation.full_clean(exclude=['space'])
                allocation.save()
                allocation.teachers.set(teachers)
                changes = {
                    'space': [None, space.name if space else None],
                    'teachers': [None, names],
                }
                return allocation, 'create', changes
            return existing, *existing.update_details(space, teachers)


class Allocation(models.Model):
    """Ocupação recorrente de um espaço por uma turma, numa disciplina, num dia e numa faixa.

    O espaço e os docentes podem faltar, porque a planilha traz atividade sem sala e
    atividade sem docente reconhecido. Duas alocações do mesmo semestre podem ter o mesmo
    espaço, dia e faixa: é a aula compartilhada por turmas diferentes, e não um conflito.
    O sistema não detecta conflito de espaço nem de docente (D8).
    """

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name='allocations', verbose_name='semestre',
    )
    class_group = models.ForeignKey(
        ClassGroup, on_delete=models.PROTECT, related_name='allocations', verbose_name='turma',
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='allocations', verbose_name='disciplina',
    )
    space = models.ForeignKey(
        Space, on_delete=models.PROTECT, related_name='allocations', null=True, blank=True, verbose_name='espaço',
    )
    teachers = models.ManyToManyField(Teacher, related_name='allocations', blank=True, verbose_name='docentes')
    weekday = models.CharField('dia da semana', max_length=8, choices=Weekday.choices)
    time_slot = models.ForeignKey(
        TimeSlot, on_delete=models.PROTECT, related_name='allocations', verbose_name='faixa de horário',
    )
    origin = models.CharField('origem', max_length=9, choices=Origin.choices, default=Origin.IMPORTED)

    objects = AllocationManager()

    class Meta:
        verbose_name = 'alocação'
        verbose_name_plural = 'alocações'
        ordering = ['weekday', 'time_slot__start_time', 'class_group__label']
        constraints = [
            models.UniqueConstraint(
                fields=['semester', 'class_group', 'weekday', 'time_slot', 'subject'],
                name='allocation_unique',
                violation_error_message='Esta turma já tem esta disciplina nesta faixa de horário deste dia.',
            ),
        ]
        indexes = [
            models.Index(fields=['semester', 'space', 'weekday'], name='allocation_space_idx'),
            models.Index(fields=['semester', 'weekday', 'time_slot'], name='allocation_slot_idx'),
            models.Index(fields=['semester', 'class_group'], name='allocation_group_idx'),
        ]

    def __str__(self):
        return f'{self.semester} {self.get_weekday_display()} {self.time_slot} {self.subject}'

    def clean(self):
        super().clean()
        if self.time_slot_id and self.semester_id and self.time_slot.semester_id != self.semester_id:
            raise ValidationError(
                {'time_slot': ValidationError('A faixa de horário é de outro semestre.', code='other_semester')},
            )

    def update_details(self, space, teachers):
        """Atualiza o espaço e os docentes, devolvendo a ação e as mudanças.

        Só estes dois campos mudam sem criar registro novo: os demais fazem parte da
        identidade da alocação (D12).
        """
        names = teacher_names(teachers)
        current_names = teacher_names(self.teachers.all())
        changes = {}
        if (self.space.name if self.space else None) != (space.name if space else None):
            changes['space'] = [self.space.name if self.space else None, space.name if space else None]
        if current_names != names:
            changes['teachers'] = [current_names, names]
        if not changes:
            return 'unchanged', {}
        with transaction.atomic():
            if 'space' in changes:
                self.space = space
                self.save(update_fields=['space'])
            if 'teachers' in changes:
                self.teachers.set(teachers)
        return 'update', changes
