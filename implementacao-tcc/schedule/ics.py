"""Exportação do calendário público em iCalendar (.ics), para importar ou assinar no Google Agenda."""

import hashlib
import unicodedata
from datetime import datetime

from django.utils import timezone

from schedule.models import AllocationException
from schedule.public import STAGES, entries_of, public_allocations, public_bookings, read_filters, weekdays_between
from schedule.timetable import WEEKDAYS

TZID = 'America/Sao_Paulo'
PRODID = '-//IFAgenda//Calendario publico//PT'


def escape(text):
    """Escapa o texto conforme a RFC 5545."""
    return (
        str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\r\n', '\\n').replace('\n', '\\n')
    )


def fold(line):
    """Quebra a linha em até 75 octetos, continuando com um espaço."""
    data = line.encode('utf-8')
    if len(data) <= 75:
        return line
    parts, current = [], b''
    for char in line:
        encoded = char.encode('utf-8')
        if len(current) + len(encoded) > (75 if not parts else 74):
            parts.append(current.decode('utf-8'))
            current = b''
        current += encoded
    parts.append(current.decode('utf-8'))
    return '\r\n '.join(parts)


def local(day, moment):
    return datetime.combine(day, moment).strftime('%Y%m%dT%H%M%S')


def event(uid, day, start, end, summary, location, description, stamp):
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}@ifagenda',
        f'DTSTAMP:{stamp}',
        f'DTSTART;TZID={TZID}:{local(day, start)}',
        f'DTEND;TZID={TZID}:{local(day, end)}',
        f'SUMMARY:{escape(summary)}',
    ]
    if location:
        lines.append(f'LOCATION:{escape(location)}')
    if description:
        lines.append(f'DESCRIPTION:{escape(description)}')
    lines.append('END:VEVENT')
    return lines


def uid_of(*parts):
    return hashlib.sha1('|'.join(str(part) for part in parts).encode('utf-8')).hexdigest()


def calendar_name(calendar):
    return f'Horários {calendar.semester_code} - {calendar.summary}'


def filename_of(calendar):
    """Nome do arquivo só com letras, números e hífens."""
    base = f'horarios-{calendar.semester_code}-{calendar.summary}'
    ascii_text = unicodedata.normalize('NFKD', base.casefold()).encode('ascii', 'ignore').decode()
    slug = ''.join(char if char.isalnum() else '-' for char in ascii_text)
    return '-'.join(part for part in slug.split('-') if part)[:80] + '.ics'


def export_calendar(params, today):
    """(calendário, texto .ics) do semestre inteiro com os filtros da URL; texto None quando não há o que exportar."""
    calendar, semester = read_filters(params, today)
    if semester is None or not semester.has_period or not calendar.has_principal:
        return calendar, None
    allocations = public_allocations(
        semester, calendar.space, calendar.teacher, calendar.course, STAGES.get(calendar.stage_key), calendar.group,
    )
    dates = [day for day in weekdays_between(semester.start_date, semester.end_date) if semester.contains(day)]
    cancelled = AllocationException.objects.cancelled(
        [allocation.pk for allocation in allocations], semester.start_date, semester.end_date,
    )
    by_weekday = {}
    for allocation, entry in entries_of(allocations):
        allocation.semester = semester
        by_weekday.setdefault(allocation.weekday, []).append((allocation, entry))
    stamp = timezone.now().strftime('%Y%m%dT%H%M%SZ')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{PRODID}',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape(calendar_name(calendar))}',
        f'X-WR-TIMEZONE:{TZID}',
    ]
    for day in dates:
        for allocation, entry in by_weekday.get(WEEKDAYS[day.weekday()], []):
            if not allocation.occurs_on(day) or (allocation.pk, day) in cancelled:
                continue
            slot = allocation.time_slot
            teachers = ', '.join(teacher.name for teacher in entry.teachers)
            description = '\n'.join(part for part in (entry.group_label, teachers and f'Docente: {teachers}') if part)
            lines += event(
                uid_of('aula', allocation.pk, day), day, slot.start_time, slot.end_time,
                entry.subject, entry.space, description, stamp,
            )
    if calendar.course is None and not calendar.stage_key:
        for booking in public_bookings(dates, calendar.space, calendar.teacher):
            entry = booking.entry
            summary = entry.subject or 'Agendamento'
            description = f'Solicitante: {entry.requester}' if entry.requester else ''
            lines += event(
                uid_of('agendamento', booking.date, booking.start, entry.space, summary), booking.date,
                booking.start, booking.end, summary, entry.space, description, stamp,
            )
    lines.append('END:VCALENDAR')
    return calendar, '\r\n'.join(fold(line) for line in lines) + '\r\n'
