from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Adaptador do allauth com as mensagens de erro reescritas nas regras de texto (D5)."""

    error_messages = DefaultAccountAdapter.error_messages | {
        'email_password_mismatch': 'E-mail ou senha incorretos. Confira os dados ou use "Esqueci minha senha".',
        'too_many_login_attempts': (
            'Tentativas de login demais em pouco tempo. Aguarde alguns minutos e tente de novo.'
        ),
        'rate_limited': 'Solicitações demais em pouco tempo. Aguarde alguns minutos e tente de novo.',
    }

    def is_open_for_signup(self, request):
        return False

    def authenticate(self, request, **credentials):
        """Trata o usuário inativo como credencial inválida.

        Com a senha correta, o allauth devolve o usuário inativo para redirecioná-lo
        a account_inactive, rota que não é exposta. Assim a resposta é a mesma de
        uma senha errada.
        """
        user = super().authenticate(request, **credentials)
        if user is not None and not user.is_active:
            return None
        return user

