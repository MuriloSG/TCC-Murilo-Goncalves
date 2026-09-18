import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import FormView, ListView, TemplateView

from accounts import permissions
from accounts.adapters import send_password_link
from accounts.forms import UserCreateForm, UserRoleForm, UserUpdateForm
from accounts.models import User

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/home.html'


class UserListView(PermissionRequiredMixin, ListView):
    permission_required = permissions.USER_VIEW
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.prefetch_related('roles').order_by('name', 'email')


class TargetUserMixin:
    """Carrega o usuário alvo da rota só depois da verificação de acesso."""

    @cached_property
    def target(self):
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=self.target, **kwargs)


class UserFormView(PermissionRequiredMixin, FormView):
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    title = ''
    submit_label = 'Salvar'

    def get_context_data(self, **kwargs):
        return super().get_context_data(title=self.title, submit_label=self.submit_label, **kwargs)

    def form_valid(self, form):
        try:
            self.perform(form.cleaned_data)
        except ValidationError as error:
            form.add_operation_error(error)
            return self.form_invalid(form)
        return super().form_valid(form)


class UserCreateView(UserFormView):
    permission_required = permissions.USER_CREATE
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


class UserUpdateView(TargetUserMixin, UserFormView):
    permission_required = permissions.USER_EDIT
    form_class = UserUpdateForm
    title = 'Editar usuário'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target, 'executor': self.request.user}

    def perform(self, data):
        self.target.update_details(self.request.user, name=data['name'], email=data['email'])
        messages.success(self.request, f'Dados de {self.target.email} atualizados.')


class UserRoleView(TargetUserMixin, UserFormView):
    permission_required = permissions.USER_CHANGE_ROLE
    form_class = UserRoleForm
    title = 'Trocar perfil'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def perform(self, data):
        self.target.change_role(data['role'])
        messages.success(self.request, f'Perfil de {self.target.email} alterado para {data["role"]}.')


class UserStatusView(TargetUserMixin, PermissionRequiredMixin, TemplateView):
    """Confirma no GET e executa só no POST (D13)."""

    permission_required = permissions.USER_CHANGE_STATUS
    template_name = 'accounts/user_status_confirm.html'
    action = ''

    def get_context_data(self, **kwargs):
        return super().get_context_data(action=self.action, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            self.perform()
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        return redirect('user_list')


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
