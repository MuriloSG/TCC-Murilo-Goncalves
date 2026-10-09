"""Cache no Redis: serializador JSON, sem pickle, e o backend tolerante dos limites de tentativa."""

import datetime
import json
import logging

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import RedisError

logger = logging.getLogger('config')

UNAVAILABLE = (RedisError, OSError)

DATE_TAG = '__data__'


def encode(value):
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return {DATE_TAG: value.isoformat()}
    raise TypeError(f'Valor sem representação no cache: {type(value).__name__}')


def decode(item):
    if set(item) == {DATE_TAG}:
        return datetime.date.fromisoformat(item[DATE_TAG])
    return item


class JsonSerializer:
    """Inteiros ficam crus, como no serializador do Django, para o `incr` atômico; tuplas voltam como listas."""

    def dumps(self, obj):
        if type(obj) is int:
            return obj
        return json.dumps(obj, default=encode, separators=(',', ':')).encode()

    def loads(self, data):
        try:
            return int(data)
        except ValueError:
            return json.loads(data, object_hook=decode)


class TolerantRedisCache(RedisCache):
    """Cache dos limites de tentativa: com o Redis fora, os limites deixam de valer em vez de o login falhar."""

    def get(self, key, default=None, version=None):
        try:
            return super().get(key, default, version)
        except UNAVAILABLE as error:
            unavailable('get', error)
            return default

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            super().set(key, value, timeout, version)
        except UNAVAILABLE as error:
            unavailable('set', error)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """Devolve True na falha para que quem espera uma trava não fique preso."""
        try:
            return super().add(key, value, timeout, version)
        except UNAVAILABLE as error:
            unavailable('add', error)
            return True

    def delete(self, key, version=None):
        try:
            return super().delete(key, version)
        except UNAVAILABLE as error:
            unavailable('delete', error)
            return False


def unavailable(operation, error):
    logger.warning('REDIS UNAVAILABLE default %s: %s', operation, type(error).__name__)
