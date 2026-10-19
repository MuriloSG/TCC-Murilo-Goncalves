from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

ERROR_MAX_LENGTH = 500


def describe_error(error):
    return f'{type(error).__name__}: {error}'[:ERROR_MAX_LENGTH]


class OutboxEntryQuerySet(models.QuerySet):
    def due(self):
        """Envios a enviar cuja próxima tentativa já venceu, na ordem de processamento."""
        return self.filter(
            status=OutboxEntry.Status.PENDING,
            next_attempt_at__lte=timezone.now(),
        ).order_by('next_attempt_at', 'pk')

    def enqueue(self, kind, reference):
        """Registra o envio sem duplicar um pendente do mesmo tipo e referência, pelo índice único parcial."""
        self.bulk_create([self.model(kind=kind, reference=str(reference))], ignore_conflicts=True)


class OutboxEntry(models.Model):
    """O conteúdo não é gravado: o tratador monta o e-mail no envio, sem token ou link no banco."""

    class Status(models.TextChoices):
        PENDING = 'A_ENVIAR', 'a enviar'
        SENT = 'ENVIADO', 'enviado'
        DISCARDED = 'DESCARTADO', 'descartado'
        FAILED = 'FALHOU', 'falhou'

    kind = models.CharField('tipo', max_length=30)
    reference = models.CharField('referência', max_length=64)
    status = models.CharField('situação', max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField('tentativas', default=0)
    next_attempt_at = models.DateTimeField('próxima tentativa', default=timezone.now)
    last_error = models.TextField('último erro', blank=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    sent_at = models.DateTimeField('enviado em', null=True, blank=True)

    objects = OutboxEntryQuerySet.as_manager()

    class Meta:
        verbose_name = 'envio de e-mail'
        verbose_name_plural = 'envios de e-mail'
        constraints = [
            models.UniqueConstraint(
                fields=['kind', 'reference'],
                condition=models.Q(status='A_ENVIAR'),
                name='outbox_entry_pending_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'next_attempt_at'], name='outbox_entry_due_idx'),
        ]

    def __str__(self):
        return f'{self.kind} {self.reference}'

    def mark_sent(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_discarded(self):
        self.status = self.Status.DISCARDED
        self.save(update_fields=['status'])

    def mark_failed(self, error):
        self.status = self.Status.FAILED
        self.last_error = error[:ERROR_MAX_LENGTH]
        self.save(update_fields=['status', 'last_error'])

    def register_failure(self, error):
        """Conta a tentativa e agenda a próxima, ou encerra em FALHOU no limite."""
        self.attempts += 1
        self.last_error = describe_error(error)
        if self.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
            self.status = self.Status.FAILED
        else:
            delays = settings.OUTBOX_RETRY_DELAYS
            delay = delays[min(self.attempts, len(delays)) - 1]
            self.next_attempt_at = timezone.now() + timedelta(seconds=delay)
        self.save(update_fields=['attempts', 'last_error', 'status', 'next_attempt_at'])
