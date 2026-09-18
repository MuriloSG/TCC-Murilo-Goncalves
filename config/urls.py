from allauth.account import views as account_views
from django.urls import path, re_path

urlpatterns = [
    path('contas/login/', account_views.login, name='account_login'),
    path('contas/logout/', account_views.logout, name='account_logout'),
    path('contas/senha/recuperar/', account_views.password_reset, name='account_reset_password'),
    path(
        'contas/senha/recuperar/enviado/',
        account_views.password_reset_done,
        name='account_reset_password_done',
    ),
    path(
        'contas/senha/redefinir/concluido/',
        account_views.password_reset_from_key_done,
        name='account_reset_password_from_key_done',
    ),
    re_path(
        r'^contas/senha/redefinir/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$',
        account_views.password_reset_from_key,
        name='account_reset_password_from_key',
    ),
]
