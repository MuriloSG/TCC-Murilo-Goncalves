"""Configurações globais do sistema, uma linha por tipo com esquema próprio."""

import base64
import hashlib
from dataclasses import dataclass, fields
from email.utils import parseaddr

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import get_connection
from django.core.validators import validate_email
from django.db import models, transaction

from audit import catalog
from audit.models import AuditLog

UNREADABLE_PASSWORD_MESSAGE = 'A senha gravada não pode ser lida com a chave atual. Informe a senha de novo.'


def cipher():
    """Fernet com a chave de DJANGO_CREDENTIALS_KEY, levada a 32 bytes pelo SHA-256."""
    digest = hashlib.sha256(settings.CREDENTIALS_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(secret):
    return cipher().encrypt(secret.encode()).decode()


def decrypt(token):
    """Decifra a senha; um token que a chave atual não abre torna a configuração inválida."""
    try:
        return cipher().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValidationError({'password': UNREADABLE_PASSWORD_MESSAGE}) from None


class Security(models.TextChoices):
    STARTTLS = 'STARTTLS', 'STARTTLS'
    SSL = 'SSL', 'SSL/TLS'
    NONE = 'NENHUMA', 'Nenhuma'


@dataclass(frozen=True)
class SmtpSettings:
    """Senha decifrada só em memória, fora do `repr` para não chegar a um log."""

    host: str
    port: int
    security: str
    username: str
    password: str
    from_email: str

    def __repr__(self):
        return f'SmtpSettings(host={self.host!r}, port={self.port!r}, username={self.username!r})'

    @classmethod
    def from_value(cls, value):
        """Converte o valor gravado, decifrando a senha, e valida o resultado."""
        names = {field.name for field in fields(cls)}
        if not isinstance(value, dict) or set(value) != names:
            raise ValidationError('A configuração do servidor de e-mail não segue o esquema esperado.')
        token = value['password']
        smtp = cls(**(value | {'password': decrypt(token) if token else ''}))
        smtp.validate()
        return smtp

    def to_value(self):
        """Valor a gravar, com a senha cifrada."""
        return {
            'host': self.host,
            'port': self.port,
            'security': self.security,
            'username': self.username,
            'password': encrypt(self.password) if self.password else '',
            'from_email': self.from_email,
        }

    def validate(self):
        errors = {}
        if not isinstance(self.host, str) or not self.host.strip():
            errors['host'] = 'Informe o servidor de e-mail.'
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            errors['port'] = 'Informe uma porta entre 1 e 65535.'
        if self.security not in Security.values:
            errors['security'] = 'Escolha a segurança da conexão.'
        try:
            validate_email(parseaddr(self.from_email)[1])
        except (ValidationError, TypeError):
            errors['from_email'] = 'Informe o remetente com um e-mail válido, como IFAgenda <agenda@ifnmg.edu.br>.'
        if self.username and not self.password:
            errors['password'] = 'Informe a senha do usuário.'
        elif self.password and not self.username:
            errors['username'] = 'Informe o usuário da senha.'
        elif self.username and self.security == Security.NONE:
            errors['security'] = 'Use STARTTLS ou SSL/TLS para enviar usuário e senha.'
        if errors:
            raise ValidationError(errors)

    def connection(self):
        """Conexão do backend configurado no ambiente com as credenciais daqui."""
        return get_connection(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            use_tls=self.security == Security.STARTTLS,
            use_ssl=self.security == Security.SSL,
            timeout=settings.EMAIL_TIMEOUT,
        )

    def prepare(self, message, connection):
        """Põe na mensagem o remetente da configuração e a conexão do lote."""
        message.from_email = self.from_email
        message.connection = connection
        return message

    def audit_values(self, password_changed):
        """Campos para a auditoria; a chave evita "senha", que o `sanitize` descartaria."""
        return {
            'servidor': self.host,
            'porta': self.port,
            'seguranca': self.security,
            'usuario': self.username,
            'remetente': self.from_email,
            'credencial': 'alterada' if password_changed else 'mantida',
        }


class SystemSettingQuerySet(models.QuerySet):
    def smtp(self):
        """Configuração SMTP pronta, ou None; lança ValidationError se a gravada for inválida."""
        setting = self.filter(kind=SystemSetting.Kind.SMTP).first()
        return None if setting is None else SmtpSettings.from_value(setting.value)

    def save_smtp(self, *, host, port, security, username, password, from_email):
        """Senha em branco mantém a gravada; sem usuário, a senha é apagada."""
        with transaction.atomic(using=self.db):
            setting = self.select_for_update().filter(kind=SystemSetting.Kind.SMTP).first()
            username = (username or '').strip()
            current = ''
            if setting is not None and username and not password and setting.value.get('password'):
                current = decrypt(setting.value['password'])
            smtp = SmtpSettings(
                host=(host or '').strip(),
                port=port,
                security=security,
                username=username,
                password=(password or current) if username else '',
                from_email=(from_email or '').strip(),
            )
            smtp.validate()
            created = setting is None
            if created:
                setting = self.model(kind=SystemSetting.Kind.SMTP)
            setting.value = smtp.to_value()
            setting.save(using=self.db)
            AuditLog.objects.record(
                catalog.CREATE if created else catalog.UPDATE,
                catalog.SETTINGS,
                resource_id=setting.kind,
                new_values=smtp.audit_values(password_changed=bool(password)),
            )
        return setting

    def clear_smtp(self):
        """Exclui a configuração SMTP, com auditoria; os envios pendentes ficam retidos."""
        with transaction.atomic(using=self.db):
            setting = self.select_for_update().get(kind=SystemSetting.Kind.SMTP)
            AuditLog.objects.record(
                catalog.DELETE,
                catalog.SETTINGS,
                resource_id=setting.kind,
                old_values={
                    'servidor': setting.value.get('host'),
                    'porta': setting.value.get('port'),
                    'seguranca': setting.value.get('security'),
                    'usuario': setting.value.get('username'),
                    'remetente': setting.value.get('from_email'),
                },
            )
            setting.delete()


class SystemSetting(models.Model):
    """Uma configuração do sistema, única por tipo, com o valor no esquema do tipo."""

    class Kind(models.TextChoices):
        SMTP = 'smtp', 'servidor de e-mail'

    kind = models.CharField('tipo', max_length=30, choices=Kind.choices, unique=True)
    value = models.JSONField('valor', default=dict)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('alterado em', auto_now=True)

    objects = SystemSettingQuerySet.as_manager()

    class Meta:
        verbose_name = 'configuração do sistema'
        verbose_name_plural = 'configurações do sistema'

    def __str__(self):
        return self.get_kind_display()

    def clean(self):
        SCHEMAS[self.kind].from_value(self.value)


SCHEMAS = {SystemSetting.Kind.SMTP: SmtpSettings}
