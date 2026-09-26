"""Telas da Agenda: a Grade, a solicitação, as solicitações do usuário e a análise.

Cada rota tem `login_required` no `urls.py` e declara a sua permissão, verificada pelo
PermissionMiddleware (D1 e D2 da Change agendar-uso-eventual-dos-espacos). As rotas de
"Minhas solicitações" carregam só as solicitações do próprio usuário, e o ID de outro
usuário responde 404. As regras ficam nas operações do model; as views só as chamam.
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from accounts import permissions
from bookings.occupancy import agenda_sources
from schedule.forms import GridFilterForm
from schedule.models import Space
from schedule.occupancy import occupancy
from schedule.timetable import (
    current_semester_code,
    dated_space_month,
    dated_space_week,
    imported_semesters,
    month_reference,
    month_start,
    natural_key,
    occupation_text,
    parse_date,
    parse_month,
    space_week,
    week_start,
)

WEEK_VIEW = 'semana'
MONTH_VIEW = 'mes'


def bookable_spaces():
    """Espaços ativos, na ordem natural do nome: só eles aceitam solicitação."""
    return sorted(Space.objects.filter(is_active=True), key=natural_key)


class AgendaGridView(TemplateView):
    """Grade da Agenda: a mesma Grade do Ensalamento, com o ensalamento e os agendamentos.

    Reúne as fontes de `agenda_sources()` pela mesma `occupancy()` e monta a semana ou o mês
    pelas funções de `schedule.timetable`, com os agendamentos postos em todas as faixas que
    cruzam (D7). Não usa a view do Ensalamento.
    """

    permission_required = permissions.BOOKING_VIEW
    template_name = 'bookings/agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        semesters = {semester.code: semester for semester in imported_semesters()}
        current = current_semester_code(today)
        codes = sorted(set(semesters) | {current}, reverse=True)
        code = self.request.GET.get('semestre')
        code = code if code in codes else current
        semester = semesters.get(code)
        spaces = bookable_spaces()
        chosen = (self.request.GET.get('sala') or '').casefold()
        space = next((option for option in spaces if option.name.casefold() == chosen), spaces[0] if spaces else None)
        view = MONTH_VIEW if self.request.GET.get('visao') == MONTH_VIEW else WEEK_VIEW
        chosen_week = parse_date(self.request.GET.get('semana'))
        chosen_month = parse_month(self.request.GET.get('mes'))
        dated = semester is not None and semester.has_period
        sources = agenda_sources()
        if dated and view == MONTH_VIEW:
            first = month_start(semester, chosen_month or chosen_week, today)
            month_end = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            occurrences = occupancy(space, first, month_end, sources=sources) if space else []
            week = dated_space_month(semester, space, first, today, occurrences, by_overlap=True)
        elif dated:
            reference = chosen_week or (month_reference(semester, chosen_month, today) if chosen_month else None)
            start = week_start(semester, reference, today)
            occurrences = occupancy(space, start, start + timedelta(days=4), sources=sources) if space else []
            week = dated_space_week(semester, space, start, today, occurrences, by_overlap=True)
        else:
            view = WEEK_VIEW
            week = space_week(semester, space, today)
        grid_url = reverse('agenda_grid')
        is_month = view == MONTH_VIEW

        def grid_link(target, day=None, fragment=''):
            query = {'semestre': code, 'sala': space.name if space else ''}
            if target == MONTH_VIEW:
                query['visao'] = MONTH_VIEW
                if day is not None:
                    query['mes'] = f'{day:%Y-%m}'
            elif day is not None:
                query['semana'] = day.isoformat()
            return f'{grid_url}?{urlencode(query)}{fragment}'

        context.update(
            week=week,
            is_month=is_month,
            semester_code=code,
            space=space,
            semester=semester,
            period_missing=semester is not None and not semester.has_period,
            filter_form=GridFilterForm(
                {
                    'semestre': code,
                    'sala': space.name if space else '',
                    'visao': view,
                    'semana': week.start.isoformat() if week.start and not is_month else '',
                    'mes': f'{week.start:%Y-%m}' if week.start and is_month else '',
                },
                semesters=codes,
                spaces=spaces,
            ),
            grid_url=grid_url,
            previous_url=grid_link(view, week.previous) if week.previous else None,
            following_url=grid_link(view, week.following) if week.following else None,
            today_url=grid_link(view, fragment='#hoje' if is_month else ''),
            occupation_text=occupation_text(week, is_month),
            can_request=self.request.user.has_perm(permissions.BOOKING_REQUEST),
            shows_requester=self.request.user.has_perm(permissions.BOOKING_REVIEW),
        )
        return context
