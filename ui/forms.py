"""Formulários com os componentes da interface, com os ids que o Django usa em aria-describedby."""

from django import forms
from django.forms.renderers import TemplatesSetting

from ui.pagination import OPTIONS_PAGE_SIZE


class FormRenderer(TemplatesSetting):
    form_template_name = 'ui/forms/form.html'
    field_template_name = 'ui/forms/field.html'


class DateInput(forms.DateInput):
    """Input date nativo, enviado e visível sem JavaScript, preenchido pelo datepicker.js."""

    input_type = 'date'
    template_name = 'ui/forms/date.html'

    def __init__(self, attrs=None, format='%Y-%m-%d'):
        super().__init__(attrs=attrs, format=format)


class GroupedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Seleção em grupos recolhíveis; o checklist.js liga a busca e a contagem."""

    template_name = 'ui/forms/grouped_checkboxes.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        groups = [
            {
                'name': group,
                'options': options,
                'selected': sum(1 for option in options if option['selected']),
                'total': len(options),
            }
            for group, options, index in context['widget']['optgroups']
        ]
        context['widget']['groups'] = groups
        context['widget']['selected_count'] = sum(group['selected'] for group in groups)
        context['widget']['total_count'] = sum(group['total'] for group in groups)
        return context


def limit_choices(field, selected=None, page_size=OPTIONS_PAGE_SIZE):
    """Limita o HTML à primeira página e às escolhidas; a validação usa o queryset inteiro."""
    items = list(field.queryset[:page_size])
    values = selected if isinstance(selected, (list, tuple, set)) else [selected]
    values = [value for value in values if value not in (None, '')]
    try:
        chosen = list(field.queryset.filter(pk__in=values)) if values else []
    except (ValueError, TypeError):
        chosen = []
    for item in reversed(chosen):
        if item not in items:
            items.insert(0, item)
    choices = [] if getattr(field, 'empty_label', None) is None else [('', field.empty_label)]
    field.widget.choices = choices + [(item.pk, field.label_from_instance(item)) for item in items]
