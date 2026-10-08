"""Separado de adapters.py porque importar os formulários do allauth daqui seria circular."""

from allauth.account.forms import EmailAwarePasswordResetTokenGenerator


class PasswordResetTokenGenerator(EmailAwarePasswordResetTokenGenerator):
    """Recusa o token de usuário inativo, que o hash do token não considera."""

    def check_token(self, user, token):
        return user is not None and user.is_active and super().check_token(user, token)
