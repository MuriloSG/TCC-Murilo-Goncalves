from datetime import date, time


from accounts import permissions
from bookings.tests.base import user_with
from panel.tests.test_panel import PanelTestCase
from reports import heatmap
from schedule.models import AllocationException, Course, ClassGroup, Semester, Space, Stage, Weekday

URL = '/relatorios/mapa-de-calor/'
CELL_URL = '/relatorios/mapa-de-calor/segunda/0/'


class HeatmapTestCase(PanelTestCase):
    """Semestre 2026/2 de 03/08 a 18/12: 20 segundas-feiras."""

    def setUp(self):
        super().setUp()
        self.viewer = user_with('relatorio@ifnmg.edu.br', permissions.REPORT_VIEW, permissions.SPACE_ALLOCATION_VIEW)

    def build(self, **kwargs):
        return heatmap.build(heatmap.Filters(Semester.objects.get(pk=self.semester.pk), **kwargs))


class AccessTests(HeatmapTestCase):
    def test_without_the_allocation_permission_is_403(self):
        self.client.force_login(user_with('relatorista@ifnmg.edu.br', permissions.REPORT_VIEW))
        for url in (URL, CELL_URL):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_with_both_permissions_shows_the_map(self):
        self.lesson()
        self.client.force_login(self.viewer)
        response = self.client.get(URL)
        self.assertContains(response, 'Espaços ocupados por faixa')
        self.assertContains(response, 'Ocupação média')


class BuildTests(HeatmapTestCase):
    def test_lesson_occupies_every_monday(self):
        self.lesson('Sala 1/3')
        Space.objects.register('Sala 2/3')
        result = self.build()
        cell = result.cell(0, 0)
        self.assertEqual(cell.weeks, 20)
        self.assertEqual(cell.occupied, 20)
        self.assertEqual(cell.percent, 50)
        self.assertEqual(cell.average, 1)
        self.assertEqual(result.peak, cell)
        self.assertEqual(result.lesson_percent, 100)

    def test_rate_is_over_every_slot_and_space(self):
        self.lesson('Sala 1/3')
        result = self.build()
        self.assertEqual(result.available_minutes, 1 * 100 * 120)
        self.assertEqual(result.occupied_minutes, 20 * 120)
        self.assertEqual(result.rate, 20)

    def test_cancelled_occurrence_is_not_counted(self):
        allocation = self.lesson('Sala 1/3')
        AllocationException.objects.create(allocation=allocation, date=date(2026, 10, 5), created_by=self.admin)
        self.assertEqual(self.build().cell(0, 0).occupied, 19)

    def test_booking_counts_in_its_week_only(self):
        self.lesson('Sala 1/3')
        self.booking('Auditório', date(2026, 10, 5), time(10, 0), time(11, 0))
        result = self.build()
        cell = result.cell(0, 0)
        self.assertEqual(cell.occupied, 21)
        self.assertEqual(cell.usage[Space.objects.get(name='Auditório').pk], [0, 1])

    def test_booking_over_a_lesson_counts_as_lesson(self):
        self.lesson('Sala 1/3')
        self.booking('Sala 1/3', date(2026, 10, 5), time(10, 0), time(11, 0))
        result = self.build()
        self.assertEqual(result.cell(0, 0).occupied, 20)
        self.assertEqual(result.lesson_percent, 100)

    def test_origin_filters(self):
        self.lesson('Sala 1/3')
        self.booking('Auditório', date(2026, 10, 5), time(10, 0), time(11, 0))
        self.assertEqual(self.build(origin=heatmap.LESSONS).cell(0, 0).occupied, 20)
        self.assertEqual(self.build(origin=heatmap.BOOKINGS).cell(0, 0).occupied, 1)

    def test_course_filter_keeps_only_its_lessons(self):
        other, _ = Course.objects.resolve('AGROPECUÁRIA', stage=Stage.UNDERGRADUATE)
        group, _ = ClassGroup.objects.resolve(other, '1º PERÍODO')
        self.lesson('Sala 1/3')
        self.lesson('Sala 2/3', group=group)
        self.assertEqual(self.build(course=other).cell(0, 0).occupied, 20)
        self.assertEqual(self.build(stage=Stage.SECONDARY).cell(0, 0).occupied, 20)
        self.assertEqual(self.build().cell(0, 0).occupied, 40)

    def test_space_filter(self):
        self.lesson('Sala 1/3')
        other = Space.objects.register('Sala 2/3')
        result = self.build(spaces=[other])
        self.assertEqual(result.space_count, 1)
        self.assertEqual(result.cell(0, 0).occupied, 0)
        self.assertIsNone(result.peak)

    def test_quietest_ignores_days_without_occupancy(self):
        self.lesson('Sala 1/3', start=time(10, 0), end=time(12, 0))
        self.lesson('Sala 1/3', start=time(14, 0), end=time(16, 0), group=self.group_b)
        result = self.build()
        self.assertEqual(result.quietest.day, 0)

    def test_semester_without_period(self):
        semester, _ = Semester.objects.resolve('2027/1')
        self.assertIsNone(heatmap.build(heatmap.Filters(semester)))

    def test_levels(self):
        cell = heatmap.Cell(0, 0, 10, 10, Weekday.MONDAY, 'Seg', None)
        for occupied, level in ((0, 0), (1, 1), (20, 1), (21, 2), (100, 5)):
            cell.occupied = occupied
            self.assertEqual(cell.level, level)


class CellTests(HeatmapTestCase):
    def test_modal_lists_busy_and_free_spaces(self):
        self.lesson('Sala 1/3')
        Space.objects.register('Sala 2/3')
        self.client.force_login(self.viewer)
        response = self.client.get(CELL_URL, headers={'HX-Request': 'true'})
        self.assertContains(response, 'Segunda-feira, 10:00 às 12:00')
        self.assertContains(response, 'Sala 1/3')
        self.assertContains(response, 'em 20 de 20 semanas')
        self.assertContains(response, 'Disponível')
        self.assertContains(response, 'Abrir na Grade')

    def test_unknown_day_or_slot_is_404(self):
        self.lesson()
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get('/relatorios/mapa-de-calor/domingo/0/').status_code, 404)
        self.assertEqual(self.client.get('/relatorios/mapa-de-calor/segunda/9/').status_code, 404)


class FilterFormTests(HeatmapTestCase):
    def test_unknown_values_fall_back(self):
        self.lesson()
        self.client.force_login(self.viewer)
        response = self.client.get(URL, {'origem': 'x', 'curso': '999', 'espacos': ['abc'], 'semestre': '1999/1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['filters'].data['origem'], heatmap.ALL)

    def test_bookings_only_hides_stage_and_course(self):
        self.lesson()
        self.client.force_login(self.viewer)
        response = self.client.get(URL, {'origem': heatmap.BOOKINGS})
        self.assertNotContains(response, 'Etapa de ensino')
        self.assertContains(self.client.get(URL), 'Etapa de ensino')
