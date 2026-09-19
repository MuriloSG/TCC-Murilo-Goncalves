from datetime import date, datetime, time
from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import translation


class BrazilianFormatsTests(SimpleTestCase):
    def render(self, source, **context):
        with translation.override('pt-br'):
            return Template(source).render(Context(context))

    def test_data_com_filtro_sem_argumento(self):
        self.assertEqual(self.render('{{ data|date }}', data=date(2026, 9, 18)), '18/09/2026')

    def test_hora_em_24_horas(self):
        self.assertEqual(self.render('{{ hora|time }}', hora=time(10, 0)), '10:00')
        self.assertEqual(self.render('{{ hora|time }}', hora=time(14, 30)), '14:30')

    def test_data_e_hora(self):
        self.assertEqual(self.render('{{ momento }}', momento=datetime(2026, 9, 18, 8, 5)), '18/09/2026 08:05')

    def test_numero_com_separador_de_milhar_e_virgula_decimal(self):
        self.assertEqual(self.render('{{ numero }}', numero=Decimal('1234.5')), '1.234,5')
        self.assertEqual(self.render('{{ numero }}', numero=1234.5), '1.234,5')
        self.assertEqual(self.render('{{ numero }}', numero=1234), '1.234')
