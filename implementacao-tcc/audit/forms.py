"""Filtros da auditoria pela URL; valor inválido é descartado sem mensagem."""

from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse

from audit import catalog
from ui.forms import DateInput, limit_choices

INPUT = {'class': 'input'}


def user_option_label(user):
    return f'{user.name} ({user.email})'


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return user_option_label(user)


def code_filter(label, labels, empty):
    return forms.ChoiceField(
        label=label,
        choices=[('', empty)] + catalog.choices(labels),
        required=False,
        widget=forms.Select(attrs=INPUT),
    )


def date_filter(label):
    return forms.DateField(label=label, required=False, widget=DateInput(attrs=INPUT))


class AuditFilterForm(forms.Form):
    usuario = UserChoiceField(
        label='Usuário',
        queryset=None,
        required=False,
        empty_label='Todos os usuários',
        widget=forms.Select(attrs=INPUT),
    )
    acao = code_filter('Ação', catalog.ACTION_LABELS, 'Todas as ações')
    recurso = code_filter('Módulo', catalog.RESOURCE_LABELS, 'Todos os módulos')
    origem = code_filter('Origem', catalog.ORIGIN_LABELS, 'Todas as origens')
    registro = forms.CharField(
        label='Identificador do registro',
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs=INPUT),
    )
    de = date_filter('De')
    ate = date_filter('Até')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['usuario']
        field.queryset = get_user_model().objects.order_by('name', 'email')
        field.widget.attrs['data-select-source'] = reverse('audit_user_options')
        limit_choices(field, self.data.get('usuario'))

    def criteria(self):
        """Critérios válidos da consulta, com os valores inválidos trocados por vazio."""
        self.is_valid()
        data = self.cleaned_data
        return {
            'user': data.get('usuario'),
            'action': data.get('acao') or '',
            'resource': data.get('recurso') or '',
            'origin': data.get('origem') or '',
            'resource_id': (data.get('registro') or '').strip(),
            'start': data.get('de'),
            'end': data.get('ate'),
        }
