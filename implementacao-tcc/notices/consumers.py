"""Canal de tempo real das notificações; o evento só avisa a mudança, e a interface busca o conteúdo."""

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

CHANGED = 'notifications.changed'
CLOSED = 'notifications.closed'


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

    def notifications_closed(self, event):
        """Encerra a conexão do usuário desativado, que de outro modo seguiria aberta até recarregar a página."""
        self.close()
