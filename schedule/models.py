"""Entidades do ensalamento e as operações que a importação aciona.

As regras de identificação, de deduplicação e de atualização são operações destes models
e dos seus managers, conforme o P2 da Constitution: a importação específica só as chama e
traduz as recusas em erros da linha.

A identidade de uma alocação é semestre, turma, dia da semana, faixa de horário e
disciplina, mais o início da vigência, que separa as versões de uma recorrência alterada
(Change alterar-recorrencia-do-ensalamento). Não existe restrição sobre semestre, espaço,
dia e faixa, porque a planilha institucional tem aulas compartilhadas por turmas diferentes
na mesma sala e no mesmo horário (D8 da Change importar-ensalamento-da-planilha).
"""

from copy import copy
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.formats import date_format

from accounts import permissions

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


class SpaceWithBookings(ValidationError):
    """Recusa da exclusão de um espaço citado por solicitações de agendamento da Agenda.

    A solicitação e o agendamento protegem o espaço (D3 da Change
    agendar-uso-eventual-dos-espacos); sem esta recusa, a exclusão falharia no banco.
    """

    def __init__(self, name):
        super().__init__(
            f'O espaço {name} tem solicitações de agendamento na Agenda e não pode ser excluído. Desative o espaço.',
            code='space_with_bookings',
        )


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
            try:
                space.delete()
            except models.ProtectedError as error:
                raise SpaceWithBookings(space.name) from error


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


class AcademicRecordInUse(ValidationError):
    """Recusa de renomear ou excluir disciplina ou turma que o ensalamento já usa.

    Com oferta ou aula, a importação identifica o registro pelo nome ou pelo rótulo: renomear
    faria a próxima importação criar outro registro com o nome da planilha, e excluir é barrado
    pelo `PROTECT` das alocações e das ofertas (D8 e D9 da Change gerenciar-disciplinas-e-turmas).
    """

    def __init__(self, description, operation):
        if operation == 'renomear':
            message = (
                f'{description} tem ofertas ou aulas no ensalamento e não pode ser renomeada, '
                'porque a próxima importação criaria outro cadastro com o nome da planilha.'
            )
        else:
            message = f'{description} tem ofertas ou aulas no ensalamento e não pode ser excluída.'
        super().__init__(message, code='academic_record_in_use')


def teacher_scope(queryset, user):
    """Registros do escopo do usuário, filtrados no banco (D1 e D2 da Change gerenciar-disciplinas-e-turmas).

    O superadmin alcança todos. Os demais alcançam as disciplinas ou turmas das ofertas em que
    o docente correspondente ao usuário (`teacher_of`) tem vínculo, atual ou histórico. Sem
    docente correspondente, o escopo é vazio. Não há vínculo gravado entre usuário e registro.
    """
    if user.is_active and user.is_superadmin:
        return queryset
    teacher = teacher_of(user)
    if teacher is None:
        return queryset.none()
    return queryset.filter(offerings__assignments__teacher=teacher).distinct()


class SubjectQuerySet(models.QuerySet):
    def visible_to(self, user):
        return teacher_scope(self, user)

    def search(self, term=''):
        return self.filter(name__icontains=term) if term else self


class SubjectManager(NamedManager.from_queryset(SubjectQuerySet)):
    def register(self, name):
        """Cadastra a disciplina pela tela de Disciplinas, com o registro de auditoria."""
        with transaction.atomic():
            subject = self.model(name=name)
            subject.full_clean()
            subject.save()
            AuditLog.objects.record(catalog.CREATE, catalog.SUBJECT, resource_id=subject.pk, new_values=subject.snapshot())
            return subject


class Subject(NamedRecord):
    """Disciplina, única pelo nome em todo o sistema.

    Não é por curso porque a planilha mostra a mesma disciplina atendendo turmas de cursos
    diferentes, na mesma sala e no mesmo horário (D12).
    """

    objects = SubjectManager()

    class Meta(NamedRecord.Meta):
        verbose_name = 'disciplina'
        verbose_name_plural = 'disciplinas'
        constraints = [models.UniqueConstraint(Lower('name'), name='subject_name_unique_ci')]

    @property
    def description(self):
        return f'A disciplina {self.name}'

    @property
    def is_in_use(self):
        """Diz se o ensalamento usa a disciplina, por oferta ou por aula."""
        return self.offerings.exists() or self.allocations.exists()

    def snapshot(self):
        return {'name': self.name}

    def lock(self):
        return type(self).objects.select_for_update().get(pk=self.pk)

    def update_details(self, name):
        """Altera o nome, recusado quando a disciplina tem uso no ensalamento; sem efeito quando igual."""
        with transaction.atomic():
            subject = self.lock()
            previous = subject.snapshot()
            subject.name = name
            subject.full_clean()
            if subject.name == previous['name']:
                return
            if subject.is_in_use:
                raise AcademicRecordInUse(f'A disciplina {previous["name"]}', 'renomear')
            subject.save(update_fields=['name'])
            AuditLog.objects.record_changes(catalog.SUBJECT, subject.pk, previous, subject.snapshot())
        self.refresh_from_db()

    def delete_subject(self):
        """Exclui a disciplina sem oferta e sem aula, com o registro de auditoria."""
        with transaction.atomic():
            subject = self.lock()
            if subject.is_in_use:
                raise AcademicRecordInUse(subject.description, 'excluir')
            AuditLog.objects.record(catalog.DELETE, catalog.SUBJECT, resource_id=subject.pk, old_values=subject.snapshot())
            try:
                subject.delete()
            except models.ProtectedError as error:
                raise AcademicRecordInUse(subject.description, 'excluir') from error


class ClassGroupQuerySet(models.QuerySet):
    def visible_to(self, user):
        return teacher_scope(self, user)

    def search(self, term='', course=None):
        """Busca pelo rótulo ou pelo nome do curso e filtra pelo curso informado."""
        queryset = self
        if term:
            queryset = queryset.filter(models.Q(label__icontains=term) | models.Q(course__name__icontains=term))
        if course is not None:
            queryset = queryset.filter(course=course)
        return queryset


class ClassGroupManager(models.Manager.from_queryset(ClassGroupQuerySet)):
    def register(self, course, label):
        """Cadastra a turma do curso pela tela de Turmas, com o registro de auditoria."""
        with transaction.atomic():
            group = self.model(course=course, label=label)
            group.full_clean()
            group.save()
            AuditLog.objects.record(catalog.CREATE, catalog.CLASS_GROUP, resource_id=group.pk, new_values=group.snapshot())
            return group

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

    @property
    def description(self):
        return f'A turma {self.label} de {self.course.name}'

    @property
    def is_in_use(self):
        """Diz se o ensalamento usa a turma, por oferta ou por aula."""
        return self.offerings.exists() or self.allocations.exists()

    def snapshot(self):
        return {'curso': self.course.name, 'rotulo': self.label}

    def lock(self):
        return type(self).objects.select_for_update().select_related('course').get(pk=self.pk)

    def update_details(self, label, course=None):
        """Altera o rótulo; o curso é imutável e a turma com uso no ensalamento não é renomeada.

        O curso chega do formulário mesmo sem poder mudar, para que um valor forjado seja
        recusado com mensagem, e não ignorado.
        """
        with transaction.atomic():
            group = self.lock()
            if course is not None and course.pk != group.course_id:
                raise ValidationError(
                    {'course': ValidationError('O curso da turma não pode ser alterado.', code='course_immutable')},
                )
            previous = group.snapshot()
            group.label = label
            group.full_clean()
            if group.label == previous['rotulo']:
                return
            if group.is_in_use:
                raise AcademicRecordInUse(f'A turma {previous["rotulo"]} de {group.course.name}', 'renomear')
            group.save(update_fields=['label'])
            AuditLog.objects.record_changes(catalog.CLASS_GROUP, group.pk, previous, group.snapshot())
        self.refresh_from_db()

    def delete_class_group(self):
        """Exclui a turma sem oferta e sem aula, com o registro de auditoria."""
        with transaction.atomic():
            group = self.lock()
            if group.is_in_use:
                raise AcademicRecordInUse(group.description, 'excluir')
            AuditLog.objects.record(catalog.DELETE, catalog.CLASS_GROUP, resource_id=group.pk, old_values=group.snapshot())
            try:
                group.delete()
            except models.ProtectedError as error:
                raise AcademicRecordInUse(group.description, 'excluir') from error


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

        Quando a identidade pertence a uma recorrência alterada no sistema, com vigência
        definida, nada muda e a alocação versionada é devolvida como `unchanged`: a planilha
        não reescreve o histórico nem recria a regra encerrada (D7 da Change
        alterar-recorrencia-do-ensalamento). A importação avisa isso na linha.
        """
        teachers = list(teachers)
        names = teacher_names(teachers)
        with transaction.atomic():
            versions = list(self.filter(
                semester=semester,
                class_group=class_group,
                subject=subject,
                weekday=weekday,
                time_slot=time_slot,
            ).order_by('valid_from', 'pk'))
            versioned = next((version for version in versions if version.is_versioned), None)
            if versioned is not None:
                return versioned, 'unchanged', {}
            existing = versions[0] if versions else None
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

    def active_on(self, day):
        """Alocações que ocorrem na data: o dia da semana dela, o período do semestre, a
        vigência e sem exceção nesta data. É a mesma regra de `Allocation.occurs_on`, em consulta."""
        if day.weekday() >= len(WEEKDAY_ORDER):
            return self.none()
        return self.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=day),
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=day),
            weekday=WEEKDAY_ORDER[day.weekday()],
            semester__start_date__lte=day,
            semester__end_date__gte=day,
        ).exclude(exceptions__date=day)

    def change_recurrence(self, allocation_ids, cut, executor, weekday, start_time, space, teachers):
        """Altera a recorrência das alocações de uma aula a partir da data de corte.

        Cada alocação é encerrada na véspera do corte e uma nova versão começa nele, com os
        dados informados e o resto copiado. As exceções do corte em diante passam para a
        versão nova. Tudo numa transação: uma recusa ou uma falha não deixa nada gravado.
        Devolve o plano executado, com as versões novas gravadas.
        """
        with transaction.atomic():
            plan = self.plan_recurrence(allocation_ids, cut, executor, weekday, start_time, space, teachers)
            for change in plan.changes:
                change.execute(cut)
            return plan

    def plan_recurrence(self, allocation_ids, cut, executor, weekday, start_time, space, teachers):
        """Confere a alteração da recorrência e devolve o plano, sem gravar nada.

        As alocações são travadas quando há transação aberta, como no cancelamento. É a
        mesma conferência da execução, usada para o resumo mostrado antes da confirmação.
        """
        allocation_ids = sorted(set(allocation_ids))
        with transaction.atomic():
            locked = list(
                self.select_for_update(of=('self',))
                .filter(pk__in=allocation_ids)
                .select_related('semester', 'subject', 'time_slot', 'space', 'class_group__course')
                .prefetch_related('teachers')
                .order_by('time_slot__start_time', 'pk'),
            )
            if not allocation_ids or len(locked) != len(allocation_ids):
                raise ValidationError('A aula informada não existe. Atualize a Grade.', code='missing')
            if not executor.has_perm(permissions.SPACE_ALLOCATION_CHANGE_RECURRENCE):
                raise ValidationError('Só quem tem permissão altera a recorrência desta aula.', code='not_allowed')
            first = locked[0]
            if any(
                (item.semester_id, item.class_group_id, item.subject_id, item.weekday)
                != (first.semester_id, first.class_group_id, first.subject_id, first.weekday)
                for item in locked
            ):
                raise ValidationError('A aula informada não existe. Atualize a Grade.', code='missing')
            semester = first.semester
            check_cut(locked, cut)
            slots = consecutive_slots(semester, start_time, len(locked))
            if slots is None:
                raise ValidationError(
                    {'horario': ValidationError('Escolha um horário do semestre.', code='invalid_slot')},
                )
            teachers = sorted(teachers, key=lambda teacher: teacher.name)
            if space is not None and not space.is_active and space.pk != first.space_id:
                raise ValidationError(
                    {'espaco': ValidationError(f'O espaço {space.name} está desativado. Escolha outro espaço.', code='inactive')},
                )
            changes = [
                RecurrenceChange(current=item, version=Allocation(
                    semester=semester,
                    class_group=item.class_group,
                    subject=item.subject,
                    space=space,
                    weekday=weekday,
                    time_slot=slot,
                    origin=Origin.MANUAL,
                    valid_from=cut,
                    valid_until=item.valid_until,
                ), teachers=teachers)
                for item, slot in zip(locked, slots)
            ]
            plan = RecurrencePlan(cut=cut, changes=changes, executor=executor)
            if plan.before == plan.after:
                raise ValidationError('Altere ao menos um dado da recorrência.', code='unchanged')
            plan.load_exceptions()
            check_duplicates(plan)
            check_conflicts(plan)
            return plan

    def managed_by(self, user):
        """Alocações cujas ocorrências o usuário pode cancelar, pela mesma regra de `manages`."""
        if user.has_perm(permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE):
            return self.all()
        if not user.is_active or not user.username:
            return self.none()
        return self.filter(teachers__name__iexact=user.username).distinct()


WEEKDAY_ORDER = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]


def shown_date(day):
    return date_format(day, 'SHORT_DATE_FORMAT')


def check_cut(allocations, cut):
    """Confere a data de corte: hoje ou depois, no semestre, ocorrência da regra atual e
    depois do início da vigência, para que a versão encerrada guarde alguma data."""
    semester = allocations[0].semester
    if cut < timezone.localdate():
        raise ValidationError(
            {'data': ValidationError('Escolha uma data a partir de hoje. As ocorrências passadas não mudam.', code='past')},
        )
    if not semester.contains(cut):
        raise ValidationError(
            {'data': ValidationError(f'A data {shown_date(cut)} está fora do período do semestre {semester}.', code='outside')},
        )
    for allocation in allocations:
        if not allocation.occurs_on(cut):
            raise ValidationError(
                {'data': ValidationError(f'A aula não acontece em {shown_date(cut)}. Escolha uma data da aula.', code='not_occurrence')},
            )
        if cut <= allocation.starts:
            raise ValidationError(
                {'data': ValidationError(
                    f'A recorrência começa em {shown_date(allocation.starts)}. Escolha uma data posterior.', code='first_date',
                )},
            )


def consecutive_slots(semester, start_time, count):
    """Faixas seguidas do semestre, `count` delas, a partir da que começa em `start_time`.

    Cada faixa começa quando a anterior termina, como nos blocos da Grade. Devolve None
    quando o semestre não tem essas faixas; nenhuma faixa é criada.
    """
    by_start = {slot.start_time: slot for slot in TimeSlot.objects.filter(semester=semester)}
    found, current = [], by_start.get(start_time)
    while current is not None and len(found) < count:
        found.append(current)
        current = by_start.get(current.end_time)
    return found if len(found) == count else None


def interval_choices(semester, count):
    """Intervalos de `count` faixas seguidas do semestre, como opções do formulário."""
    slots = sorted(TimeSlot.objects.filter(semester=semester), key=lambda slot: slot.start_time)
    by_start = {slot.start_time: slot for slot in slots}
    choices = []
    for slot in slots:
        chain = [slot]
        while len(chain) < count and chain[-1].end_time in by_start:
            chain.append(by_start[chain[-1].end_time])
        if len(chain) == count:
            choices.append((slot.start_time, chain[-1].end_time))
    return choices


def check_duplicates(plan):
    """Recusa uma versão nova que repete a turma, a disciplina, o dia e a faixa de outra
    alocação vigente no mesmo período, que a restrição de identidade não alcança."""
    first = plan.changes[0].version
    locked = [change.current.pk for change in plan.changes]
    for change in plan.changes:
        version = change.version
        taken = (
            Allocation.objects.filter(
                semester=version.semester,
                class_group=version.class_group,
                subject=version.subject,
                weekday=version.weekday,
                time_slot=version.time_slot,
            )
            .exclude(pk__in=locked)
            .filter(models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=plan.cut))
        )
        if version.valid_until is not None:
            taken = taken.filter(models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=version.valid_until))
        if taken.exists():
            raise ValidationError(
                f'A turma {first.class_group} já tem {first.subject} neste horário deste dia. Escolha outro horário.',
                code='duplicate',
            )


def check_conflicts(plan):
    """Recusa a alteração quando o espaço está ocupado em alguma ocorrência da versão nova.

    As ocupações vêm das mesmas fontes da Grade, a partir do corte até o fim da vigência:
    o ensalamento, já sem as ocorrências canceladas e com a vigência de cada alocação, e
    os agendamentos aprovados da Agenda. Outra aula com a mesma disciplina e os mesmos
    docentes é turma junta e não conflita; o resto é choque (D6). A importação é feita
    aqui dentro porque o módulo da ocupação depende destes models.
    """
    from schedule.occupancy import grid_sources

    first = plan.changes[0].version
    if first.space is None:
        return
    end = plan.changes[0].ends
    days = [
        day for day in dates_from(plan.cut, end)
        if first.occurs_on(day) and day not in plan.moved_dates
    ]
    if not days:
        return
    start_at, end_at = plan.changes[0].version.time_slot.start_time, plan.changes[-1].version.time_slot.end_time
    locked = {change.current.pk for change in plan.changes}
    wanted = set(days)
    lesson = (first.subject.name.casefold(), frozenset(teacher.name.casefold() for teacher in plan.changes[0].teachers))
    found = []
    for source in grid_sources():
        for occurrence in source.occurrences(first.space, days[0], days[-1]):
            if occurrence.date not in wanted or not (occurrence.start < end_at and occurrence.end > start_at):
                continue
            entry = occurrence.entry
            if getattr(entry, 'is_booking', False):
                found.append((occurrence, None))
                continue
            if set(entry.allocation_ids) & locked:
                continue
            other = (entry.subject.casefold(), frozenset(name.casefold() for name in entry.teachers))
            if other != lesson:
                found.append((occurrence, entry))
    if not found:
        return
    occurrence, entry = min(found, key=lambda item: (item[0].date, item[0].start))
    when = f'em {shown_date(occurrence.date)}, das {occurrence.start:%H:%M} às {occurrence.end:%H:%M}'
    if entry is None:
        message = f'O espaço {first.space.name} tem um agendamento aprovado {when}. Escolha outro espaço ou horário.'
    else:
        message = (
            f'O espaço {first.space.name} está ocupado pela aula de {entry.subject} ({entry.group_label}) {when}. '
            'Escolha outro espaço ou horário.'
        )
    raise ValidationError(message, code='conflict')


def dates_from(start, end):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def slot_text(start, end):
    return f'{start:%H:%M} às {end:%H:%M}'


@dataclass
class RecurrenceChange:
    """Uma alocação da aula, a versão nova que a substitui a partir do corte e as exceções
    que passam para ela."""

    current: object
    version: object
    teachers: list
    moved: list = field(default_factory=list)

    @property
    def ends(self):
        return self.current.ends

    def execute(self, cut):
        """Encerra a alocação na véspera do corte, grava a versão nova, move as exceções e
        registra a auditoria."""
        current, version = self.current, self.version
        previous = current.audit_values()
        current.valid_until = cut - timedelta(days=1)
        current.full_clean(exclude=['space'])
        current.save(update_fields=['valid_until'])
        version.full_clean(exclude=['space'])
        version.save()
        version.teachers.set(self.teachers)
        ClassOffering.objects.record(version.semester, version.subject, version.class_group)
        moved_ids = [exception.pk for exception in self.moved]
        AllocationException.objects.filter(pk__in=moved_ids).update(allocation=version)
        for exception in self.moved:
            AuditLog.objects.record(
                catalog.UPDATE,
                catalog.SPACE_ALLOCATION_EXCEPTION,
                resource_id=exception.pk,
                old_values={'alocacao': current.pk},
                new_values={'alocacao': version.pk},
                metadata={'data': iso(exception.date), 'a_partir_de': iso(cut)},
            )
        after = version.audit_values()
        changed = [key for key in ('dia', 'horario', 'espaco', 'docentes') if previous[key] != after[key]]
        AuditLog.objects.record(
            catalog.UPDATE,
            catalog.SPACE_ALLOCATION,
            resource_id=current.pk,
            old_values={key: previous[key] for key in changed},
            new_values={key: after[key] for key in changed},
            metadata=previous | {
                'vigente_ate': iso(current.valid_until),
                'a_partir_de': iso(cut),
                'nova_alocacao': version.pk,
                'excecoes_transferidas': sorted(iso(exception.date) for exception in self.moved),
            },
        )


@dataclass(frozen=True)
class RecurrenceSummary:
    """Dia, horário, espaço e docentes de uma aula, como o resumo da alteração mostra."""

    weekday: str
    start: object
    end: object
    space: str
    teachers: tuple

    @property
    def text(self):
        parts = [Weekday(self.weekday).label, f'das {slot_text(self.start, self.end)}', self.space or 'Sem espaço']
        return ', '.join(parts)


def summary_of(allocations, teachers):
    first, last = allocations[0], allocations[-1]
    return RecurrenceSummary(
        weekday=first.weekday,
        start=first.time_slot.start_time,
        end=last.time_slot.end_time,
        space=first.space.name if first.space else '',
        teachers=tuple(teacher.name for teacher in teachers),
    )


@dataclass
class RecurrencePlan:
    """Alteração conferida da recorrência de uma aula: o corte, cada alocação com a versão
    nova e o resumo de antes e de depois."""

    cut: object
    changes: list
    executor: object = None

    @property
    def lesson(self):
        return self.changes[0].current

    @property
    def before(self):
        return summary_of(
            [change.current for change in self.changes], sorted(self.lesson.teachers.all(), key=lambda item: item.name),
        )

    @property
    def after(self):
        return summary_of([change.version for change in self.changes], self.changes[0].teachers)

    @property
    def moved_dates(self):
        return sorted({exception.date for change in self.changes for exception in change.moved})

    def load_exceptions(self):
        """Separa as exceções do corte em diante, que passam para a versão nova.

        Uma exceção cuja data não é ocorrência da versão nova recusa a alteração, para que
        nenhum cancelamento seja perdido em silêncio (D5).
        """
        by_allocation = {}
        for exception in AllocationException.objects.filter(
            allocation__in=[change.current.pk for change in self.changes], date__gte=self.cut,
        ).order_by('date'):
            by_allocation.setdefault(exception.allocation_id, []).append(exception)
        lost = set()
        for change in self.changes:
            change.moved = by_allocation.get(change.current.pk, [])
            lost |= {exception.date for exception in change.moved if not change.version.occurs_on(exception.date)}
        if lost:
            dates = ', '.join(shown_date(day) for day in sorted(lost))
            raise ValidationError(
                f'As ocorrências canceladas de {dates} não são datas da nova recorrência. '
                'Mantenha o dia da semana ou escolha uma data de início posterior a elas.',
                code='exceptions',
            )


def teacher_of(user):
    """Docente do ensalamento que corresponde ao usuário, ou None.

    É a mesma regra de `manages`: o nome do docente igual ao `username`, sem diferenciar
    a caixa. Não há vínculo gravado entre docente e usuário (D7 da Change
    importar-ensalamento-da-planilha).
    """
    if not user.is_active or not user.username:
        return None
    return Teacher.objects.filter(name__iexact=user.username).first()


def manages(user, teacher_names):
    """Diz se o usuário pode cancelar ocorrências de uma aula com estes docentes.

    Pode quem tem `ENSALAMENTO.CANCELAR_OCORRENCIA` (o superadmin tem todas) e o docente da
    aula, reconhecido pelo nome do docente igual ao `username`, sem diferenciar a caixa. Não
    há vínculo gravado entre docente e usuário (D7 da Change importar-ensalamento-da-planilha).
    """
    if user.has_perm(permissions.SPACE_ALLOCATION_CANCEL_OCCURRENCE):
        return True
    if not user.is_active or not user.username:
        return False
    return user.username.casefold() in {name.casefold() for name in teacher_names}


class Allocation(models.Model):
    """Ocupação recorrente de um espaço por uma turma, numa disciplina, num dia e numa faixa.

    O espaço e os docentes podem faltar, porque a planilha traz atividade sem sala e
    atividade sem docente reconhecido. Duas alocações do mesmo semestre podem ter o mesmo
    espaço, dia e faixa: é a aula compartilhada por turmas diferentes, e não um conflito.
    A importação não detecta conflito de espaço nem de docente (D8).

    A vigência (`valid_from` e `valid_until`) fica vazia na alocação da planilha, que vale o
    semestre inteiro. A alteração da recorrência encerra a alocação na véspera de uma data e
    cria outra a partir dela: as ocorrências anteriores continuam na versão antiga, e a
    versão nova só nasce sem choque com outra aula nem com agendamento (Change
    alterar-recorrencia-do-ensalamento).
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
    valid_from = models.DateField('vigente desde', null=True, blank=True)
    valid_until = models.DateField('vigente até', null=True, blank=True)

    objects = AllocationManager()

    class Meta:
        verbose_name = 'alocação'
        verbose_name_plural = 'alocações'
        ordering = ['weekday', 'time_slot__start_time', 'class_group__label']
        constraints = [
            models.UniqueConstraint(
                fields=['semester', 'class_group', 'weekday', 'time_slot', 'subject', 'valid_from'],
                name='allocation_unique',
                nulls_distinct=False,
                violation_error_message='Esta turma já tem esta disciplina nesta faixa de horário deste dia.',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valid_from__isnull=True)
                    | models.Q(valid_until__isnull=True)
                    | models.Q(valid_from__lte=models.F('valid_until'))
                ),
                name='allocation_validity_valid',
                violation_error_message='O fim da vigência deve ser igual ou posterior ao início.',
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

    def occurs_on(self, day):
        """Diz se a regra semanal gera uma ocorrência na data: o dia da semana, o período do
        semestre e a vigência da alocação."""
        return (
            day.weekday() < len(WEEKDAY_ORDER)
            and WEEKDAY_ORDER[day.weekday()] == self.weekday
            and self.semester.contains(day)
            and (self.valid_from is None or self.valid_from <= day)
            and (self.valid_until is None or day <= self.valid_until)
        )

    @property
    def is_versioned(self):
        """Diz se a alocação faz parte de uma recorrência alterada no sistema."""
        return self.valid_from is not None or self.valid_until is not None

    @property
    def starts(self):
        """Primeira data da vigência: o início dela ou, sem ele, o do semestre."""
        return self.valid_from or self.semester.start_date

    @property
    def ends(self):
        """Última data da vigência: o fim dela ou, sem ele, o do semestre."""
        return self.valid_until or self.semester.end_date

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

    def audit_values(self):
        """Identificação da alocação para o registro de auditoria, em valores canônicos."""
        return {
            'alocacao': self.pk,
            'semestre': self.semester.code,
            'disciplina': self.subject.name,
            'turma': str(self.class_group),
            'dia': self.weekday,
            'horario': str(self.time_slot),
            'espaco': self.space.name if self.space else None,
            'docentes': teacher_names(self.teachers.all()),
            'vigente_desde': iso(self.valid_from),
            'vigente_ate': iso(self.valid_until),
        }


class ClassOfferingManager(models.Manager):
    def record(self, semester, subject, class_group):
        """Devolve a oferta da disciplina para a turma no semestre, criando-a quando não
        existir, e sincroniza os docentes dela com as alocações atuais.

        É a operação que a importação e a alteração de recorrência chamam, na transação de
        quem chama. Nada é excluído, e chamar de novo com os mesmos dados não muda nada
        (D5 da Change relacionar-professor-disciplina-turma).
        """
        with transaction.atomic():
            offering, _ = self.get_or_create(semester=semester, subject=subject, class_group=class_group)
            offering.sync_assignments()
            return offering


class ClassOffering(models.Model):
    """Oferta de uma disciplina para uma turma num semestre (D2).

    A disciplina e a turma valem para todos os semestres; é a oferta que as liga a um
    semestre. Uma disciplina tem várias turmas e uma turma tem várias disciplinas, sempre por
    oferta. A oferta é identificada pela mesma tripla de semestre, disciplina e turma das
    alocações, sem FK entre elas (D4), e nunca é excluída automaticamente.
    """

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name='offerings', verbose_name='semestre',
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='offerings', verbose_name='disciplina',
    )
    class_group = models.ForeignKey(
        ClassGroup, on_delete=models.PROTECT, related_name='offerings', verbose_name='turma',
    )

    objects = ClassOfferingManager()

    class Meta:
        verbose_name = 'oferta de disciplina'
        verbose_name_plural = 'ofertas de disciplina'
        ordering = ['semester__code', 'subject__name', 'class_group__label']
        constraints = [
            models.UniqueConstraint(
                fields=['semester', 'subject', 'class_group'],
                name='class_offering_unique',
                violation_error_message='Esta turma já tem esta disciplina neste semestre.',
            ),
        ]
        indexes = [models.Index(fields=['semester', 'class_group'], name='class_offering_group_idx')]

    def __str__(self):
        return f'{self.semester} {self.subject} {self.class_group}'

    def current_allocations(self):
        """Alocações atuais da oferta: a mesma tripla e sem fim de vigência (D3)."""
        return Allocation.objects.filter(
            semester=self.semester_id, subject=self.subject_id, class_group=self.class_group_id, valid_until__isnull=True,
        )

    def sync_assignments(self):
        """Marca como atuais os docentes das alocações atuais e como históricos os demais.

        Cria o vínculo que falta e nunca exclui nenhum: o docente que saiu das alocações
        atuais fica registrado com `is_current=False` e volta a `True` se reaparecer.
        """
        present = set(
            self.current_allocations().filter(teachers__isnull=False).values_list('teachers', flat=True),
        )
        TeachingAssignment.objects.bulk_create(
            [TeachingAssignment(offering=self, teacher_id=teacher, is_current=True) for teacher in present],
            ignore_conflicts=True,
        )
        self.assignments.filter(teacher__in=present, is_current=False).update(is_current=True)
        self.assignments.exclude(teacher__in=present).filter(is_current=True).update(is_current=False)


class TeachingAssignmentQuerySet(models.QuerySet):
    def available(self, semester, teacher=None, subject=None, class_group=None):
        """Combinações atuais de docente, disciplina e turma do semestre, numa consulta só.

        Só os vínculos com `is_current=True` entram: o histórico fica fora, e combinação que
        não existe como vínculo nunca é devolvida (D7). Os filtros são opcionais.
        """
        queryset = self.filter(is_current=True, offering__semester=semester)
        if teacher is not None:
            queryset = queryset.filter(teacher=teacher)
        if subject is not None:
            queryset = queryset.filter(offering__subject=subject)
        if class_group is not None:
            queryset = queryset.filter(offering__class_group=class_group)
        return queryset.select_related('teacher', 'offering__subject', 'offering__class_group__course')

    def is_available(self, semester, teacher, subject, class_group):
        """Diz se a combinação é um vínculo atual do semestre."""
        return self.available(semester, teacher, subject, class_group).exists()


class TeachingAssignment(models.Model):
    """Docente de uma oferta de disciplina (D3).

    Histórico e disponibilidade atual são conceitos diferentes. O histórico são todos os
    vínculos da oferta, que nunca são excluídos automaticamente. `is_current=True` indica
    que o docente está presente em alguma alocação atual da oferta, e `is_current=False`
    que o vínculo é preservado como histórico, sem o docente nas alocações atuais. Não
    significa docente responsável pela disciplina. A Agenda oferece só os vínculos atuais.
    """

    offering = models.ForeignKey(
        ClassOffering, on_delete=models.PROTECT, related_name='assignments', verbose_name='oferta',
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.PROTECT, related_name='assignments', verbose_name='docente',
    )
    is_current = models.BooleanField('atual', default=True)

    objects = TeachingAssignmentQuerySet.as_manager()

    class Meta:
        verbose_name = 'docente da oferta'
        verbose_name_plural = 'docentes das ofertas'
        ordering = ['teacher__name']
        constraints = [
            models.UniqueConstraint(
                fields=['offering', 'teacher'],
                name='teaching_assignment_unique',
                violation_error_message='Este docente já está nesta oferta.',
            ),
        ]
        indexes = [models.Index(fields=['teacher', 'offering'], name='assignment_teacher_idx')]

    def __str__(self):
        return f'{self.teacher} {self.offering}'


class AllocationExceptionManager(models.Manager):
    def cancelled(self, allocation_ids, start_date, end_date):
        """Pares (alocação, data) cancelados no intervalo, numa consulta só.

        É o filtro único que a ocupação do ensalamento aplica antes de montar a Grade, a
        Agenda e o calendário público.
        """
        allocation_ids = list(allocation_ids)
        if not allocation_ids:
            return set()
        return set(
            self.filter(
                allocation__in=allocation_ids,
                date__range=(start_date, end_date),
                kind=AllocationException.Kind.CANCELLED,
            ).values_list('allocation_id', 'date'),
        )

    def cancel(self, allocation_ids, day, executor):
        """Cancela a ocorrência das alocações na data, sem alterar as alocações.

        Todas as alocações são travadas e conferidas antes de qualquer gravação: o executor
        precisa administrar cada uma, a data precisa ser uma ocorrência dela e a ocorrência
        não pode estar cancelada. Cada exceção criada gera um registro de auditoria.
        """
        allocation_ids = sorted(set(allocation_ids))
        with transaction.atomic():
            locked = list(
                Allocation.objects.select_for_update(of=('self',))
                .filter(pk__in=allocation_ids)
                .select_related('semester', 'subject', 'time_slot', 'space', 'class_group__course')
                .prefetch_related('teachers')
                .order_by('pk'),
            )
            if not allocation_ids or len(locked) != len(allocation_ids):
                raise ValidationError('A aula informada não existe. Atualize a Grade.', code='missing')
            shown = date_format(day, 'SHORT_DATE_FORMAT')
            for allocation in locked:
                if not manages(executor, [teacher.name for teacher in allocation.teachers.all()]):
                    raise ValidationError(
                        'Só um docente da aula ou quem tem permissão cancela esta ocorrência.',
                        code='not_allowed',
                    )
                if not allocation.occurs_on(day):
                    raise ValidationError(
                        f'A aula não acontece em {shown}. Escolha uma data da aula.', code='not_occurrence',
                    )
            if self.filter(allocation__in=locked, date=day).exists():
                raise ValidationError(f'A ocorrência de {shown} já está cancelada.', code='already_cancelled')
            created = []
            for allocation in locked:
                exception = self.create(
                    allocation=allocation, date=day, kind=AllocationException.Kind.CANCELLED, created_by=executor,
                )
                AuditLog.objects.record(
                    catalog.CANCEL,
                    catalog.SPACE_ALLOCATION_EXCEPTION,
                    resource_id=exception.pk,
                    new_values={'tipo': exception.kind, 'data': iso(day)},
                    metadata=allocation.audit_values(),
                )
                created.append(exception)
            return created


class AllocationException(models.Model):
    """Alteração de uma ocorrência da alocação numa data, sem alterar a regra semanal.

    Nesta versão o único tipo é o cancelamento. A exceção aponta para a alocação com
    PROTECT, e a importação reaproveita a alocação pela identidade, sem excluir nem recriar,
    por isso a exceção continua valendo depois de uma nova importação.
    """

    class Kind(models.TextChoices):
        CANCELLED = 'CANCELADA', 'Cancelada'

    allocation = models.ForeignKey(
        Allocation, on_delete=models.PROTECT, related_name='exceptions', verbose_name='alocação',
    )
    date = models.DateField('data')
    kind = models.CharField('tipo', max_length=9, choices=Kind.choices, default=Kind.CANCELLED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', verbose_name='registrada por',
    )
    created_at = models.DateTimeField('registrada em', auto_now_add=True)

    objects = AllocationExceptionManager()

    class Meta:
        verbose_name = 'exceção do ensalamento'
        verbose_name_plural = 'exceções do ensalamento'
        ordering = ['-created_at', '-pk']
        constraints = [
            models.UniqueConstraint(
                fields=['allocation', 'date'],
                name='allocation_exception_unique',
                violation_error_message='Esta ocorrência já tem uma exceção.',
            ),
        ]

    def __str__(self):
        return f'{self.allocation} {self.date} {self.get_kind_display()}'


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
