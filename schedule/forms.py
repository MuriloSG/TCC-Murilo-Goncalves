from django import forms


class RoomFilterForm(forms.Form):
    """Sala escolhida na Grade, recebida pela URL (D3 da Change visualizar-grade-do-ensalamento)."""

    sala = forms.ChoiceField(label='Sala', required=False, widget=forms.Select(attrs={'class': 'input'}))

    def __init__(self, *args, spaces=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sala'].choices = [
            (option.name, f'{option.name}, com choque' if option.has_clash else option.name) for option in spaces
        ]
