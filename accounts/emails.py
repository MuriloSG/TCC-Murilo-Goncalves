"""E-mails de accounts enviados pelo outbox (D6 da Change enviar-emails-por-outbox)."""

from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import user_pk_to_url_str
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

PASSWORD_LINK = 'LINK_SENHA'


def password_link(reference):
    """Monta o e-mail com o link de definição de senha do usuário `reference`.

    O token é gerado aqui, no envio, pelo mesmo gerador e para a mesma rota da
    recuperação de senha, e nunca é gravado. O link usa a URL base configurada,
    porque o worker não tem requisição. Devolve None quando o usuário não existe
    mais, está inativo ou já definiu a senha, e o envio é descartado.
    """
    user = get_user_model().objects.filter(pk=reference).first()
    if user is None or not user.is_active or user.has_usable_password():
        return None
    token = app_settings.PASSWORD_RESET_TOKEN_GENERATOR().make_token(user)
    path = reverse('account_reset_password_from_key', kwargs={'uidb36': user_pk_to_url_str(user), 'key': token})
    context = {'user': user, 'password_reset_url': settings.SITE_URL.rstrip('/') + path}
    return get_adapter().render_mail('account/email/password_reset_key', user.email, context)
