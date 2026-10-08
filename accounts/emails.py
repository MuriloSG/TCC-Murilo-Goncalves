"""E-mails de accounts enviados pelo outbox."""

from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import user_pk_to_url_str
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

PASSWORD_LINK = 'LINK_SENHA'


def password_link(reference):
    """Gera o token no envio e devolve None quando o link não se aplica mais."""
    user = get_user_model().objects.filter(pk=reference).first()
    if user is None or not user.is_active or user.has_usable_password():
        return None
    token = app_settings.PASSWORD_RESET_TOKEN_GENERATOR().make_token(user)
    path = reverse('account_reset_password_from_key', kwargs={'uidb36': user_pk_to_url_str(user), 'key': token})
    context = {'user': user, 'password_reset_url': settings.SITE_URL.rstrip('/') + path}
    return get_adapter().render_mail('account/email/password_reset_key', user.email, context)
