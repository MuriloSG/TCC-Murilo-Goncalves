from django.urls import path

from accounts import views

urlpatterns = [
    path('inicio/', views.HomeView.as_view(), name='home'),
    path('usuarios/', views.UserListView.as_view(), name='user_list'),
    path('usuarios/novo/', views.UserCreateView.as_view(), name='user_create'),
    path('usuarios/<int:pk>/editar/', views.UserUpdateView.as_view(), name='user_update'),
    path('usuarios/<int:pk>/perfil/', views.UserRoleView.as_view(), name='user_change_role'),
    path('usuarios/<int:pk>/desativar/', views.UserDeactivateView.as_view(), name='user_deactivate'),
    path('usuarios/<int:pk>/reativar/', views.UserReactivateView.as_view(), name='user_reactivate'),
]
