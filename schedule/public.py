"""Consulta e montagem do calendário público do ensalamento (Change calendario-publico).

Tudo o que a página pública expõe sai deste módulo. Ele lê as alocações do ensalamento
acadêmico e nunca chama `occupancy()` nem `grid_sources()`: além das aulas, só entram as
fontes registradas como públicas, hoje os agendamentos aprovados da Agenda, e só na consulta
por sala ou por docente, com o horário, a sala, o nome e o e-mail de quem solicitou, sem a
descrição (Change agendar-uso-eventual-dos-espacos). Os
templates recebem só `PublicEntry`, `PublicBooking` e a estrutura da Grade, sem referência a
model e sem IDs (D5).

A quantidade de consultas é fixa: no máximo dez, qualquer que seja o intervalo (D10), com a
consulta das ocorrências canceladas, que somem da Grade datada sem expor a exceção (Change
cancelar-ocorrencia-do-ensalamento).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace

from django.db.models import Prefetch
from django.db.models.functions import Lower

from accounts.models import User
from schedule.models import Allocation, AllocationException, Course, Space, Stage, Teacher
from schedule.occupancy import public_sources
from schedule.timetable import (
    WEEKDAYS,
    Row,
    build_week,
    slots_of,
    with_uncovered,
    listed_spaces,
    clamp,
    current_semester_code,
    group_fields,
    imported_semesters,
    monday_of,
    natural_key,
    semester_slots,
    week_dates,
)

MAX_DAYS = 31
MAX_LENGTH = 200
STAGES = {'graduacao': Stage.UNDERGRADUATE, 'ensino-medio': Stage.SECONDARY}
STAGE_CHOICES = [('graduacao', Stage.UNDERGRADUATE.label), ('ensino-medio', Stage.SECONDARY.label)]

CHOOSE_MESSAGE = 'Escolha uma sala, um docente ou um curso.'
BOTH_DATES_MESSAGE = 'Informe a data inicial e a data final.'
INVALID_DATE_MESSAGE = 'Informe uma data válida.'
ORDER_MESSAGE = 'A data final deve ser igual ou posterior à data inicial.'
LIMIT_MESSAGE = f'Escolha um intervalo de até {MAX_DAYS} dias.'


@dataclass(frozen=True)
class PublicTeacher:
    """Docente no card: o nome do ensalamento e, quando houver correspondência, o e-mail."""

    name: str
    email: str = ''

    @property
    def mailbox(self):
        """Parte do e-mail antes do @, para a quebra de linha cair no @ e não numa letra solta."""
        return self.email.partition('@')[0]

    @property
    def domain(self):
        return self.email.partition('@')[2]


@dataclass(frozen=True)
class PublicEntry:
    """Uma aula no calendário público, só com os campos que o card mostra."""

    subject: str
    group_label: str
    space: str
    teachers: tuple
    stage: str
    course: str = ''
    group: str = ''

    @property
    def is_undergraduate(self):
        return self.stage == Stage.UNDERGRADUATE

    @property
    def stage_label(self):
        return Stage(self.stage).label


@dataclass(frozen=True)
class PublicBooking:
    """Agendamento aprovado no calendário público: horário, sala, disciplina, curso, turma e docente.

    A descrição fica fora da página. Os campos `group_label` e `teachers` existem só para a
    ordenação da célula.
    """

    start: object
    end: object
    space: str
    requester: str
    email: str
    group_label: str = ''
    subject: str = ''
    teachers: tuple = ()
    course: str = ''
    group: str = ''
    teacher: str = ''
    is_booking = True

    @property
    def mailbox(self):
        return self.email.partition('@')[0]

    @property
    def domain(self):
        return self.email.partition('@')[2]


@dataclass(frozen=True)
class Cluster:
    """Aulas de uma célula com a mesma sala, disciplina e docentes: turmas juntas quando mais de uma."""

    entries: tuple

    @property
    def is_joint(self):
        return len(self.entries) > 1


@dataclass
class PublicCell:
    """Bloco de faixas seguidas com as mesmas aulas, agrupadas em `Cluster`, sem a marca de choque,
    e os agendamentos aprovados da faixa."""

    clusters: list
    start: object
    end: object
    span: int = 1
    bookings: list = field(default_factory=list)
    is_continued = False
    is_outside = False


@dataclass
class Options:
    """Opções dos filtros de um semestre, só com nome e código."""

    semesters: list = field(default_factory=list)
    spaces: list = field(default_factory=list)
    teachers: list = field(default_factory=list)
    courses: list = field(default_factory=list)


def semester_options(semester):
    """Salas, docentes e cursos do semestre, em três consultas (D6).

    As salas ativas entram todas, com ou sem aula; as inativas, só quando têm alocação no
    semestre. Os docentes vêm de `Teacher`,
    nunca da tabela de usuários (D4).
    """
    if semester is None:
        return [], [], []
    spaces = sorted(listed_spaces(semester).only('name'), key=natural_key)
    teachers = list(
        Teacher.objects.filter(allocations__semester=semester).distinct().only('name').order_by('name'),
    )
    courses = list(
        Course.objects.filter(class_groups__allocations__semester=semester).distinct().only('name', 'stage').order_by('name'),
    )
    return spaces, teachers, courses


def chosen(value, records):
    """Registro cujo nome é o valor informado, sem diferenciar a caixa; o resto é descartado."""
    value = (value or '').strip()
    if not value or len(value) > MAX_LENGTH:
        return None
    key = value.casefold()
    return next((record for record in records if record.name.casefold() == key), None)


def teacher_emails(names):
    """E-mails dos usuários ativos cujo `username` corresponde exatamente ao nome do docente (D4).

    Uma consulta, só com `username` e `email`, pelo índice de `Lower('username')`.
    """
    keys = {name.lower() for name in names}
    if not keys:
        return {}
    found = (
        User.objects.annotate(key=Lower('username'))
        .filter(key__in=keys, is_active=True)
        .values_list('key', 'email')
    )
    return dict(found)


def public_allocations(semester, space=None, teacher=None, course=None, stage=None):
    """Alocações do semestre com os filtros aplicados no banco, só com as colunas do card."""
    queryset = Allocation.objects.filter(semester=semester)
    if space is not None:
        queryset = queryset.filter(space=space)
    if teacher is not None:
        queryset = queryset.filter(teachers=teacher)
    if course is not None:
        queryset = queryset.filter(class_group__course=course)
    if stage is not None:
        queryset = queryset.filter(class_group__course__stage=stage)
    return list(
        queryset.select_related('subject', 'time_slot', 'space', 'class_group__course')
        .only(
            'weekday', 'valid_from', 'valid_until',
            'subject', 'subject__name',
            'time_slot', 'time_slot__start_time', 'time_slot__end_time',
            'space', 'space__name',
            'class_group', 'class_group__label',
            'class_group__course', 'class_group__course__name', 'class_group__course__stage',
        )
        .prefetch_related(Prefetch('teachers', queryset=Teacher.objects.only('name').order_by('name')))
        .order_by(),
    )


def entries_of(allocations):
    """Aulas do card de cada alocação, com os e-mails dos docentes numa consulta só."""
    names = {teacher.name for allocation in allocations for teacher in allocation.teachers.all()}
    emails = teacher_emails(names)
    result = []
    for allocation in allocations:
        teachers = tuple(
            PublicTeacher(name=teacher.name, email=emails.get(teacher.name.lower(), ''))
            for teacher in sorted(allocation.teachers.all(), key=lambda item: item.name)
        )
        result.append((allocation, PublicEntry(
            subject=allocation.subject.name,
            **group_fields(allocation.class_group),
            space=allocation.space.name if allocation.space else '',
            teachers=teachers,
            stage=allocation.class_group.course.stage,
        )))
    return result


def entry_order(entry):
    """Sala na ordem natural, com as aulas sem sala por último, depois curso e turma."""
    return (not entry.space, natural_key(SimpleNamespace(name=entry.space)), entry.group_label.casefold(), entry.subject.casefold())


def clusters_of(entries):
    """Agrupa as aulas da célula pela mesma sala, disciplina e docentes (D9)."""
    groups = {}
    for entry in sorted(entries, key=entry_order):
        key = (entry.space.casefold(), entry.subject.casefold(), frozenset(teacher.name.casefold() for teacher in entry.teachers))
        groups.setdefault(key, []).append(entry)
    return [Cluster(entries=tuple(items)) for items in groups.values()]


def publish(week):
    """Troca as células da Grade pelas públicas, que não classificam choque."""
    for day in week.days:
        day.cells = [
            PublicCell(
                clusters=clusters_of([entry for entry in cell.entries if not getattr(entry, 'is_booking', False)]),
                bookings=[entry for entry in cell.entries if getattr(entry, 'is_booking', False)],
                start=cell.start, end=cell.end, span=cell.span,
            )
            if cell and not cell.is_continued and not cell.is_outside else cell
            for cell in day.cells
        ]
    week.rows = [
        Row(start=row.start, end=row.end, cells=[day.cells[index] for day in week.days], days=week.days)
        for index, row in enumerate(week.rows)
    ]
    return week


def result_slots(semester, placed, every_slot=None):
    """Todas as faixas do semestre, com ou sem aula no resultado.

    A Grade aparece sempre completa, como na área autenticada, mesmo quando a consulta não
    tem aula no intervalo; as células vazias indicam os horários sem aula. `placed` fica na
    assinatura para as chamadas existentes e não recorta as linhas.
    """
    return semester_slots(semester) if every_slot is None else every_slot


def typical_week(semester, allocations, today):
    by_day_slot = {}
    for allocation, entry in entries_of(allocations):
        slot = (allocation.time_slot.start_time, allocation.time_slot.end_time)
        by_day_slot.setdefault((allocation.weekday, slot), []).append(entry)
    slots = result_slots(semester, {slot for _, slot in by_day_slot})
    return publish(build_week(slots, sorted_entries(by_day_slot), today))


def sorted_entries(by_day_slot):
    return {key: sorted(entries, key=entry_order) for key, entries in by_day_slot.items()}


def public_bookings(dates, space=None, teacher=None):
    """Agendamentos aprovados das datas, das fontes públicas, pela sala, pelo docente ou pelos dois."""
    if not dates or (space is None and teacher is None):
        return []
    return [
        SimpleNamespace(
            date=occurrence.date, start=occurrence.start, end=occurrence.end,
            entry=PublicBooking(
                start=occurrence.start, end=occurrence.end, space=occurrence.space,
                requester=occurrence.requester, email=occurrence.email,
                subject=occurrence.subject, course=occurrence.course,
                group=occurrence.group, teacher=occurrence.teacher,
            ),
        )
        for source in public_sources()
        for occurrence in source.public_occurrences(dates[0], dates[-1], space, teacher.name if teacher else None)
    ]


def dated_week(semester, allocations, dates, today, bookings=()):
    """Grade datada: cada alocação em cada data do seu dia da semana dentro do período.

    Os agendamentos aprovados entram em todas as faixas que cruzam; o que não cruza nenhuma
    faixa ganha uma linha própria, como na Grade autenticada.
    """
    by_weekday = {}
    for allocation, entry in entries_of(allocations):
        allocation.semester = semester
        by_weekday.setdefault(allocation.weekday, []).append((allocation, entry))
    cancelled = AllocationException.objects.cancelled(
        [allocation.pk for allocation in allocations], dates[0], dates[-1],
    ) if dates else set()
    by_day_slot = {}
    for day in dates:
        if not semester.contains(day):
            continue
        for allocation, entry in by_weekday.get(WEEKDAYS[day.weekday()], []):
            if not allocation.occurs_on(day) or (allocation.pk, day) in cancelled:
                continue
            slot = (allocation.time_slot.start_time, allocation.time_slot.end_time)
            by_day_slot.setdefault((day, slot), []).append(entry)
    wanted = {day for day in dates if semester.contains(day)}
    bookings = [booking for booking in bookings if booking.date in wanted]
    every_slot = semester_slots(semester)
    placed = {slot for _, slot in by_day_slot}
    placed |= {slot for booking in bookings for slot in slots_of(booking, every_slot, True)}
    slots = with_uncovered(result_slots(semester, placed, every_slot), bookings)
    for booking in bookings:
        for slot in slots_of(booking, slots, True):
            by_day_slot.setdefault((booking.date, slot), []).append(booking.entry)
    return publish(build_week(slots, sorted_entries(by_day_slot), today, dates=dates, semester=semester))


def weekdays_between(start, end):
    days = []
    day = start
    while day <= end:
        if day.weekday() < len(WEEKDAYS):
            days.append(day)
        day += timedelta(days=1)
    return days


def default_range(semester, today):
    """Segunda e sexta da semana de hoje, levada para dentro do período do semestre (D7)."""
    start = monday_of(clamp(semester, today, today))
    dates = week_dates(start)
    return dates[0], dates[-1]


def parse_day(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def read_range(params):
    """Datas da URL: (início, fim, erro). Sem as duas, (None, None, None) para usar o padrão."""
    start_text = (params.get('inicio') or '').strip()[:MAX_LENGTH]
    end_text = (params.get('fim') or '').strip()[:MAX_LENGTH]
    if not start_text and not end_text:
        return None, None, None
    if not start_text or not end_text:
        return None, None, BOTH_DATES_MESSAGE
    start, end = parse_day(start_text), parse_day(end_text)
    if start is None or end is None:
        return None, None, INVALID_DATE_MESSAGE
    if end < start:
        return start, end, ORDER_MESSAGE
    if (end - start).days + 1 > MAX_DAYS:
        return start, end, LIMIT_MESSAGE
    return start, end, None


def touches(semester, start, end):
    return start <= semester.end_date and end >= semester.start_date


@dataclass
class PublicCalendar:
    """Tudo o que o template público recebe: filtros normalizados, estado e a Grade."""

    semester_code: str
    options: Options
    space: object = None
    teacher: object = None
    course: object = None
    stage_key: str = ''
    start: object = None
    end: object = None
    dates_enabled: bool = False
    date_error: str = ''
    message: str = ''
    notice: str = ''
    week: object = None
    free_label: str = 'sem aula'

    @property
    def has_principal(self):
        return any(record is not None for record in (self.space, self.teacher, self.course))

    @property
    def summary(self):
        """Resumo dos filtros escolhidos, usado na legenda da Grade para leitores de tela."""
        parts = [record.name for record in (self.space, self.teacher, self.course) if record is not None]
        if self.stage_key:
            parts.append(STAGES[self.stage_key].label)
        return ', '.join(parts)


def public_calendar(params, today):
    """Lê os filtros da URL e monta o calendário público, consultando as aulas só quando pode (D7, D8)."""
    semesters = {semester.code: semester for semester in imported_semesters()}
    current = current_semester_code(today)
    codes = sorted(set(semesters) | {current}, reverse=True)
    code = (params.get('semestre') or '').strip()
    code = code if code in codes else current
    semester = semesters.get(code)
    spaces, teachers, courses = semester_options(semester)
    stage_key = (params.get('nivel') or '').strip()
    calendar = PublicCalendar(
        semester_code=code,
        options=Options(semesters=codes, spaces=spaces, teachers=teachers, courses=courses),
        space=chosen(params.get('sala'), spaces),
        teacher=chosen(params.get('docente'), teachers),
        course=chosen(params.get('curso'), courses),
        stage_key=stage_key if stage_key in STAGES else '',
    )
    if semester is None:
        calendar.message = f'Nenhum horário publicado no semestre {code}.'
        return calendar
    calendar.dates_enabled = semester.has_period
    if semester.has_period:
        start, end, error = read_range(params)
        if start is None and error is None:
            start, end = default_range(semester, today)
        calendar.start, calendar.end, calendar.date_error = start, end, error or ''
    if not calendar.has_principal:
        calendar.message = CHOOSE_MESSAGE
        return calendar
    if calendar.date_error:
        return calendar
    calendar.free_label = 'disponível' if calendar.space is not None and calendar.teacher is None and calendar.course is None and not calendar.stage_key else 'sem aula'
    if semester.has_period and not touches(semester, calendar.start, calendar.end):
        calendar.message = (
            f'O intervalo escolhido está fora do semestre {code}, de '
            f'{semester.start_date:%d/%m/%Y} a {semester.end_date:%d/%m/%Y}.'
        )
        return calendar
    allocations = public_allocations(
        semester, calendar.space, calendar.teacher, calendar.course, STAGES.get(calendar.stage_key),
    )
    if semester.has_period:
        dates = weekdays_between(calendar.start, calendar.end)
        with_bookings = calendar.course is None and not calendar.stage_key
        bookings = public_bookings(dates, calendar.space, calendar.teacher) if with_bookings else []
        calendar.week = dated_week(semester, allocations, dates, today, bookings)
    else:
        calendar.notice = f'Datas do semestre {code} ainda não definidas. O calendário mostra a semana típica.'
        calendar.week = typical_week(semester, allocations, today)
    return calendar
