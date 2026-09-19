from django import forms

from imports.reader import FileRejected, listing, read_csv


class ImportUploadForm(forms.Form):
    """Envio do arquivo. A leitura e a conferência da estrutura acontecem na validação.

    As recusas do arquivo inteiro viram erro do campo, e nenhuma importação é criada.
    """

    file = forms.FileField(
        label='Arquivo CSV',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv,text/csv'}),
        error_messages={'required': 'Escolha o arquivo CSV.'},
    )

    def __init__(self, *args, definition, **kwargs):
        super().__init__(*args, **kwargs)
        self.definition = definition
        labels = listing([column.label for column in definition.columns])
        self.fields['file'].help_text = f'CSV em UTF-8, separado por ";", com as colunas {labels}.'

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        try:
            self.cleaned_data['rows'] = read_csv(uploaded, self.definition)
        except FileRejected as error:
            raise forms.ValidationError(error.message, code='file_rejected') from None
        return uploaded
