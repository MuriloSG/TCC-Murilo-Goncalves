from django import forms

from schedule.models import SpaceOrigin


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



class SpaceFilterForm(forms.Form):
    """Busca e filtros da lista de espaços, recebidos pela URL, como na lista de usuários.

    Um valor inválido é descartado sem mensagem, e a lista trata o campo como todos.
    """

    busca = forms.CharField(
        label='Buscar pelo nome ou por outro nome',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar espaço'}),
    )
    situacao = forms.ChoiceField(
        label='Situação',
        choices=[('todos', 'Todas as situações'), ('ativos', 'Ativos'), ('inativos', 'Inativos')],
        required=False,
        widget=forms.Select(attrs={'class': 'input'}),
    )
    origem = forms.ChoiceField(
        label='Origem',
        choices=[('todas', 'Todas as origens'), *SpaceOrigin.choices],
        required=False,
        widget=forms.Select(attrs={'class': 'input'}),
    )

    def criteria(self):
        """Devolve (termo, situação, origem) válidos, com os valores inválidos trocados pelo padrão."""
        self.is_valid()
        data = self.cleaned_data
        return data.get('busca', ''), data.get('situacao') or 'todos', data.get('origem') or 'todas'


class SpaceForm(forms.Form):
    """Nome e outros nomes do espaço, no cadastro e na edição pela tela de Espaços.

    A origem não é campo do formulário: ela é definida pela operação e nunca muda.
    """

    name = forms.CharField(
        label='Nome',
        max_length=200,
        help_text='Como o campus chama o espaço, por exemplo 1/10 ou Lab. 1 - Info.',
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
    )
    other_names = forms.CharField(
        label='Outros nomes usados na planilha',
        required=False,
        help_text='Um por linha. A importação reconhece o espaço por qualquer um deles.',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, target=None, **kwargs):
        if target is not None:
            kwargs['initial'] = {'name': target.name, 'other_names': '\n'.join(target.other_names)} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)

    def clean_other_names(self):
        return [line for line in self.cleaned_data['other_names'].splitlines() if line.strip()]
