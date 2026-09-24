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


class GroupedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Lista de seleção em grupos recolhíveis, com contagem, busca e seleção de todas.

    As contagens vêm do servidor, e o ui/static/ui/js/checklist.js as atualiza e
    liga a busca e o botão de seleção, que ficam ocultos sem JavaScript.

    Os textos dizem de que lista se trata, porque o componente serve a mais de uma:
    as permissões de um perfil e os destinatários de uma notificação. Com
    `show_values`, cada opção aparece como o código em destaque seguido da
    descrição, que é o formato das permissões; sem ele, aparece só o rótulo.
    """

    template_name = 'ui/forms/grouped_checkboxes.html'

    def __init__(
        self,
        attrs=None,
        summary_label='permissões selecionadas',
        search_label='Buscar permissão',
        empty_label='Nenhuma permissão encontrada para a busca.',
        show_values=True,
    ):
        super().__init__(attrs)
        self.summary_label = summary_label
        self.search_label = search_label
        self.empty_label = empty_label
        self.show_values = show_values

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        optgroups = context['widget']['optgroups']
        if all(group is None for group, options, index in optgroups):
            optgroups = [(None, [option for group, options, index in optgroups for option in options], 0)]
        groups = [
            {
                'name': group,
                'options': options,
                'selected': sum(1 for option in options if option['selected']),
                'total': len(options),
            }
            for group, options, index in optgroups
        ]
        context['widget']['groups'] = groups
        context['widget']['selected_count'] = sum(group['selected'] for group in groups)
        context['widget']['total_count'] = sum(group['total'] for group in groups)
        context['widget']['summary_label'] = self.summary_label
        context['widget']['search_label'] = self.search_label
        context['widget']['empty_label'] = self.empty_label
        context['widget']['show_values'] = self.show_values
        return context


def limit_choices(field, selected=None, page_size=OPTIONS_PAGE_SIZE):
    """Deixa no campo só a primeira página das opções, mais a escolhida (D5).

    A validação continua usando o queryset inteiro: só a lista que vai para o HTML
    é limitada, e as demais opções chegam pela rota de opções.
    """
    items = list(field.queryset[:page_size])
    try:
        chosen = field.queryset.filter(pk=selected).first() if selected else None
    except (ValueError, TypeError):
        chosen = None
    if chosen is not None and chosen not in items:
        items.insert(0, chosen)
    choices = [] if field.empty_label is None else [('', field.empty_label)]
    field.widget.choices = choices + [(item.pk, field.label_from_instance(item)) for item in items]
