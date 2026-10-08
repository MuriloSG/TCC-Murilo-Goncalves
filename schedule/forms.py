from datetime import time

from django import forms
from django.db.models import Q

from schedule.models import (
    ClassGroup, Course, Space, SpaceOrigin, Stage, Subject, Teacher, TimeSlot, Weekday,
)
from schedule.timetable import natural_key
from ui.forms import DateInput


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


class CourseFilterForm(forms.Form):
    """Busca e filtro de etapa da lista de cursos, recebidos pela URL.

    Uma etapa inválida é descartada sem mensagem, e a lista trata o campo como todas.
    """

    busca = forms.CharField(
        label='Buscar pelo nome',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar curso'}),
    )
    etapa = forms.ChoiceField(
        label='Etapa de ensino',
        choices=[('', 'Todas as etapas'), *Stage.choices],
        required=False,
        widget=forms.Select(attrs={'class': 'input'}),
    )

    def criteria(self):
        self.is_valid()
        data = self.cleaned_data
        return data.get('busca', ''), data.get('etapa', '')


class CourseForm(forms.Form):
    """Nome e etapa do curso, no cadastro e na edição pela tela de Cursos.

    A importação reaproveita o curso só pelo nome igual ao do título da planilha, sem
    diferenciar a caixa e os espaços repetidos; acentos diferentes dão outro curso.
    """

    name = forms.CharField(
        label='Nome',
        max_length=200,
        help_text='Use o nome como aparece no título da planilha do ensalamento, com os mesmos acentos.',
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
    )
    stage = forms.ChoiceField(
        label='Etapa de ensino',
        choices=[('', 'Selecione a etapa'), *Stage.choices],
        widget=forms.Select(attrs={'class': 'input'}),
    )

    def __init__(self, *args, target=None, **kwargs):
        if target is not None:
            kwargs['initial'] = {'name': target.name, 'stage': target.stage} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)


class SubjectFilterForm(forms.Form):
    """Busca da lista de disciplinas, recebida pela URL."""

    busca = forms.CharField(
        label='Buscar pelo nome',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar disciplina'}),
    )

    def criteria(self):
        self.is_valid()
        return self.cleaned_data.get('busca', '')


class SubjectForm(forms.Form):
    """Nome da disciplina, no cadastro e na edição pela tela de Disciplinas."""

    name = forms.CharField(label='Nome', max_length=200, widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    def __init__(self, *args, target=None, **kwargs):
        if target is not None:
            kwargs['initial'] = {'name': target.name} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)


class ClassGroupFilterForm(forms.Form):
    """Busca e filtro de curso da lista de turmas, recebidos pela URL.

    Um curso inválido é descartado sem mensagem, e a lista trata o campo como todos.
    """

    busca = forms.CharField(
        label='Buscar pelo rótulo ou pelo curso',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar turma'}),
    )
    curso = forms.ModelChoiceField(
        label='Curso',
        queryset=Course.objects.all(),
        required=False,
        empty_label='Todos os cursos',
        widget=forms.Select(attrs={'class': 'input'}),
    )

    def criteria(self):
        self.is_valid()
        data = self.cleaned_data
        return data.get('busca', ''), data.get('curso')


class ClassGroupForm(forms.Form):
    """Curso e rótulo da turma, no cadastro e na edição pela tela de Turmas.

    Na edição o curso é `readonly`, e não `disabled`, para que um curso forjado chegue ao
    model e seja recusado com mensagem.
    """

    course = forms.ModelChoiceField(
        label='Curso', queryset=Course.objects.all(), empty_label='Selecione o curso', widget=forms.Select(attrs={'class': 'input'}),
    )
    label = forms.CharField(label='Rótulo', max_length=200, widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    def __init__(self, *args, target=None, **kwargs):
        if target is not None:
            kwargs['initial'] = {'course': target.course_id, 'label': target.label} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        if target is not None:
            self.fields['course'].widget.attrs['readonly'] = True


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
    turma = forms.ChoiceField(label='Turma', required=False, widget=forms.Select(attrs={'class': 'input', 'form': 'filtros-form'}))
    inicio = forms.DateField(
        label='Data inicial', required=False, widget=DateInput(attrs={'class': 'input'}),
    )
    fim = forms.DateField(
        label='Data final', required=False, widget=DateInput(attrs={'class': 'input'}),
    )

    def __init__(self, calendar, stage_choices, *args, with_dates=True, **kwargs):
        options = calendar.options
        super().__init__(*args, initial={
            'semestre': calendar.semester_code,
            'sala': calendar.space.name if calendar.space else '',
            'docente': calendar.teacher.name if calendar.teacher else '',
            'curso': calendar.course.name if calendar.course else '',
            'nivel': calendar.stage_key,
            'turma': calendar.group.label if calendar.group else '',
            'inicio': calendar.start,
            'fim': calendar.end,
        }, **kwargs)
        self.fields['semestre'].choices = [(code, code) for code in options.semesters]
        self.fields['sala'].choices = [('', 'Todas as salas'), *[(space.name, space.name) for space in options.spaces]]
        self.fields['docente'].choices = [('', 'Todos os docentes'), *[(teacher.name, teacher.name) for teacher in options.teachers]]
        self.fields['curso'].choices = [('', 'Todos os cursos'), *[(course.name, course.name) for course in options.courses]]
        self.fields['nivel'].choices = [('', 'Todos os níveis'), *stage_choices]
        self.fields['turma'].choices = [('', 'Turma'), *[(group.label, group.label) for group in options.groups]]
        if not with_dates:
            del self.fields['inicio'], self.fields['fim']
            return
        for name in ('inicio', 'fim'):
            self.fields[name].disabled = not calendar.dates_enabled
            if calendar.date_error:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'
                self.fields[name].widget.attrs['aria-describedby'] = 'erro-datas'


class RecurrenceChangeForm(forms.Form):
    """Data de corte e dados novos da recorrência de uma aula, iniciados com os atuais.

    Só dia, horário, duração, espaço e docentes são campos: turma, disciplina e semestre
    são a própria aula. O horário e a duração seguem o cadastro da aula, e a duração pode
    aumentar ou diminuir a quantidade de faixas seguidas (D1 da Change
    alterar-duracao-da-recorrencia). O espaço é um dos ativos ou o atual (D3 da Change
    alterar-recorrencia-do-ensalamento). A conferência das regras fica no model.
    """

    data = forms.DateField(
        label='A partir de',
        help_text='Data da primeira aula com os dados novos.',
        widget=DateInput(),
    )
    dia = forms.ChoiceField(label='Dia da semana', choices=Weekday.choices, widget=forms.Select(attrs={'class': 'input'}))
    horario = forms.ChoiceField(label='Horário de início', widget=forms.Select(attrs={'class': 'input'}))
    duracao = forms.ChoiceField(label='Duração', widget=forms.Select(attrs={'class': 'input'}))
    espaco = forms.ModelChoiceField(
        label='Espaço',
        queryset=Space.objects.none(),
        required=False,
        empty_label='Sem espaço',
        widget=forms.Select(attrs={'class': 'input'}),
    )
    docentes = forms.ModelMultipleChoiceField(
        label='Docentes',
        queryset=Teacher.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'input'}),
    )

    def __init__(self, *args, allocations=(), **kwargs):
        super().__init__(*args, **kwargs)
        first = allocations[0]
        slots = sorted(TimeSlot.objects.filter(semester=first.semester), key=lambda slot: slot.start_time)
        self.fields['horario'].choices = [
            (f'{slot.start_time:%H:%M}', f'A partir das {slot.start_time:%H:%M}') for slot in slots
        ]
        self.fields['duracao'].choices = duration_choices(slots)
        current = Q(pk=first.space_id) if first.space_id else Q(pk__in=[])
        self.fields['espaco'].queryset = Space.objects.filter(Q(is_active=True) | current).order_by('name')
        self.fields['espaco'].label_from_instance = lambda space: space.name

    def clean_horario(self):
        value = self.cleaned_data['horario']
        hours, minutes = value.split(':')
        return time(int(hours), int(minutes))

    def clean_duracao(self):
        return int(self.cleaned_data['duracao'])


class RecurrenceCreateForm(forms.Form):
    """Dados de uma aula recorrente cadastrada na Grade, dentro de um semestre.

    O semestre não é campo: ele vem da Grade de onde o cadastro foi aberto. O dia da semana
    também não é campo, porque vem da data da primeira aula (D3 da Change
    criar-recorrencia-do-ensalamento). A conferência das regras fica no model.
    """

    turma = forms.ModelChoiceField(
        label='Turma',
        queryset=ClassGroup.objects.none(),
        empty_label='Escolha a turma',
        widget=forms.Select(attrs={'class': 'input'}),
    )
    disciplina = forms.ModelChoiceField(
        label='Disciplina',
        queryset=Subject.objects.none(),
        empty_label='Escolha a disciplina',
        widget=forms.Select(attrs={'class': 'input'}),
    )
    docentes = forms.ModelMultipleChoiceField(
        label='Docentes',
        queryset=Teacher.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'input'}),
    )
    espaco = forms.ModelChoiceField(
        label='Espaço',
        queryset=Space.objects.none(),
        required=False,
        empty_label='Sem espaço',
        widget=forms.Select(attrs={'class': 'input'}),
    )
    data = forms.DateField(
        label='Primeira aula',
        help_text='A aula se repete toda semana neste dia.',
        widget=DateInput(),
    )
    fim = forms.DateField(
        label='Última aula',
        required=False,
        help_text='Sem data, a aula vale até o fim do semestre.',
        widget=DateInput(),
    )
    horario = forms.ChoiceField(label='Horário de início', widget=forms.Select(attrs={'class': 'input'}))
    duracao = forms.ChoiceField(label='Duração', widget=forms.Select(attrs={'class': 'input'}))

    def __init__(self, *args, semester=None, **kwargs):
        super().__init__(*args, **kwargs)
        slots = sorted(TimeSlot.objects.filter(semester=semester), key=lambda slot: slot.start_time)
        self.fields['horario'].choices = [
            (f'{slot.start_time:%H:%M}', f'A partir das {slot.start_time:%H:%M}') for slot in slots
        ]
        self.fields['duracao'].choices = duration_choices(slots)
        self.fields['turma'].queryset = ClassGroup.objects.select_related('course').order_by('course__name', 'label')
        self.fields['turma'].label_from_instance = str
        self.fields['disciplina'].queryset = Subject.objects.order_by('name')
        self.fields['disciplina'].label_from_instance = lambda subject: subject.name
        self.fields['espaco'].queryset = Space.objects.filter(is_active=True).order_by('name')
        self.fields['espaco'].label_from_instance = lambda space: space.name

    def clean_horario(self):
        hours, minutes = self.cleaned_data['horario'].split(':')
        return time(int(hours), int(minutes))

    def clean_duracao(self):
        return int(self.cleaned_data['duracao'])


def duration_choices(slots):
    """Opções de duração, de uma faixa até a maior sequência de faixas seguidas do semestre."""
    return [
        (count, '1 faixa' if count == 1 else f'{count} faixas seguidas')
        for count in range(1, longest_run(slots) + 1)
    ]


def longest_run(slots):
    """Maior quantidade de faixas seguidas do semestre, com o mínimo de uma."""
    by_start = {slot.start_time: slot for slot in slots}
    longest = 1
    for slot in slots:
        length, current = 1, slot
        while current.end_time in by_start:
            current = by_start[current.end_time]
            length += 1
        longest = max(longest, length)
    return longest
