from contextlib import contextmanager
from contextvars import ContextVar

from allauth.account.models import EmailAddress
from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils.crypto import salted_hmac

from accounts.emails import PASSWORD_LINK

from accounts.permissions import (
    ADMINISTRATIVE_CAPABILITY,
    RESOURCE_LABELS,
    SUPERADMIN_RESERVED_PERMISSIONS,
)
from accounts import notifications
from audit import catalog
from audit.models import AuditLog
from notices.events import announce
from notices.realtime import close_connections
from outbox.models import OutboxEntry

ROLE_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*$'
PERMISSION_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*\.[A-Z]+(_[A-Z]+)*$'
INSTITUTIONAL_EMAIL_DOMAIN = 'ifnmg.edu.br'
USERNAME_TAKEN_MESSAGE = 'Este nome de usuário já pertence a outro usuário. Use outro nome de usuário.'
UNCHANGED = object()
"""Ausência de valor em uma operação, distinta de um valor vazio que exclui o dado."""


def normalize_username(value):
    """Apara e reduz espaços sem mudar caixa nem acentos, que precisam casar com dados externos."""
    return ' '.join((value or '').split()) or None


class AdministrativeContinuityViolation(ValidationError):
    def __init__(self, message=None):
        super().__init__(
            message
            or 'Operação recusada: o sistema ficaria sem nenhum usuário ativo '
            'com capacidade administrativa. Antes, garanta que outro usuário ativo '
            'tenha as permissões de gestão de usuários.',
            code='administrative_continuity',
        )


class SuperadminOnlyOperation(ValidationError):
    def __init__(self, message=None):
        super().__init__(
            message or 'Somente um superadmin ativo pode alterar o e-mail de um superadmin.',
            code='superadmin_only',
        )


def validate_institutional_email(value):
    """Recusa o e-mail fora do domínio institucional, sem diferenciar maiúsculas e minúsculas."""
    if not (value or '').strip().lower().endswith(f'@{INSTITUTIONAL_EMAIL_DOMAIN}'):
        raise ValidationError(
            f'Este e-mail não é institucional. Use um e-mail terminado em @{INSTITUTIONAL_EMAIL_DOMAIN}.',
            code='institutional_email',
        )


def role_required_error():
    return ValidationError({'role': 'Informe o perfil.'}, code='required')


ROLE_NOT_COVERED_MESSAGE = 'Somente quem já tem todas as permissões deste perfil pode atribuí-lo.'
OWN_USERNAME_MESSAGE = 'O próprio nome de usuário só pode ser alterado por outro usuário com permissão para isso.'
ACCOUNT_NOT_COVERED_MESSAGE = (
    'Somente quem já tem todas as permissões deste usuário pode alterar o e-mail, '
    'o nome de usuário, o perfil ou a situação dele.'
)
SUPERADMIN_ACCOUNT_MESSAGE = (
    'Somente um superadmin ativo pode alterar o nome de usuário, o perfil ou a situação de um superadmin.'
)


class InsufficientAuthority(ValidationError):
    def __init__(self, message, field=None):
        error = ValidationError(message, code='insufficient_authority')
        super().__init__({field: error} if field else error)


def is_active_superadmin(user):
    return user.is_active and user.is_superadmin


def check_role_assignable(executor, role):
    """Recusa perfil com permissão que o executor não tem; `None` é operação fora da web."""
    if executor is None or is_active_superadmin(executor):
        return
    codes = set(role.permissions.values_list('code', flat=True)) - SUPERADMIN_RESERVED_PERMISSIONS
    if not executor.covers(codes):
        raise InsufficientAuthority(ROLE_NOT_COVERED_MESSAGE, 'role')


def teacher_link_change(previous, current):
    """Docentes que a troca de nome de usuário desliga e liga, em destaque na auditoria por mudar o escopo."""
    if (previous or '').casefold() == (current or '').casefold():
        return None
    Teacher = apps.get_model('schedule', 'Teacher')
    names = {
        key: Teacher.objects.filter(name__iexact=value).values_list('name', flat=True).first() if value else None
        for key, value in (('docente_desligado', previous), ('docente_ligado', current))
    }
    return {key: value for key, value in names.items() if value} or None


def check_account_manageable(executor, target, field=None):
    """Recusa alterar conta com permissão que o executor não tem; superadmin só por superadmin ativo."""
    if executor is None or is_active_superadmin(executor):
        return
    if target.is_superadmin:
        raise InsufficientAuthority(SUPERADMIN_ACCOUNT_MESSAGE, field)
    if not executor.covers(target.granted_permissions()):
        raise InsufficientAuthority(ACCOUNT_NOT_COVERED_MESSAGE, field)


class ReservedPermissionNotGrantable(ValidationError):
    def __init__(self, codes):
        super().__init__(
            'Permissões reservadas ao superadmin não podem ser concedidas a perfis: '
            + ', '.join(sorted(codes))
            + '.',
            code='reserved_permission',
        )


class RoleInUse(ValidationError):
    def __init__(self, count):
        linked = '1 usuário vinculado' if count == 1 else f'{count} usuários vinculados'
        super().__init__(
            f'O perfil não pode ser excluído porque tem {linked}. '
            'Troque o perfil desses usuários antes de excluí-lo.',
            code='role_in_use',
            params={'count': count},
        )


def lock_active_users():
    list(
        User.objects.filter(is_active=True)
        .order_by('pk')
        .select_for_update()
        .values_list('pk', flat=True)
    )


def ensure_administrative_continuity():
    if not User.objects.with_administrative_capability().exists():
        raise AdministrativeContinuityViolation()


_continuity_deferred = ContextVar('continuity_deferred', default=False)


@contextmanager
def deferred_administrative_continuity():
    """Adia a verificação da continuidade administrativa para quem abriu o bloco, como na importação."""
    token = _continuity_deferred.set(True)
    try:
        yield
    finally:
        _continuity_deferred.reset(token)


@contextmanager
def administrative_continuity():
    with transaction.atomic():
        lock_active_users()
        yield
        if not _continuity_deferred.get():
            ensure_administrative_continuity()


def grantable_permissions(permissions):
    codes = {
        permission.code if isinstance(permission, Permission) else permission
        for permission in permissions
    }
    reserved = codes & SUPERADMIN_RESERVED_PERMISSIONS
    if reserved:
        raise ReservedPermissionNotGrantable(reserved)
    found = list(Permission.objects.filter(code__in=codes))
    missing = codes - {permission.code for permission in found}
    if missing:
        raise ValidationError(
            {'permissions': 'Permissões inexistentes no catálogo: ' + ', '.join(sorted(missing)) + '.'},
            code='unknown_permission',
        )
    return found


USER_STATUS_FILTERS = {'ativos': True, 'inativos': False}


class UserQuerySet(models.QuerySet):
    def search(self, term='', status=''):
        """Filtra pelo termo, sem diferenciar caixa, e pela situação ativos ou inativos."""
        queryset = self
        if term:
            queryset = queryset.filter(
                models.Q(name__icontains=term)
                | models.Q(email__icontains=term)
                | models.Q(username__icontains=term),
            )
        if status in USER_STATUS_FILTERS:
            queryset = queryset.filter(is_active=USER_STATUS_FILTERS[status])
        return queryset

    def with_permission(self, code):
        """Usuários ativos com a permissão, pela mesma regra de `User.has_perm`."""
        by_role = models.Q(roles__permissions__code=code)
        if code in SUPERADMIN_RESERVED_PERMISSIONS:
            by_role = models.Q(pk__in=[])
        return self.filter(models.Q(is_superadmin=True) | by_role, is_active=True).distinct()

    def with_administrative_capability(self):
        return (
            self.filter(is_active=True)
            .annotate(
                administrative_permission_count=models.Count(
                    'roles__permissions',
                    filter=models.Q(roles__permissions__code__in=ADMINISTRATIVE_CAPABILITY),
                    distinct=True,
                ),
            )
            .filter(
                models.Q(is_superadmin=True)
                | models.Q(administrative_permission_count=len(ADMINISTRATIVE_CAPABILITY)),
            )
        )


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    @classmethod
    def normalize_email(cls, email):
        return (email or '').strip().lower()

    def register(self, email, name, role, username=None, executor=None):
        """Cadastra sem senha e enfileira o link no outbox na mesma transação."""
        if role is None:
            raise role_required_error()
        check_role_assignable(executor, role)
        try:
            validate_institutional_email(email)
        except ValidationError as error:
            raise ValidationError({'email': error.error_list}) from None
        user = self.model(
            email=self.normalize_email(email),
            name=(name or '').strip(),
            username=username,
            is_active=True,
            is_superadmin=False,
        )
        user.set_unusable_password()
        user.full_clean()
        with transaction.atomic(using=self.db):
            user.save(using=self.db)
            UserRole.objects.using(self.db).create(user=user, role=role)
            OutboxEntry.objects.using(self.db).enqueue(PASSWORD_LINK, user.pk)
            AuditLog.objects.record(
                catalog.CREATE,
                catalog.USER,
                resource_id=user.pk,
                new_values={
                    'email': user.email,
                    'name': user.name,
                    'username': user.username,
                    'role': role.code,
                },
            )
        return user

    def create_superadmin(self, email, name, password):
        """Cria sem perfil: o acesso do superadmin vem do atributo, e não das permissões de um perfil."""
        user = self.model(
            email=self.normalize_email(email),
            name=(name or '').strip(),
            is_active=True,
            is_superadmin=True,
        )
        user.set_password(password)
        user.full_clean()
        with transaction.atomic(using=self.db):
            user.save(using=self.db)
            AuditLog.objects.record(
                catalog.CREATE,
                catalog.USER,
                resource_id=user.pk,
                new_values={'email': user.email, 'name': user.name, 'superadmin': True},
            )
        return user


class User(AbstractBaseUser):
    """Usuário autenticado pelo e-mail; `username` é identificador de domínio, e não credencial."""

    email = models.EmailField('e-mail', max_length=254, unique=True)
    name = models.CharField('nome', max_length=150)
    username = models.CharField('nome de usuário', max_length=150, null=True, blank=True)
    is_active = models.BooleanField('ativo', default=True)
    is_superadmin = models.BooleanField('superadmin', default=False)
    session_epoch = models.PositiveIntegerField('geração das sessões', default=0)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    roles = models.ManyToManyField(
        'Role',
        through='UserRole',
        related_name='users',
        verbose_name='perfis',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='user_email_unique_ci',
                violation_error_message='Já existe um usuário com este e-mail.',
            ),
            models.UniqueConstraint(
                Lower('username'),
                name='user_username_unique_ci',
                violation_error_message=USERNAME_TAKEN_MESSAGE,
            ),
        ]

    def __str__(self):
        return self.email

    def clean(self):
        """Confere a unicidade do nome de usuário sem caixa, que o `unique=True` não alcança."""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)
        self.username = normalize_username(self.username)
        if self.username is None:
            return
        taken = self.__class__.objects.filter(username__iexact=self.username)
        if self.pk is not None:
            taken = taken.exclude(pk=self.pk)
        if taken.exists():
            raise ValidationError({'username': ValidationError(USERNAME_TAKEN_MESSAGE, code='username_taken')})

    def effective_permissions(self):
        if not self.is_active or self.pk is None:
            return frozenset()
        if not hasattr(self, '_effective_permissions_cache'):
            if self.is_superadmin:
                codes = Permission.objects.values_list('code', flat=True)
            else:
                codes = (
                    Permission.objects.filter(roles__users=self)
                    .exclude(code__in=SUPERADMIN_RESERVED_PERMISSIONS)
                    .values_list('code', flat=True)
                    .distinct()
                )
            self._effective_permissions_cache = frozenset(codes)
        return self._effective_permissions_cache

    def _get_session_auth_hash(self, secret=None):
        """Na geração 0, o hash padrão do Django; depois, a geração entra no hash e derruba as sessões anteriores."""
        if not self.session_epoch:
            return super()._get_session_auth_hash(secret)
        key_salt = 'accounts.models.User.get_session_auth_hash'
        return salted_hmac(key_salt, f'{self.password}:{self.session_epoch}', secret=secret, algorithm='sha256').hexdigest()

    def end_sessions_if_changed_by_another(self, executor):
        """Encerra as sessões da conta alterada por outra pessoa, em qualquer backend de sessão."""
        if executor is not None and executor.pk == self.pk:
            return
        type(self).objects.filter(pk=self.pk).update(session_epoch=models.F('session_epoch') + 1)
        self.session_epoch = type(self).objects.values_list('session_epoch', flat=True).get(pk=self.pk)

    def granted_permissions(self):
        """Permissões que a conta concede quando ativa; o superadmin concede também as reservadas."""
        if self.is_superadmin:
            return frozenset(Permission.objects.values_list('code', flat=True)) | SUPERADMIN_RESERVED_PERMISSIONS
        return frozenset(
            Permission.objects.filter(roles__users=self)
            .exclude(code__in=SUPERADMIN_RESERVED_PERMISSIONS)
            .values_list('code', flat=True)
        )

    def covers(self, codes):
        """Diz se o usuário ativo tem todas as permissões de `codes`."""
        if not self.is_active:
            return False
        return self.is_superadmin or set(codes) <= self.effective_permissions()

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superadmin:
            return True
        return perm in self.effective_permissions()

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        if not self.is_active:
            return False
        if self.is_superadmin:
            return True
        prefix = f'{app_label}.'
        return any(code.startswith(prefix) for code in self.effective_permissions())

    @property
    def role(self):
        return self.roles.first()

    def has_administrative_capability(self):
        return self.has_perms(ADMINISTRATIVE_CAPABILITY)

    def change_role(self, role, executor=None):
        if role is None:
            raise role_required_error()
        check_role_assignable(executor, role)
        check_account_manageable(executor, self, 'role')
        with administrative_continuity():
            previous = self.role
            UserRole.objects.update_or_create(user=self, defaults={'role': role})
            if previous is None or previous.pk != role.pk:
                self.end_sessions_if_changed_by_another(executor)
            AuditLog.objects.record_changes(
                catalog.USER,
                self.pk,
                {'role': previous.code if previous else None},
                {'role': role.code},
            )
            if previous is None or previous.pk != role.pk:
                announce(notifications.ROLE_CHANGED, user=self, role=role)
        self.__dict__.pop('_effective_permissions_cache', None)

    def update_details(self, executor, name, email, username=UNCHANGED):
        """Nome de usuário omitido fica como está; vazio, é excluído."""
        name = (name or '').strip()
        email = type(self).objects.normalize_email(email)
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if (
                email != current.email
                and current.is_superadmin
                and not (executor.is_active and executor.is_superadmin)
            ):
                raise SuperadminOnlyOperation()
            changes_username = username is not UNCHANGED and normalize_username(username) != current.username
            if changes_username and executor.pk == current.pk and not is_active_superadmin(executor):
                raise InsufficientAuthority(OWN_USERNAME_MESSAGE, 'username')
            if email != current.email or changes_username:
                check_account_manageable(executor, current, 'email' if email != current.email else 'username')
            previous = (self.name, self.email, self.username)
            self.name, self.email = name, email
            if username is not UNCHANGED:
                self.username = username
            try:
                self.full_clean()
                self.save(update_fields=['name', 'email', 'username'])
                EmailAddress.objects.filter(user=self).exclude(email__iexact=self.email).delete()
                AuditLog.objects.record_changes(
                    catalog.USER,
                    self.pk,
                    {'name': previous[0], 'email': previous[1], 'username': previous[2]},
                    {'name': self.name, 'email': self.email, 'username': self.username},
                    metadata=teacher_link_change(previous[2], self.username),
                )
                if self.email != previous[1]:
                    self.end_sessions_if_changed_by_another(executor)
            except BaseException:
                self.name, self.email, self.username = previous
                raise

    def deactivate(self, executor=None):
        check_account_manageable(executor, self)
        with transaction.atomic():
            changed = self.is_active
            self._apply_guarded(is_active=False)
            if changed:
                AuditLog.objects.record(catalog.DEACTIVATE, catalog.USER, resource_id=self.pk)
                close_connections(self.pk)

    def reactivate(self, executor=None):
        check_account_manageable(executor, self)
        with transaction.atomic():
            changed = not self.is_active
            self._apply(is_active=True)
            if changed:
                AuditLog.objects.record(catalog.ACTIVATE, catalog.USER, resource_id=self.pk)

    def set_superadmin(self, value):
        with transaction.atomic():
            previous = self.is_superadmin
            if value:
                self._apply(is_superadmin=True)
            else:
                self._apply_guarded(is_superadmin=False)
            AuditLog.objects.record_changes(
                catalog.USER, self.pk, {'superadmin': previous}, {'superadmin': value},
            )

    def _apply(self, **values):
        previous = {field: getattr(self, field) for field in values}
        for field, value in values.items():
            setattr(self, field, value)
        try:
            self.save(update_fields=list(values))
        except BaseException:
            for field, value in previous.items():
                setattr(self, field, value)
            raise
        finally:
            self.__dict__.pop('_effective_permissions_cache', None)

    def _apply_guarded(self, **values):
        previous = {field: getattr(self, field) for field in values}
        try:
            with administrative_continuity():
                self._apply(**values)
        except BaseException:
            for field, value in previous.items():
                setattr(self, field, value)
            raise


class RoleManager(models.Manager):
    def create_role(self, code, name, description='', permissions=()):
        role = self.model(
            code=code or '',
            name=(name or '').strip(),
            description=description or '',
        )
        role.full_clean()
        granted = grantable_permissions(permissions)
        with transaction.atomic(using=self.db):
            role.save(using=self.db)
            RolePermission.objects.using(self.db).bulk_create(
                RolePermission(role=role, permission=permission) for permission in granted
            )
            AuditLog.objects.record(
                catalog.CREATE,
                catalog.ROLE,
                resource_id=role.pk,
                new_values={
                    'code': role.code,
                    'name': role.name,
                    'description': role.description,
                    'permissions': sorted(permission.code for permission in granted),
                },
            )
        return role


class Role(models.Model):
    code = models.CharField(
        'código',
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                ROLE_CODE_PATTERN,
                'Use letras maiúsculas sem acento, com palavras separadas por "_".',
            ),
        ],
    )
    name = models.CharField('nome', max_length=100)
    description = models.TextField('descrição', blank=True)
    permissions = models.ManyToManyField(
        'Permission',
        through='RolePermission',
        related_name='roles',
        verbose_name='permissões',
    )

    class Meta:
        verbose_name = 'perfil'
        verbose_name_plural = 'perfis'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=ROLE_CODE_PATTERN),
                name='role_code_format',
                violation_error_message='Código de perfil fora do formato.',
            ),
            models.UniqueConstraint(
                Lower('name'),
                name='role_name_unique_ci',
                violation_error_message='Já existe um perfil com este nome.',
            ),
        ]

    def __str__(self):
        return self.name

    objects = RoleManager()

    def clean(self):
        super().clean()
        self.name = (self.name or '').strip()

    def update_details(self, name, description):
        previous = (self.name, self.description)
        self.name, self.description = (name or '').strip(), description or ''
        try:
            self.full_clean()
            self.save(update_fields=['name', 'description'])
            AuditLog.objects.record_changes(
                catalog.ROLE,
                self.pk,
                {'name': previous[0], 'description': previous[1]},
                {'name': self.name, 'description': self.description},
            )
        except BaseException:
            self.name, self.description = previous
            raise

    def set_permissions(self, permissions):
        granted = {permission.code: permission for permission in grantable_permissions(permissions)}
        with transaction.atomic():
            lock_active_users()
            Role.objects.select_for_update(no_key=True).filter(pk=self.pk).get()
            current = set(self.permissions.values_list('code', flat=True))
            removed = current - granted.keys()
            added = granted.keys() - current
            RolePermission.objects.filter(role=self, permission__code__in=removed).delete()
            RolePermission.objects.bulk_create(
                RolePermission(role=self, permission=granted[code]) for code in added
            )
            AuditLog.objects.record_changes(
                catalog.ROLE,
                self.pk,
                {'permissions': sorted(current)},
                {'permissions': sorted(granted)},
            )
            if removed & ADMINISTRATIVE_CAPABILITY:
                ensure_administrative_continuity()

    def delete_role(self):
        with transaction.atomic():
            role = Role.objects.select_for_update().get(pk=self.pk)
            count = role.user_roles.count()
            if count:
                raise RoleInUse(count)
            AuditLog.objects.record(
                catalog.DELETE,
                catalog.ROLE,
                resource_id=role.pk,
                old_values={'code': role.code, 'name': role.name, 'description': role.description},
            )
            role.delete()


class Permission(models.Model):
    code = models.CharField(
        'código',
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(PERMISSION_CODE_PATTERN, 'Use o formato RECURSO.ACAO.'),
        ],
    )
    description = models.CharField('descrição', max_length=255)

    class Meta:
        verbose_name = 'permissão'
        verbose_name_plural = 'permissões'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=PERMISSION_CODE_PATTERN),
                name='permission_code_format',
                violation_error_message='Código de permissão fora do formato RECURSO.ACAO.',
            ),
        ]

    def __str__(self):
        return self.code

    @property
    def resource(self):
        return self.code.partition('.')[0]

    @property
    def resource_label(self):
        """Nome do recurso para a interface, com o próprio código quando não há nome."""
        return RESOURCE_LABELS.get(self.resource, self.resource)

    @property
    def action(self):
        return self.code.partition('.')[2]


class UserRole(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='usuário',
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='user_roles',
        verbose_name='perfil',
    )

    class Meta:
        verbose_name = 'perfil do usuário'
        verbose_name_plural = 'perfis dos usuários'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role'],
                name='user_role_unique',
            ),
            models.UniqueConstraint(
                fields=['user'],
                name='user_role_one_per_user',
                violation_error_message='O usuário já possui um perfil.',
            ),
        ]

    def __str__(self):
        return f'{self.user} → {self.role}'


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='perfil',
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='permissão',
    )

    class Meta:
        verbose_name = 'permissão do perfil'
        verbose_name_plural = 'permissões dos perfis'
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'permission'],
                name='role_permission_unique',
            ),
        ]

    def __str__(self):
        return f'{self.role} → {self.permission}'
