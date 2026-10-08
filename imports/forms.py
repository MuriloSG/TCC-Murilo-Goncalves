from django import forms

from imports.reader import FileRejected


class ImportUploadForm(forms.Form):
    """Os campos próprios viram coluna lógica de todas as linhas, para a confirmação usar o valor da prévia."""

    file = forms.FileField()

    def __init__(self, *args, definition, **kwargs):
        super().__init__(*args, **kwargs)
        self.definition = definition
        self.source = definition.source()
        field = self.fields['file']
        field.label = self.source.file_label
        field.help_text = self.source.help_text(definition)
        field.widget = forms.ClearableFileInput(attrs={'accept': self.source.accept})
        field.error_messages['required'] = self.source.missing_message
        for label, own_field in definition.upload_fields.items():
            self.fields[self.field_name(label)] = own_field

    def field_name(self, label):
        return 'own_' + ''.join(char for char in label.lower() if char.isalnum())

    def clean(self):
        """Valida os campos próprios juntos e lê o arquivo depois deles, para que o valor deles entre nas linhas."""
        cleaned = super().clean()
        uploaded = cleaned.get('file')
        if uploaded is None or self.errors:
            return cleaned
        try:
            self.definition.clean_upload({label: cleaned.get(self.field_name(label)) for label in self.definition.upload_fields})
        except forms.ValidationError as error:
            if hasattr(error, 'error_dict'):
                for label, errors in error.error_dict.items():
                    field = self.field_name(label) if label in self.definition.upload_fields else None
                    self.add_error(field, errors)
            else:
                self.add_error(None, error)
            return cleaned
        own_values = {
            label: '' if cleaned[self.field_name(label)] is None else str(cleaned[self.field_name(label)])
            for label in self.definition.upload_fields
        }
        try:
            rows = self.source.read(uploaded, self.definition)
        except FileRejected as error:
            self.add_error('file', forms.ValidationError(error.message, code='file_rejected'))
            return cleaned
        for row in rows:
            row.values.update(own_values)
        cleaned['rows'] = rows
        return cleaned


class RowFilterForm(forms.Form):
    """Recorte das linhas da prévia, escolhido num select e recebido pela URL."""

    linhas = forms.ChoiceField(label='Mostrar', required=False, widget=forms.Select(attrs={'class': 'input'}))

    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['linhas'].choices = choices
