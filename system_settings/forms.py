from django import forms

from system_settings.models import Security


class SmtpForm(forms.Form):
    """Dados do servidor de e-mail; a senha nunca volta para a tela."""

    host = forms.CharField(label='Servidor', max_length=255, error_messages={'required': 'Informe o servidor de e-mail.'})
    port = forms.IntegerField(
        label='Porta',
        min_value=1,
        max_value=65535,
        error_messages={
            'required': 'Informe uma porta entre 1 e 65535.',
            'invalid': 'Informe uma porta entre 1 e 65535.',
            'min_value': 'Informe uma porta entre 1 e 65535.',
            'max_value': 'Informe uma porta entre 1 e 65535.',
        },
    )
    security = forms.ChoiceField(
        label='Segurança',
        choices=Security.choices,
        error_messages={'required': 'Escolha a segurança da conexão.', 'invalid_choice': 'Escolha a segurança da conexão.'},
    )
    username = forms.CharField(label='Usuário', max_length=255, required=False)
    password = forms.CharField(
        label='Senha',
        max_length=255,
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
    )
    from_email = forms.CharField(
        label='Remetente',
        max_length=255,
        help_text='Nome e e-mail, como IFAgenda <agenda@ifnmg.edu.br>.',
        error_messages={'required': 'Informe o remetente com um e-mail válido, como IFAgenda <agenda@ifnmg.edu.br>.'},
    )

    def __init__(self, *args, has_password=False, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields['password']
        password.conditional = True
        if has_password:
            password.help_text = 'Deixe em branco para manter a senha gravada.'
        else:
            password.help_text = 'Exigida quando há usuário.'
