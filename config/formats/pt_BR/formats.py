"""Formatos brasileiros de data, hora e número (seção 9.5 das convenções, D6).

Os formatos não definidos aqui continuam vindo de django.conf.locale.pt_BR.
"""

DATE_FORMAT = 'd/m/Y'
SHORT_DATE_FORMAT = 'd/m/Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/m/Y H:i'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
