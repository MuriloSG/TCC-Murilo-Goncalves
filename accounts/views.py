import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from accounts import permissions
from accounts.adapters import send_password_link
from accounts.forms import (
    RoleCreateForm,
    RolePermissionsForm,
    RoleUpdateForm,
    UserCreateForm,
    UserRoleForm,
    UserUpdateForm,
)
from accounts.models import Role, User
from accounts.utils import add_operation_error

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = 'accounts/home.html'


class OperationFormView(FormView):
    """Formulário que executa uma operação do model.

    Quando a rota tem `pk`, carrega o objeto alvo de `model`. As recusas das regras
    de negócio (ValidationError) voltam como erros do próprio formulário.
    """

    model = None
    target = None
    title = ''
    submit_label = 'Salvar'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if 'pk' in kwargs:
            self.target = get_object_or_404(self.model, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title=self.title, submit_label=self.submit_label, target=self.target, **kwargs,
        )

    def form_valid(self, form):
        try:
            self.perform(form.cleaned_data)
        except ValidationError as error:
            add_operation_error(form, error)
            return self.form_invalid(form)
        return super().form_valid(form)


class ConfirmedActionView(TemplateView):
    """Mostra a confirmação no GET e executa a operação só no POST (D13, D22).

    As recusas das regras de negócio viram mensagens de erro, sem alterar dados.
    """

    model = None
    success_url = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target = get_object_or_404(self.model, pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=self.target, **kwargs)

    def get_success_url(self):
        return self.success_url

    def get_failure_url(self):
        return self.get_success_url()

    def post(self, request, *args, **kwargs):
        try:
            self.perform()
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect(self.get_failure_url())
        return redirect(self.get_success_url())


class UserListView(ListView):
    permission_required = permissions.USER_VIEW
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.prefetch_related('roles').order_by('name', 'email')


class UserCreateView(OperationFormView):
    permission_required = permissions.USER_CREATE
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    form_class = UserCreateForm
    title = 'Cadastrar usuário'
    submit_label = 'Cadastrar'

    def perform(self, data):
        user = User.objects.register(email=data['email'], name=data['name'], role=data['role'])
        messages.success(self.request, f'Usuário {user.email} cadastrado.')
        transaction.on_commit(lambda: self.send_password_link(user))

    def send_password_link(self, user):
        try:
            sent = send_password_link(self.request, user.email)
        except Exception:
            logger.exception('Falha ao enviar o link de definição de senha para %s.', user.email)
            sent = False
        if sent:
            messages.info(self.request, f'O link para definir a senha foi enviado para {user.email}.')
        else:
            messages.warning(
                self.request,
                f'Não foi possível enviar o e-mail para {user.email}. O usuário foi cadastrado e pode '
                'pedir um novo link em "Esqueci minha senha", na página de login.',
            )


class UserUpdateView(OperationFormView):
    permission_required = permissions.USER_EDIT
    model = User
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    form_class = UserUpdateForm
    title = 'Editar usuário'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target, 'executor': self.request.user}

    def perform(self, data):
        self.target.update_details(self.request.user, name=data['name'], email=data['email'])
        messages.success(self.request, f'Dados de {self.target.email} atualizados.')


class UserRoleView(OperationFormView):
    permission_required = permissions.USER_CHANGE_ROLE
    model = User
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    form_class = UserRoleForm
    title = 'Trocar perfil'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def perform(self, data):
        self.target.change_role(data['role'])
        messages.success(self.request, f'Perfil de {self.target.email} alterado para {data["role"]}.')


class UserStatusView(ConfirmedActionView):
    permission_required = permissions.USER_CHANGE_STATUS
    model = User
    template_name = 'accounts/user_status_confirm.html'
    success_url = reverse_lazy('user_list')
    action = ''

    def get_context_data(self, **kwargs):
        return super().get_context_data(action=self.action, **kwargs)


class UserDeactivateView(UserStatusView):
    action = 'desativar'

    def perform(self):
        self.target.deactivate()
        messages.success(self.request, f'Usuário {self.target.email} desativado.')


class UserReactivateView(UserStatusView):
    action = 'reativar'

    def perform(self):
        self.target.reactivate()
        messages.success(self.request, f'Usuário {self.target.email} reativado.')


class RoleListView(ListView):
    permission_required = permissions.ROLE_VIEW
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count('user_roles')).order_by('name')


class RoleDetailView(DetailView):
    permission_required = permissions.ROLE_VIEW
    template_name = 'accounts/role_detail.html'
    context_object_name = 'role'

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count('user_roles'))

    def get_context_data(self, **kwargs):
        return super().get_context_data(permissions=self.object.permissions.order_by('code'), **kwargs)


class RoleFormView(OperationFormView):
    model = Role
    template_name = 'accounts/role_form.html'

    def get_success_url(self):
        return reverse('role_detail', args=[self.target.pk])


class RoleCreateView(RoleFormView):
    permission_required = permissions.ROLE_CREATE
    form_class = RoleCreateForm
    title = 'Criar perfil'
    submit_label = 'Criar'

    def perform(self, data):
        self.target = Role.objects.create_role(
            code=data['code'],
            name=data['name'],
            description=data['description'],
            permissions=data['permissions'],
        )
        messages.success(self.request, f'Perfil {self.target.code} criado.')


class RoleUpdateView(RoleFormView):
    permission_required = permissions.ROLE_EDIT
    form_class = RoleUpdateForm
    title = 'Editar perfil'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def perform(self, data):
        self.target.update_details(name=data['name'], description=data['description'])
        messages.success(self.request, f'Perfil {self.target.code} atualizado.')


class RolePermissionsView(RoleFormView):
    permission_required = permissions.ROLE_CHANGE_PERMISSIONS
    form_class = RolePermissionsForm
    title = 'Permissões do perfil'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def get_context_data(self, **kwargs):
        return super().get_context_data(user_count=self.target.user_roles.count(), **kwargs)

    def perform(self, data):
        self.target.set_permissions(data['permissions'])
        messages.success(self.request, f'Permissões do perfil {self.target.code} atualizadas.')


class RoleDeleteView(ConfirmedActionView):
    permission_required = permissions.ROLE_DELETE
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    success_url = reverse_lazy('role_list')

    def get_failure_url(self):
        return reverse('role_detail', args=[self.target.pk])

    def perform(self):
        code = self.target.code
        self.target.delete_role()
        messages.success(self.request, f'Perfil {code} excluído.')
