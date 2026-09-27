"""Renderização de formulários com os componentes da interface (D11).

O Django 5.2 já coloca aria-invalid e aria-describedby nos campos, apontando para
os ids {id}_helptext e {id}_error. Os templates de ui/forms usam esses mesmos ids.
"""

from django import forms
from django.forms.renderers import TemplatesSetting

from ui.pagination import OPTIONS_PAGE_SIZE


class FormRenderer(TemplatesSetting):
    form_template_name = 'ui/forms/form.html'
    field_template_name = 'ui/forms/field.html'


class DateInput(forms.DateInput):
    """Campo de data com o calendário do ui/static/ui/js/datepicker.js.

    O input nativo do tipo date continua sendo o campo enviado, no formato
    aaaa-mm-dd, e sem JavaScript é ele que aparece. O calendário só preenche o
    input e dispara os eventos input e change.
    """

    input_type = 'date'
    template_name = 'ui/forms/date.html'

    def __init__(self, attrs=None, format='%Y-%m-%d'):
        super().__init__(attrs=attrs, format=format)


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


def limit_choices(field, selected=None, page_size=OPTIONS_PAGE_SIZE):
    """Deixa no campo só a primeira página das opções, mais as escolhidas (D5).

    `selected` é um valor ou vários, conforme o campo escolha um ou vários. A
    validação continua usando o queryset inteiro: só a lista que vai para o HTML
    é limitada, e as demais opções chegam pela rota de opções.
    """
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
