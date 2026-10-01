from django import forms

from panel.indicators import TODAY, WEEK


class PanelFilterForm(forms.Form):
    """Semestre das pendências da grade e período da ocupação, pela URL.

    Um valor que não é opção é ignorado e vale o padrão, sem erro (Change
    exibir-painel-administrativo).
    """

    PERIODS = [(TODAY, 'Hoje'), (WEEK, 'Semana')]

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    ocupacao = forms.ChoiceField(label='Ocupação', required=False, choices=PERIODS, widget=forms.Select(attrs={'class': 'input'}))

    def __init__(self, data, semesters, semester, **kwargs):
        period = data.get('ocupacao')
        initial = {
            'semestre': semester.code if semester else '',
            'ocupacao': period if period in dict(self.PERIODS) else TODAY,
        }
        super().__init__(initial, **kwargs)
        self.fields['semestre'].choices = [(item.code, item.code) for item in semesters]

    @property
    def period(self):
        return self.data['ocupacao']
