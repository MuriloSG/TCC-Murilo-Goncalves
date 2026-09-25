from django import forms


class GridFilterForm(forms.Form):
    """Semestre, sala, visualização, semana e mês escolhidos na Grade do ensalamento, recebidos pela URL (D15).

    A semana ou o mês mostrados acompanham a troca de semestre, de sala e de visualização,
    e caem no padrão quando não servem (D8 da Change visualizar-ocupacao-por-semana-e-mes).
    """

    VIEWS = [('semana', 'Semana'), ('mes', 'Mês')]

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    sala = forms.ChoiceField(label='Sala', required=False, widget=forms.Select(attrs={'class': 'input'}))
    semana = forms.CharField(required=False, widget=forms.HiddenInput)
    mes = forms.CharField(required=False, widget=forms.HiddenInput)
    visao = forms.ChoiceField(label='Visualização', required=False, choices=VIEWS, widget=forms.Select(attrs={'class': 'input'}))

    def __init__(self, *args, semesters=(), spaces=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['semestre'].choices = [(code, code) for code in semesters]
        self.fields['sala'].choices = [(space.name, space.name) for space in spaces]

