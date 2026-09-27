"""Formulários da Agenda: a solicitação, a rejeição e a alternativa sugerida.

Os campos têm os nomes dos campos do model, para que a recusa de uma operação volte ao
campo certo pelo `add_operation_error`. A faixa da Grade preenche o espaço, a data e o
horário da solicitação, que podem ser trocados; qualquer valor chega ao model e passa pelas
mesmas regras (D8 da Change agendar-uso-eventual-dos-espacos e D3 da Change
solicitar-agendamento-com-vinculo-academico).
"""

from django import forms

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.formats import date_format

from bookings.models import (
    ASSIGNMENT_REQUIRED_MESSAGE,
    COURSE_REQUIRED_MESSAGE,
    DESCRIPTION_MAX_LENGTH,
    DESCRIPTION_REQUIRED_MESSAGE,
    REASON_MAX_LENGTH,
    REASON_REQUIRED_MESSAGE,
    REQUESTER_REQUIRED_MESSAGE,
    SUBJECT_REQUIRED_MESSAGE,
)
from schedule.forms import GridFilterForm
from accounts.models import User
from schedule.models import Course, Semester, Space, Subject, TeachingAssignment, TimeSlot, teacher_of, teacher_users

DATE_REQUIRED_MESSAGE = 'Informe a data.'
START_REQUIRED_MESSAGE = 'Informe o início.'
END_REQUIRED_MESSAGE = 'Informe o fim.'


def date_field(label):
    attrs = {'type': 'date', 'class': 'input'}
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


def semester_options(today):
    """Semestres que aceitam solicitação: com período e que ainda não terminaram."""
    return Semester.objects.filter(start_date__isnull=False, end_date__gte=today).order_by('-code')


def semester_of(value, today):
    """Semestre da Agenda para a data informada: o que a tem no período, ou None."""
    day = value if hasattr(value, 'isoformat') else parse_date(value or '')
    if day is None:
        return None
    return semester_options(today).filter(start_date__lte=day, end_date__gte=day).first()


def chosen(form, name):
    """Valor escolhido no campo, do envio ou do preenchimento inicial, como texto."""
    value = form.data.get(name) if form.is_bound else form.initial.get(name)
    value = getattr(value, 'pk', value)
    return str(value) if value not in (None, '') else ''


class AssignmentChoiceField(forms.ModelChoiceField):
    """Turma da disciplina escolhida, identificada pelo vínculo do docente com ela."""

    def label_from_instance(self, obj):
        return str(obj.offering.class_group)


class BookingRequestForm(forms.Form):
    """Disciplina, turma, espaço, data, horário e descrição da solicitação.

    Quem solicita é o docente, reconhecido pelo `username` do usuário (`teacher_of`). O
    semestre não é escolhido: é o da Agenda, o que tem a data no período, calculado aqui a
    cada envio. A disciplina oferece as disciplinas dos vínculos atuais do docente nesse
    semestre, e a turma só as turmas da disciplina escolhida, tudo de uma consulta só
    (`TeachingAssignment.objects.available`). A troca da data ou da disciplina recarrega as
    opções seguintes pelo htmx, na mesma rota. As opções só orientam: um ID fora delas é
    recusado aqui, e a operação do model confere de novo que a turma é do próprio docente
    (Change solicitar-agendamento-com-vinculo-academico).
    """

    subject = forms.ModelChoiceField(
        label='Disciplina',
        queryset=Subject.objects.none(),
        empty_label='Escolha a disciplina',
        error_messages={'required': SUBJECT_REQUIRED_MESSAGE, 'invalid_choice': 'Escolha uma das suas disciplinas do semestre.'},
    )
    teaching_assignment = AssignmentChoiceField(
        label='Turma',
        queryset=TeachingAssignment.objects.none(),
        empty_label='Escolha a turma',
        error_messages={'required': ASSIGNMENT_REQUIRED_MESSAGE, 'invalid_choice': 'Escolha uma turma da disciplina escolhida.'},
    )
    space = forms.ModelChoiceField(
        label='Espaço',
        queryset=Space.objects.none(),
        empty_label='Escolha o espaço',
        error_messages={'required': 'Escolha o espaço.', 'invalid_choice': 'Escolha um espaço ativo.'},
    )
    date = date_field('Data')
    start_time = time_field('Início', START_REQUIRED_MESSAGE)
    end_time = time_field('Fim', END_REQUIRED_MESSAGE)
    description = forms.CharField(
        label='Descrição',
        max_length=DESCRIPTION_MAX_LENGTH,
        help_text='O que será feito no espaço, em uma ou duas frases.',
        widget=forms.Textarea(attrs={'rows': 3}),
        error_messages={'required': DESCRIPTION_REQUIRED_MESSAGE},
    )

    DEPENDENTS = {}

    def __init__(self, *args, user=None, refresh_url='', today=None, trigger='', **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_after(trigger)
        self.refresh = {
            'hx-get': refresh_url,
            'hx-trigger': 'change',
            'hx-include': '#request-fields',
            'hx-target': '#request-fields',
            'hx-select': '#request-fields',
            'hx-swap': 'outerHTML',
        } if refresh_url else {}
        self.semester = semester_of(chosen(self, 'date'), today or timezone.localdate())
        semester = self.semester
        self.teacher = self.teacher_for(user)
        assignments = (
            list(TeachingAssignment.objects.available(semester, teacher=self.teacher))
            if semester is not None and self.teacher is not None
            else []
        )
        self.fields['date'].widget.attrs.update(self.refresh)
        self.fields['date'].help_text = f'Semestre {semester.code}.' if semester else 'A data define o semestre da Agenda.'
        self.build_chain(assignments)
        self.fields['space'].queryset = Space.objects.filter(is_active=True).order_by('name')
        self.fields['space'].widget.attrs['class'] = 'input'
        slots = sorted(TimeSlot.objects.filter(semester=semester), key=lambda slot: slot.start_time) if semester else []
        self.slot_starts = sorted({f'{slot.start_time:%H:%M}' for slot in slots})
        self.slot_ends = sorted({f'{slot.end_time:%H:%M}' for slot in slots})
        self.fields['start_time'].widget.attrs['list'] = 'horarios-inicio'
        self.fields['end_time'].widget.attrs['list'] = 'horarios-fim'
        self.fields['start_time'].help_text = 'Os horários das aulas do semestre aparecem como sugestão.' if slots else ''

    def clear_after(self, trigger):
        """Descarta a escolha dos campos que dependem do campo trocado, para recarregá-los vazios.

        O htmx informa o campo trocado no cabeçalho `HX-Trigger-Name`. O valor anterior poderia
        continuar entre as opções novas e ficaria escolhido sem ter sido conferido de novo
        (D6 da Change criar-agendamento-para-outro-usuario).
        """
        names = self.DEPENDENTS.get(trigger, ())
        if not names:
            return
        if self.is_bound:
            self.data = self.data.copy()
            for name in names:
                self.data.pop(name, None)
        else:
            self.initial = {key: value for key, value in self.initial.items() if key not in names}

    def teacher_for(self, user):
        """Docente de quem solicita: aqui, o próprio usuário logado."""
        return teacher_of(user) if user is not None else None

    def build_chain(self, assignments):
        """Disciplinas dos vínculos e turmas da disciplina escolhida, só entre as opções válidas."""
        subjects = {item.offering.subject.pk: item.offering.subject for item in assignments}
        field = self.fields['subject']
        field.queryset = Subject.objects.filter(pk__in=subjects)
        field.choices = [
            ('', field.empty_label),
            *((item.pk, item.name) for item in sorted(subjects.values(), key=lambda item: item.name.casefold())),
        ]
        field.widget.attrs.update({'class': 'input', **self.refresh})
        subject_id = chosen(self, 'subject')
        of_subject = sorted(
            (item for item in assignments if str(item.offering.subject_id) == subject_id),
            key=lambda item: str(item.offering.class_group).casefold(),
        )
        field = self.fields['teaching_assignment']
        field.queryset = TeachingAssignment.objects.filter(pk__in=[item.pk for item in of_subject])
        field.widget.attrs['class'] = 'input'
        field.choices = [('', field.empty_label), *((item.pk, field.label_from_instance(item)) for item in of_subject)]

    def clean(self):
        cleaned = super().clean()
        day = cleaned.get('date')
        if day is not None and self.semester is None:
            self.add_error('date', ValidationError(
                f'A data {date_format(day, "SHORT_DATE_FORMAT")} não está no período de nenhum semestre da Agenda. '
                'Escolha outra data.',
                code='outside',
            ))
        return cleaned

    def add_error(self, field, error):
        super().add_error(field if field in self.fields or field is None else None, error)


class UserChoiceField(forms.ModelChoiceField):
    """Usuário identificado pelo nome e pelo `username`, que é o nome do docente no ensalamento."""

    def label_from_instance(self, obj):
        return f'{obj.name} ({obj.username})'


class BookingOnBehalfForm(BookingRequestForm):
    """Usuário, curso, disciplina, turma, espaço, data, horário e descrição, nesta ordem.

    Quem cria tem `AGENDA.CRIAR` e escolhe o usuário em nome de quem a solicitação é feita. A
    cadeia vem dos vínculos atuais do docente desse usuário no semestre da data
    (`TeachingAssignment.objects.available`), numa consulta só: o curso lista os cursos das
    turmas dos vínculos, a disciplina, as dos vínculos no curso escolhido, e a turma, os
    vínculos na disciplina e no curso escolhidos. A troca de um campo limpa os seguintes
    (`DEPENDENTS`). As opções só orientam: um ID fora delas é recusado aqui, e a operação do
    model confere a cadeia de novo (Change criar-agendamento-para-outro-usuario).
    """

    DEPENDENTS = {
        'requested_for': ('course', 'subject', 'teaching_assignment'),
        'course': ('subject', 'teaching_assignment'),
        'subject': ('teaching_assignment',),
    }

    requested_for = UserChoiceField(
        label='Usuário',
        queryset=User.objects.none(),
        empty_label='Escolha o usuário',
        error_messages={'required': REQUESTER_REQUIRED_MESSAGE, 'invalid_choice': 'Escolha um dos usuários docentes do semestre.'},
    )
    course = forms.ModelChoiceField(
        label='Curso',
        queryset=Course.objects.none(),
        empty_label='Escolha o curso',
        error_messages={'required': COURSE_REQUIRED_MESSAGE, 'invalid_choice': 'Escolha um dos cursos do usuário no semestre.'},
    )

    field_order = [
        'requested_for', 'course', 'subject', 'teaching_assignment', 'space', 'date', 'start_time', 'end_time', 'description',
    ]

    def __init__(self, *args, **kwargs):
        self.requester = None
        super().__init__(*args, **kwargs)
        self.fields['subject'].error_messages['invalid_choice'] = 'Escolha uma das disciplinas do usuário no curso escolhido.'
        self.fields['teaching_assignment'].error_messages['invalid_choice'] = (
            'Escolha uma das turmas do usuário na disciplina escolhida.'
        )

    def teacher_for(self, user):
        """Docente do usuário escolhido, entre os usuários docentes do semestre da data."""
        field = self.fields['requested_for']
        field.queryset = teacher_users(self.semester)
        field.widget.attrs.update({'class': 'input', **self.refresh})
        requester_id = chosen(self, 'requested_for')
        if requester_id.isdigit():
            self.requester = field.queryset.filter(pk=requester_id).first()
        return teacher_of(self.requester) if self.requester is not None else None

    def build_chain(self, assignments):
        """Cursos das turmas dos vínculos, e disciplina e turma só dos vínculos do curso escolhido."""
        courses = {item.offering.class_group.course.pk: item.offering.class_group.course for item in assignments}
        field = self.fields['course']
        field.queryset = Course.objects.filter(pk__in=courses)
        field.choices = [
            ('', field.empty_label),
            *((item.pk, item.name) for item in sorted(courses.values(), key=lambda item: item.name.casefold())),
        ]
        field.widget.attrs.update({'class': 'input', **self.refresh})
        course_id = chosen(self, 'course')
        super().build_chain([item for item in assignments if str(item.offering.class_group.course_id) == course_id])


class ReviewFilterForm(forms.Form):
    """Recorte da lista de análise pela URL: as que precisam de decisão ou todas."""

    CHOICES = [('decidir', 'Para decidir'), ('todas', 'Todas')]

    situacao = forms.ChoiceField(label='Situação', required=False, choices=CHOICES, widget=forms.Select(attrs={'class': 'input'}))

    def only_open(self):
        return not (self.is_valid() and self.cleaned_data['situacao'] == 'todas')


class RejectForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Motivo da rejeição',
        max_length=REASON_MAX_LENGTH,
        help_text='O motivo aparece para quem solicitou.',
        widget=forms.Textarea(attrs={'rows': 3}),
        error_messages={'required': REASON_REQUIRED_MESSAGE},
    )


class SuggestForm(forms.Form):
    """Outro espaço, outra data, outro horário ou a combinação deles, com a mensagem opcional."""

    suggested_space = forms.ModelChoiceField(
        label='Espaço sugerido',
        queryset=Space.objects.none(),
        widget=forms.Select(attrs={'class': 'input'}),
        error_messages={'required': 'Escolha o espaço sugerido.', 'invalid_choice': 'Escolha um espaço ativo.'},
    )
    suggested_date = date_field('Data sugerida')
    suggested_start_time = time_field('Início sugerido', START_REQUIRED_MESSAGE)
    suggested_end_time = time_field('Fim sugerido', END_REQUIRED_MESSAGE)
    suggestion_message = forms.CharField(
        label='Mensagem para quem solicitou',
        max_length=REASON_MAX_LENGTH,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, target=None, **kwargs):
        if target is not None:
            kwargs['initial'] = {
                'suggested_space': target.suggested_space_id or target.space_id,
                'suggested_date': target.suggested_date or target.date,
                'suggested_start_time': target.suggested_start_time or target.start_time,
                'suggested_end_time': target.suggested_end_time or target.end_time,
                'suggestion_message': target.suggestion_message,
            } | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        field = self.fields['suggested_space']
        field.queryset = Space.objects.filter(is_active=True).order_by('name')


ALL_AGENDAS = 'todas'
OWN_AGENDA = 'minha'


class AgendaFilterForm(GridFilterForm):
    """Filtros da Grade da Agenda: os da Grade do ensalamento e a escolha entre todas as agendas ou só a do usuário."""

    AGENDAS = [(ALL_AGENDAS, 'Todas as agendas'), (OWN_AGENDA, 'Minha agenda')]

    agenda = forms.ChoiceField(label='Agenda', required=False, choices=AGENDAS, widget=forms.Select(attrs={'class': 'input'}))
