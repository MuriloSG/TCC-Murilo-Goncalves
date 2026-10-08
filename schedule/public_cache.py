"""Cache compartilhado das telas públicas (Change cachear-telas-publicas-com-redis).

É o único módulo que lê e grava o alias `public` do cache. O PostgreSQL continua sendo a fonte
de verdade: o cache guarda só o que as telas públicas mostram a qualquer visitante e, com o
Redis indisponível ou sem configuração, as telas consultam o banco como sem cache (D8).

As chaves têm o formato `public:<recurso>:g<geração>:<hash>` (D4). A geração é um contador
global sem TTL, incrementado depois do commit de toda escrita num modelo lido pelas telas
públicas (D5 e D6). As entradas de gerações anteriores deixam de ser lidas e saem pelo TTL.
"""

import hashlib
import json
import logging
import pickle
import time

from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.db import connection, transaction
from django.db.models.signals import post_delete, post_save
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

ALIAS = 'public'
GENERATION_KEY = 'public:generation'
PAUSE_SECONDS = 30

OPTIONS = 'options'
CALENDAR_GRID = 'calendar-grid'
ORIGINAL_GRID = 'original-grid'
TTL = {
    OPTIONS: 60 * 60,
    CALENDAR_GRID: 10 * 60,
    ORIGINAL_GRID: 30 * 60,
}

USER_PUBLIC_FIELDS = ('name', 'username', 'email', 'is_active')

HIT = 'hit'
MISS = 'miss'
BYPASS = 'bypass'

UNAVAILABLE = (RedisError, OSError)

_paused_until = 0.0


def backend():
    return caches[ALIAS]


def is_enabled():
    """O cache só é usado com um backend real e fora da pausa que segue uma falha (D8)."""
    return not isinstance(backend(), DummyCache) and time.monotonic() >= _paused_until


def pause(operation, error):
    """Deixa de chamar o Redis por `PAUSE_SECONDS` neste processo e registra a falha uma vez."""
    global _paused_until
    _paused_until = time.monotonic() + PAUSE_SECONDS
    logger.warning('REDIS UNAVAILABLE %s: %s', operation, type(error).__name__)


def resume():
    """Encerra a pausa; usado pelos testes para não depender do relógio."""
    global _paused_until
    _paused_until = 0.0


def cache_key(resource, generation, params):
    """Chave do recurso na geração, com o hash da forma canônica dos parâmetros normalizados.

    Os parâmetros já passaram pela normalização contra o cadastro; nenhum valor da URL entra
    em texto na chave, que tem tamanho fixo qualquer que seja a requisição.
    """
    if resource not in TTL:
        raise ValueError(f'Tipo de cache desconhecido: {resource}')
    canonical = json.dumps(params, sort_keys=True, default=str, separators=(',', ':'))
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:32]
    return f'public:{resource}:g{generation}:{digest}'


def current_generation():
    """Geração atual; quando o contador não existe, é criado com um valor que nunca repete um anterior."""
    cache = backend()
    generation = cache.get(GENERATION_KEY)
    if generation is None:
        cache.add(GENERATION_KEY, time.time_ns(), timeout=None)
        generation = cache.get(GENERATION_KEY)
    return generation


def bump_generation():
    """Incrementa a geração; é chamado só depois do commit, e uma falha nunca chega a quem escreveu."""
    if isinstance(backend(), DummyCache):
        return
    try:
        try:
            generation = backend().incr(GENERATION_KEY)
        except ValueError:
            generation = time.time_ns()
            backend().add(GENERATION_KEY, generation, timeout=None)
    except UNAVAILABLE as error:
        pause('invalidate', error)
        return
    logger.info('CACHE INVALIDATED generation=%s', generation)


def invalidate_on_commit():
    """Agenda o incremento da geração para depois do commit da transação atual.

    Um rollback descarta o agendamento, e o cache anterior continua valendo. Só um
    agendamento fica pendente por transação: os savepoints desfeitos removem os seus, e um
    agendamento ainda pendente cobre toda escrita feita dentro dos mesmos savepoints.
    """
    if any(item[1] is bump_generation for item in connection.run_on_commit):
        return
    transaction.on_commit(bump_generation, robust=True)


class Lookup:
    """Leituras do cache de uma requisição: a geração é lida uma vez, e o estado vai para o cabeçalho.

    O estado é `hit` só quando todas as leituras foram hits, `bypass` quando o cache não foi
    usado e `miss` nos demais casos.
    """

    def __init__(self):
        self.statuses = []
        self._generation = None

    @property
    def status(self):
        if not self.statuses or BYPASS in self.statuses:
            return BYPASS
        return HIT if all(status == HIT for status in self.statuses) else MISS

    def generation(self):
        if self._generation is None:
            self._generation = current_generation()
        return self._generation

    def fetch(self, resource, params, builder):
        """Valor do recurso pelos parâmetros, do cache quando houver, ou do `builder`, que consulta o banco."""
        if not is_enabled():
            self.statuses.append(BYPASS)
            return builder()
        try:
            key = cache_key(resource, self.generation(), params)
            value = backend().get(key)
        except UNAVAILABLE as error:
            pause('read', error)
            self.statuses.append(BYPASS)
            return builder()
        except (pickle.UnpicklingError, EOFError, AttributeError, ImportError, ValueError, TypeError):
            value = None
        if value is not None:
            self.statuses.append(HIT)
            logger.debug('CACHE HIT %s', resource)
            return value
        value = builder()
        self.statuses.append(MISS)
        logger.debug('CACHE MISS %s', resource)
        try:
            backend().set(key, value, TTL[resource])
        except UNAVAILABLE as error:
            pause('write', error)
        return value


def changed_public_fields(fields, update_fields):
    """Diz se a gravação toca algum campo público; sem `update_fields`, toda gravação toca."""
    return fields is None or update_fields is None or bool(set(update_fields) & set(fields))


def watch(model, fields=None):
    """Invalida o cache público depois do commit de toda gravação ou exclusão do model.

    Com `fields`, só a gravação que inclui um desses campos invalida: o login, que grava só
    `last_login` do usuário, não muda nada nas telas públicas (D6).
    """
    def saved(sender, update_fields=None, **kwargs):
        if changed_public_fields(fields, update_fields):
            invalidate_on_commit()

    def deleted(sender, **kwargs):
        invalidate_on_commit()

    post_save.connect(saved, sender=model, weak=False, dispatch_uid=f'public_cache_save_{model._meta.label}')
    post_delete.connect(deleted, sender=model, weak=False, dispatch_uid=f'public_cache_delete_{model._meta.label}')

