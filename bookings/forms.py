"""Formulários da Agenda: a solicitação, a rejeição e a alternativa sugerida.

Os campos têm os nomes dos campos do model, para que a recusa de uma operação volte ao
campo certo pelo `add_operation_error`. O espaço e a data da solicitação vêm da faixa
escolhida e não são editáveis; um valor forjado chega ao model e é recusado pelas mesmas
regras (D8 da Change agendar-uso-eventual-dos-espacos).
"""

from django import forms

from bookings.models import DESCRIPTION_MAX_LENGTH, DESCRIPTION_REQUIRED_MESSAGE, REASON_MAX_LENGTH, REASON_REQUIRED_MESSAGE
from schedule.models import Space

SPACE_REQUIRED_MESSAGE = 'Escolha o espaço na Grade da Agenda.'
DATE_REQUIRED_MESSAGE = 'Informe a data.'
START_REQUIRED_MESSAGE = 'Informe o início.'
END_REQUIRED_MESSAGE = 'Informe o fim.'


def date_field(label, readonly=False):
    attrs = {'type': 'date', 'class': 'input'}
    if readonly:
        attrs['readonly'] = True
    return forms.DateField(
        label=label,
        widget=forms.DateInput(attrs=attrs, format='%Y-%m-%d'),
        error_messages={'required': DATE_REQUIRED_MESSAGE, 'invalid': 'Informe a data no formato dd/mm/aaaa.'},
    )


def time_field(label, required_message):
    return forms.TimeField(
        label=label,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'input'}, format='%H:%M'),
        error_messages={'required': required_message, 'invalid': 'Informe a hora no formato 14:00.'},
    )


class BookingRequestForm(forms.Form):
    """Espaço, data, início, fim e a descrição obrigatória da solicitação.

    O espaço é um campo oculto; o erro dele é mostrado como erro do formulário, porque o
    campo não aparece na tela.
    """

    space = forms.ModelChoiceField(
        queryset=Space.objects.all(),
        widget=forms.HiddenInput,
        error_messages={'required': SPACE_REQUIRED_MESSAGE, 'invalid_choice': SPACE_REQUIRED_MESSAGE},
    )
    date = date_field('Data', readonly=True)
    start_time = time_field('Início', START_REQUIRED_MESSAGE)
    end_time = time_field('Fim', END_REQUIRED_MESSAGE)
    description = forms.CharField(
        label='Descrição',
        max_length=DESCRIPTION_MAX_LENGTH,
        help_text='O que será feito no espaço, em uma ou duas frases.',
        widget=forms.Textarea(attrs={'rows': 3}),
        error_messages={'required': DESCRIPTION_REQUIRED_MESSAGE},
    )

    def add_error(self, field, error):
        super().add_error(None if field == 'space' else field, error)
