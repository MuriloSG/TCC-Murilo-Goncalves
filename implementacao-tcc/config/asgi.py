"""ASGI com HTTP e WebSocket; `get_asgi_application` vem antes das rotas, que exigem os apps carregados."""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_application = get_asgi_application()

from notices.routing import websocket_urlpatterns


def websocket_application():
    """Confere a origem no handshake; a autenticação fica no `NotificationsConsumer`."""
    return AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)))


application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': websocket_application(),
})
