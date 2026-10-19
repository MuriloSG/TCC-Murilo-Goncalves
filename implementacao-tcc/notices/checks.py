"""Aviso da camada do Channels em memória, que não alcança as notificações dos workers."""

from django.conf import settings
from django.core.checks import Warning

IN_MEMORY = 'channels.layers.InMemoryChannelLayer'


def channel_layer_shared(app_configs, **kwargs):
    """Avisa quando a camada é a em memória fora dos testes."""
    if settings.CHANNEL_LAYERS['default']['BACKEND'] != IN_MEMORY or getattr(settings, 'TESTING', False):
        return []
    return [Warning(
        'A camada do Channels está em memória: notificações criadas fora do processo web não '
        'chegam ao sino em tempo real.',
        hint='Defina DJANGO_REDIS_URL para usar o Redis como camada compartilhada.',
        id='notices.W001',
    )]
