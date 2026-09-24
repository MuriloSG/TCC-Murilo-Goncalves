"""Notificações do sistema: criação, entrega por destinatário e leitura (D2, D4, D6).

Uma notificação pertence a um único destinatário. O conteúdo destinado a várias
pessoas vira uma notificação por pessoa, cada uma com o próprio estado de leitura,
e o título e a mensagem são copiados para cada uma, de modo que a notificação
continue legível mesmo quando o que a originou deixar de existir.

Os módulos do mecanismo não importam apps de domínio: o destinatário é o usuário
configurado em AUTH_USER_MODEL e a resolução dos destinatários usa a consulta do
próprio usuário, sem conhecer os apps que definem as telas.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from notices import catalog

TITLE_MAX_LENGTH = 120
MESSAGE_MAX_LENGTH = 500
TARGET_MAX_LENGTH = 200


class UnknownNoticeType(ValidationError):
    def __init__(self, code):
        super().__init__(
            {'type': f'Tipo de notificação fora do catálogo: {code}.'},
            code='unknown_type',
        )


class UnknownDestination(ValidationError):
    def __init__(self, code):
        super().__init__(
            {'destination': f'Forma de destinar fora do catálogo: {code}.'},
            code='unknown_destination',
        )


class NoRecipients(ValidationError):
    def __init__(self):
        super().__init__(
            'Nenhum usuário ativo corresponde aos destinatários escolhidos. Escolha outro destino.',
            code='no_recipients',
        )


def validate_type(code):
    """Recusa o tipo fora do catálogo antes de montar a notificação.

    O `clean` do model faz a mesma verificação para uma gravação direta, mas o
    `full_clean` devolveria a recusa como erro comum de campo, e quem chama as
    operações espera a exceção do tipo desconhecido.
    """
    if code not in catalog.TYPES:
        raise UnknownNoticeType(code)


def resolve_recipients(destination, role=None, users=()):
    """Usuários que recebem uma publicação manual, sempre só os ativos (D6).

    O usuário inativo é apenas excluído do conjunto, inclusive quando escolhido um
    a um, porque ele não entra no sistema e não leria a notificação.
    """
    people = get_user_model().objects.filter(is_active=True)
    if destination == catalog.ALL_USERS:
        return people
    if destination == catalog.ROLE:
        return people.filter(roles=role) if role is not None else people.none()
    if destination == catalog.USERS:
        return people.filter(pk__in=[getattr(person, 'pk', person) for person in users])
    raise UnknownDestination(destination)


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(recipient=user)

    def unread(self):
        return self.filter(read_at__isnull=True)


class NotificationManager(models.Manager.from_queryset(NotificationQuerySet)):
    def notify(self, recipient, notice_type, title, message, target_url=''):
        """Cria a notificação de um destinatário e a devolve."""
        validate_type(notice_type)
        notification = self.model(
            recipient=recipient,
            type=notice_type,
            title=(title or '').strip(),
            message=(message or '').strip(),
            target_url=target_url or '',
        )
        notification.full_clean()
        with transaction.atomic(using=self.db):
            notification.save(using=self.db)
        return notification

    def publish(self, notice_type, title, message, recipients, target_url=''):
        """Entrega a mesma notificação a cada destinatário e devolve quantos foram alcançados.

        Os destinatários são resolvidos por quem chama e percorridos aqui uma única
        vez, numa transação: ou todos recebem, ou ninguém recebe.
        """
        validate_type(notice_type)
        prototype = self.model(
            type=notice_type,
            title=(title or '').strip(),
            message=(message or '').strip(),
            target_url=target_url or '',
        )
        prototype.full_clean(exclude=['recipient'])
        people = list(recipients)
        if not people:
            raise NoRecipients()
        with transaction.atomic(using=self.db):
            self.bulk_create(
                self.model(
                    recipient=person,
                    type=prototype.type,
                    title=prototype.title,
                    message=prototype.message,
                    target_url=prototype.target_url,
                )
                for person in people
            )
        return len(people)

    def unread_count(self, user):
        return self.for_user(user).unread().count()

    def mark_all_as_read(self, user):
        """Marca as não lidas do usuário e devolve quantas mudaram."""
        with transaction.atomic(using=self.db):
            return self.for_user(user).unread().update(read_at=timezone.now())


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='destinatário',
    )
    type = models.CharField('tipo', max_length=50)
    title = models.CharField('título', max_length=TITLE_MAX_LENGTH)
    message = models.TextField('mensagem', max_length=MESSAGE_MAX_LENGTH)
    target_url = models.CharField('destino', max_length=TARGET_MAX_LENGTH, blank=True)
    read_at = models.DateTimeField('lida em', null=True, blank=True)
    created_at = models.DateTimeField('criada em', auto_now_add=True)

    objects = NotificationManager()

    class Meta:
        verbose_name = 'notificação'
        verbose_name_plural = 'notificações'
        ordering = ['-created_at', '-pk']
        indexes = [
            models.Index(fields=['recipient', 'read_at'], name='notification_recipient_read'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.type not in catalog.TYPES:
            raise UnknownNoticeType(self.type)

    @property
    def unread(self):
        return self.read_at is None

    @property
    def label(self):
        return catalog.label(self.type)

    @property
    def icon(self):
        return catalog.icon(self.type)

    @property
    def tone(self):
        return catalog.tone(self.type)

    def mark_as_read(self):
        """Marca como lida e devolve se o estado mudou. Marcar de novo não altera nada."""
        if self.read_at is not None:
            return False
        with transaction.atomic():
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
        return True
