from django import forms

from accounts.models import Role


def role_choice_field():
    return forms.ModelChoiceField(
        label='Perfil',
        queryset=Role.objects.order_by('name'),
        empty_label='Selecione o perfil',
    )


class ModelOperationFormMixin:
    """Leva para o formulário os erros de validação lançados pelas operações do model."""

    def add_operation_error(self, error):
        if hasattr(error, 'error_dict'):
            for field, errors in error.error_dict.items():
                self.add_error(field if field in self.fields else None, errors)
        else:
            self.add_error(None, error)


class UserCreateForm(ModelOperationFormMixin, forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=254)
    role = role_choice_field()


class UserUpdateForm(ModelOperationFormMixin, forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=254)

    def __init__(self, *args, target, executor, **kwargs):
        kwargs.setdefault('initial', {'name': target.name, 'email': target.email})
        super().__init__(*args, **kwargs)
        # Só apresentação: a regra está em User.update_details (D16). Com readonly,
        # e não disabled, um e-mail forjado no POST chega ao model e é recusado com erro.
        if target.is_superadmin and not (executor.is_active and executor.is_superadmin):
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].help_text = 'Somente um superadmin pode alterar o e-mail de um superadmin.'


class UserRoleForm(ModelOperationFormMixin, forms.Form):
    role = role_choice_field()

    def __init__(self, *args, target, **kwargs):
        kwargs.setdefault('initial', {'role': target.role})
        super().__init__(*args, **kwargs)

