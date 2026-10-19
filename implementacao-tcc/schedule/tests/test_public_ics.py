"""Exportação do calendário público em .ics: filtro por turma, cancelamentos e acesso."""

from datetime import date

from django.urls import reverse

from accounts.models import User
from schedule.models import AllocationException
from schedule.tests.test_public_calendar import PublicCalendarTestCase

URL = reverse('public_calendar_ics')


class PublicIcsTests(PublicCalendarTestCase):
    def test_exports_only_the_chosen_group(self):
        response = self.client.get(URL, {'curso': 'INFORMÁTICA', 'turma': '2º ANO A'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/calendar'))
        self.assertIn('attachment;', response['Content-Disposition'])
        content = response.content.decode()
        self.assertIn('BEGIN:VCALENDAR', content)
        self.assertIn('SUMMARY:Banco de Dados', content)
        self.assertIn('DTSTART;TZID=America/Sao_Paulo:20260601T070000', content)
        whole_course = self.client.get(URL, {'curso': 'INFORMÁTICA'}).content.decode()
        self.assertIn('ano b', whole_course.casefold())
        self.assertNotIn('ano b', content.casefold())

    def test_cancelled_occurrence_is_left_out(self):
        allocation = self.group_a.allocations.get(subject__name='Banco de Dados')
        superadmin = User.objects.get(email='super@ifnmg.edu.br')
        AllocationException.objects.cancel([allocation.pk], date(2026, 6, 8), superadmin)
        content = self.client.get(URL, {'curso': 'INFORMÁTICA', 'turma': '2º ANO A'}).content.decode()
        self.assertIn('20260601T070000', content)
        self.assertNotIn('20260608T070000', content)

    def test_without_filter_is_not_found(self):
        self.assertEqual(self.client.get(URL).status_code, 404)

    def test_post_is_not_allowed(self):
        self.assertEqual(self.client.post(URL).status_code, 405)

    def test_calendar_shows_download_icon_with_filters(self):
        response = self.client.get(reverse('public_calendar'), {'curso': 'INFORMÁTICA', 'turma': '2º ANO A'})
        self.assertContains(response, 'class="icon-btn public-export"')
        self.assertContains(response, URL + '?')
