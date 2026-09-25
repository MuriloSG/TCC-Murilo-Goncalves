"""Grade da semana de uma sala, montada das alocações confirmadas de um semestre.

Os templates recebem só `Week`, sem referência a `Allocation`. A leitura é feita em uma
quantidade fixa de consultas e nada é gravado (D15 e D16 da Change
visualizar-grade-do-ensalamento).
"""

import re
from dataclasses import dataclass, field

from schedule.models import Allocation, Semester, Space, Stage, TimeSlot, Weekday

SMALL_WORDS = {'a', 'as', 'o', 'os', 'e', 'em', 'de', 'do', 'da', 'dos', 'das', 'para'}

WEEKDAYS = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]


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


class Continued:
    """Faixa coberta pelo bloco de uma faixa anterior do mesmo dia."""

    is_continued = True


CONTINUED = Continued()


@dataclass
class Day:
    weekday: str
    label: str
    is_today: bool
    cells: list

    @property
    def has_activity(self):
        return any(self.cells)


@dataclass
class Row:
    """Uma faixa de horário, com o conteúdo dela em cada dia da semana."""

    start: object
    end: object
    cells: list


@dataclass
class Week:
    """Semana de uma sala: as faixas, os dias e as contagens."""

    rows: list = field(default_factory=list)
    days: list = field(default_factory=list)
    occupied: int = 0
    available: int = 0

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
    """Células do dia, uma por faixa, com as faixas seguidas de mesmas aulas unidas num bloco."""
    cells, previous_entries, open_cell, previous_slot = [], None, None, None
    for slot in slots:
        entries = by_slot.get(slot)
        contiguous = previous_slot is not None and previous_slot[1] == slot[0]
        if entries and entries == previous_entries and contiguous:
            open_cell.span += 1
            open_cell.end = slot[1]
            cells.append(CONTINUED)
        elif entries:
            open_cell = Cell(entries=entries, start=slot[0], end=slot[1])
            cells.append(open_cell)
        else:
            open_cell = None
            cells.append(None)
        previous_entries, previous_slot = entries, slot
    return cells


def build_week(slots, by_day_slot, today):
    """Semana com as faixas nas linhas e os dias de segunda a sexta nas colunas."""
    today_code = weekday_of(today)
    days = []
    for weekday in WEEKDAYS:
        by_slot = {slot: entries for (day, slot), entries in by_day_slot.items() if day == weekday}
        days.append(Day(
            weekday=weekday,
            label=Weekday(weekday).label.split('-')[0],
            is_today=weekday == today_code,
            cells=build_day(slots, by_slot),
        ))
    rows = [Row(start=slot[0], end=slot[1], cells=[day.cells[index] for day in days]) for index, slot in enumerate(slots)]
    occupied = len(by_day_slot)
    return Week(rows=rows, days=days, occupied=occupied, available=len(slots) * len(WEEKDAYS) - occupied)


def imported_semesters():
    """Semestres com alocação confirmada, do mais recente ao mais antigo."""
    return list(Semester.objects.filter(allocations__isnull=False).distinct().order_by('-code'))


def spaces_of(semester):
    """Salas com alocação no semestre, na ordem natural do nome: `1/4` vem antes de `1/10`."""
    if semester is None:
        return []
    return sorted(Space.objects.filter(allocations__semester=semester).distinct(), key=natural_key)


def space_week(semester, space, today):
    """Grade da semana da sala no semestre, a partir das alocações confirmadas.

    As linhas são as faixas com aula no semestre, iguais para toda sala, para que duas
    salas possam ser comparadas.
    """
    if semester is None or space is None:
        return Week()
    slots = sorted(set(
        TimeSlot.objects.filter(semester=semester, allocations__isnull=False).values_list('start_time', 'end_time'),
    ))
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
