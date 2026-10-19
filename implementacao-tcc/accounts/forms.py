from allauth.account import forms as allauth_forms
from django import forms

from accounts.emails import PASSWORD_RESET
from accounts.models import Permission, Role, validate_institutional_email
from accounts.permissions import SUPERADMIN_RESERVED_PERMISSIONS
from accounts.utils import typed_email
from audit import catalog
from audit.models import AuditLog
from outbox.models import OutboxEntry
from ui.forms import GroupedCheckboxSelectMultiple


INVALID_EMAIL_MESSAGE = 'Informe um e-mail válido.'
PASSWORD_MISMATCH_MESSAGE = 'As duas senhas informadas são diferentes. Digite a mesma senha nos dois campos.'


def email_field():
    return forms.EmailField(label='E-mail', max_length=254, error_messages={'invalid': INVALID_EMAIL_MESSAGE})


def use_email_messages(field):
    """Aplica ao campo de e-mail de um formulário do allauth o rótulo e o erro do projeto."""
    field.label = 'E-mail'
    field.error_messages = field.error_messages | {'invalid': INVALID_EMAIL_MESSAGE}


class LoginForm(allauth_forms.LoginForm):
    """Login sem a ajuda do campo de senha, porque a tela já tem o link de recuperação."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        use_email_messages(self.fields['login'])
        self.fields['login'].label = 'E-mail institucional'
        self.fields['login'].widget.attrs['placeholder'] = ''
        self.fields['password'].label = 'Senha'
        self.fields['password'].help_text = ''
        self.fields['password'].widget.attrs.pop('placeholder', None)
        self.fields['remember'].label = 'Manter conectado'


class PasswordResetForm(allauth_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        use_email_messages(self.fields['email'])

    def save(self, request, **kwargs):
        """Enfileira o link no outbox e audita igual para e-mail existente ou não, para não revelar contas."""
        email = self.cleaned_data['email']
        for user in self.users:
            OutboxEntry.objects.enqueue(PASSWORD_RESET, user.pk)
        AuditLog.objects.record(
            catalog.PASSWORD_REQUESTED,
            catalog.AUTHENTICATION,
            metadata={'email': typed_email(self.cleaned_data.get('email'))},
        )
        return email


class PasswordResetKeyForm(allauth_forms.ResetPasswordKeyForm):
    """Pula o clean do allauth, cuja mensagem fala na segunda pessoa; a comparação é a mesma."""

    def clean(self):
        cleaned_data = super(allauth_forms.PasswordVerificationMixin, self).clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', PASSWORD_MISMATCH_MESSAGE)
        return cleaned_data


def username_field():
    """Nome de usuário opcional e livre; normalização e unicidade ficam no model."""
    return forms.CharField(
        label='Nome de usuário',
        max_length=150,
        required=False,
        help_text='Identificador do usuário em dados vindos de fora do sistema. Pode ficar em branco.',
    )


def role_choice_field():
    return forms.ModelChoiceField(
        label='Perfil',
        queryset=Role.objects.order_by('name'),
        empty_label='Selecione o perfil',
    )


def assignable_roles(executor):
    """Perfis cujas permissões o executor tem todas; a recusa com motivo fica no model."""
    roles = Role.objects.order_by('name')
    if executor.is_active and executor.is_superadmin:
        return roles
    missing = Permission.objects.exclude(code__in=executor.effective_permissions()).exclude(
        code__in=SUPERADMIN_RESERVED_PERMISSIONS,
    )
    return roles.exclude(permissions__in=missing)


def clean_single_role(form):
    """Recusa mais de um perfil, que o ModelChoiceField reduziria ao último valor."""
    if len(form.data.getlist(form.add_prefix('role'))) > 1:
        raise forms.ValidationError('Escolha exatamente um perfil.', code='multiple_roles')
    return form.cleaned_data['role']


class UserCreateForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    email = email_field()
    username = username_field()
    role = role_choice_field()

    def __init__(self, *args, executor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = assignable_roles(executor)

    def clean_email(self):
        validate_institutional_email(self.cleaned_data['email'])
        return self.cleaned_data['email']

    def clean_role(self):
        return clean_single_role(self)


class UserUpdateForm(forms.Form):
    """O e-mail de superadmin fica readonly, e não disabled, para que um POST forjado seja recusado pelo model."""

    name = forms.CharField(label='Nome', max_length=150)
    email = email_field()
    username = username_field()

    def __init__(self, *args, target, executor, **kwargs):
        current = {'name': target.name, 'email': target.email, 'username': target.username}
        kwargs['initial'] = current | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        if target.is_superadmin and not (executor.is_active and executor.is_superadmin):
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].help_text = 'Somente um superadmin pode alterar o e-mail de um superadmin.'


class UserFilterForm(forms.Form):
    """Filtros da lista de usuários pela URL; valor inválido é descartado sem mensagem."""

    busca = forms.CharField(
        label='Buscar por nome, e-mail ou nome de usuário',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar usuário'}),
    )
    situacao = forms.ChoiceField(
        label='Situação',
        choices=[('todos', 'Todas as situações'), ('ativos', 'Ativos'), ('inativos', 'Inativos')],
        required=False,
        widget=forms.Select(attrs={'class': 'input'}),
    )

    def criteria(self):
        """Devolve (termo, situação) válidos, com os valores inválidos trocados pelo padrão."""
        self.is_valid()
        return self.cleaned_data.get('busca', ''), self.cleaned_data.get('situacao') or 'todos'


class UserRoleForm(forms.Form):
    role = role_choice_field()

    def __init__(self, *args, target, executor, **kwargs):
        kwargs['initial'] = {'role': target.role} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = assignable_roles(executor)

    def clean_role(self):
        return clean_single_role(self)



def grantable_permission_choices():
    """Permissões concedíveis agrupadas pelo nome do recurso."""
    groups = {}
    for permission in Permission.objects.exclude(code__in=SUPERADMIN_RESERVED_PERMISSIONS).order_by('code'):
        groups.setdefault(permission.resource_label, []).append((permission.code, permission.description))
    return list(groups.items())


def permission_choice_field():
    """Valida contra o catálogo inteiro para que a permissão reservada seja recusada pelo model, com o motivo."""
    return forms.ModelMultipleChoiceField(
        label='Permissões',
        queryset=Permission.objects.all(),
        to_field_name='code',
        required=False,
        widget=GroupedCheckboxSelectMultiple,
    )


class RoleCreateForm(forms.Form):
    """Primeira etapa da criação de perfil; as permissões são escolhidas na tela seguinte."""

    code = forms.CharField(
        label='Código',
        max_length=50,
        help_text='Letras maiúsculas sem acento, com palavras separadas por "_". Não pode ser alterado depois.',
    )
    name = forms.CharField(label='Nome', max_length=100)
    description = forms.CharField(label='Descrição', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    permissions = permission_choice_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget = forms.MultipleHiddenInput()


class RoleUpdateForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=100)
    description = forms.CharField(label='Descrição', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, target, **kwargs):
        kwargs['initial'] = {'name': target.name, 'description': target.description} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)


class RolePermissionsForm(forms.Form):
    permissions = permission_choice_field()

    def __init__(self, *args, target, **kwargs):
        current = {'permissions': list(target.permissions.values_list('code', flat=True))}
        kwargs['initial'] = current | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget.choices = grantable_permission_choices()
