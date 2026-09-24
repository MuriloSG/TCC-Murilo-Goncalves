"""Aplicação ASGI do projeto, com o HTTP do Django e o canal das notificações (D11).

O `get_asgi_application` é chamado antes de as rotas do WebSocket serem importadas,
porque elas dependem dos apps carregados.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_application = get_asgi_application()

from notices.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
