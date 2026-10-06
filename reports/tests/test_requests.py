from datetime import date, time, timedelta

from django.http import QueryDict

from accounts import permissions
from bookings.models import BookingRequest
from bookings.tests.base import academic, user_with
from panel.tests.test_panel import PanelTestCase, at
from reports import requests
from reports.forms import RequestsFilterForm
from schedule.models import Course, Semester, Space, Stage

URL = '/relatorios/solicitacoes/'
Status = BookingRequest.Status


class RequestsTestCase(PanelTestCase):
    """Semestre 2026/2 de 03/08 a 18/12: 20 semanas, com o relógio em 05/10/2026 às 10:00.

    A aula na Sala 9/9 deixa o semestre importado, para que o filtro o ofereça.
    """

    def setUp(self):
        super().setUp()
        self.lesson('Sala 9/9')
        self.viewer = user_with('relatorio@ifnmg.edu.br', permissions.REPORT_VIEW, permissions.BOOKING_REVIEW)

    def ask(self, day=date(2026, 10, 7), status=Status.PENDING, space='Auditório', created=None, decided=None, assignment=None, **fields):
        place = Space.objects.filter(name=space).first() or Space.objects.register(space)
        request = BookingRequest.objects.create(
            requested_by=self.admin, space=place, date=day, start_time=time(14, 0), end_time=time(16, 0),
            description='Palestra.', status=status, teaching_assignment=assignment, **fields,
        )
        BookingRequest.objects.filter(pk=request.pk).update(created_at=created or at(date(2026, 10, 1)), decided_at=decided)
        request.refresh_from_db()
        return request

    def build(self, **kwargs):
        return requests.build(requests.Filters(Semester.objects.get(pk=self.semester.pk), **kwargs), date(2026, 10, 5))


class AccessTests(RequestsTestCase):
    def test_without_the_review_permission_is_403(self):
        self.client.force_login(user_with('relatorista@ifnmg.edu.br', permissions.REPORT_VIEW))
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_with_both_permissions_shows_the_report(self):
        self.ask()
        self.client.force_login(self.viewer)
        response = self.client.get(URL)
        self.assertContains(response, 'Solicitações por semana')
        self.assertContains(response, 'Taxa de aprovação')
        self.assertContains(response, '1 solicitação: 1 pendente.')


class PageTests(RequestsTestCase):
    def test_empty_period_shows_the_empty_states(self):
        self.client.force_login(self.viewer)
        response = self.client.get(URL)
        self.assertContains(response, 'Nenhuma solicitação de agendamento no período.')
        self.assertContains(response, 'Nenhuma solicitação rejeitada no período.')

    def test_semester_without_period_shows_the_warning(self):
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(URL), 'não tem período definido')

    def test_rejection_links_to_the_review_detail(self):
        request = self.ask(status=Status.REJECTED, decided=at(date(2026, 10, 2)), rejection_reason='Espaço em manutenção.')
        self.client.force_login(self.viewer)
        response = self.client.get(URL)
        self.assertContains(response, 'Espaço em manutenção.')
        self.assertContains(response, f'/agenda/solicitacoes/{request.pk}/')

    def test_space_links_to_the_agenda(self):
        self.ask(space='Sala 1/3')
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(URL), '/agenda/?sala=Sala+1%2F3')


class BuildTests(RequestsTestCase):
    def test_semester_without_period(self):
        Semester.objects.filter(pk=self.semester.pk).update(start_date=None, end_date=None)
        self.assertIsNone(self.build())

    def test_only_requests_used_in_the_period_count(self):
        self.ask(day=date(2026, 8, 3))
        self.ask(day=date(2026, 12, 18))
        self.ask(day=date(2026, 7, 31))
        self.ask(day=date(2026, 12, 21))
        self.assertEqual(self.build().total, 2)

    def test_weeks_cover_the_period_from_monday(self):
        self.ask(day=date(2026, 8, 3))
        self.ask(day=date(2026, 8, 9))
        self.ask(day=date(2026, 8, 10))
        report = self.build()
        self.assertEqual(report.week_count, 20)
        self.assertEqual((report.weeks[0].start, report.weeks[-1].end), (date(2026, 8, 3), date(2026, 12, 20)))
        self.assertEqual([week.total for week in report.weeks[:3]], [2, 1, 0])
        self.assertEqual(report.peak, report.weeks[0])
        self.assertTrue(report.weeks[0].is_peak)
        self.assertEqual(report.week_average, 3 / 20)

    def test_current_week(self):
        weeks = self.build().weeks
        self.assertEqual([week.number for week in weeks if week.is_current], [10])
        self.assertEqual(weeks[9].title, 'Semana 10 (atual), de 05/10/2026 a 11/10/2026')

    def test_week_detail_lists_the_statuses(self):
        self.ask(status=Status.APPROVED)
        self.ask(status=Status.APPROVED)
        self.ask(status=Status.SUGGESTED)
        week = self.build().weeks[9]
        self.assertEqual(week.detail, '3 solicitações: 1 com alternativa sugerida e 2 aprovadas.')

    def test_approval_rate_is_over_decided_requests(self):
        self.ask(status=Status.APPROVED, decided=at(date(2026, 10, 2)))
        self.ask(status=Status.REJECTED, decided=at(date(2026, 10, 2)))
        self.ask(status=Status.DECLINED, decided=at(date(2026, 10, 2)))
        self.ask(status=Status.PENDING)
        report = self.build()
        self.assertEqual((report.approved, report.decided, report.approval_percent), (1, 3, 33))
        self.assertEqual([(row.label, row.count, row.percent) for row in report.statuses][2], ('Aprovada', 1, 25))

    def test_cancelled_counts_as_approved(self):
        self.ask(status=Status.APPROVED, decided=at(date(2026, 10, 2)))
        self.ask(status=Status.CANCELLED, decided=at(date(2026, 10, 2)))
        self.ask(status=Status.REJECTED, decided=at(date(2026, 10, 2)))
        report = self.build()
        self.assertEqual((report.approved, report.decided), (2, 3))
        self.assertEqual([(row.label, row.count) for row in report.statuses][-1], ('Cancelada', 1))
        self.assertEqual(report.weeks[9].detail, '3 solicitações: 1 aprovada, 1 rejeitada e 1 cancelada.')

    def test_decision_time_is_the_median(self):
        start = at(date(2026, 10, 1), 8)
        for hours in (2, 4, 30):
            self.ask(status=Status.APPROVED, created=start, decided=start + timedelta(hours=hours))
        self.ask(status=Status.PENDING, created=start)
        self.assertEqual(self.build().decision_time, '4 horas')

    def test_without_decisions(self):
        self.ask()
        report = self.build()
        self.assertEqual((report.decision_time, report.approval_percent), ('', 0))

    def test_pending_counts_open_requests_and_the_oldest(self):
        self.ask(status=Status.PENDING, created=at(date(2026, 10, 2)))
        self.ask(status=Status.SUGGESTED, created=at(date(2026, 9, 28)), decided=at(date(2026, 9, 29)))
        self.ask(status=Status.APPROVED, created=at(date(2026, 9, 1)), decided=at(date(2026, 9, 2)))
        report = self.build()
        self.assertEqual((report.pending, report.oldest_pending), (2, 'há 7 dias'))

    def test_suggestions(self):
        space = Space.objects.register('Sala 2/3')
        suggestion = {'suggested_space': space, 'suggested_date': date(2026, 10, 8)}
        self.ask(status=Status.APPROVED, decided=at(date(2026, 10, 2)), responded_at=at(date(2026, 10, 3)), **suggestion)
        self.ask(status=Status.DECLINED, decided=at(date(2026, 10, 2)), **suggestion)
        self.ask(status=Status.SUGGESTED, decided=at(date(2026, 10, 2)), **suggestion)
        self.ask(status=Status.APPROVED, decided=at(date(2026, 10, 2)))
        report = self.build()
        self.assertEqual(report.suggested, 3)
        self.assertEqual((report.suggestion_accepted, report.suggestion_declined, report.suggestion_awaiting), (1, 1, 1))
        self.assertEqual(report.approved, 2)

    def test_on_behalf_requests(self):
        self.ask(created_by=self.viewer)
        self.ask()
        self.assertEqual(self.build().on_behalf, 1)

    def test_course_and_stage_leave_out_requests_without_link(self):
        assignment = academic(teacher='Ana Souza')
        self.ask(assignment=assignment)
        self.ask()
        course = assignment.offering.class_group.course
        other, _ = Course.objects.resolve('AGROPECUÁRIA', stage=Stage.UNDERGRADUATE)
        self.assertEqual(self.build().total, 2)
        self.assertEqual(self.build(course=course).total, 1)
        self.assertEqual(self.build(course=other).total, 0)
        self.assertEqual(self.build(stage=Stage.SECONDARY).total, 1)
        self.assertEqual(self.build(stage=Stage.UNDERGRADUATE).total, 0)

    def test_space_filter(self):
        self.ask(space='Sala 1/3')
        self.ask(space='Auditório')
        self.assertEqual(self.build(spaces=[Space.objects.get(name='Sala 1/3')]).total, 1)

    def test_ranking_orders_by_total_then_name(self):
        for _ in range(3):
            self.ask(space='Sala 2/3', status=Status.REJECTED, decided=at(date(2026, 10, 2)))
        self.ask(space='Auditório', status=Status.APPROVED, decided=at(date(2026, 10, 2)))
        self.ask(space='Sala 1/3')
        ranking = self.build().spaces
        self.assertEqual([item.space.name for item in ranking], ['Sala 2/3', 'Auditório', 'Sala 1/3'])
        self.assertEqual((ranking[0].rejected, ranking[0].rejection_percent), (3, 100))

    def test_ranking_keeps_ten_spaces(self):
        for number in range(12):
            self.ask(space=f'Sala {number}')
        self.assertEqual(len(self.build().spaces), requests.RANKING_SIZE)

    def test_recent_rejections_newest_first(self):
        older = self.ask(status=Status.REJECTED, decided=at(date(2026, 9, 1)), rejection_reason='Antigo.')
        newer = self.ask(status=Status.REJECTED, decided=at(date(2026, 10, 2)), rejection_reason='Recente.')
        self.ask(status=Status.APPROVED, decided=at(date(2026, 10, 3)))
        self.assertEqual(self.build().rejections, [newer, older])


class AxisTests(RequestsTestCase):
    def test_axis_ticks(self):
        cases = {0: [4, 3, 2, 1, 0], 2: [4, 3, 2, 1, 0], 7: [8, 6, 4, 2, 0], 11: [15, 10, 5, 0], 140: [150, 100, 50, 0]}
        for highest, ticks in cases.items():
            with self.subTest(highest=highest):
                self.assertEqual(requests.axis_ticks(highest), ticks)

    def test_peak_is_the_first_highest_week(self):
        self.ask(day=date(2026, 8, 4))
        self.ask(day=date(2026, 8, 11))
        self.assertEqual(self.build().peak.number, 1)


class TextTests(RequestsTestCase):
    def test_duration_text(self):
        cases = {
            timedelta(seconds=20): '1 minuto',
            timedelta(minutes=40): '40 minutos',
            timedelta(hours=1, minutes=59): '1 hora',
            timedelta(hours=3): '3 horas',
            timedelta(hours=24): '1 dia',
            timedelta(hours=28): '1 dia e 4 horas',
            timedelta(days=3, hours=1): '3 dias e 1 hora',
        }
        for delta, text in cases.items():
            with self.subTest(delta=delta):
                self.assertEqual(requests.duration_text(delta), text)


class FilterFormTests(RequestsTestCase):
    def form(self, query):
        semester = Semester.objects.get(pk=self.semester.pk)
        return RequestsFilterForm(QueryDict(query), [semester], semester)

    def test_unknown_values_fall_back(self):
        form = self.form('etapa=OUTRA&curso=999&espacos=999')
        self.assertEqual((form.data['etapa'], form.data['curso'], form.data['espacos']), ('', '', []))
        self.assertFalse(form.academic_filtered)

    def test_chosen_values_become_filters(self):
        space = Space.objects.register('Sala 1/3')
        filters = self.form(f'etapa={Stage.SECONDARY}&espacos={space.pk}').filters()
        self.assertEqual((filters.stage, filters.spaces), (Stage.SECONDARY, [space]))

    def test_academic_filter_shows_the_help(self):
        self.client.force_login(self.viewer)
        response = self.client.get(f'{URL}?etapa={Stage.SECONDARY}')
        self.assertContains(response, 'as solicitações sem disciplina e turma ficam de fora')
