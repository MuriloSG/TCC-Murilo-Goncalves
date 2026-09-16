from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

ROLE_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*$'
PERMISSION_CODE_PATTERN = r'^[A-Z]+(_[A-Z]+)*\.[A-Z]+(_[A-Z]+)*$'


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        """Strip surrounding whitespace and lowercase the whole address."""
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
            # In this version each user has at most one role (D6).
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
