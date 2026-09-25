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
from django.conf import settings
from django.db import IntegrityError, models, transaction
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

    def check_period(self, code, start_date, end_date):
        """Confere as datas do período informadas no envio da importação do semestre (D3).

        As duas datas vão juntas e seguem as regras do período. Em branco, só servem para
        um semestre que já tem período, que é preservado; o semestre novo ou sem período
        exige as duas. O fim nunca é inferido do código. Nada é gravado.
        """
        existing = self.filter(code=(code or '').strip()).first()
        if start_date is None and end_date is None:
            if existing is None or not existing.has_period:
                raise ValidationError({
                    'start_date': ValidationError(PERIOD_REQUIRED_MESSAGE, code='required'),
                    'end_date': ValidationError(PERIOD_REQUIRED_MESSAGE, code='required'),
                })
            return
        candidate = copy(existing) if existing is not None else self.model(code=(code or '').strip())
        candidate.start_date, candidate.end_date = start_date, end_date
        candidate.clean()


PERIOD_REQUIRED_MESSAGE = 'Informe o início e o fim do semestre, que ainda não tem período.'


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
        """Grava o período do semestre e devolve se ele mudou (D2 e D3).

        Quem chama é a importação, que registra o período no resumo auditado; por isso
        esta operação não grava auditoria própria. A recusa não altera o semestre: os
        valores só ficam no objeto depois de validados.
        """
        with transaction.atomic():
            candidate = copy(self)
            candidate.start_date, candidate.end_date = start_date, end_date
            candidate.full_clean()
            if (self.start_date, self.end_date) == (start_date, end_date):
                return False
            self.start_date, self.end_date = start_date, end_date
            self.save(update_fields=['start_date', 'end_date'])
            return True


class SpaceOrigin(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual'
    SPREADSHEET = 'PLANILHA', 'Planilha'


SPACE_NAME_TAKEN_MESSAGE = 'Já existe um espaço com este nome.'
SPACE_PERMISSION_MESSAGE = (
    'A importação encontrou espaços que precisam ser cadastrados ou associados. '
    'O seu perfil não tem permissão para essa configuração.'
)


def name_taken_message(name):
    return f'Já existe um espaço com o nome {name}.'


class SpaceNameTaken(ValidationError):
    """Recusa de uma grafia que já identifica outro espaço, no campo em que ela foi informada."""

    def __init__(self, field, name=None):
        message = name_taken_message(name) if name else SPACE_NAME_TAKEN_MESSAGE
        super().__init__({field: ValidationError(message, code='name_taken')})


class SpaceInUse(ValidationError):
    def __init__(self, name):
        super().__init__(
            f'O espaço {name} tem aulas no ensalamento e não pode ser excluído. Desative o espaço.',
            code='space_in_use',
        )


def distinct_names(values, excluded=()):
    """Nomes normalizados, sem vazios e sem repetição que só difere na caixa, na ordem dada."""
    seen = {name.casefold() for name in excluded}
    names = []
    for value in values:
        name = normalize_name(value)
        if name is None or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        names.append(name)
    return names


SPACE_STATUS_FILTERS = {'ativos': True, 'inativos': False}


class SpaceQuerySet(models.QuerySet):
    def search(self, term='', status='', origin=''):
        """Aplica a busca pelo nome atual ou por outro nome e os filtros de situação e origem."""
        queryset = self
        if term:
            queryset = queryset.filter(pk__in=SpaceName.objects.filter(name__icontains=term).values('space'))
        if status in SPACE_STATUS_FILTERS:
            queryset = queryset.filter(is_active=SPACE_STATUS_FILTERS[status])
        if origin in SpaceOrigin.values:
            queryset = queryset.filter(origin=origin)
        return queryset


class SpaceManager(models.Manager.from_queryset(SpaceQuerySet)):
    """Operações do cadastro de espaços (D2 e D3 da Change manipulacao-dos-espacos).

    Cada operação que altera o cadastro grava o próprio registro de auditoria no módulo
    `ESPACO`, na transação de quem chama. Chamada pela importação, ela roda com a origem de
    importação, e `metadata` leva a chave da importação e quem decidiu.
    """

    def named(self, name):
        """Espaço identificado pelo nome atual ou por um outro nome, sem diferenciar a caixa."""
        normalized = normalize_name(name)
        if normalized is None:
            return None
        found = SpaceName.objects.filter(name__iexact=normalized).select_related('space').first()
        return found.space if found else None

    def register(self, name, other_names=(), origin=SpaceOrigin.MANUAL, source_import=None, metadata=None):
        """Cadastra o espaço com o nome atual e os outros nomes, ativo, e devolve o espaço."""
        current = normalize_name(name)
        if current is None:
            raise ValidationError({'name': ValidationError(NAME_REQUIRED_MESSAGE, code='required')})
        others = distinct_names(other_names, excluded=[current])
        with transaction.atomic():
            refuse_taken(current, others)
            space = self.model(name=current, origin=origin, source_import=source_import, is_active=True)
            space.full_clean()
            space.save()
            save_names(space, [current, *others])
            AuditLog.objects.record(
                catalog.CREATE,
                catalog.SPACE,
                resource_id=space.pk,
                new_values={
                    'name': space.name,
                    'outros_nomes': sorted(others),
                    'origem': space.origin,
                    'importacao': space.source_import_id,
                },
                metadata=metadata,
            )
            return space


def refuse_taken(current, others, space=None):
    """Recusa as grafias que já identificam outro espaço, apontando o campo de cada uma."""
    taken = SpaceName.objects.filter(name__iexact=current)
    if space is not None:
        taken = taken.exclude(space=space)
    if taken.exists():
        raise SpaceNameTaken('name')
    for other in others:
        taken = SpaceName.objects.filter(name__iexact=other)
        if space is not None:
            taken = taken.exclude(space=space)
        if taken.exists():
            raise SpaceNameTaken('other_names', other)


def save_names(space, names):
    """Grava os nomes do espaço; a restrição do banco vira a recusa de grafia já usada."""
    try:
        with transaction.atomic():
            SpaceName.objects.bulk_create(SpaceName(space=space, name=name) for name in names)
    except IntegrityError as error:
        raise SpaceNameTaken('name') from error


class Space(NamedRecord):
    """Espaço físico do campus, com o nome atual, os outros nomes, a origem e a situação.

    A origem e a importação de origem são definidas na criação e nunca mudam: `MANUAL` para
    o cadastro pela tela e `PLANILHA` para o espaço criado pela confirmação de uma
    importação. Todos os nomes que identificam o espaço, o atual inclusive, ficam em
    `SpaceName`, cuja restrição garante que uma grafia identifique um espaço só (D2 e D3 da
    Change manipulacao-dos-espacos).
    """

    origin = models.CharField('origem', max_length=8, choices=SpaceOrigin.choices)
    source_import = models.ForeignKey(
        'imports.Import',
        on_delete=models.PROTECT,
        related_name='+',
        null=True,
        blank=True,
        verbose_name='importação de origem',
    )
    is_active = models.BooleanField('ativo', default=True)

    objects = SpaceManager()

    class Meta(NamedRecord.Meta):
        verbose_name = 'espaço'
        verbose_name_plural = 'espaços'
        constraints = [models.UniqueConstraint(Lower('name'), name='space_name_unique_ci')]

    @property
    def other_names(self):
        """Outros nomes do espaço, em ordem alfabética, sem o nome atual."""
        current = self.name.casefold()
        return sorted((item.name for item in self.names.all() if item.name.casefold() != current), key=str.casefold)

    def snapshot(self):
        return {'name': self.name, 'outros_nomes': self.other_names}

    def lock(self):
        return type(self).objects.select_for_update().get(pk=self.pk)

    def update_details(self, name, other_names):
        """Altera o nome e os outros nomes; o nome anterior passa a ser outro nome.

        Um outro nome escolhido como nome novo deixa de ser outro nome. Origem, importação de
        origem, situação e alocações não mudam.
        """
        current = normalize_name(name)
        if current is None:
            raise ValidationError({'name': ValidationError(NAME_REQUIRED_MESSAGE, code='required')})
        with transaction.atomic():
            space = self.lock()
            previous = space.snapshot()
            kept = [*other_names, space.name] if space.name.casefold() != current.casefold() else list(other_names)
            others = distinct_names(kept, excluded=[current])
            refuse_taken(current, others, space=space)
            space.set_names(current, others)
            AuditLog.objects.record_changes(catalog.SPACE, space.pk, previous, space.snapshot())
        self.refresh_from_db()

    def set_names(self, current, others):
        """Troca os nomes do espaço pelos informados, mantendo os que continuam."""
        wanted = {name.casefold(): name for name in [current, *others]}
        existing = {item.name.casefold(): item for item in self.names.all()}
        self.names.filter(pk__in=[item.pk for key, item in existing.items() if key not in wanted]).delete()
        save_names(self, [name for key, name in wanted.items() if key not in existing])
        if self.name != current:
            self.name = current
            self.full_clean(exclude=['origin', 'source_import'])
            self.save(update_fields=['name'])

    def add_name(self, name, metadata=None):
        """Acrescenta um outro nome ao espaço, pela confirmação de uma importação."""
        with transaction.atomic():
            space = self.lock()
            previous = space.snapshot()
            refuse_taken(space.name, distinct_names([name]), space=space)
            space.set_names(space.name, [*space.other_names, name])
            AuditLog.objects.record_changes(catalog.SPACE, space.pk, previous, space.snapshot(), metadata=metadata)

    def remove_name(self, name, metadata=None):
        """Retira um outro nome do espaço, que volta a ser desconhecido para as importações."""
        with transaction.atomic():
            space = self.lock()
            previous = space.snapshot()
            space.set_names(space.name, [other for other in space.other_names if other.casefold() != name.casefold()])
            AuditLog.objects.record_changes(catalog.SPACE, space.pk, previous, space.snapshot(), metadata=metadata)

    def deactivate(self):
        """Desativa o espaço sem mexer nas alocações; sem efeito quando já está inativo."""
        self.change_status(False, catalog.DEACTIVATE)

    def reactivate(self, metadata=None):
        """Reativa o espaço; sem efeito quando já está ativo."""
        self.change_status(True, catalog.ACTIVATE, metadata)

    def change_status(self, active, action, metadata=None):
        with transaction.atomic():
            space = self.lock()
            if space.is_active == active:
                return
            space.is_active = active
            space.save(update_fields=['is_active'])
            AuditLog.objects.record(action, catalog.SPACE, resource_id=space.pk, metadata=metadata)
        self.refresh_from_db()

    @property
    def is_deletable(self):
        return not self.allocations.exists()

    def delete_space(self):
        """Exclui o espaço sem aula, com os outros nomes e as decisões que o citam (D17)."""
        with transaction.atomic():
            space = self.lock()
            if space.allocations.exists():
                raise SpaceInUse(space.name)
            AuditLog.objects.record(
                catalog.DELETE,
                catalog.SPACE,
                resource_id=space.pk,
                old_values={'name': space.name, 'outros_nomes': space.other_names, 'origem': space.origin},
            )
            space.delete()


class SpaceName(models.Model):
    """Grafia que identifica um espaço: o nome atual ou um outro nome (D2)."""

    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='names', verbose_name='espaço')
    name = models.CharField('nome', max_length=200)

    class Meta:
        verbose_name = 'nome do espaço'
        verbose_name_plural = 'nomes dos espaços'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'), name='space_alias_unique_ci', violation_error_message=SPACE_NAME_TAKEN_MESSAGE,
            ),
        ]

    def __str__(self):
        return self.name


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


def decision_values(decision):
    """Valores canônicos de uma decisão, para o registro de auditoria da importação."""
    if decision is None:
        return {}
    return {
        'nome_encontrado': decision.found_name,
        'decisao': decision.kind,
        'espaco': decision.space.name if decision.space_id else (decision.target_name or None),
    }


class SpaceDecisionManager(models.Manager):
    """Decisões de espaço de uma importação (D9 da Change manipulacao-dos-espacos).

    Gravar ou desfazer uma decisão trava a importação, confere a situação, o nome encontrado,
    o tipo e a permissão de espaço do executor, e registra a auditoria no módulo da
    importação. Nenhuma das duas operações toca no cadastro de espaços: a decisão só é
    aplicada na confirmação. A classificação é importada aqui dentro porque o módulo dela
    depende destes models.
    """

    def locked_import(self, importation):
        from imports.models import Import

        current = Import.objects.select_for_update().get(pk=importation.pk)
        if current.status not in (Import.Status.VALIDATED, Import.Status.PENDING):
            raise ValidationError(
                f'Esta importação está {current.get_status_display().lower()} e não aceita decisões de espaço.',
                code='decision_closed',
            )
        return current

    def check_permissions(self, executor, required):
        if any(not executor.has_perm(code) for code in required):
            raise ValidationError(SPACE_PERMISSION_MESSAGE, code='space_permission')

    def decide(self, importation, found_name, kind, executor, space=None, target_name=''):
        """Grava a decisão do nome encontrado, substituindo a anterior, e devolve a decisão."""
        from schedule import spaces

        with transaction.atomic():
            current = self.locked_import(importation)
            resolution = spaces.classify_import(current)
            entry = resolution.found.get(spaces.key_of(normalize_name(found_name) or ''))
            if entry is None or kind not in spaces.options_of(entry):
                raise ValidationError('Esta decisão não se aplica a este espaço.', code='decision_invalid')
            target_name = normalize_name(target_name) or ''
            if kind == self.model.Kind.SAME:
                target = resolution.found.get(spaces.key_of(target_name)) if target_name else None
                if (space is None) == (target is None):
                    raise ValidationError('Escolha o espaço que é o mesmo.', code='decision_target')
                if target is not None and (target.key == entry.key or target.outcome != spaces.CREATE):
                    raise ValidationError('O espaço escolhido não será cadastrado por esta importação.', code='decision_target')
                if target is not None:
                    target_name = target.name
            else:
                space, target_name = None, ''
            self.check_permissions(executor, spaces.decision_permissions(entry, kind, space, target_name))
            previous = self.filter(importation=current, found_name__iexact=entry.name).select_related('space').first()
            old_values = decision_values(previous)
            if previous is not None:
                previous.delete()
            decision = self.create(
                importation=current, found_name=entry.name, kind=kind, space=space,
                target_name=target_name, decided_by=executor,
            )
            AuditLog.objects.record(
                catalog.UPDATE,
                catalog.SPACE_ALLOCATION_IMPORT,
                resource_id=current.pk,
                old_values=old_values,
                new_values=decision_values(decision),
            )
            return decision

    def withdraw(self, importation, found_name, executor):
        """Desfaz a decisão do nome encontrado, que volta a ser classificado sem ela."""
        from schedule import spaces

        with transaction.atomic():
            current = self.locked_import(importation)
            decision = self.filter(
                importation=current, found_name__iexact=normalize_name(found_name) or '',
            ).select_related('space').first()
            if decision is None:
                raise ValidationError('Este espaço não tem decisão para desfazer.', code='decision_missing')
            entry = spaces.classify_import(current).found.get(spaces.key_of(decision.found_name))
            if entry is not None:
                required = spaces.decision_permissions(entry, decision.kind, decision.space, decision.target_name)
                self.check_permissions(executor, required)
            AuditLog.objects.record(
                catalog.UPDATE,
                catalog.SPACE_ALLOCATION_IMPORT,
                resource_id=current.pk,
                old_values=decision_values(decision),
            )
            decision.delete()


class SpaceDecision(models.Model):
    """Decisão de um usuário sobre um nome de espaço encontrado numa importação (D9).

    Fica guardada na importação e só é aplicada na confirmação: gravar ou desfazer uma
    decisão não altera o cadastro de espaços. `space` é o espaço escolhido ou reativado, e
    `target_name` é o nome encontrado da mesma importação, a ser cadastrado, que recebe este
    nome como outro nome.
    """

    class Kind(models.TextChoices):
        NEW = 'NOVO', 'É um espaço novo'
        SAME = 'ASSOCIAR', 'É o mesmo que'
        REACTIVATE = 'REATIVAR', 'Reativar'

    importation = models.ForeignKey(
        'imports.Import', on_delete=models.CASCADE, related_name='space_decisions', verbose_name='importação',
    )
    found_name = models.CharField('nome encontrado', max_length=200)
    kind = models.CharField('decisão', max_length=8, choices=Kind.choices)
    space = models.ForeignKey(
        Space, on_delete=models.CASCADE, related_name='decisions', null=True, blank=True, verbose_name='espaço',
    )
    target_name = models.CharField('nome de destino', max_length=200, blank=True, default='')
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', verbose_name='decidida por',
    )
    decided_at = models.DateTimeField('decidida em', auto_now=True)

    objects = SpaceDecisionManager()

    class Meta:
        verbose_name = 'decisão de espaço'
        verbose_name_plural = 'decisões de espaço'
        ordering = ['found_name']
        constraints = [
            models.UniqueConstraint('importation', Lower('found_name'), name='space_decision_unique_ci'),
        ]

    def __str__(self):
        return f'{self.found_name}: {self.get_kind_display()}'
