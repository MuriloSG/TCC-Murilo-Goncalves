from allauth.account.adapter import DefaultAccountAdapter

from audit import catalog
from audit.models import AuditLog


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
        """Trata o usuário inativo como credencial inválida e audita a recusa (D6).

        Com a senha correta, o allauth devolve o usuário inativo para redirecioná-lo
        a account_inactive, rota que não é exposta. Assim a resposta é a mesma de
        uma senha errada. A recusa é registrada aqui, e não pelo sinal do Django,
        porque o usuário inativo não chega a ele. A senha nunca é registrada.
        """
        user = super().authenticate(request, **credentials)
        if user is not None and not user.is_active:
            user = None
        if user is None:
            AuditLog.objects.record(
                catalog.LOGIN_REFUSED,
                catalog.AUTHENTICATION,
                metadata={'email': credentials.get('email') or credentials.get('username') or ''},
            )
        return user

