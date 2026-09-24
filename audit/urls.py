"""Rotas da consulta de auditoria.

A autenticação é exigida aqui, com login_required. A permissão de cada view é
declarada nela, em permission_required, e aplicada pelo PermissionMiddleware.
"""

from django.contrib.auth.decorators import login_required
from django.urls import path

from audit import views

urlpatterns = [
    path('auditoria/', login_required(views.AuditLogListView.as_view()), name='audit_log_list'),
    path('auditoria/<int:pk>/', login_required(views.AuditLogDetailView.as_view()), name='audit_log_detail'),
    path(
        'auditoria/opcoes/usuarios/',
        login_required(views.UserOptionsView.as_view()),
        name='audit_user_options',
    ),
]
