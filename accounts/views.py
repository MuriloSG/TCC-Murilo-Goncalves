
from allauth.account import views as allauth_views
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from audit import catalog
from imports.views import (
    ImportConfirmView,
    ImportDetailView,
    ImportDiscardView,
    ImportListView,
    ImportScreens,
    ImportTemplateView,
    ImportUploadView,
)
from ui.pagination import paginate
from ui.views import ModalView

from accounts import permissions
from accounts.forms import (
    RoleCreateForm,
    RolePermissionsForm,
    RoleUpdateForm,
    UserCreateForm,
    UserFilterForm,
    UserRoleForm,
    UserUpdateForm,
)
from accounts.imports import UserImport, concluded_message
from accounts.models import Role, User
from accounts.utils import add_operation_error

class LogoutView(allauth_views.LogoutView):
    """Saída do sistema, com a confirmação em modal quando pedida pelo htmx.

    O POST continua sendo o envio comum do formulário, e o allauth redireciona
    para a página de login.
    """

    modal_template_name = 'account/logout_modal.html'

    def get_template_names(self):
        if self.request.htmx:
            return [self.modal_template_name]
        return super().get_template_names()


class HomeView(TemplateView):
    template_name = 'accounts/home.html'


class OperationFormView(ModalView, FormView):
    """Formulário que executa uma operação do model, aberto em modal (D16).

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


class ConfirmedActionView(ModalView, TemplateView):
    """Mostra a confirmação no GET e executa a operação só no POST (D13, D22).

    As recusas das regras de negócio viram mensagens de erro, sem alterar dados.
    A confirmação abre em modal (D16).
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
            return self.redirect_to(self.get_failure_url())
        return self.redirect_to(self.get_success_url())


class UserListView(ListView):
    """Lista de usuários com busca e filtro pela URL.

    Quando o formulário de filtros pede pelo htmx, responde só com a tabela e o
    rodapé, o alvo da troca.
    """

    permission_required = permissions.USER_VIEW
    audit_resource = catalog.USER
    template_name = 'accounts/user_list.html'
    table_template_name = 'accounts/partials/user_table.html'
    table_target = 'tabela-usuarios'
    context_object_name = 'users'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters = UserFilterForm(request.GET)
        self.term, self.status = self.filters.criteria()

    def get_queryset(self):
        return User.objects.search(self.term, self.status).prefetch_related('roles').order_by('name', 'email')

    def get_template_names(self):
        if self.request.htmx and self.request.htmx.target == self.table_target:
            return [self.table_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            filters=self.filters,
            filtered=bool(self.term) or self.status != 'todos',
            total=User.objects.count(),
            table_target=self.table_target,
            **kwargs,
        )
        context['page'] = paginate(self.request, self.object_list)
        context['users'] = context['page'].object_list
        return context


class UserCreateView(OperationFormView):
    permission_required = permissions.USER_CREATE
    audit_resource = catalog.USER
    template_name = 'accounts/user_form.html'
    modal_template_name = 'accounts/user_form_modal.html'
    success_url = reverse_lazy('user_list')
    form_class = UserCreateForm
    title = 'Cadastrar usuário'
    submit_label = 'Cadastrar'

    def perform(self, data):
        user = User.objects.register(email=data['email'], name=data['name'], role=data['role'])
        messages.success(
            self.request,
            f'Usuário {user.email} cadastrado. O link para definir a senha será enviado para {user.email}.',
        )


class UserUpdateView(OperationFormView):
    permission_required = permissions.USER_EDIT
    audit_resource = catalog.USER
    model = User
    template_name = 'accounts/user_form.html'
    modal_template_name = 'accounts/user_form_modal.html'
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
    audit_resource = catalog.USER
    model = User
    template_name = 'accounts/user_form.html'
    modal_template_name = 'accounts/user_form_modal.html'
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
    audit_resource = catalog.USER
    model = User
    template_name = 'accounts/user_status_confirm.html'
    modal_template_name = 'accounts/user_status_modal.html'
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
    audit_resource = catalog.ROLE
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count('user_roles')).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = paginate(self.request, self.object_list)
        context['roles'] = context['page'].object_list
        return context


class RoleDetailView(DetailView):
    permission_required = permissions.ROLE_VIEW
    audit_resource = catalog.ROLE
    template_name = 'accounts/role_detail.html'
    context_object_name = 'role'

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count('user_roles'))

    def get_context_data(self, **kwargs):
        return super().get_context_data(permissions=self.object.permissions.order_by('code'), **kwargs)


class RoleFormView(OperationFormView):
    audit_resource = catalog.ROLE
    model = Role
    template_name = 'accounts/role_form.html'
    modal_template_name = 'accounts/role_form_modal.html'

    def get_success_url(self):
        return reverse('role_detail', args=[self.target.pk])

    def get_close_url(self):
        return reverse('role_detail', args=[self.target.pk]) if self.target else reverse('role_list')


class RoleCreateView(RoleFormView):
    """Primeira etapa da criação. Depois dela, as permissões do perfil criado."""

    permission_required = permissions.ROLE_CREATE
    form_class = RoleCreateForm
    title = 'Criar perfil'
    submit_label = 'Criar perfil'
    continues_in_modal = True
    extra_context = {'step': 1}

    def get_success_url(self):
        return reverse('role_permissions', args=[self.target.pk]) + '?etapa=2'

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
    submit_label = 'Salvar permissões'

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {'target': self.target}

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            user_count=self.target.user_roles.count(),
            step=2 if self.request.GET.get('etapa') == '2' else None,
            **kwargs,
        )

    def perform(self, data):
        self.target.set_permissions(data['permissions'])
        messages.success(self.request, f'Permissões do perfil {self.target.code} atualizadas.')


class RoleDeleteView(ConfirmedActionView):
    permission_required = permissions.ROLE_DELETE
    audit_resource = catalog.ROLE
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    modal_template_name = 'accounts/role_delete_modal.html'
    success_url = reverse_lazy('role_list')

    def get_failure_url(self):
        return reverse('role_detail', args=[self.target.pk])

    def get_close_url(self):
        return self.get_failure_url()

    def perform(self):
        code = self.target.code
        self.target.delete_role()
        messages.success(self.request, f'Perfil {code} excluído.')


USER_IMPORT_SCREENS = ImportScreens(
    definition=UserImport(),
    url_prefix='user_import',
    section_title='Usuários',
    section_url_name='user_list',
    list_title='Importações de usuários',
    upload_title='Importar usuários',
    template_file_name='modelo-importacao-usuarios.csv',
    empty_message='Nenhuma importação de usuários.',
    concluded_message=concluded_message,
)


class UserImportListView(ImportListView):
    permission_required = permissions.USER_IMPORT
    audit_resource = catalog.USER_IMPORT
    screens = USER_IMPORT_SCREENS


class UserImportUploadView(ImportUploadView):
    permission_required = permissions.USER_IMPORT
    audit_resource = catalog.USER_IMPORT
    screens = USER_IMPORT_SCREENS


class UserImportTemplateView(ImportTemplateView):
    permission_required = permissions.USER_IMPORT
    screens = USER_IMPORT_SCREENS


class UserImportDetailView(ImportDetailView):
    permission_required = permissions.USER_IMPORT
    audit_resource = catalog.USER_IMPORT
    screens = USER_IMPORT_SCREENS


class UserImportConfirmView(ImportConfirmView):
    permission_required = permissions.USER_IMPORT
    screens = USER_IMPORT_SCREENS


class UserImportDiscardView(ImportDiscardView):
    permission_required = permissions.USER_IMPORT
    audit_resource = catalog.USER_IMPORT
    screens = USER_IMPORT_SCREENS
