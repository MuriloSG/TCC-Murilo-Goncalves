## 1. P0: linha de base e infraestrutura Redis

- [x] 1.1 Medir a linha de base (D11, cenário a). **Feito:** com o código anterior à Change num `git worktree`, no banco `perf_check`, por um script fora do repositório no lugar do comando `measure_public_pages`. Números em "Resultados da implementação" do `design.md`; os 73 ms do calendário sem filtro eram de aquecimento (7,5 ms medidos).
- [x] 1.2 Serviço `redis` no `compose.yaml` (D3): `redis:8-alpine`, sem `ports`, sem persistência, `maxmemory 64mb` com `allkeys-lru`, healthcheck `redis-cli ping`; `DJANGO_REDIS_URL`, `DJANGO_REDIS_TIMEOUT` e `DJANGO_CACHE_KEY_PREFIX` no `x-app-env`; `web`, `worker` e `import_worker` com `depends_on: redis: condition: service_started`. **Validado:** `make up`; `docker compose port redis 6379` sem porta publicada; `/` responde com `miss` e depois `hit`.
- [x] 1.3 Dependência `redis==8.1.0` no `requirements.txt`.
- [x] 1.4 `CACHES` em `config/settings.py` (D2): `default` `LocMemCache` explícito; `public` `RedisCache` com `KEY_PREFIX` e tempos limite de 0,1 s, ou `DummyCache` sem `DJANGO_REDIS_URL` e durante `manage.py test`.
- [x] 1.5 `schedule/public_cache.py` (D4, D5, D8, D12): `cache_key`, `current_generation`, `bump_generation`, `invalidate_on_commit`, `watch`, `Lookup`, pausa de 30 s e logs. Testes em `schedule/tests/test_public_cache.py` (`KeyTests`, `LookupTests`, `UnavailableTests`).

## 2. P0: cache das opções do semestre e invalidação

- [x] 2.1 Sinais de invalidação (D6) em `schedule/apps.py` e `bookings/apps.py`, com o filtro de `update_fields` de `User`. O `m2m_changed` de `Allocation.teachers` foi trocado por invalidação explícita em `Allocation.update_details`, porque aumentava as consultas da importação (desvio registrado no D6). **Validado:** `CommitTests`.
- [x] 2.2 Invalidação explícita nas escritas em massa (D6): `ClassOfferingManager.record_many`, `sync_offerings` (usada por `sync_assignments`), `Allocation.update_details` e `clear_data`. **Validado:** `CommitTests`.
- [x] 2.3 Importação (D6, D7). **Validado:** `ImportInvalidationTests`: a prévia não incrementa; a confirmação pelo worker incrementa uma vez o mesmo alias que a tela lê.
- [x] 2.4 Opções do semestre em cache (D1, D14), guardadas como tuplas e reconstruídas como instâncias dos models. **Validado:** os testes do calendário público passam sem mudança; `PublicViewCacheTests` compara o HTML sem cache, frio e quente; quatro consultas a menos no quente (benchmark).
- [x] 2.5 Cabeçalho `X-Public-Cache` (D12) e `Cache-Control: no-cache` nas duas views. **Validado:** `PublicViewCacheTests`.
- [x] 2.6 Teste de varredura das escritas em massa (`BulkWriteScanTests`).
- [x] 2.7 Medir o P0 (D11). **Feito:** critério cumprido; números no `design.md`.

## 3. P1: Grade em cache, condicionada à medição

- [x] 3.1 Decidir pelo resultado da 2.7: com as opções em cache, o tempo restante estava na montagem da Grade (p95 de 17,6 a 30,3 ms com 4 a 6 consultas).
- [x] 3.2 Grade do calendário público em cache, chave `calendar-grid`, TTL de 10 minutos.
- [x] 3.3 Grade do horário original em cache, chave `original-grid`, TTL de 30 minutos. **Validado 3.2 e 3.3:** HTML idêntico com e sem cache; a troca de dia muda a chave; agendamento aprovado, alterado, cancelado e excluído invalida (`BookingInvalidationTests`); visitante autenticado recebe o mesmo conteúdo.
- [x] 3.4 Medir o P1 (D11). **Feito:** queda do p95 de 61% a 77% sobre o P0; as duas Grades foram mantidas.

## 4. P2: observabilidade e melhorias futuras

- [ ] 4.1 Comando `public_cache_stats` (D12): geração atual e `keyspace_hits`, `keyspace_misses`, `evicted_keys`.
- [x] 4.2 Benchmark de concorrência depois de uma invalidação (D9, cenário e). **Feito:** consultas sempre abaixo da linha de base e p95 na faixa de variação dela; nenhuma proteção contra stampede adicionada.
- [ ] 4.3 Taxa de hit em uso real, depois de algumas semanas. Só considerar invalidação por semestre se a taxa ficar baixa por excesso de invalidação.
- [ ] 4.4 Avaliar, em Change própria, o Redis como camada do Django Channels e os limites de tentativas do allauth num cache compartilhado.

## 5. Documentação e fechamento

- [x] 5.1 README: serviço `redis`, variáveis, recomendações de produção e o aviso sobre o cache HTTP do proxy de produção, que está fora do repositório.
- [x] 5.2 Banco `perf_check`, banco lógico `/1` do Redis e `git worktree` da linha de base apagados. Nenhum comando de medição foi criado no repositório.
- [x] 5.3 `openspec/conventions.md` (seção 4 e seção 7) atualizado.
- [x] 5.4 `make test` passando e `openspec validate cachear-telas-publicas-com-redis --strict`.
