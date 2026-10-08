"""Aplicação ASGI do projeto, com o HTTP do Django e o canal das notificações (D11).

O `get_asgi_application` é chamado antes de as rotas do WebSocket serem importadas,
porque elas dependem dos apps carregados.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_application = get_asgi_application()

from notices.routing import websocket_urlpatterns


def websocket_application():
    """Canal das notificações: origem conferida antes da sessão, e a sessão no consumer.

    O `AllowedHostsOriginValidator` recusa o handshake cujo cabeçalho `Origin` não esteja em
    `ALLOWED_HOSTS`, e também o handshake sem `Origin`, que todo navegador envia. Ele lê
    `ALLOWED_HOSTS` uma vez, na montagem; com `DEBUG` e a lista vazia, aceita só localhost,
    127.0.0.1 e [::1]. A autenticação continua no `NotificationsConsumer`.
    """
    return AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)))


application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': websocket_application(),
})
