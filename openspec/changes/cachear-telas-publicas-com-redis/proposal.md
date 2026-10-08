## Why

O sistema tem duas telas abertas sem login com conteúdo de domínio: o calendário público (`/`, `PublicCalendarView`) e o horário original (`/horario-original/`, `OriginalTimetableView`), as duas montadas por `schedule/public.py`. São as telas de maior audiência potencial: alunos e docentes consultam a mesma sala, o mesmo docente ou o mesmo curso repetidas vezes ao longo do dia, e o resultado é igual para todo visitante.

A medição da Change `otimizar-consultas-do-sistema` mostra que elas já são baratas no banco:

| Tela | Consultas | Tempo |
|---|---|---|
| Calendário público sem filtro / sala na semana / docente no mês | 4 / 10 / 10 | 73 / 24 / 31 ms |
| Horário original sem filtro / sala | 4 / 8 | 10 / 17 ms |

Cada consulta leva menos de 1 ms. O custo de uma requisição está na repetição: a cada acesso, as mesmas 4 consultas das opções dos filtros (semestres, salas, docentes, cursos) e a mesma montagem da Grade em Python e no template, para um conteúdo que só muda numa importação, numa alteração do ensalamento, num cadastro ou num agendamento aprovado ou cancelado.

Hoje não existe cache configurado (`CACHES` ausente, o Django usa o `LocMemCache` padrão, por processo) e a convenção do projeto deixa o cache da rota pública para o proxy de produção. Um cache HTTP no proxy não sabe quando o ensalamento mudou: só expira por tempo. Um cache em memória do processo não serve, porque a confirmação da importação roda no container `import_worker` e a invalidação precisa chegar ao `web`.

## What Changes

- **Redis como cache compartilhado**, num serviço novo `redis` do Docker Compose, só na rede interna, sem persistência em disco, usado **somente como cache** por um alias próprio (`public`) do framework de cache do Django. O alias `default` continua `LocMemCache`, como hoje, para os limites de tentativas do allauth.
- **Módulo único de cache público** (`schedule/public_cache.py`), o único ponto que lê e grava o Redis: monta as chaves, lê a geração, trata a indisponibilidade e registra hits, misses e invalidações.
- **Cache das opções do semestre (P0)**: semestres publicados, salas, docentes e cursos do semestre, lidos em toda requisição das duas telas, com ou sem filtro.
- **Cache da Grade montada (P1, condicionado à medição)**: o fragmento HTML da Grade do calendário público e do horário original, pela combinação normalizada dos filtros e pela data de hoje. Só entra se a linha de base e a medição depois do P0 mostrarem ganho, pelo critério do `design.md`.
- **Invalidação por geração, depois do commit**: toda escrita confirmada num modelo lido pelas telas públicas incrementa um contador de geração no Redis por `transaction.on_commit`. As chaves levam a geração, e as antigas deixam de ser lidas e expiram pelo TTL. Um rollback descarta o `on_commit`, e o cache anterior continua valendo.
- **Fallback**: com o Redis indisponível ou sem configuração, as telas consultam o PostgreSQL como hoje, sem erro e sem esperar mais que o tempo limite curto de conexão.
- **Cabeçalho de diagnóstico** `X-Public-Cache: hit | miss | bypass` nas duas telas públicas, e logs só de invalidação e de indisponibilidade.
- **`Cache-Control: no-cache`** nas duas telas públicas, como medida defensiva para caches intermediários. A configuração do proxy de produção está fora do repositório e precisa ser conferida na infraestrutura.
- **Linha de base e benchmark** antes e depois, num banco próprio de medição, com tempo médio, p95, consultas por requisição e hits/misses.
- Atualização de `openspec/conventions.md` (seção 4): o cache dos dados públicos passa a ser da aplicação, com invalidação; o rate limit continua no proxy.

## Capabilities

### New Capabilities
- `cache-publico`: cache compartilhado dos dados das telas públicas, com chaves normalizadas, invalidação por geração depois do commit, TTL por cache, fallback e diagnóstico.

### Modified Capabilities
- `calendario-publico`: o requisito de desempenho passa a admitir a leitura do cache, com zero consultas ao banco quando o conteúdo está em cache, sem mudar o que a página mostra.
- `ambiente-desenvolvimento`: serviço `redis` no Docker Compose, só na rede interna, e a variável de ambiente da conexão.

## Impact

- **Dependências:** `redis` (cliente Python, exigido por `django.core.cache.backends.redis.RedisCache`), com versão fixada no `requirements.txt`. Nenhuma outra biblioteca.
- **Infraestrutura:** serviço `redis` no `compose.yaml`; `web`, `worker` e `import_worker` recebem `DJANGO_REDIS_URL`, `DJANGO_REDIS_TIMEOUT` e `DJANGO_CACHE_KEY_PREFIX`.
- **Código:** `config/settings.py` (`CACHES`), `schedule/public_cache.py` (novo), `schedule/public.py` e `schedule/public_views.py` (leitura do cache), `schedule/apps.py` e `bookings/apps.py` (sinais de invalidação), `schedule/models.py` (invalidação explícita em `record_many`, `sync_offerings` e `Allocation.update_details`), `accounts/management/commands/clear_data.py` (invalidação explícita após o `TRUNCATE`).
- **Sem migration, sem mudança de regra de negócio e sem mudança no conteúdo das telas.**

## Fora do escopo

- Redis como fila, broker do Celery ou camada do Django Channels (o `InMemoryChannelLayer` continua; a troca é registrada como possibilidade futura no `design.md`).
- Redis como banco principal ou para sessões.
- Mover os limites de tentativas do allauth para o Redis.
- Cache de qualquer tela autenticada e das telas do allauth (login, sair, recuperação de senha).
- `cache_page` ou cache da resposta inteira.
- Proteção contra cache stampede (lock, `SET NX`, stale-while-revalidate, jitter), sem evidência de necessidade (D9 do `design.md`).
- Configuração do Redis de produção além das variáveis e das recomendações documentadas no `design.md`.
