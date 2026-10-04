"""Auxiliares de teste das configurações, usados também pelos testes que enviam e-mail."""

from system_settings.models import Security, SmtpSettings, SystemSetting

SMTP_PASSWORD = 'senha-de-app-secreta'


def smtp_settings(**values):
    defaults = {
        'host': 'smtp.ifnmg.edu.br',
        'port': 587,
        'security': Security.STARTTLS,
        'username': 'agenda',
        'password': SMTP_PASSWORD,
        'from_email': 'IFAgenda <agenda@ifnmg.edu.br>',
    }
    return SmtpSettings(**(defaults | values))


def configure_smtp(**values):
    """Grava a configuração SMTP direto no banco, sem auditoria, para preparar o cenário."""
    setting, _ = SystemSetting.objects.update_or_create(
        kind=SystemSetting.Kind.SMTP, defaults={'value': smtp_settings(**values).to_value()},
    )
    return setting
