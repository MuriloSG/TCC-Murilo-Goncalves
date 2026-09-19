from allauth.account import forms as allauth_forms
from django import forms

from accounts.models import Permission, Role
from accounts.permissions import SUPERADMIN_RESERVED_PERMISSIONS
from ui.forms import GroupedCheckboxSelectMultiple


INVALID_EMAIL_MESSAGE = 'Informe um e-mail válido.'
PASSWORD_MISMATCH_MESSAGE = 'As duas senhas informadas são diferentes. Digite a mesma senha nos dois campos.'


def email_field():
    return forms.EmailField(label='E-mail', max_length=254, error_messages={'invalid': INVALID_EMAIL_MESSAGE})


def use_email_messages(field):
    """Aplica ao campo de e-mail de um formulário do allauth o rótulo e o erro do projeto (D5)."""
    field.label = 'E-mail'
    field.error_messages = field.error_messages | {'invalid': INVALID_EMAIL_MESSAGE}


class LoginForm(allauth_forms.LoginForm):
    """Login com os rótulos da tela de entrada (D14 da Change definir-identidade-visual).

    A ajuda do campo de senha, que o allauth usa para o link de recuperação, sai
    porque a tela já tem o link "Esqueci minha senha".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        use_email_messages(self.fields['login'])
        self.fields['login'].label = 'E-mail institucional'
        self.fields['login'].widget.attrs['placeholder'] = 'nome.sobrenome@ifnmg.edu.br'
        self.fields['password'].label = 'Senha'
        self.fields['password'].help_text = ''
        self.fields['password'].widget.attrs.pop('placeholder', None)
        self.fields['remember'].label = 'Manter conectado'


class PasswordResetForm(allauth_forms.ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        use_email_messages(self.fields['email'])


class PasswordResetKeyForm(allauth_forms.ResetPasswordKeyForm):
    """Definição de senha com a mensagem de senhas diferentes nas regras de texto.

    O clean do PasswordVerificationMixin do allauth é pulado porque a mensagem dele
    fala com o usuário na segunda pessoa. A comparação é a mesma.
    """

    def clean(self):
        cleaned_data = super(allauth_forms.PasswordVerificationMixin, self).clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', PASSWORD_MISMATCH_MESSAGE)
        return cleaned_data


def role_choice_field():
    return forms.ModelChoiceField(
        label='Perfil',
        queryset=Role.objects.order_by('name'),
        empty_label='Selecione o perfil',
    )


def clean_single_role(form):
    """Recusa o envio de mais de um perfil.

    O ModelChoiceField usaria só o último valor recebido, e o usuário seria gravado
    com um dos perfis em vez de a operação ser recusada.
    """
    if len(form.data.getlist(form.add_prefix('role'))) > 1:
        raise forms.ValidationError('Escolha exatamente um perfil.', code='multiple_roles')
    return form.cleaned_data['role']


class UserCreateForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    email = email_field()
    role = role_choice_field()

    def clean_role(self):
        return clean_single_role(self)


class UserUpdateForm(forms.Form):
    """Edição de nome e e-mail.

    Quando o alvo é superadmin e o executor não é superadmin ativo, o e-mail é
    exibido como somente leitura. Isso é só apresentação: a regra está em
    User.update_details (D16). O campo usa readonly, e não disabled, para que um
    e-mail forjado no POST chegue ao model e seja recusado com mensagem de erro.
    """

    name = forms.CharField(label='Nome', max_length=150)
    email = email_field()

    def __init__(self, *args, target, executor, **kwargs):
        kwargs['initial'] = {'name': target.name, 'email': target.email} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)
        if target.is_superadmin and not (executor.is_active and executor.is_superadmin):
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].help_text = 'Somente um superadmin pode alterar o e-mail de um superadmin.'


class UserFilterForm(forms.Form):
    """Busca e filtro da lista de usuários, recebidos pela URL (D1 da Change filtrar-lista-de-usuarios).

    Os nomes dos campos são os parâmetros da URL, em português, como os caminhos.
    Um valor inválido é descartado sem mensagem, e a lista trata o campo como vazio.
    """

    busca = forms.CharField(
        label='Buscar por nome ou e-mail',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'type': 'search', 'class': 'input', 'placeholder': 'Buscar por nome ou e-mail'}),
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

    def __init__(self, *args, target, **kwargs):
        kwargs['initial'] = {'role': target.role} | (kwargs.get('initial') or {})
        super().__init__(*args, **kwargs)

    def clean_role(self):
        return clean_single_role(self)



def grantable_permission_choices():
    """Permissões do catálogo que podem ser concedidas, agrupadas por recurso (D4, D21)."""
    groups = {}
    for permission in Permission.objects.exclude(code__in=SUPERADMIN_RESERVED_PERMISSIONS).order_by('code'):
        groups.setdefault(permission.resource, []).append(
            (permission.code, f'{permission.code} · {permission.description}'),
        )
    return list(groups.items())


def permission_choice_field():
    """Campo de permissões validado contra o catálogo inteiro.

    O widget só exibe as permissões concedíveis. Uma permissão reservada enviada
    no POST passa pelo campo e é recusada pela operação do model, que informa o
    motivo (D21).
    """
    return forms.ModelMultipleChoiceField(
        label='Permissões',
        queryset=Permission.objects.all(),
        to_field_name='code',
        required=False,
        widget=GroupedCheckboxSelectMultiple,
    )


class RoleCreateForm(forms.Form):
    code = forms.CharField(
        label='Código',
        max_length=50,
        help_text='Letras maiúsculas sem acento, com palavras separadas por "_". Não pode ser alterado depois.',
    )
    name = forms.CharField(label='Nome', max_length=100)
    description = forms.CharField(label='Descrição', required=False, widget=forms.Textarea)
    permissions = permission_choice_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget.choices = grantable_permission_choices()


class RoleUpdateForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=100)
    description = forms.CharField(label='Descrição', required=False, widget=forms.Textarea)

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
