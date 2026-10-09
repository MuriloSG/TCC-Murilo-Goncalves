"""Conferências de `check --deploy` que o Django não faz: segredos de desenvolvimento e Redis sem senha."""

from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Warning

DEVELOPMENT_REDIS_PASSWORD = 'redis-somente-para-desenvolvimento-local'
DEVELOPMENT_SECRETS = {
    'SECRET_KEY': 'django-insecure-somente-para-desenvolvimento-local',
    'CREDENTIALS_KEY': 'chave-de-credenciais-somente-para-desenvolvimento-local',
}


def deployment_settings(app_configs, **kwargs):
    """Recusa os segredos padrão do compose e avisa do Redis sem senha e dos cookies sem `Secure`."""
    problems = [
        Error(
            f'{name} usa o valor padrão do compose.yaml, que só serve ao desenvolvimento.',
            hint=f'Defina DJANGO_{name} com um valor próprio desta instalação.',
            id='system_settings.E001',
        )
        for name, value in DEVELOPMENT_SECRETS.items()
        if getattr(settings, name, None) == value
    ]
    redis_url = getattr(settings, 'REDIS_URL', '')
    redis_password = urlsplit(redis_url).password if redis_url else None
    if redis_password == DEVELOPMENT_REDIS_PASSWORD:
        problems.append(Error(
            'DJANGO_REDIS_URL usa a senha padrão do compose.yaml, que só serve ao desenvolvimento.',
            hint='Defina REDIS_PASSWORD e DJANGO_REDIS_URL com uma senha própria desta instalação.',
            id='system_settings.E002',
        ))
    if redis_url and not redis_password:
        problems.append(Warning(
            'DJANGO_REDIS_URL não tem senha: qualquer processo na rede do Redis lê e grava o cache e as notificações.',
            hint='Configure requirepass ou ACL no Redis e informe a senha na URL (redis://:senha@host:6379/0).',
            id='system_settings.W001',
        ))
    if not getattr(settings, 'SECURE_COOKIES', False):
        problems.append(Warning(
            'Os cookies de sessão e de CSRF não estão marcados como Secure.',
            hint='Com HTTPS, deixe DJANGO_SECURE_COOKIES sem valor ou com 1.',
            id='system_settings.W002',
        ))
    return problems
