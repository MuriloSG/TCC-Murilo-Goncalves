"""Canal de tempo real das notificações (D11).

A conexão é autenticada pela mesma sessão da interface, e cada usuário escuta só o
destino dele: a separação é do servidor, e não do navegador. O evento não carrega
a notificação, apenas avisa que as notificações daquele usuário mudaram, e a
interface busca a contagem e a lista numa requisição autenticada.
"""

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

CHANGED = 'notifications.changed'


def group_name(user_id):
    return f'notificacoes-{user_id}'


class NotificationsConsumer(JsonWebsocketConsumer):
    group = None

    def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated or not user.is_active:
            self.close()
            return
        self.group = group_name(user.pk)
        async_to_sync(self.channel_layer.group_add)(self.group, self.channel_name)
        self.accept()

    def disconnect(self, code):
        if self.group:
            async_to_sync(self.channel_layer.group_discard)(self.group, self.channel_name)

    def notifications_changed(self, event):
        self.send_json({'evento': 'notificacoes'})
