from django.apps import AppConfig


class NoticesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notices'
    verbose_name = 'Notificações'

    def ready(self):
        """Registra o aviso da camada do Channels em memória."""
        from django.core.checks import register

        from notices.checks import channel_layer_shared

        register(channel_layer_shared)
