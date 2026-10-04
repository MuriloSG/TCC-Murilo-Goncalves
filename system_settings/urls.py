"""Rotas das configurações do sistema.

A autenticação é exigida aqui, com login_required, e a permissão é declarada em
cada view e verificada pelo PermissionMiddleware.
"""

from django.contrib.auth.decorators import login_required
from django.urls import path

from system_settings import views

urlpatterns = [
    path(
        'configuracoes/email/',
        login_required(views.SmtpDetailView.as_view()),
        name='settings_email',
    ),
    path(
        'configuracoes/email/editar/',
        login_required(views.SmtpUpdateView.as_view()),
        name='settings_email_update',
    ),
    path(
        'configuracoes/email/excluir/',
        login_required(views.SmtpClearView.as_view()),
        name='settings_email_clear',
    ),
]
