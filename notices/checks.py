"""Aviso de configuração da camada do Channels.

Sem `DJANGO_REDIS_URL`, a camada fica em memória e só alcança as conexões do mesmo processo:
as notificações criadas no `import_worker` não atualizam o sino na hora. A aplicação continua
funcionando, por isso é um aviso, e não um erro, mas ele aparece em todo comando de gestão,
inclusive na subida do `web` e dos workers.
"""

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
