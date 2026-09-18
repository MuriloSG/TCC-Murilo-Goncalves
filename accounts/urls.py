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
]
