"""Gerador de token da recuperação de senha.

Fica separado de adapters.py porque allauth.account.forms instancia o gerador
durante a própria importação, e importar os formulários do allauth daqui seria
circular.
"""

from allauth.account.forms import EmailAwarePasswordResetTokenGenerator


class PasswordResetTokenGenerator(EmailAwarePasswordResetTokenGenerator):
    """Recusa o token de usuário inativo (D12).

    O hash do token não considera is_active, então um link emitido antes da
    desativação continuaria redefinindo a senha.
    """

    def check_token(self, user, token):
        return user is not None and user.is_active and super().check_token(user, token)
