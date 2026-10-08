"""Ocupação média por dia da semana e faixa, pela mesma união de intervalos do painel."""

import math
from dataclasses import dataclass, field
from datetime import timedelta

from panel.indicators import bookings_between, minutes, union_minutes
from schedule.models import WEEKDAY_ORDER, Allocation, Space, TimeSlot
from schedule.occupancy import occurrences_of_all_spaces
from schedule.timetable import natural_key

ALL = 'todos'
LESSONS = 'aulas'
BOOKINGS = 'agendamentos'
LEVELS = 5
WEEKDAY_SHORT = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex')


def day_slug(weekday):
    return weekday.value.lower()


@dataclass
class Filters:
    semester: object
    origin: str = ALL
    stage: str = ''
    course: object = None
    spaces: list = field(default_factory=list)


@dataclass
class Slot:
    start: object
    end: object

    @property
    def label(self):
        return f'{self.start:%H:%M} às {self.end:%H:%M}'

    @property
    def length(self):
        return minutes(self.end) - minutes(self.start)


@dataclass
class Cell:
    """Um dia da semana numa faixa, com os rótulos para o template."""

    day: int
    slot: int
    weeks: int
    space_count: int
    weekday: object
    day_short: str
    slot_obj: Slot
    occupied: int = 0
    usage: dict = field(default_factory=dict)

    @property
    def share(self):
        capacity = self.weeks * self.space_count
        return self.occupied / capacity if capacity else 0

    @property
    def percent(self):
        return round(self.share * 100)

    @property
    def average(self):
        """Espaços ocupados em média nas semanas do semestre."""
        return round(self.occupied / self.weeks) if self.weeks else 0

    @property
    def slug(self):
        return day_slug(self.weekday)

    @property
    def level(self):
        return min(LEVELS, math.ceil(self.share * LEVELS)) if self.occupied else 0


@dataclass
class Heatmap:
    slots: list
    days: list
    rows: list
    space_count: int
    occupied_minutes: int = 0
    lesson_minutes: int = 0
    available_minutes: int = 0
    peak: Cell = None
    quietest: Cell = None

    @property
    def rate(self):
        return round(self.occupied_minutes * 100 / self.available_minutes) if self.available_minutes else 0

    @property
    def occupied_hours(self):
        return round(self.occupied_minutes / 60)

    @property
    def available_hours(self):
        return round(self.available_minutes / 60)

    @property
    def lesson_percent(self):
        return round(self.lesson_minutes * 100 / self.occupied_minutes) if self.occupied_minutes else 0

    @property
    def booking_percent(self):
        return 100 - self.lesson_percent if self.occupied_minutes else 0

    def cell(self, day, slot):
        return self.rows[slot][day]


def semester_slots(semester):
    """Faixas do semestre sem repetição, na ordem do dia."""
    seen = []
    for start, end in TimeSlot.objects.filter(semester=semester).values_list('start_time', 'end_time'):
        if (start, end) not in seen:
            seen.append((start, end))
    return [Slot(start, end) for start, end in sorted(seen)]


def chosen_spaces(filters):
    spaces = filters.spaces or Space.objects.filter(is_active=True)
    return sorted(spaces, key=natural_key)


def allowed_allocations(filters):
    """Alocações do semestre que passam pelos filtros de etapa e curso."""
    allocations = Allocation.objects.filter(semester=filters.semester)
    if filters.course is not None:
        allocations = allocations.filter(class_group__course=filters.course)
    elif filters.stage:
        allocations = allocations.filter(class_group__course__stage=filters.stage)
    return set(allocations.values_list('pk', flat=True))


def covered(intervals, slot):
    """Minutos da faixa cobertos pela união dos intervalos."""
    low, high = minutes(slot.start), minutes(slot.end)
    return union_minutes([(max(start, low), min(end, high)) for start, end in intervals if start < high and end > low])


def build(filters):
    """Matriz faixa × dia com os indicadores, ou None quando o semestre não tem período."""
    semester = filters.semester
    if semester is None or semester.start_date is None or semester.end_date is None:
        return None
    slots = semester_slots(semester)
    spaces = chosen_spaces(filters)
    space_ids = {space.pk for space in spaces}
    dates = []
    day = semester.start_date
    while day <= semester.end_date:
        if day.weekday() < len(WEEKDAY_ORDER):
            dates.append(day)
        day += timedelta(days=1)
    weeks = [sum(1 for item in dates if item.weekday() == index) for index in range(len(WEEKDAY_ORDER))]
    rows = [
        [
            Cell(index, position, weeks[index], len(spaces), WEEKDAY_ORDER[index], WEEKDAY_SHORT[index], slot)
            for index in range(len(WEEKDAY_ORDER))
        ]
        for position, slot in enumerate(slots)
    ]
    heatmap = Heatmap(
        slots, list(WEEKDAY_SHORT), rows, len(spaces),
        available_minutes=len(spaces) * len(dates) * sum(slot.length for slot in slots),
    )
    lessons, bookings = {}, {}
    if filters.origin != BOOKINGS:
        allowed = allowed_allocations(filters)
        for occurrence in occurrences_of_all_spaces(semester.start_date, semester.end_date):
            if occurrence.allocation_id in allowed and occurrence.space_id in space_ids:
                lessons.setdefault((occurrence.space_id, occurrence.date), []).append((minutes(occurrence.start), minutes(occurrence.end)))
    if filters.origin != LESSONS:
        for day, space_id, starts, ends, *_ in bookings_between(semester.start_date, semester.end_date):
            if space_id in space_ids and day.weekday() < len(WEEKDAY_ORDER):
                bookings.setdefault((space_id, day), []).append((starts, ends))
    for key in set(lessons) | set(bookings):
        space_id, day = key
        lesson_intervals = lessons.get(key, [])
        every_interval = [*lesson_intervals, *bookings.get(key, [])]
        for position, slot in enumerate(slots):
            total = covered(every_interval, slot)
            if not total:
                continue
            lesson_total = covered(lesson_intervals, slot)
            heatmap.occupied_minutes += total
            heatmap.lesson_minutes += lesson_total
            cell = rows[position][day.weekday()]
            cell.occupied += 1
            usage = cell.usage.setdefault(space_id, [0, 0])
            usage[0 if lesson_total else 1] += 1
    busy_days = {cell.day for row in rows for cell in row if cell.occupied}
    for index in range(len(WEEKDAY_ORDER)):
        for row in rows:
            cell = row[index]
            if heatmap.peak is None or cell.share > heatmap.peak.share:
                heatmap.peak = cell
            if index in busy_days and (heatmap.quietest is None or cell.share < heatmap.quietest.share):
                heatmap.quietest = cell
    if heatmap.peak is not None and not heatmap.peak.occupied:
        heatmap.peak = None
    return heatmap


@dataclass
class SpaceUsage:
    space: Space
    lesson_weeks: int = 0
    booking_weeks: int = 0

    @property
    def kind(self):
        return 'Aula' if self.lesson_weeks >= self.booking_weeks else 'Agendamento'

    @property
    def tone(self):
        return 'success' if self.kind == 'Aula' else 'warning'

    @property
    def icon(self):
        return 'calendar-check' if self.kind == 'Aula' else 'calendar-clock'

    @property
    def weeks(self):
        return self.lesson_weeks + self.booking_weeks


def cell_spaces(heatmap, cell, filters):
    """Espaços ocupados, do mais frequente ao menos, e os disponíveis em todas as semanas."""
    spaces = chosen_spaces(filters)
    busy = [SpaceUsage(space, *cell.usage[space.pk]) for space in spaces if space.pk in cell.usage]
    busy.sort(key=lambda item: -item.weeks)
    free = [space for space in spaces if space.pk not in cell.usage]
    return busy, free
