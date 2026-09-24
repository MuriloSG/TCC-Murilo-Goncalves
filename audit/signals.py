"""Ligação dos sinais de autenticação com a auditoria (D6).

O login realizado, a saída e a redefinição de senha são registrados pelos sinais
do Django e do allauth. A recusa do login não tem sinal que cubra o usuário
inativo com a senha correta e fica no adaptador de contas, que é o ponto único
onde a recusa é decidida.
"""

from allauth.account.signals import password_reset
from django.contrib.auth.signals import user_logged_in, user_logged_out

from audit import catalog
from audit.context import acting_as_user
from audit.models import AuditLog


def record(action, user):
    with acting_as_user(user):
        AuditLog.objects.record(action, catalog.AUTHENTICATION, resource_id=user.pk)


def record_login(sender, request, user, **kwargs):
    record(catalog.LOGIN, user)


def record_logout(sender, request, user, **kwargs):
    if user is not None and user.is_authenticated:
        record(catalog.LOGOUT, user)


def record_password_reset(sender, request, user, **kwargs):
    record(catalog.PASSWORD_RESET, user)


def connect():
    user_logged_in.connect(record_login, dispatch_uid='audit_login')
    user_logged_out.connect(record_logout, dispatch_uid='audit_logout')
    password_reset.connect(record_password_reset, dispatch_uid='audit_password_reset')
