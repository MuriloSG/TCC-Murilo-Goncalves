"""Indicadores do painel administrativo, calculados a cada requisição e nunca gravados.

Cada função atende um bloco do painel e só é chamada quando o usuário tem a permissão do
módulo dono dos dados (D1 da Change exibir-painel-administrativo). As contagens que o ORM
resolve ficam no banco; a união dos intervalos e o conflito de docente são feitos em Python
sobre as alocações de um semestre (D10).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from bookings.models import Booking, BookingRequest
from imports.models import Import
from schedule.models import WEEKDAY_ORDER, Allocation, Semester, Space
from schedule.occupancy import occurrences_of_all_spaces
from schedule.timetable import current_semester_code, group_label, imported_semesters, monday_of, natural_key

TODAY = 'hoje'
WEEK = 'semana'
LIST_SIZE = 5
MODAL_PAGE_SIZE = 5
TOP_SPACES = 10
SPACE_ALLOCATION_IMPORT = 'ENSALAMENTO'
OPEN_IMPORT_STATUSES = (Import.Status.VALIDATED, Import.Status.PENDING, Import.Status.WITH_ERRORS)
WEEKDAY_SHORT = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')


def now_local():
    return timezone.localtime(timezone.now())


def default_semester(semesters, today):
    """O semestre do dia, quando importado, ou o mais recente."""
    current = current_semester_code(today)
    return next((semester for semester in semesters if semester.code == current), semesters[0] if semesters else None)


def chosen_semester(code, today):
    """Semestres importados e o escolhido; um código que não é opção cai no padrão."""
    semesters = imported_semesters()
    chosen = next((semester for semester in semesters if semester.code == code), None)
    return semesters, chosen or default_semester(semesters, today)


def waiting_text(created_at, today):
    days = (today - timezone.localtime(created_at).date()).days
    if days <= 0:
        return 'hoje'
    return 'há 1 dia' if days == 1 else f'há {days} dias'


def requests_summary(moment):
    """Contagens das solicitações e as cinco pendentes pedidas por último, na ordem da data de uso (A1 a A5)."""
    today, at = moment.date(), moment.time()
    passed = Q(date__lt=today) | Q(date=today, start_time__lte=at)
    pending = Q(status=BookingRequest.Status.PENDING)
    counts = BookingRequest.objects.aggregate(
        pending=Count('pk', filter=pending),
        overdue=Count('pk', filter=pending & passed),
        awaiting=Count('pk', filter=Q(status=BookingRequest.Status.SUGGESTED)),
    )
    upcoming = sorted(
        BookingRequest.objects.filter(status=BookingRequest.Status.PENDING)
        .exclude(passed)
        .select_related('space', 'requested_by')
        .order_by('-created_at', '-pk')[:LIST_SIZE],
        key=lambda request: (request.date, request.start_time, request.created_at, request.pk),
    )
    for request in upcoming:
        request.waiting = waiting_text(request.created_at, today)
    return {**counts, 'upcoming': upcoming}


def union_minutes(intervals):
    """Minutos cobertos pela união de intervalos `[início, fim)` em minutos do dia."""
    total, current_start, current_end = 0, None, None
    for start, end in sorted(intervals):
        if current_end is None or start > current_end:
            if current_end is not None:
                total += current_end - current_start
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_end is not None:
        total += current_end - current_start
    return total


def minutes(at):
    return at.hour * 60 + at.minute


def step(value, maximum):
    """Proporção em passos de 5%, para as classes `bar-w-*` e `bar-h-*`."""
    if not maximum or not value:
        return 0
    return max(5, min(100, round(value * 20 / maximum) * 5))


@dataclass
class SpaceLoad:
    """Horas ocupadas de um espaço no período, com a parte das aulas e a dos agendamentos fora de aula."""

    space: Space
    total: int = 0
    lessons: int = 0
    lesson_count: int = 0
    booking_count: int = 0
    total_width: int = 0
    lesson_width: int = 0
    booking_width: int = 0

    @property
    def hours(self):
        return self.total / 60

    @property
    def lesson_hours(self):
        return self.lessons / 60

    @property
    def booking_hours(self):
        return (self.total - self.lessons) / 60


@dataclass
class DayLoad:
    day: date
    label: str
    is_today: bool
    total: int = 0
    lessons: int = 0
    height: int = 0
    lesson_share: int = 0
    booking_share: int = 0

    @property
    def hours(self):
        return self.total / 60


@dataclass
class Occupancy:
    view: str
    start: date
    end: date
    spaces: list = field(default_factory=list)
    idle: list = field(default_factory=list)
    days: list = field(default_factory=list)
    without_semester: bool = False
    without_period: Semester = None


def bookings_between(start, end):
    """Agendamentos que começam nas datas do intervalo, com a data e as horas locais."""
    first = timezone.make_aware(datetime.combine(start, time.min))
    last = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    result = []
    for booking in Booking.objects.filter(starts_at__lt=last, ends_at__gt=first).values('pk', 'space_id', 'starts_at', 'ends_at'):
        starts, ends = timezone.localtime(booking['starts_at']), timezone.localtime(booking['ends_at'])
        result.append((starts.date(), booking['space_id'], minutes(starts.time()), minutes(ends.time()) or 24 * 60, booking['pk'], starts, ends))
    return result


def occupancy(view, today):
    """Ocupação de hoje ou da semana atual por espaço e por dia, pela união dos intervalos (D4).

    Aula compartilhada, faixas sobrepostas e agendamento sobre aula contam uma vez, e o trecho
    de agendamento sobreposto a aula entra na parte das aulas. As contagens são de ocorrências:
    a aula conta uma vez por espaço, data e faixa. Sem percentual (D5).
    """
    start, end = (today, today) if view == TODAY else (monday_of(today), monday_of(today) + timedelta(days=6))
    lessons, bookings = {}, {}
    for occurrence in occurrences_of_all_spaces(start, end):
        lessons.setdefault((occurrence.space_id, occurrence.date), set()).add((minutes(occurrence.start), minutes(occurrence.end)))
    for day, space_id, starts, ends, *_ in bookings_between(start, end):
        bookings.setdefault((space_id, day), []).append((starts, ends))
    by_space, by_day = {}, {}
    for key in set(lessons) | set(bookings):
        space_id, day = key
        lesson_intervals = lessons.get(key, set())
        booking_intervals = bookings.get(key, [])
        total = union_minutes([*lesson_intervals, *booking_intervals])
        lesson_total = union_minutes(lesson_intervals)
        load = by_space.setdefault(space_id, [0, 0, 0, 0])
        load[0] += total
        load[1] += lesson_total
        load[2] += len(lesson_intervals)
        load[3] += len(booking_intervals)
        day_load = by_day.setdefault(day, [0, 0])
        day_load[0] += total
        day_load[1] += lesson_total
    spaces = Space.objects.filter(Q(is_active=True) | Q(pk__in=by_space)).only('pk', 'name', 'is_active')
    loads, idle = [], []
    for space in spaces:
        values = by_space.get(space.pk)
        if values and values[0]:
            loads.append(SpaceLoad(space, *values))
        elif space.is_active:
            idle.append(space)
    loads.sort(key=lambda load: (-load.total, natural_key(load.space)))
    loads = loads[:TOP_SPACES]
    highest = loads[0].total if loads else 0
    for load in loads:
        load.total_width = step(load.total, highest)
        load.lesson_width = min(step(load.lessons, highest), load.total_width)
        load.booking_width = load.total_width - load.lesson_width
    days = []
    if view == WEEK:
        busiest = max((values[0] for values in by_day.values()), default=0)
        for offset in range(7):
            day = start + timedelta(days=offset)
            total, lesson_total = by_day.get(day, (0, 0))
            item = DayLoad(day, WEEKDAY_SHORT[offset], day == today, total, lesson_total, step(total, busiest))
            item.lesson_share = step(lesson_total, total)
            item.booking_share = 100 - item.lesson_share if total > lesson_total else 0
            if not item.booking_share:
                item.lesson_share = 100
            days.append(item)
    running = Semester.objects.filter(start_date__lte=end, end_date__gte=start).exists()
    without_period = Semester.objects.filter(code=current_semester_code(today), start_date__isnull=True).first()
    return Occupancy(
        view, start, end, loads, sorted(idle, key=natural_key), days,
        without_semester=not running, without_period=without_period,
    )


def current_allocations(semester, today):
    """Alocações vigentes do semestre: a vigência não terminou antes de hoje e não termina antes de começar (D6)."""
    return (
        Allocation.objects.filter(semester=semester)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        .exclude(valid_from__isnull=False, valid_until__isnull=False, valid_until__lt=F('valid_from'))
        .select_related('subject', 'time_slot', 'space', 'class_group__course')
        .prefetch_related('teachers')
    )


def lesson_order(allocation):
    return WEEKDAY_ORDER.index(allocation.weekday), allocation.time_slot.start_time, allocation.subject.name


def lesson_key(allocation):
    return allocation.class_group_id, allocation.subject_id, allocation.weekday, allocation.time_slot_id


@dataclass
class Issue:
    """Uma pendência da grade com o texto da aula e o espaço, para o link à Grade."""

    text: str
    space: Space = None


def lesson_text(allocation):
    slot = allocation.time_slot
    return (
        f'{allocation.subject.name}, {group_label(allocation.class_group)}, '
        f'{allocation.get_weekday_display().lower()} das {slot.start_time:%H:%M} às {slot.end_time:%H:%M}'
    )


def overlaps(first, second):
    return first.time_slot.start_time < second.time_slot.end_time and second.time_slot.start_time < first.time_slot.end_time


def validity_crosses(first, second):
    return (first.valid_from or date.min) <= (second.valid_until or date.max) and (second.valid_from or date.min) <= (first.valid_until or date.max)


def teacher_conflicts(allocations):
    """Pares de aulas do mesmo docente no mesmo dia, em faixas sobrepostas, com vigências que se
    cruzam e em espaços diferentes ou sem espaço. Aula no mesmo espaço é a compartilhada (D7)."""
    by_teacher = {}
    for allocation in allocations:
        for teacher in allocation.teachers.all():
            by_teacher.setdefault((teacher, allocation.weekday), []).append(allocation)
    found = {}
    for (teacher, _), items in by_teacher.items():
        for index, first in enumerate(items):
            for second in items[index + 1:]:
                if lesson_key(first) == lesson_key(second):
                    continue
                if first.space_id is not None and first.space_id == second.space_id:
                    continue
                if not overlaps(first, second) or not validity_crosses(first, second):
                    continue
                pair = (teacher.pk, *sorted([lesson_key(first), lesson_key(second)]))
                if pair not in found:
                    places = ' e '.join(allocation.space.name if allocation.space else 'sem espaço' for allocation in (first, second))
                    slot = first.time_slot
                    found[pair] = Issue(
                        f'{teacher.name}: {places}, {first.get_weekday_display().lower()} das {slot.start_time:%H:%M} às {slot.end_time:%H:%M}',
                        first.space or second.space,
                    )
    return list(found.values())


def booking_clashes(semester, moment):
    """Agendamentos futuros, até o fim do semestre, sobrepostos a uma aula ativa do mesmo espaço (D8)."""
    if semester is None or not semester.has_period or semester.end_date < moment.date():
        return []
    start, end = moment.date(), semester.end_date
    lessons = {}
    for occurrence in occurrences_of_all_spaces(start, end):
        lessons.setdefault((occurrence.space_id, occurrence.date), []).append((minutes(occurrence.start), minutes(occurrence.end)))
    clashes = []
    for day, space_id, starts, ends, pk, starts_at, ends_at in bookings_between(start, end):
        if starts_at <= moment:
            continue
        if any(starts < lesson_end and lesson_start < ends for lesson_start, lesson_end in lessons.get((space_id, day), [])):
            clashes.append((pk, day, starts_at, ends_at))
    if not clashes:
        return []
    spaces = {booking.pk: booking.space for booking in Booking.objects.filter(pk__in=[pk for pk, *_ in clashes]).select_related('space')}
    return [
        Issue(f'{spaces[pk].name}, {day:%d/%m/%Y} das {starts_at:%H:%M} às {ends_at:%H:%M}', spaces[pk])
        for pk, day, starts_at, ends_at in sorted(clashes, key=lambda item: item[2])
    ]


@dataclass
class IssueGroup:
    key: str
    label: str
    icon: str
    tone: str
    items: list
    hint: str = ''

    @property
    def count(self):
        return len(self.items)

    @property
    def shown(self):
        return self.items[:LIST_SIZE]


def grid_issues(semester, moment, with_bookings):
    """Aulas sem espaço, sem docente, possíveis conflitos de docente e agendamentos em choque (C1, C2, C5 e C7)."""
    allocations = list(current_allocations(semester, moment.date()))
    without_space, without_teacher = {}, {}
    for allocation in sorted(allocations, key=lesson_order):
        key = lesson_key(allocation)
        if allocation.space_id is None:
            without_space.setdefault(key, Issue(lesson_text(allocation)))
        if not allocation.teachers.all():
            without_teacher.setdefault(key, Issue(lesson_text(allocation), allocation.space))
    groups = [
        IssueGroup('sem-espaco', 'Sem espaço', 'map-pin', 'warning', list(without_space.values()), 'Aulas vigentes do semestre que ainda não têm sala definida.'),
        IssueGroup('sem-docente', 'Sem docente', 'user-x', 'warning', list(without_teacher.values()), 'Aulas vigentes do semestre sem nenhum docente na grade.'),
        IssueGroup('conflito', 'Possível conflito', 'arrow-left-right', 'error', teacher_conflicts(allocations), 'Mesmo docente em dois espaços diferentes, no mesmo dia e horário.'),
    ]
    if with_bookings:
        groups.append(IssueGroup('choque', 'Agendamento em choque', 'calendar-x', 'error', booking_clashes(semester, moment), 'Agendamentos aprovados que passaram a coincidir com uma aula no mesmo espaço.'))
    return groups


def idle_group(occupancy):
    """Espaços ativos sem ocupação no período da ocupação, como um bloco das pendências."""
    period = 'hoje' if occupancy.view == TODAY else 'nesta semana'
    return IssueGroup(
        'sem-ocupacao', 'Sem ocupação', 'door-open', 'neutral', [Issue(space.name, space) for space in occupancy.idle],
        f'Espaços ativos sem aula nem agendamento {period}.',
    )


def open_imports():
    """Importações do ensalamento que não foram confirmadas nem descartadas (D1 da avaliação)."""
    queryset = Import.objects.filter(kind=SPACE_ALLOCATION_IMPORT, status__in=OPEN_IMPORT_STATUSES).order_by('created_at', 'pk')
    return queryset.count(), list(queryset[:LIST_SIZE])
