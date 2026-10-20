from allauth.account import views as account_views
from django.urls import include, path, re_path

from accounts.views import LogoutView

urlpatterns = [
    path('', include('accounts.urls')),
    path('', include('audit.urls')),
    path('', include('notices.urls')),
    path('', include('schedule.urls')),
    path('', include('bookings.urls')),
    path('', include('panel.urls')),
    path('', include('reports.urls')),
    path('', include('system_settings.urls')),
    path('', include('tutorials.urls')),
    path('contas/login/', account_views.login, name='account_login'),
    path('contas/logout/', LogoutView.as_view(), name='account_logout'),
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
