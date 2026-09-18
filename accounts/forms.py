from django import forms

from accounts.models import Permission, Role
from accounts.permissions import SUPERADMIN_RESERVED_PERMISSIONS


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
    email = forms.EmailField(label='E-mail', max_length=254)
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
    email = forms.EmailField(label='E-mail', max_length=254)

    def __init__(self, *args, target, executor, **kwargs):
        kwargs.setdefault('initial', {'name': target.name, 'email': target.email})
        super().__init__(*args, **kwargs)
        if target.is_superadmin and not (executor.is_active and executor.is_superadmin):
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].help_text = 'Somente um superadmin pode alterar o e-mail de um superadmin.'


class UserRoleForm(forms.Form):
    role = role_choice_field()

    def __init__(self, *args, target, **kwargs):
        kwargs.setdefault('initial', {'role': target.role})
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
        widget=forms.CheckboxSelectMultiple,
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
        kwargs.setdefault('initial', {'name': target.name, 'description': target.description})
        super().__init__(*args, **kwargs)


class RolePermissionsForm(forms.Form):
    permissions = permission_choice_field()

    def __init__(self, *args, target, **kwargs):
        kwargs.setdefault('initial', {'permissions': list(target.permissions.values_list('code', flat=True))})
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget.choices = grantable_permission_choices()
