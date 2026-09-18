from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

    def authenticate(self, request, **credentials):
        # Com a senha correta, o allauth devolve o usuário inativo para
        # redirecioná-lo a account_inactive, rota que não é exposta. Tratá-lo
        # como credencial inválida mantém a mesma resposta de uma senha errada.
        user = super().authenticate(request, **credentials)
        if user is not None and not user.is_active:
            return None
        return user
