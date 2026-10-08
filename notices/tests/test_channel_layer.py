import asyncio
import importlib.util
import os
import subprocess
import sys
import uuid
from unittest.mock import patch

from channels_redis.core import RedisChannelLayer
from django.conf import settings
from django.test import SimpleTestCase, override_settings

from notices.checks import channel_layer_shared
from notices.consumers import CHANGED, group_name

REDIS_URL = os.environ.get('DJANGO_REDIS_URL', '')
SETTINGS_FILE = settings.BASE_DIR / 'config' / 'settings.py'


def load_settings(environment, argv):
    """Executa o `settings.py` num módulo à parte, com o ambiente e os argumentos informados."""
    spec = importlib.util.spec_from_file_location('settings_under_test', SETTINGS_FILE)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, environment), patch.object(sys, 'argv', argv):
        spec.loader.exec_module(module)
    return module


class LayerSettingsTests(SimpleTestCase):
    def layer(self, url, argv=('manage.py', 'runserver'), prefix=None):
        environment = {'DJANGO_REDIS_URL': url}
        if prefix is not None:
            environment['DJANGO_CACHE_KEY_PREFIX'] = prefix
        return load_settings(environment, list(argv)).CHANNEL_LAYERS['default']

    def test_redis_url_uses_the_shared_layer_with_its_own_prefix(self):
        layer = self.layer('redis://redis:6379/0', prefix='campus')
        self.assertEqual(layer['BACKEND'], 'channels_redis.core.RedisChannelLayer')
        self.assertEqual(layer['CONFIG']['prefix'], 'campus:channels')
        self.assertEqual(layer['CONFIG']['hosts'][0]['address'], 'redis://redis:6379/0')

    def test_shared_layer_has_no_read_timeout_shorter_than_the_blocking_wait(self):
        host = self.layer('redis://redis:6379/0')['CONFIG']['hosts'][0]
        self.assertNotIn('socket_timeout', host)
        self.assertIn('socket_connect_timeout', host)

    def test_missing_url_keeps_the_layer_in_memory(self):
        self.assertEqual(self.layer('')['BACKEND'], 'channels.layers.InMemoryChannelLayer')

    def test_tests_keep_the_layer_in_memory(self):
        layer = self.layer('redis://redis:6379/0', argv=('manage.py', 'test'))
        self.assertEqual(layer['BACKEND'], 'channels.layers.InMemoryChannelLayer')


class LayerCheckTests(SimpleTestCase):
    @override_settings(TESTING=False, CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
    def test_layer_in_memory_is_warned(self):
        self.assertEqual([message.id for message in channel_layer_shared(None)], ['notices.W001'])

    @override_settings(TESTING=False, CHANNEL_LAYERS={'default': {'BACKEND': 'channels_redis.core.RedisChannelLayer'}})
    def test_shared_layer_is_not_warned(self):
        self.assertEqual(channel_layer_shared(None), [])

    @override_settings(TESTING=True, CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
    def test_tests_are_not_warned(self):
        self.assertEqual(channel_layer_shared(None), [])


SENDER = """
import django
django.setup()
from django.conf import settings
from notices.realtime import send_change
assert settings.CHANNEL_LAYERS['default']['BACKEND'] == 'channels_redis.core.RedisChannelLayer'
send_change([{user_id}])
"""


class CrossProcessTests(SimpleTestCase):
    """Aviso enviado por outro processo pelo Redis do ambiente chega a quem escuta o grupo."""

    def setUp(self):
        if not REDIS_URL:
            self.skipTest('DJANGO_REDIS_URL não definida neste ambiente.')

    def test_event_sent_by_another_process_arrives(self):
        prefix = f'teste-{uuid.uuid4().hex}'
        user_id = 4242
        layer = RedisChannelLayer(hosts=[REDIS_URL], prefix=f'{prefix}:channels')

        async def listen():
            channel = await layer.new_channel()
            await layer.group_add(group_name(user_id), channel)
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-c', SENDER.format(user_id=user_id),
                cwd=settings.BASE_DIR,
                env={**os.environ, 'DJANGO_CACHE_KEY_PREFIX': prefix, 'DJANGO_SETTINGS_MODULE': 'config.settings'},
                stderr=subprocess.PIPE,
            )
            _, error = await process.communicate()
            self.assertEqual(process.returncode, 0, error.decode())
            try:
                return await asyncio.wait_for(layer.receive(channel), 5)
            finally:
                await layer.group_discard(group_name(user_id), channel)
                await layer.flush()

        self.assertEqual(asyncio.run(listen()), {'type': CHANGED})
