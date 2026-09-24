"""Rotas das notificações.

A autenticação é exigida aqui, com login_required. As notificações são sempre as do
próprio usuário, por isso nenhuma destas rotas declara permissão.
"""

from django.contrib.auth.decorators import login_required
from django.urls import path

from notices import views

urlpatterns = [
    path(
        'notificacoes/<int:pk>/abrir/',
        login_required(views.NotificationOpenView.as_view()),
        name='notification_open',
    ),
    path(
        'notificacoes/lidas/',
        login_required(views.NotificationsReadAllView.as_view()),
        name='notifications_read_all',
    ),
]
