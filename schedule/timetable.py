"""Grade da semana de uma sala, montada das linhas gravadas de uma importação de ensalamento.

A estrutura não conhece `ImportRow` nem `Allocation`: os templates recebem só `RoomWeek`,
para que a mesma tela sirva depois ao ensalamento confirmado (D4 e D11 da Change
visualizar-grade-do-ensalamento).

A leitura usa as mesmas funções que a execução da importação, sobre os mesmos valores
gravados, e por isso a Grade mostra exatamente o que a prévia executou (D1 e D2). Nada é
gravado.
"""

from dataclasses import dataclass, field

from schedule.activities import ACTIVITY_COLUMN, Catalog, resolve
from schedule.imports import (
    CELL_COLUMN,
    COURSE_COLUMN,
    DAY_COLUMN,
    GROUP_COLUMN,
    KIND_COLUMN,
    NAME_COLUMN,
    SLOT_COLUMN,
    STAGES,
    sheet_of,
)
from schedule.models import Weekday
from schedule.sheets import ACTIVITY_KIND, SPACE_KIND, TEACHER_KIND, parse_slot, parse_weekday, split_header, strip_parentheses
from schedule.sheets import text as sheet_text

WEEKDAYS = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]

SINGLE = 'single'
JOINT = 'joint'
CLASH = 'clash'
OK = 'ok'
ERROR = 'error'


@dataclass(frozen=True)
class Activity:
    """Uma atividade lida de uma linha da importação, já interpretada."""

    space: str | None
    weekday: str | None
    slot: tuple | None
    subject: str
    class_group: str
    course: str
    stage: str
    teachers: tuple
    raw_text: str
    state: str
    action: str | None
    line: int
    message: str | None


@dataclass
class Entry:
    """Atividade de uma turma num bloco da Grade, com as linhas de todas as faixas do bloco."""

    subject: str
    class_group: str
    course: str
    stage: str
    teachers: tuple
    raw_text: str
    state: str
    action: str | None
    message: str | None
    lines: list = field(default_factory=list)

    @property
    def is_error(self):
        return self.state == ERROR


@dataclass
class Cell:
    """Bloco de uma ou mais faixas seguidas de um dia, com as atividades que ocupam a sala."""

    entries: list
    kind: str
    start: object
    end: object
    span: int = 1

    @property
    def group_count(self):
        return len({(entry.course, entry.class_group) for entry in self.entries})

    @property
    def lines(self):
        return sorted({line for entry in self.entries for line in entry.lines})

    @property
    def has_error(self):
        return any(entry.is_error for entry in self.entries)

    @property
    def first_message(self):
        return next((entry.message for entry in self.entries if entry.message), None)


class Continued:
    """Faixa coberta pelo bloco de uma faixa anterior do mesmo dia."""


CONTINUED = Continued()


@dataclass(frozen=True)
class SpaceOption:
    name: str
    has_clash: bool


@dataclass
class Day:
    weekday: str
    label: str
    is_today: bool
    cells: list


@dataclass
class Row:
    """Uma faixa de horário, com o conteúdo dela em cada dia da semana."""

    start: object
    end: object
    cells: list


@dataclass
class RoomWeek:
    """Semana de uma sala: as salas do filtro, as faixas, os dias e as contagens."""

    space: str | None
    spaces: list
    rows: list
    days: list
    occupied: int
    available: int
    clash_count: int
    error_count: int
    outside_error_count: int

    @property
    def has_activities(self):
        return bool(self.rows)


@dataclass
class ImportReading:
    """Atividades lidas de uma importação, com a lista de salas e os erros sem lugar na Grade."""

    spaces: list
    activities: list
    outside_error_count: int


def unique(names):
    """Nomes sem repetição, sem diferenciar a caixa, na ordem em que aparecem."""
    seen, found = set(), []
    for name in names:
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            found.append(name)
    return found


def safe_slot(value):
    try:
        return parse_slot(value)
    except ValueError:
        return None


def read_import(importation):
    """Lê as linhas da importação numa consulta e interpreta cada atividade (D1, D2).

    O catálogo sai das linhas `SALA` e `DOCENTE`, como em `SpaceAllocationImport.lock`, e a
    atividade é lida por `resolve` contra ele. A atividade com erro guarda o texto da
    planilha, que é o que a Grade mostra no lugar da leitura (D7).
    """
    rows = list(importation.rows.order_by('line_number').values('line_number', 'values', 'action', 'errors'))
    teachers, spaces = [], []
    for row in rows:
        kind = row['values'].get(KIND_COLUMN)
        name = sheet_text(row['values'].get(NAME_COLUMN))
        if kind == SPACE_KIND:
            spaces.append(strip_parentheses(name))
        elif kind == TEACHER_KIND:
            teachers.append(name)
    spaces = unique(spaces)
    catalog = Catalog.build(teachers, spaces)
    activities, outside = [], 0
    for row in rows:
        values, errors = row['values'], row['errors']
        if values.get(KIND_COLUMN) != ACTIVITY_KIND:
            outside += bool(errors)
            continue
        raw = sheet_text(values.get(ACTIVITY_COLUMN))
        reading = resolve(raw, catalog)
        label, short_name = split_header(values.get(GROUP_COLUMN))
        activity = Activity(
            space=reading.space_name,
            weekday=parse_weekday(values.get(DAY_COLUMN)),
            slot=safe_slot(values.get(SLOT_COLUMN)),
            subject=reading.subject_name or raw,
            class_group=label or '',
            course=sheet_text(values.get(COURSE_COLUMN)) or short_name or '',
            stage=STAGES.get(sheet_of(values), ''),
            teachers=tuple(reading.teacher_names),
            raw_text=raw,
            state=ERROR if errors else OK,
            action=row['action'],
            line=row['line_number'],
            message=errors[0]['message'] if errors else None,
        )
        if activity.space is None or activity.weekday is None or activity.slot is None:
            outside += activity.state == ERROR
            continue
        activities.append(activity)
    return ImportReading(spaces=spaces, activities=activities, outside_error_count=outside)


def cell_kind(activities):
    """Classifica as atividades da faixa: uma turma, turmas juntas ou choque (D13)."""
    groups = {(activity.course, activity.class_group) for activity in activities}
    if len(groups) <= 1:
        return SINGLE
    subjects = {(activity.subject.casefold(), frozenset(name.casefold() for name in activity.teachers)) for activity in activities}
    return JOINT if len(subjects) == 1 else CLASH


def slot_key(activities):
    """Chave que diz se duas faixas seguidas têm as mesmas atividades (D5)."""
    return tuple(sorted((activity.raw_text.casefold(), activity.course, activity.class_group, activity.state) for activity in activities))


def ordered(activities):
    return sorted(activities, key=lambda activity: (activity.course, activity.class_group, activity.line))


def build_day(slots, by_slot):
    """Células do dia, uma por faixa, com os blocos de faixas seguidas unidos (D5, D6)."""
    cells, previous_key, open_cell, previous_slot = [], None, None, None
    for slot in slots:
        activities = by_slot.get(slot, [])
        key = slot_key(activities) if activities else None
        contiguous = previous_slot is not None and previous_slot[1] == slot[0]
        if key and key == previous_key and contiguous:
            open_cell.span += 1
            open_cell.end = slot[1]
            for entry, activity in zip(open_cell.entries, ordered(activities)):
                entry.lines.append(activity.line)
            cells.append(CONTINUED)
        elif activities:
            open_cell = Cell(
                entries=[
                    Entry(
                        subject=activity.subject,
                        class_group=activity.class_group,
                        course=activity.course,
                        stage=activity.stage,
                        teachers=activity.teachers,
                        raw_text=activity.raw_text,
                        state=activity.state,
                        action=activity.action,
                        message=activity.message,
                        lines=[activity.line],
                    )
                    for activity in ordered(activities)
                ],
                kind=cell_kind(activities),
                start=slot[0],
                end=slot[1],
            )
            cells.append(open_cell)
        else:
            open_cell = None
            cells.append(None)
        previous_key, previous_slot = key, slot
    return cells


def weekday_of(today):
    """Código do dia da semana de uma data, ou None no sábado e no domingo."""
    if today is None or today.weekday() > 4:
        return None
    return WEEKDAYS[today.weekday()]


def build_room_week(spaces, activities, space_name, today, outside_error_count=0):
    """Semana da sala escolhida, ou da primeira sala da lista quando a escolhida não existe (D3)."""
    by_space = {}
    for activity in activities:
        by_space.setdefault(activity.space.casefold(), {}).setdefault((activity.weekday, activity.slot), []).append(activity)
    clashes = {
        name: sum(1 for found in by_space.get(name.casefold(), {}).values() if cell_kind(found) == CLASH)
        for name in spaces
    }
    chosen = next((name for name in spaces if space_name and name.casefold() == space_name.casefold()), None)
    chosen = chosen or (spaces[0] if spaces else None)
    slots = sorted({activity.slot for activity in activities})
    today_code = weekday_of(today)
    room = by_space.get(chosen.casefold(), {}) if chosen else {}
    days = []
    for weekday in WEEKDAYS:
        by_slot = {slot: found for (day, slot), found in room.items() if day == weekday}
        days.append(Day(
            weekday=weekday,
            label=Weekday(weekday).label.split('-')[0],
            is_today=weekday == today_code,
            cells=build_day(slots, by_slot),
        ))
    rows = [Row(start=slot[0], end=slot[1], cells=[day.cells[index] for day in days]) for index, slot in enumerate(slots)]
    occupied = len(room)
    return RoomWeek(
        space=chosen,
        spaces=[SpaceOption(name=name, has_clash=bool(clashes[name])) for name in spaces],
        rows=rows,
        days=days,
        occupied=occupied,
        available=len(slots) * len(WEEKDAYS) - occupied,
        clash_count=clashes.get(chosen, 0) if chosen else 0,
        error_count=sum(1 for found in room.values() for activity in found if activity.state == ERROR),
        outside_error_count=outside_error_count,
    )


def room_week_from_import(importation, space_name, today):
    """Grade da semana de uma sala, a partir das linhas da importação."""
    reading = read_import(importation)
    return build_room_week(reading.spaces, reading.activities, space_name, today, reading.outside_error_count)
