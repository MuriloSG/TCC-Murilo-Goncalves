from contextlib import contextmanager

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower

from accounts.permissions import (
    ADMINISTRATIVE_CAPABILITY,
    SUPERADMIN_RESERVED_PERMISSIONS,
)

ROLE_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*$'
PERMISSION_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*\.[A-Z]+(_[A-Z]+)*$'


class AdministrativeContinuityViolation(ValidationError):
    def __init__(self, message=None):
        super().__init__(
            message
            or 'Operação recusada: o sistema ficaria sem nenhum usuário ativo '
            'com capacidade administrativa.',
            code='administrative_continuity',
        )


@contextmanager
def administrative_continuity():
    with transaction.atomic():
        list(
            User.objects.filter(is_active=True)
            .order_by('pk')
            .select_for_update()
            .values_list('pk', flat=True)
        )
        yield
        if not User.objects.with_administrative_capability().exists():
            raise AdministrativeContinuityViolation()


class UserQuerySet(models.QuerySet):
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


class User(AbstractBaseUser):
    email = models.EmailField('e-mail', max_length=254, unique=True)
    name = models.CharField('nome', max_length=150)
    is_active = models.BooleanField('ativo', default=True)
    is_superadmin = models.BooleanField('superadmin', default=False)
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
        ]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

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

    def has_administrative_capability(self):
        return self.has_perms(ADMINISTRATIVE_CAPABILITY)

    def deactivate(self):
        self._apply_guarded(is_active=False)

    def reactivate(self):
        self._apply(is_active=True)

    def set_superadmin(self, value):
        if value:
            self._apply(is_superadmin=True)
        else:
            self._apply_guarded(is_superadmin=False)

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
    is_system = models.BooleanField('perfil do sistema', default=False)
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

    def clean(self):
        super().clean()
        self.name = (self.name or '').strip()


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
