from datetime import date, datetime, time
from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import translation


class BrazilianFormatsTests(SimpleTestCase):
    def render(self, source, **context):
        with translation.override('pt-br'):
            return Template(source).render(Context(context))

    def test_datas_horas_e_numeros_no_formato_brasileiro(self):
        cases = [
            ('{{ valor|date }}', date(2026, 9, 18), '18/09/2026'),
            ('{{ valor|time }}', time(10, 0), '10:00'),
            ('{{ valor|time }}', time(14, 30), '14:30'),
            ('{{ valor }}', datetime(2026, 9, 18, 8, 5), '18/09/2026 08:05'),
            ('{{ valor }}', Decimal('1234.5'), '1.234,5'),
            ('{{ valor }}', 1234.5, '1.234,5'),
            ('{{ valor }}', 1234, '1.234'),
        ]
        for source, value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(self.render(source, valor=value), expected)
