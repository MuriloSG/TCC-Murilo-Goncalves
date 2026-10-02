from django import forms

from reports import requests
from reports.heatmap import ALL, BOOKINGS, LESSONS, Filters
from schedule.models import Course, Space, Stage
from schedule.timetable import natural_key


def filter_options(form, data, semesters, semester):
    """Opções e valores de semestre, etapa, curso e espaços, comuns aos filtros dos relatórios.

    Guarda as opções no formulário e devolve os valores escolhidos: um valor que não é opção
    vale o padrão, sem erro (D8 da Change gerar-relatorio-de-solicitacoes).
    """
    form.semesters = {item.code: item for item in semesters}
    form.courses = {str(course.pk): course for course in Course.objects.order_by('name')}
    form.space_options = {str(space.pk): space for space in sorted(Space.objects.filter(is_active=True), key=natural_key)}
    stage = data.get('etapa')
    course = data.get('curso')
    return {
        'semestre': semester.code if semester else '',
        'etapa': stage if stage in Stage.values else '',
        'curso': course if course in form.courses else '',
        'espacos': [value for value in data.getlist('espacos') if value in form.space_options] if hasattr(data, 'getlist') else [],
    }


def fill_choices(form):
    """Escolhas dos campos comuns, depois do `__init__` do formulário."""
    form.fields['semestre'].choices = [(code, code) for code in form.semesters]
    form.fields['etapa'].choices = [('', 'Todas as etapas'), *Stage.choices]
    form.fields['curso'].choices = [('', 'Todos os cursos'), *((pk, course.name) for pk, course in form.courses.items())]
    form.fields['espacos'].choices = [(pk, space.name) for pk, space in form.space_options.items()]
    form.fields['espacos'].widget.attrs.update({
        'data-select-none': 'Todos os espaços ativos',
        'data-select-one': 'espaço selecionado',
        'data-select-many': 'espaços selecionados',
    })


class HeatmapFilterForm(forms.Form):
    """Filtros do mapa de calor pela URL, todos no select do projeto (D5).

    Um valor que não é opção é ignorado e vale o padrão, sem erro, como no painel. Etapa e
    curso restringem só as aulas e são ignorados com a origem "só agendamentos".
    """

    ORIGINS = [(ALL, 'Aulas e agendamentos'), (LESSONS, 'Só aulas'), (BOOKINGS, 'Só agendamentos')]

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    origem = forms.ChoiceField(label='Origem', required=False, choices=ORIGINS, widget=forms.Select(attrs={'class': 'input'}))
    etapa = forms.ChoiceField(label='Etapa de ensino', required=False, widget=forms.Select(attrs={'class': 'input'}))
    curso = forms.ChoiceField(label='Curso', required=False, widget=forms.Select(attrs={'class': 'input'}))
    espacos = forms.MultipleChoiceField(label='Espaços', required=False, widget=forms.SelectMultiple(attrs={'class': 'input'}))

    def __init__(self, data, semesters, semester, **kwargs):
        values = filter_options(self, data, semesters, semester)
        origin = data.get('origem')
        values['origem'] = origin if origin in dict(self.ORIGINS) else ALL
        super().__init__(values, **kwargs)
        fill_choices(self)

    @property
    def lessons_filtered(self):
        """Etapa e curso valem só para as aulas: ficam ocultos com a origem "só agendamentos"."""
        return self.data['origem'] != BOOKINGS

    def filters(self):
        semester = self.semesters.get(self.data['semestre'])
        origin = self.data['origem']
        course = self.courses.get(self.data['curso']) if origin != BOOKINGS else None
        stage = self.data['etapa'] if origin != BOOKINGS else ''
        spaces = [self.space_options[pk] for pk in self.data['espacos']]
        return Filters(semester, origin, stage, course, spaces)


class RequestsFilterForm(forms.Form):
    """Filtros do relatório de solicitações pela URL, todos no select do projeto (D8).

    Etapa e curso vêm do vínculo acadêmico da solicitação: com um dos dois escolhido, as
    solicitações sem vínculo ficam de fora.
    """

    semestre = forms.ChoiceField(label='Semestre', required=False, widget=forms.Select(attrs={'class': 'input'}))
    etapa = forms.ChoiceField(label='Etapa de ensino', required=False, widget=forms.Select(attrs={'class': 'input'}))
    curso = forms.ChoiceField(label='Curso', required=False, widget=forms.Select(attrs={'class': 'input'}))
    espacos = forms.MultipleChoiceField(label='Espaços', required=False, widget=forms.SelectMultiple(attrs={'class': 'input'}))

    def __init__(self, data, semesters, semester, **kwargs):
        super().__init__(filter_options(self, data, semesters, semester), **kwargs)
        fill_choices(self)

    @property
    def academic_filtered(self):
        """Diz se a etapa ou o curso deixam de fora as solicitações sem vínculo acadêmico."""
        return bool(self.data['etapa'] or self.data['curso'])

    def filters(self):
        return requests.Filters(
            self.semesters.get(self.data['semestre']),
            self.data['etapa'],
            self.courses.get(self.data['curso']),
            [self.space_options[pk] for pk in self.data['espacos']],
        )
