"""Ocupação calculada das regras e nunca gravada; outras fontes entram por `register_source`."""

from dataclasses import dataclass
from datetime import date, time, timedelta

from schedule.models import Allocation, AllocationException, Semester
from schedule.timetable import WEEKDAYS, Entry, group_fields

SPACE_ALLOCATION = 'ENSALAMENTO'


@dataclass(frozen=True)
class Occurrence:
    """Uma ocupação do espaço numa data e numa faixa, com o tipo da fonte e o conteúdo do card."""

    date: date
    start: time
    end: time
    space_id: int
    kind: str
    entry: Entry


def dates_between(start_date, end_date):
    day = start_date
    while day <= end_date:
        yield day
        day += timedelta(days=1)


class AllocationSource:
    """Ocorrências do ensalamento em quatro consultas, sem as canceladas."""

    kind = SPACE_ALLOCATION

    def occurrences(self, space, start_date, end_date):
        semesters = {
            semester.pk: semester
            for semester in Semester.objects.filter(start_date__lte=end_date, end_date__gte=start_date)
        }
        if not semesters:
            return []
        allocations = (
            Allocation.objects.filter(semester__in=semesters, space=space)
            .select_related('subject', 'time_slot', 'class_group__course')
            .prefetch_related('teachers')
        )
        by_weekday = {}
        for allocation in allocations:
            allocation.semester = semesters[allocation.semester_id]
            by_weekday.setdefault(allocation.weekday, []).append(allocation)
        cancelled = AllocationException.objects.cancelled(
            [allocation.pk for items in by_weekday.values() for allocation in items], start_date, end_date,
        )
        result = []
        for day in dates_between(start_date, end_date):
            if day.weekday() >= len(WEEKDAYS):
                continue
            for allocation in by_weekday.get(WEEKDAYS[day.weekday()], []):
                if not allocation.occurs_on(day) or (allocation.pk, day) in cancelled:
                    continue
                result.append(Occurrence(
                    date=day,
                    start=allocation.time_slot.start_time,
                    end=allocation.time_slot.end_time,
                    space_id=space.pk,
                    kind=self.kind,
                    entry=Entry(
                        subject=allocation.subject.name,
                        **group_fields(allocation.class_group),
                        teachers=tuple(sorted(teacher.name for teacher in allocation.teachers.all())),
                        stage=allocation.class_group.course.stage,
                        allocation_ids=(allocation.pk,),
                    ),
                ))
        return result


@dataclass(frozen=True)
class SpaceOccurrence:
    """Uma ocorrência de aula com espaço numa data, sem o conteúdo do card."""

    date: date
    start: time
    end: time
    space_id: int
    allocation_id: int


def occurrences_of_all_spaces(start_date, end_date):
    """Ocorrências de todos os espaços no intervalo, em três consultas, para o painel."""
    if start_date > end_date:
        return []
    semesters = {
        semester.pk: semester
        for semester in Semester.objects.filter(start_date__lte=end_date, end_date__gte=start_date)
    }
    if not semesters:
        return []
    by_weekday = {}
    for allocation in Allocation.objects.filter(semester__in=semesters, space__isnull=False).select_related('time_slot'):
        allocation.semester = semesters[allocation.semester_id]
        by_weekday.setdefault(allocation.weekday, []).append(allocation)
    cancelled = AllocationException.objects.cancelled(
        [allocation.pk for items in by_weekday.values() for allocation in items], start_date, end_date,
    )
    result = []
    for day in dates_between(start_date, end_date):
        if day.weekday() >= len(WEEKDAYS):
            continue
        for allocation in by_weekday.get(WEEKDAYS[day.weekday()], []):
            if not allocation.occurs_on(day) or (allocation.pk, day) in cancelled:
                continue
            result.append(SpaceOccurrence(
                date=day,
                start=allocation.time_slot.start_time,
                end=allocation.time_slot.end_time,
                space_id=allocation.space_id,
                allocation_id=allocation.pk,
            ))
    return result


_registered = []
_public = []


def register_source(source, public=False):
    """Acrescenta a fonte de outro app no `ready()`, sem que o `schedule` dependa dele."""
    if not any(type(item) is type(source) for item in _registered):
        _registered.append(source)
        if public:
            _public.append(source)


def grid_sources():
    """Fontes de ocupação que a Grade reúne, na ordem em que aparecem na célula."""
    return [AllocationSource(), *_registered]


def public_sources():
    """Fontes registradas que o calendário público mostra, além do ensalamento."""
    return list(_public)


def occupancy(space, start_date, end_date, sources=None):
    """Ocorrências do espaço no intervalo, de todas as fontes, em ordem de data e de horário."""
    if space is None or start_date > end_date:
        return []
    found = []
    for source in grid_sources() if sources is None else sources:
        found.extend(source.occurrences(space, start_date, end_date))
    return sorted(found, key=lambda item: (item.date, item.start, item.end, item.entry.group_label, item.entry.subject))
