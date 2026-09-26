"""Grade da semana de uma sala, montada das alocações confirmadas de um semestre.

Os templates recebem só `Week`, sem referência a `Allocation`. A leitura é feita em uma
quantidade fixa de consultas e nada é gravado (D15 e D16 da Change
visualizar-grade-do-ensalamento).

Com o período do semestre definido, a semana é datada e montada das ocorrências calculadas
em `schedule.occupancy`; sem ele, continua sendo a semana típica (D7 e D9 da Change
visualizar-ocupacao-por-semana-e-mes).
"""

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from django.db.models import Q

from schedule.models import WEEKDAY_ORDER, Allocation, Semester, Space, Stage, TimeSlot, Weekday

SMALL_WORDS = {'a', 'as', 'o', 'os', 'e', 'em', 'de', 'do', 'da', 'dos', 'das', 'para'}

SINGLE = 'single'
JOINT = 'joint'
CLASH = 'clash'

WEEKDAYS = WEEKDAY_ORDER


def all_caps(name):
    return bool(name) and name == name.upper() and any(char.isalpha() for char in name)


def readable_course(name):
    """Nome do curso em caixa alta passado para iniciais maiúsculas, só na exibição (D12).

    `LICENCIATURA EM FÍSICA` aparece como `Licenciatura em Física`. O dado gravado não
    muda, e nomes que já têm minúsculas ficam como estão.
    """
    if not all_caps(name):
        return name
    words = name.lower().split()
    return ' '.join(word if position and word in SMALL_WORDS else word[:1].upper() + word[1:] for position, word in enumerate(words))


def readable_group(label):
    """Rótulo da turma em caixa alta passado para caixa de frase: `1º ANO A` vira `1º ano A`."""
    if not all_caps(label):
        return label
    words = label.lower().split()
    words = [word.upper() if len(word) == 1 and word.isalpha() else word for word in words]
    text = ' '.join(words)
    return text[:1].upper() + text[1:]


def group_label(class_group):
    """Curso e turma, como aparecem no card: `Informática, 2º ano A`."""
    return ', '.join(part for part in (readable_course(class_group.course.name), readable_group(class_group.label)) if part)


def natural_key(space):
    return [(0, int(part), '') if part.isdigit() else (1, 0, part.casefold()) for part in re.split(r'(\d+)', space.name)]


def current_semester_code(today):
    """Semestre letivo de uma data: janeiro a junho é o primeiro, julho a dezembro o segundo."""
    return f'{today.year}/{1 if today.month <= 6 else 2}'


@dataclass(frozen=True)
class Entry:
    """Uma aula na sala numa faixa: a disciplina, a turma com o curso e os docentes."""

    subject: str
    group_label: str
    teachers: tuple
    stage: str
    allocation_ids: tuple = field(default=(), compare=False)
    cancel_url: str = field(default='', compare=False)

    @property
    def is_undergraduate(self):
        return self.stage == Stage.UNDERGRADUATE


@dataclass
class Cell:
    """Bloco de uma ou mais faixas seguidas de um dia, com as mesmas aulas."""

    entries: list
    start: object
    end: object
    span: int = 1
    is_continued = False
    is_outside = False

    @property
    def lessons(self):
        """Aulas da célula, sem os agendamentos, que têm o próprio selo."""
        return [entry for entry in self.entries if not getattr(entry, 'is_booking', False)]

    @property
    def group_count(self):
        return len({entry.group_label for entry in self.lessons})

    @property
    def kind(self):
        """Uma turma, turmas juntas ou choque (D13 da Change visualizar-grade-do-ensalamento).

        Turmas juntas têm a mesma disciplina e os mesmos docentes; o resto é choque, que
        só é mostrado. A classificação é das entradas da célula, e não um dado gravado.
        """
        if self.group_count <= 1:
            return SINGLE
        lessons = {(entry.subject.casefold(), frozenset(name.casefold() for name in entry.teachers)) for entry in self.lessons}
        return JOINT if len(lessons) == 1 else CLASH


class Continued:
    """Faixa coberta pelo bloco de uma faixa anterior do mesmo dia."""

    is_continued = True
    is_outside = False


CONTINUED = Continued()


@dataclass
class Outside:
    """Dia fora do período do semestre, num bloco que cobre todas as faixas."""

    span: int
    is_continued = False
    is_outside = True


@dataclass
class Day:
    weekday: str
    label: str
    is_today: bool
    cells: list
    date: object = None
    in_period: bool = True
    available: int = 0
    is_week_start: bool = False

    @property
    def short_label(self):
        """Dia da semana abreviado do cabeçalho do mês: `Seg`, mostrado em caixa alta pelo CSS."""
        return self.label[:3]

    @property
    def full_label(self):
        return Weekday(self.weekday).label

    @property
    def has_activity(self):
        return any(cell and not cell.is_outside for cell in self.cells)


@dataclass
class Row:
    """Uma faixa de horário, com o conteúdo dela em cada dia da semana."""

    start: object
    end: object
    cells: list
    days: list = field(default_factory=list)

    @property
    def day_cells(self):
        """Cada dia com a sua célula nesta faixa, para o nome acessível da faixa disponível."""
        return list(zip(self.days, self.cells))


@dataclass
class Week:
    """Semana de uma sala: as faixas, os dias e as contagens."""

    rows: list = field(default_factory=list)
    days: list = field(default_factory=list)
    occupied: int = 0
    available: int = 0
    start: object = None
    end: object = None
    previous: object = None
    following: object = None

    @property
    def is_dated(self):
        return self.start is not None

    @property
    def has_activities(self):
        return self.occupied > 0

    @property
    def today_index(self):
        return next((index for index, day in enumerate(self.days) if day.is_today), None)


def weekday_of(today):
    """Código do dia da semana de uma data, ou None no sábado e no domingo."""
    if today is None or today.weekday() > 4:
        return None
    return WEEKDAYS[today.weekday()]


def build_day(slots, by_slot):
    """Células do dia, uma por faixa, com as faixas seguidas de mesmas aulas unidas num bloco.

    O bloco junta as alocações de cada aula das faixas unidas, para que cancelar a
    ocorrência do bloco alcance todas elas.
    """
    cells, previous_entries, open_cell, previous_slot = [], None, None, None
    for slot in slots:
        entries = by_slot.get(slot)
        contiguous = previous_slot is not None and previous_slot[1] == slot[0]
        if entries and entries == previous_entries and contiguous:
            open_cell.span += 1
            open_cell.end = slot[1]
            open_cell.entries = [
                replace(kept, allocation_ids=kept.allocation_ids + joined.allocation_ids)
                if hasattr(kept, 'allocation_ids') else kept
                for kept, joined in zip(open_cell.entries, entries)
            ]
            cells.append(CONTINUED)
        elif entries:
            open_cell = Cell(entries=entries, start=slot[0], end=slot[1])
            cells.append(open_cell)
        else:
            open_cell = None
            cells.append(None)
        previous_entries, previous_slot = entries, slot
    return cells


def build_week(slots, by_day_slot, today, dates=None, semester=None):
    """Grade com as faixas nas linhas e os dias nas colunas.

    Sem `dates`, é a semana típica, de segunda a sexta, com as entradas indexadas pelo dia
    da semana e o dia atual pelo dia da semana. Com `dates`, os dias úteis de uma semana ou
    de um mês, com as entradas indexadas pela data: "Hoje" é a data de hoje e o dia fora do
    período do semestre não tem células nem entra na contagem. A semana e o mês são a mesma
    estrutura, com listas de datas diferentes (D8 da Change visualizar-ocupacao-por-semana-e-mes).
    """
    today_code = weekday_of(today)
    columns = [(weekday, weekday, None) for weekday in WEEKDAYS] if dates is None else [
        (WEEKDAYS[day.weekday()], day, day) for day in dates
    ]
    days = []
    counted, occupied = 0, 0
    for position, (weekday, key, day_date) in enumerate(columns):
        in_period = semester.contains(day_date) if day_date else True
        by_slot = {slot: entries for (day, slot), entries in by_day_slot.items() if day == key}
        if in_period:
            cells = build_day(slots, by_slot)
            counted += 1
            occupied += len(by_slot)
        else:
            cells = [Outside(span=len(slots))] + [CONTINUED] * (len(slots) - 1) if slots else []
        days.append(Day(
            weekday=weekday,
            label=Weekday(weekday).label.split('-')[0],
            is_today=day_date == today if day_date else weekday == today_code,
            cells=cells,
            date=day_date,
            in_period=in_period,
            available=len(slots) - len(by_slot) if in_period else 0,
            is_week_start=bool(position) and weekday == WEEKDAYS[0],
        ))
    rows = [Row(start=slot[0], end=slot[1], cells=[day.cells[index] for day in days], days=days) for index, slot in enumerate(slots)]
    return Week(
        rows=rows,
        days=days,
        occupied=occupied,
        available=len(slots) * counted - occupied,
        start=dates[0] if dates else None,
        end=dates[-1] if dates else None,
    )


def imported_semesters():
    """Semestres com alocação confirmada, do mais recente ao mais antigo."""
    return list(Semester.objects.filter(allocations__isnull=False).distinct().order_by('-code'))


def listed_spaces(semester):
    """Espaços ativos e os inativos com alocação no semestre, sem repetição.

    Um espaço ativo sem aula também é listado, e a Grade dele aparece com as faixas vazias
    (Change listar-salas-sem-aula). O inativo só entra quando tem aula no semestre.
    """
    return Space.objects.filter(Q(is_active=True) | Q(allocations__semester=semester)).distinct()


def spaces_of(semester):
    """Salas da Grade do semestre, na ordem natural do nome: `1/4` vem antes de `1/10`."""
    if semester is None:
        return []
    return sorted(listed_spaces(semester), key=natural_key)


def semester_slots(semester):
    """Faixas com aula no semestre, iguais para toda sala, para que duas salas possam ser comparadas."""
    return sorted(set(
        TimeSlot.objects.filter(semester=semester, allocations__isnull=False).values_list('start_time', 'end_time'),
    ))


def space_week(semester, space, today):
    """Semana típica da sala no semestre, a partir das alocações confirmadas, sem datas."""
    if semester is None or space is None:
        return Week()
    slots = semester_slots(semester)
    allocations = (
        Allocation.objects.filter(semester=semester, space=space)
        .select_related('subject', 'time_slot', 'class_group__course')
        .prefetch_related('teachers')
        .order_by('class_group__course__name', 'class_group__label', 'subject__name')
    )
    by_day_slot = {}
    for allocation in allocations:
        slot = (allocation.time_slot.start_time, allocation.time_slot.end_time)
        by_day_slot.setdefault((allocation.weekday, slot), []).append(Entry(
            subject=allocation.subject.name,
            group_label=group_label(allocation.class_group),
            teachers=tuple(sorted(teacher.name for teacher in allocation.teachers.all())),
            stage=allocation.class_group.course.stage,
        ))
    return build_week(slots, by_day_slot, today)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def clamp(semester, reference, today):
    """Data de referência levada para dentro do período do semestre (D7, D8).

    A referência é a data da URL ou, sem ela, hoje. Antes do período vale o primeiro dia
    dele; depois, o último.
    """
    return min(max(reference or today, semester.start_date), semester.end_date)


def week_start(semester, reference, today):
    """Segunda-feira da semana mostrada, dentro do período do semestre."""
    return monday_of(clamp(semester, reference, today))


def month_start(semester, reference, today):
    """Primeiro dia do mês mostrado, dentro do período do semestre."""
    return clamp(semester, reference, today).replace(day=1)


def week_dates(start):
    return [start + timedelta(days=index) for index in range(len(WEEKDAYS))]


def month_dates(first):
    """Dias úteis do mês, de segunda a sexta, porque o ensalamento não tem fim de semana."""
    following = next_month(first)
    return [day for day in dates_until(first, following) if day.weekday() < len(WEEKDAYS)]


def dates_until(start, stop):
    day = start
    while day < stop:
        yield day
        day += timedelta(days=1)


def next_month(first):
    return (first.replace(day=28) + timedelta(days=4)).replace(day=1)


def previous_month(first):
    return (first - timedelta(days=1)).replace(day=1)


def slots_of(occurrence, slots, by_overlap):
    """Faixas em que a ocorrência aparece: a faixa igual à dela ou, com `by_overlap`, todas
    as que ela cruza, no intervalo `[início, fim)`.

    A sobreposição serve às ocorrências de horário livre, como o agendamento da Agenda, que
    não coincidem com as faixas do semestre (D7 da Change agendar-uso-eventual-dos-espacos).
    """
    if by_overlap:
        return [slot for slot in slots if occurrence.start < slot[1] and occurrence.end > slot[0]]
    slot = (occurrence.start, occurrence.end)
    return [slot] if slot in slots else []


def with_uncovered(slots, occurrences):
    """Faixas do semestre mais o intervalo de cada ocorrência que não cruza nenhuma delas.

    Um agendamento fora das faixas do semestre, como no almoço, ganha a própria linha, para
    que nenhum uso aprovado fique fora da Grade da Agenda.
    """
    extra = {
        (occurrence.start, occurrence.end)
        for occurrence in occurrences
        if not any(occurrence.start < slot[1] and occurrence.end > slot[0] for slot in slots)
    }
    return sorted(set(slots) | extra)


def dated_grid(semester, space, dates, today, occurrences, by_overlap=False):
    """Grade datada da sala nas datas pedidas, a partir das ocorrências do intervalo."""
    if semester is None or space is None:
        return Week()
    slots = semester_slots(semester)
    wanted = set(dates)
    if by_overlap:
        slots = with_uncovered(slots, [occurrence for occurrence in occurrences if occurrence.date in wanted])
    by_day_slot = {}
    for occurrence in occurrences:
        if occurrence.date not in wanted:
            continue
        for slot in slots_of(occurrence, slots, by_overlap):
            by_day_slot.setdefault((occurrence.date, slot), []).append(occurrence.entry)
    return build_week(slots, by_day_slot, today, dates=dates, semester=semester)


def dated_space_week(semester, space, start, today, occurrences, by_overlap=False):
    """Semana datada da sala, com as semanas vizinhas que tocam o período do semestre."""
    week = dated_grid(semester, space, week_dates(start), today, occurrences, by_overlap)
    if semester is None or space is None:
        return week
    previous, following = start - timedelta(days=7), start + timedelta(days=7)
    last_weekday = timedelta(days=len(WEEKDAYS) - 1)
    week.previous = previous if previous + last_weekday >= semester.start_date else None
    week.following = following if following <= semester.end_date else None
    return week


def dated_space_month(semester, space, first, today, occurrences, by_overlap=False):
    """Mês da sala: a mesma Grade da semana, com um dia útil do mês por coluna (D8).

    Os meses vizinhos só são oferecidos quando tocam o período do semestre.
    """
    month = dated_grid(semester, space, month_dates(first), today, occurrences, by_overlap)
    if semester is None or space is None:
        return month
    previous, following = previous_month(first), next_month(first)
    month.previous = previous if next_month(previous) > semester.start_date else None
    month.following = following if following <= semester.end_date else None
    return month


def counted(total, singular, plural):
    return f'{total} {singular if total == 1 else plural}'


def occupation_text(week, is_month=False):
    """Faixas ocupadas e disponíveis da sala na semana ou no mês."""
    period = 'no mês' if is_month else 'na semana'
    return f'{counted(week.occupied, "faixa ocupada", "faixas ocupadas")} e {counted(week.available, "disponível", "disponíveis")} {period}.'


def parse_date(value):
    """Data no formato AAAA-MM-DD da URL, ou None quando não serve."""
    try:
        return date.fromisoformat(value or '')
    except ValueError:
        return None


def month_reference(semester, first, today):
    """Data que leva do mês à semana: hoje, quando está no mês, ou o primeiro dia dele no período."""
    in_period = [day for day in month_dates(first) if semester.contains(day)]
    if today in in_period:
        return today
    return in_period[0] if in_period else first


def parse_month(value):
    """Primeiro dia do mês no formato AAAA-MM da URL, ou None quando não serve."""
    return parse_date(f'{value}-01') if value and len(value) == 7 else None
