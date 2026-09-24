"""Registro centralizado das ações do sistema (D1, D2, D8, D9, D10).

Toda ação auditável de qualquer módulo vira uma linha desta tabela, gravada por
`AuditLog.objects.record`. A gravação acontece na transação de quem chama, de
modo que uma operação desfeita leve o registro junto e uma operação aplicada
nunca fique sem registro.
"""

from django.conf import settings
from django.db import models

from audit import catalog
from audit.context import current_actor

SENSITIVE_PARTS = ('senha', 'password', 'token', 'secret', 'chave', 'hash', 'key')

USER_AGENT_MAX_LENGTH = 255
RESOURCE_ID_MAX_LENGTH = 64


class AuditLogProtected(Exception):
    """Recusa de alteração ou de exclusão de um registro de auditoria."""

    def __init__(self):
        super().__init__('Registros de auditoria não podem ser alterados nem excluídos.')


class UnknownAuditCode(Exception):
    """Recusa de um código de ação ou de módulo fora do catálogo."""

    def __init__(self, kind, code):
        super().__init__(f'Código de {kind} fora do catálogo de auditoria: {code}.')


def sanitize(values):
    """Copia os valores sem os campos cujo nome indica senha, token ou segredo.

    É a rede de proteção do ponto único de gravação: quem registra a ação já monta
    os valores campo a campo, sem dados sensíveis.
    """
    return {
        name: value
        for name, value in (values or {}).items()
        if not any(part in str(name).lower() for part in SENSITIVE_PARTS)
    }


class AuditLogQuerySet(models.QuerySet):
    def update(self, **values):
        raise AuditLogProtected()

    def delete(self):
        raise AuditLogProtected()


class AuditLogManager(models.Manager.from_queryset(AuditLogQuerySet)):
    def record(self, action, resource, resource_id=None, old_values=None, new_values=None, metadata=None):
        """Grava a ação com o ator do contexto e devolve o registro criado."""
        if action not in catalog.ACTION_LABELS:
            raise UnknownAuditCode('ação', action)
        if resource not in catalog.RESOURCE_LABELS:
            raise UnknownAuditCode('módulo', resource)
        actor = current_actor()
        user = actor.user if getattr(actor.user, 'pk', None) else None
        return self.create(
            user=user,
            action=action,
            resource=resource,
            resource_id='' if resource_id is None else str(resource_id)[:RESOURCE_ID_MAX_LENGTH],
            old_values=sanitize(old_values),
            new_values=sanitize(new_values),
            metadata=sanitize(metadata),
            origin=actor.origin,
            ip_address=actor.ip_address,
            user_agent=(actor.user_agent or '')[:USER_AGENT_MAX_LENGTH],
        )

    def record_changes(self, resource, resource_id, previous, current):
        """Registra a alteração só com os campos que mudaram, e nada quando nada mudou."""
        changed = {field: value for field, value in current.items() if previous.get(field) != value}
        if not changed:
            return None
        return self.record(
            catalog.UPDATE,
            resource,
            resource_id=resource_id,
            old_values={field: previous.get(field) for field in changed},
            new_values=changed,
        )


class AuditLog(models.Model):
    """Ação registrada: quem fez, o que fez, sobre o quê, quando e de onde."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        null=True,
        blank=True,
        verbose_name='usuário',
    )
    action = models.CharField('ação', max_length=30)
    resource = models.CharField('módulo', max_length=30)
    resource_id = models.CharField('identificador do registro', max_length=RESOURCE_ID_MAX_LENGTH, blank=True)
    old_values = models.JSONField('valores anteriores', default=dict, blank=True)
    new_values = models.JSONField('valores posteriores', default=dict, blank=True)
    metadata = models.JSONField('informações adicionais', default=dict, blank=True)
    origin = models.CharField('origem', max_length=15, default=catalog.SYSTEM)
    ip_address = models.GenericIPAddressField('endereço IP', null=True, blank=True)
    user_agent = models.CharField('cliente', max_length=USER_AGENT_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField('registrado em', auto_now_add=True)

    objects = AuditLogManager()

    class Meta:
        verbose_name = 'registro de auditoria'
        verbose_name_plural = 'registros de auditoria'
        ordering = ['-created_at', '-pk']
        indexes = [
            models.Index(fields=['-created_at'], name='audit_log_created_idx'),
            models.Index(fields=['user', '-created_at'], name='audit_log_user_idx'),
            models.Index(fields=['action', '-created_at'], name='audit_log_action_idx'),
            models.Index(fields=['resource', 'resource_id'], name='audit_log_resource_idx'),
        ]

    def __str__(self):
        return f'{self.action} {self.resource} {self.resource_id}'.strip()

    def save(self, *args, **values):
        """Só aceita a inserção: um registro gravado nunca muda (D10)."""
        if self.pk is not None:
            raise AuditLogProtected()
        super().save(*args, **values)

    def delete(self, *args, **values):
        raise AuditLogProtected()

    @property
    def action_label(self):
        return catalog.label(catalog.ACTION_LABELS, self.action)

    @property
    def resource_label(self):
        return catalog.label(catalog.RESOURCE_LABELS, self.resource)

    @property
    def origin_label(self):
        return catalog.label(catalog.ORIGIN_LABELS, self.origin)
