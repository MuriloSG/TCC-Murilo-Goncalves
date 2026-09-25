from django import forms

from imports.reader import FileRejected


class ImportUploadForm(forms.Form):
    """Envio do arquivo. A leitura e a conferência da estrutura acontecem na validação.

    As recusas do arquivo inteiro viram erro do campo, e nenhuma importação é criada. Os
    campos próprios da importação específica entram ao lado do arquivo, e o valor de cada
    um é gravado como coluna lógica nos valores de todas as linhas, para que a confirmação
    reexecute com o valor que foi visto na prévia.
    """

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
        """Lê o arquivo depois dos campos próprios, para que o valor deles entre nas linhas."""
        cleaned = super().clean()
        uploaded = cleaned.get('file')
        if uploaded is None or self.errors:
            return cleaned
        own_values = {
            label: str(cleaned[self.field_name(label)]) for label in self.definition.upload_fields
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
