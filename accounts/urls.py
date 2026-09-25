"""Rotas da app accounts.

A autenticação é exigida aqui, com login_required. A permissão de cada view é
declarada nela, em permission_required, e aplicada pelo PermissionMiddleware (D14).
"""

from django.contrib.auth.decorators import login_required
from django.urls import path

from accounts import views

urlpatterns = [
    path('inicio/', login_required(views.HomeView.as_view()), name='home'),
    path('usuarios/', login_required(views.UserListView.as_view()), name='user_list'),
    path('usuarios/novo/', login_required(views.UserCreateView.as_view()), name='user_create'),
    path('usuarios/<int:pk>/editar/', login_required(views.UserUpdateView.as_view()), name='user_update'),
    path('usuarios/<int:pk>/perfil/', login_required(views.UserRoleView.as_view()), name='user_change_role'),
    path('usuarios/<int:pk>/desativar/', login_required(views.UserDeactivateView.as_view()), name='user_deactivate'),
    path('usuarios/<int:pk>/reativar/', login_required(views.UserReactivateView.as_view()), name='user_reactivate'),
    path('usuarios/importacoes/', login_required(views.UserImportListView.as_view()), name='user_import_list'),
    path('usuarios/importacoes/nova/', login_required(views.UserImportUploadView.as_view()), name='user_import_upload'),
    path(
        'usuarios/importacoes/modelo/',
        login_required(views.UserImportTemplateView.as_view()),
        name='user_import_template',
    ),
    path(
        'usuarios/importacoes/<int:pk>/',
        login_required(views.UserImportDetailView.as_view()),
        name='user_import_detail',
    ),
    path(
        'usuarios/importacoes/<int:pk>/confirmar/',
        login_required(views.UserImportConfirmView.as_view()),
        name='user_import_confirm',
    ),
    path(
        'usuarios/importacoes/<int:pk>/descartar/',
        login_required(views.UserImportDiscardView.as_view()),
        name='user_import_discard',
    ),
    path(
        'usuarios/importacoes/<int:pk>/excluir/',
        login_required(views.UserImportDeleteView.as_view()),
        name='user_import_delete',
    ),
    path('perfis/', login_required(views.RoleListView.as_view()), name='role_list'),
    path('perfis/novo/', login_required(views.RoleCreateView.as_view()), name='role_create'),
    path('perfis/<int:pk>/', login_required(views.RoleDetailView.as_view()), name='role_detail'),
    path('perfis/<int:pk>/editar/', login_required(views.RoleUpdateView.as_view()), name='role_update'),
    path('perfis/<int:pk>/permissoes/', login_required(views.RolePermissionsView.as_view()), name='role_permissions'),
    path('perfis/<int:pk>/excluir/', login_required(views.RoleDeleteView.as_view()), name='role_delete'),
]
