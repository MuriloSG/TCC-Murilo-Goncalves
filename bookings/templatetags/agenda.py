"""Auxiliares dos templates da Agenda."""

from django import template

from schedule.timetable import CLASH, JOINT, SINGLE

register = template.Library()


@register.filter
def lesson_kind(cell):
    """Uma turma, turmas juntas ou choque, contando só as aulas da célula.

    Os agendamentos têm o próprio selo e não entram na classificação das turmas.
    """
    lessons = [entry for entry in cell.entries if not getattr(entry, 'is_booking', False)]
    groups = {entry.group_label for entry in lessons}
    if len(groups) <= 1:
        return SINGLE
    kinds = {(entry.subject.casefold(), frozenset(name.casefold() for name in entry.teachers)) for entry in lessons}
    return JOINT if len(kinds) == 1 else CLASH


@register.filter
def lesson_groups(cell):
    return len({entry.group_label for entry in cell.entries if not getattr(entry, 'is_booking', False)})
