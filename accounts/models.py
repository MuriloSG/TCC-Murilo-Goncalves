from contextlib import contextmanager

from allauth.account.models import EmailAddress
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


class SuperadminOnlyOperation(ValidationError):
    def __init__(self, message=None):
        super().__init__(
            message or 'Somente um superadmin ativo pode alterar o e-mail de um superadmin.',
            code='superadmin_only',
        )


def role_required_error():
    return ValidationError({'role': 'Informe o perfil.'}, code='required')


class ReservedPermissionNotGrantable(ValidationError):
    def __init__(self, codes):
        super().__init__(
            'Permissões reservadas ao superadmin não podem ser concedidas a perfis: '
            + ', '.join(sorted(codes))
            + '.',
            code='reserved_permission',
        )


class SystemRoleProtected(ValidationError):
    def __init__(self):
        super().__init__('Perfis do sistema não podem ser excluídos.', code='system_role')


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


@contextmanager
def administrative_continuity():
    with transaction.atomic():
        lock_active_users()
        yield
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

    def register(self, email, name, role):
        if role is None:
            raise role_required_error()
        user = self.model(
            email=self.normalize_email(email),
            name=(name or '').strip(),
            is_active=True,
            is_superadmin=False,
        )
        user.set_unusable_password()
        user.full_clean()
        with transaction.atomic(using=self.db):
            user.save(using=self.db)
            UserRole.objects.using(self.db).create(user=user, role=role)
        return user


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

    @property
    def role(self):
        return self.roles.first()

    def has_administrative_capability(self):
        return self.has_perms(ADMINISTRATIVE_CAPABILITY)

    def change_role(self, role):
        if role is None:
            raise role_required_error()
        with administrative_continuity():
            UserRole.objects.update_or_create(user=self, defaults={'role': role})
        self.__dict__.pop('_effective_permissions_cache', None)

    def update_details(self, executor, name, email):
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
            previous = (self.name, self.email)
            self.name, self.email = name, email
            try:
                self.full_clean()
                self.save(update_fields=['name', 'email'])
                EmailAddress.objects.filter(user=self).exclude(email__iexact=self.email).delete()
            except BaseException:
                self.name, self.email = previous
                raise

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


class RoleManager(models.Manager):
    def create_role(self, code, name, description='', permissions=()):
        role = self.model(
            code=code or '',
            name=(name or '').strip(),
            description=description or '',
            is_system=False,
        )
        role.full_clean()
        granted = grantable_permissions(permissions)
        with transaction.atomic(using=self.db):
            role.save(using=self.db)
            RolePermission.objects.using(self.db).bulk_create(
                RolePermission(role=role, permission=permission) for permission in granted
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
            if removed & ADMINISTRATIVE_CAPABILITY:
                ensure_administrative_continuity()

    def delete_role(self):
        with transaction.atomic():
            role = Role.objects.select_for_update().get(pk=self.pk)
            if role.is_system:
                raise SystemRoleProtected()
            count = role.user_roles.count()
            if count:
                raise RoleInUse(count)
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
