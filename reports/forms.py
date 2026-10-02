from django import forms

from reports.heatmap import ALL, BOOKINGS, LESSONS, Filters
from schedule.models import Course, Space, Stage
from schedule.timetable import natural_key


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
        self.semesters = {item.code: item for item in semesters}
        self.courses = {str(course.pk): course for course in Course.objects.order_by('name')}
        self.space_options = {str(space.pk): space for space in sorted(Space.objects.filter(is_active=True), key=natural_key)}
        origin = data.get('origem')
        stage = data.get('etapa')
        course = data.get('curso')
        chosen = [value for value in data.getlist('espacos') if value in self.space_options] if hasattr(data, 'getlist') else []
        values = {
            'semestre': semester.code if semester else '',
            'origem': origin if origin in dict(self.ORIGINS) else ALL,
            'etapa': stage if stage in Stage.values else '',
            'curso': course if course in self.courses else '',
            'espacos': chosen,
        }
        super().__init__(values, **kwargs)
        self.fields['semestre'].choices = [(code, code) for code in self.semesters]
        self.fields['etapa'].choices = [('', 'Todas as etapas'), *Stage.choices]
        self.fields['curso'].choices = [('', 'Todos os cursos'), *((pk, course.name) for pk, course in self.courses.items())]
        self.fields['espacos'].choices = [(pk, space.name) for pk, space in self.space_options.items()]
        self.fields['espacos'].widget.attrs.update({
            'data-select-none': 'Todos os espaços ativos',
            'data-select-one': 'espaço selecionado',
            'data-select-many': 'espaços selecionados',
        })

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
