"""Renderização de formulários com os componentes da interface (D11).

O Django 5.2 já coloca aria-invalid e aria-describedby nos campos, apontando para
os ids {id}_helptext e {id}_error. Os templates de ui/forms usam esses mesmos ids.
"""

from django import forms
from django.forms.renderers import TemplatesSetting


class FormRenderer(TemplatesSetting):
    form_template_name = 'ui/forms/form.html'
    field_template_name = 'ui/forms/field.html'


class GroupedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Lista de seleção em grupos recolhíveis, com contagem, busca e seleção de todas.

    O valor de cada opção aparece como código e o rótulo como descrição. As
    contagens vêm do servidor, e o ui/static/ui/js/checklist.js as atualiza e
    liga a busca e o botão de seleção, que ficam ocultos sem JavaScript.
    """

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
