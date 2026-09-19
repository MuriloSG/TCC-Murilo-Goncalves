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
    """Caixas de seleção com cada grupo de opções num fieldset com legenda."""

    template_name = 'ui/forms/grouped_checkboxes.html'
