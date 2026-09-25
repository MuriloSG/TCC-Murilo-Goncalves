from django import forms


class GridFilterForm(forms.Form):
    """Semestre, sala e semana escolhidos na Grade do ensalamento, recebidos pela URL (D15).

    A semana acompanha a troca de semestre e de sala, e cai no padrão quando não serve.
    """

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    sala = forms.ChoiceField(label='Sala', required=False, widget=forms.Select(attrs={'class': 'input'}))
    semana = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, semesters=(), spaces=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['semestre'].choices = [(code, code) for code in semesters]
        self.fields['sala'].choices = [(space.name, space.name) for space in spaces]


class SemesterPeriodForm(forms.Form):
    """Início e fim do período do semestre, validados pela operação do model (D3)."""

    start_date = forms.DateField(label='Início', widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}, format='%Y-%m-%d'))
    end_date = forms.DateField(label='Fim', widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}, format='%Y-%m-%d'))
