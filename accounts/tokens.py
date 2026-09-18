# Módulo separado de adapters.py: allauth.account.forms instancia o gerador
# durante a própria importação, e importar os formulários daqui seria circular.
from allauth.account.forms import EmailAwarePasswordResetTokenGenerator


class PasswordResetTokenGenerator(EmailAwarePasswordResetTokenGenerator):
    # O hash do token não considera is_active, então um link emitido antes da
    # desativação continuaria redefinindo a senha.
    def check_token(self, user, token):
        return user is not None and user.is_active and super().check_token(user, token)
