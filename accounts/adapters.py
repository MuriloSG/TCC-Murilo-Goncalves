from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.forms import ResetPasswordForm
from allauth.core import ratelimit


class AccountAdapter(DefaultAccountAdapter):
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


def send_password_link(request, email):
    """Dispara a recuperação de senha do allauth, com o mesmo limite de tentativas
    da tela pública. Devolve False quando o limite foi atingido ou nada foi enviado."""
    if not ratelimit.consume(request, action='reset_password', key=email.lower()):
        return False
    form = ResetPasswordForm(data={'email': email})
    if not form.is_valid():
        return False
    form.save(request)
    return bool(form.users)
