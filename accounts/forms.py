from django import forms

from accounts.models import Role


def role_choice_field():
    return forms.ModelChoiceField(
        label='Perfil',
        queryset=Role.objects.order_by('name'),
        empty_label='Selecione o perfil',
    )


class UserCreateForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=254)
    role = role_choice_field()


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

