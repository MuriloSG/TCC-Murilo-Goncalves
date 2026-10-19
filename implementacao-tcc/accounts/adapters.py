import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

from accounts.utils import typed_email
from audit import catalog
from audit.models import AuditLog
from system_settings.models import SystemSetting

logger = logging.getLogger('accounts')


class AccountAdapter(DefaultAccountAdapter):
    """Adaptador do allauth com as mensagens de erro do projeto."""

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
        """Recusa o usuário inativo como credencial inválida e audita a recusa, que o sinal do Django não alcança."""
        user = super().authenticate(request, **credentials)
        if user is not None and not user.is_active:
            user = None
        if user is None:
            AuditLog.objects.record(
                catalog.LOGIN_REFUSED,
                catalog.AUTHENTICATION,
                metadata={'email': typed_email(credentials.get('email') or credentials.get('username'))},
            )
        return user

    def send_mail(self, template_prefix, email, context):
        """Envia pela configuração SMTP gravada; sem ela, só registra o motivo no log."""
        try:
            smtp = SystemSetting.objects.smtp()
        except ValidationError:
            smtp = None
            reason = 'a configuração do servidor de e-mail é inválida'
        else:
            reason = 'o servidor de e-mail não está configurado'
        if smtp is None:
            logger.warning('E-mail %s não enviado: %s.', template_prefix, reason)
            return
        message = self.render_mail(template_prefix, email, context)
        smtp.prepare(message, smtp.connection()).send()
