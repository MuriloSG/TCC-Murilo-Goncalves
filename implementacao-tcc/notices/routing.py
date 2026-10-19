"""Rota do canal de tempo real das notificações."""

from django.urls import path

from notices.consumers import NotificationsConsumer

websocket_urlpatterns = [
    path('ws/notificacoes/', NotificationsConsumer.as_asgi()),
]
