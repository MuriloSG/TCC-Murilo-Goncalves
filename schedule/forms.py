from django import forms

from schedule.models import Space, SpaceOrigin
from schedule.timetable import natural_key


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


class SpaceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, space):
        return space.name if space.is_active else f'{space.name} (desativado, será reativado)'


class SpaceAssociateForm(forms.Form):
    """Espaço do cadastro que é o mesmo que o nome encontrado na planilha.

    O campo é obrigatório, e por isso lista todos os espaços, sem fonte paginada, na ordem
    natural do nome; a busca é a do componente de seleção.
    """

    espaco = SpaceChoiceField(
        label='Espaço cadastrado',
        queryset=Space.objects.all(),
        empty_label='Escolha o espaço',
        widget=forms.Select(attrs={'class': 'input'}),
        error_messages={'required': 'Escolha o espaço que é o mesmo.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['espaco']
        field.widget.choices = [('', field.empty_label)] + [
            (space.pk, field.label_from_instance(space)) for space in sorted(Space.objects.all(), key=natural_key)
        ]


class PublicCalendarFilterForm(forms.Form):
    """Filtros do calendário público, só para exibir os valores já normalizados (D6 e D13).

    A leitura e a validação dos parâmetros ficam em `schedule.public`, que descarta sem
    mensagem o valor fora das opções. As opções são nomes e códigos, nunca IDs.
    """

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    sala = forms.ChoiceField(label='Sala', required=False, widget=forms.Select(attrs={'class': 'input'}))
    docente = forms.ChoiceField(label='Docente', required=False, widget=forms.Select(attrs={'class': 'input'}))
    curso = forms.ChoiceField(label='Curso', required=False, widget=forms.Select(attrs={'class': 'input'}))
    nivel = forms.ChoiceField(label='Nível', required=False, widget=forms.Select(attrs={'class': 'input'}))
    inicio = forms.DateField(
        label='Data inicial', required=False, widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}, format='%Y-%m-%d'),
    )
    fim = forms.DateField(
        label='Data final', required=False, widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}, format='%Y-%m-%d'),
    )

    def __init__(self, calendar, stage_choices, *args, **kwargs):
        options = calendar.options
        super().__init__(*args, initial={
            'semestre': calendar.semester_code,
            'sala': calendar.space.name if calendar.space else '',
            'docente': calendar.teacher.name if calendar.teacher else '',
            'curso': calendar.course.name if calendar.course else '',
            'nivel': calendar.stage_key,
            'inicio': calendar.start,
            'fim': calendar.end,
        }, **kwargs)
        self.fields['semestre'].choices = [(code, code) for code in options.semesters]
        self.fields['sala'].choices = [('', 'Todas as salas'), *[(space.name, space.name) for space in options.spaces]]
        self.fields['docente'].choices = [('', 'Todos os docentes'), *[(teacher.name, teacher.name) for teacher in options.teachers]]
        self.fields['curso'].choices = [('', 'Todos os cursos'), *[(course.name, course.name) for course in options.courses]]
        self.fields['nivel'].choices = [('', 'Todos os níveis'), *stage_choices]
        for name in ('inicio', 'fim'):
            self.fields[name].disabled = not calendar.dates_enabled
            if calendar.date_error:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'
                self.fields[name].widget.attrs['aria-describedby'] = 'erro-datas'
