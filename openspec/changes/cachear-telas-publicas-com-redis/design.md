## Context

### Telas públicas encontradas

As rotas sem login são as de `PUBLIC_ROUTES` em `accounts/tests/test_route_protection.py`, que falha se uma rota ficar fora da tabela. São oito:

| Rota | View | Natureza |
|---|---|---|
| `/` (`public_calendar`) | `schedule.public_views.PublicCalendarView` | conteúdo de domínio, só GET e HEAD |
| `/horario-original/` (`public_original_timetable`) | `schedule.public_views.OriginalTimetableView` | conteúdo de domínio, só GET e HEAD |
| `contas/login/` | `allauth.account.views.login` | formulário com CSRF, sessão e limite de tentativas |
| `contas/logout/` | `accounts.views.LogoutView` | altera a sessão |
| `contas/senha/recuperar/` e `.../enviado/` | allauth | formulário com CSRF; envia e-mail |
| `contas/senha/redefinir/<uidb36>-<key>/` e `.../concluido/` | allauth | chave individual na URL |

### Calendário público (`/`)

```text
GET /?semestre=&sala=&docente=&curso=&turma=&nivel=&inicio=&fim=
→ PublicCalendarView.get_context_data
→ schedule.public.public_calendar(request.GET, timezone.localdate())
   → read_filters
      1. imported_semesters()             Semester ⋈ Allocation (distinct)
      2. semester_options: listed_spaces  Space (ativos ou com alocação no semestre)
      3.                   teachers       Teacher ⋈ allocation_teachers ⋈ Allocation
      4.                   courses        Course ⋈ ClassGroup ⋈ Allocation
      5. course_groups (só com curso)     ClassGroup ⋈ Allocation
   → sem filtro principal: para aqui (4 consultas)
   → public_allocations                   Allocation ⋈ Subject, TimeSlot, Space, ClassGroup, Course
      + prefetch teachers                 Teacher
   → entries_of → teacher_emails          User (username, email, is_active)
   → dated_week → AllocationException.objects.cancelled
                → semester_slots          TimeSlot ⋈ Allocation
                → public_bookings         Booking ⋈ Space, User, BookingRequest, TeachingAssignment,
                                          Teacher, ClassOffering, Subject, ClassGroup, Course
                                          (só com sala ou docente, sem curso e sem nível)
   → typical_week (semestre sem período)  semester_slots
→ templates schedule/public/calendar.html, filters.html, grid.html, entry.html, booking.html
   sobre ui/layouts/public.html
→ exibe: filtros (semestres, salas, docentes, cursos, turmas, nível, datas); Grade com disciplina,
  curso, turma, sala, docentes com e-mail, turmas juntas; agendamentos aprovados com horário,
  sala, disciplina, curso, turma, docente ou solicitante e e-mail; mensagens de estado.
```

### Horário original (`/horario-original/`)

```text
GET /horario-original/?semestre=&sala=&docente=&curso=&turma=&nivel=
→ OriginalTimetableView → schedule.public.original_timetable
   → read_filters (as mesmas 4 a 5 consultas)
   → public_allocations(original=True)   só Origin.IMPORTED, sem exceções e sem agendamentos
   → typical_week → semester_slots
→ templates schedule/public/original.html, filters.html, grid.html, entry.html
→ exibe: a semana típica importada, sem datas.
```

### Medição existente (Change `otimizar-consultas-do-sistema`)

| Tela | Consultas | Tempo |
|---|---|---|
| Calendário, sem filtro / sala na semana / docente no mês | 4 / 10 / 10 | 73 / 24 / 31 ms |
| Horário original, sem filtro / sala | 4 / 8 | 10 / 17 ms |

As tabelas lidas têm de dezenas a 1.498 linhas (alocações) e cada consulta leva menos de 1 ms. **O tempo das telas está na montagem da Grade (`build_week`, `publish`, `clusters_of`) e no template, e não no PostgreSQL.** Isso decide o que cachear: guardar só o resultado das consultas reduz idas ao banco, mas quase não reduz o tempo; guardar a Grade já montada reduz os dois. Os 73 ms da tela sem filtro, com 4 consultas, ainda precisam ser confirmados na linha de base (tarefa 1.1): o número pode ter vindo de uma primeira requisição sem templates carregados.

### Características dos dados

| Pergunta | Calendário | Horário original |
|---|---|---|
| Igual para todos os visitantes? | Sim. A view não lê `request.user`, sessão nem cookie; o layout `ui/layouts/public.html` não usa usuário, `messages` nem CSRF. | Sim, idem. |
| Parâmetros | `semestre`, `sala`, `docente`, `curso`, `turma`, `nivel`, `inicio`, `fim`; todos normalizados contra as opções do semestre ou descartados (`chosen`, `chosen_group`, `read_range`). | Os mesmos, sem datas. |
| Depende de outra coisa além dos parâmetros? | Da data de hoje: a semana padrão (`default_range`), o semestre padrão (`current_semester_code`) e o destaque do dia (`build_week(today)`). | Da data de hoje (semestre padrão e destaque). |
| Frequência de mudança | Ensalamento: importação uma ou poucas vezes por semestre, alterações pontuais de recorrência e exceções. Agendamentos: aprovações e cancelamentos ao longo do dia. Cadastros: raros. | Só importação e cadastros (espaço, docente, disciplina, turma, curso, usuário). |
| Frequência de acesso esperada | Alta e repetitiva: a mesma sala, o mesmo docente e a semana atual. | Menor que a do calendário. |

### Restrições do projeto

- `openspec/conventions.md` (seção 4) diz que o cache da rota pública fica no proxy de produção. Esta Change muda a regra e a seção é atualizada (tarefa 5.3).
- A spec `importacao-planilhas` proíbe a importação específica de "produzir efeitos fora da transação do banco, como [...] uso de cache". A invalidação desta Change não é chamada pela importação: é um efeito dos sinais dos modelos, registrado em `transaction.on_commit`, que o Django descarta na prévia (`run_preview` e `run_refresh` usam `transaction.set_rollback(True)`) e só executa depois do commit da confirmação no `import_worker`. É o mesmo mecanismo do `notices/realtime.py`.
- Sem comentários `#`; documentação em docstrings (conventions, seção 3).

## Goals / Non-Goals

**Goals:**
- Reduzir as consultas repetidas das telas públicas e, se medido, o tempo de resposta.
- Nenhuma alteração confirmada deixa uma tela pública desatualizada além do tempo de um `INCR` no Redis depois do commit.
- O Redis é uma otimização: sem ele as telas respondem como hoje.

**Non-Goals:**
- Cachear telas autenticadas, o fluxo do allauth ou a resposta HTTP inteira.
- Redis como fila, broker, camada do Channels, sessão ou banco.
- Proteção contra stampede sem evidência.

## Decisions

### D1. Classificação das telas

| Tela | Classe | Decisão |
|---|---|---|
| Opções do semestre (calendário e horário original) | **A, recomendado** | Consultadas em **toda** requisição das duas telas, inclusive na sem filtro, que é a de entrada. Iguais para todos, mudam raramente, a invalidação é clara. Cache de conjunto de dados, P0. |
| Grade do calendário público | **B, possível** | Ganho provável no tempo (a montagem é o custo maior), mas o espaço de chaves é maior (filtro × intervalo de datas) e os agendamentos mudam ao longo do dia. Entra em P1 só se a medição passar no critério de D11. |
| Grade do horário original | **B, possível** | Conteúdo muito estável, mas a tela é a menos acessada e já responde em 10 a 17 ms. Entra em P1 com o mesmo critério. |
| Login, sair, recuperação e redefinição de senha | **C, não cachear** | Formulário com CSRF, sessão, limite de tentativas, chave individual na URL, efeitos (e-mail, logout). O conteúdo depende do visitante, e o cache traria risco sem ganho. |
| Telas autenticadas | **C, fora do escopo** | Dependem de usuário e permissão. |

O resultado inteiro de `public_calendar` não é cacheado como objeto: ele carrega instâncias de model (`Space`, `Teacher`, `Course` com `only()`), cuja serialização depende de campos adiados e acopla o cache à forma do model.

### D2. Redis só como cache, num alias próprio

```python
CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    'public': <RedisCache se DJANGO_REDIS_URL estiver definida, senão DummyCache>,
}
```

- `default` fica explícito e igual ao comportamento atual. O allauth guarda nele os limites de tentativas; trocá-lo mudaria um comportamento de segurança fora do escopo.
- `public` usa `django.core.cache.backends.redis.RedisCache`, nativo do Django 5.2, que só exige o pacote `redis`. Sem `django-redis`.
- Sem `DJANGO_REDIS_URL`, o alias usa `DummyCache` e o sistema funciona sem Redis. A suíte de testes usa `LocMemCache` no alias `public` (por `override_settings` nos testes de cache e `DummyCache` no resto), e nunca o Redis do ambiente.
- `OPTIONS`: `socket_connect_timeout` e `socket_timeout` de **0,1 s**, lidos de `DJANGO_REDIS_TIMEOUT` (padrão `0.1`). O Redis está na mesma rede do Docker e responde em menos de 1 ms; 100 ms limitam o pior caso de uma requisição com o Redis travado.
- `KEY_PREFIX`: `DJANGO_CACHE_KEY_PREFIX`, padrão `ifagenda`. O Django monta a chave final como `<KEY_PREFIX>:<VERSION>:<chave>`.

**Isolamento entre ambientes:** cada ambiente aponta para o seu Redis ou para um banco lógico próprio pela URL (`redis://redis:6379/0` no desenvolvimento) e, quando dividir um servidor, por `DJANGO_CACHE_KEY_PREFIX` diferente (`ifagenda-homolog`, `ifagenda-prod`). O banco `visual_check` e o de medição usam outro banco lógico (`/1`), para não ler a geração do desenvolvimento.

### D3. Serviço `redis` no Docker Compose

```yaml
redis:
  image: redis:8-alpine
  command: redis-server --save "" --appendonly no --maxmemory 64mb --maxmemory-policy allkeys-lru
  healthcheck: redis-cli ping
```

- Imagem oficial com a versão maior fixada, como `postgres:17`.
- **Sem `ports`**: alcançável só pela rede interna do Compose, por `web`, `worker` e `import_worker`. O Redis nunca é exposto ao host nem à rede pública.
- **Sem persistência** (`--save ""`, `--appendonly no`): ao reiniciar, o cache começa vazio, o que nunca é inconsistente. Isso também elimina o caso de um Redis que volta com entradas antigas depois de perder um `INCR` (D7).
- `maxmemory 64mb` com `allkeys-lru`: o conjunto previsto cabe em poucos MB; a política evita erro de memória cheia. A remoção da própria chave de geração é tratada em D5.
- `web`, `worker` e `import_worker` dependem de `redis` com `condition: service_started`, e não `service_healthy`: a aplicação deve subir mesmo com o Redis fora do ar.
- **Produção:** senha pela URL (`redis://:senha@host:6379/0`, `requirepass`), sem porta publicada, só na rede privada dos containers da aplicação, e TLS (`rediss://`) se o Redis estiver em outra máquina. Fica documentado no README, sem arquivo de produção nesta Change.

### D4. Chaves

Formato, antes do prefixo do Django:

```text
public:<recurso>:g<geracao>:<hash>
```

- `recurso`: `options`, `calendar-grid`, `original-grid`. Lista fechada, constante do módulo.
- `geracao`: contador global (D5).
- `hash`: SHA-256 em hexadecimal, truncado em 32 caracteres, da forma canônica dos parâmetros **depois de normalizados**, nunca da query string:
  - `options`: o código do semestre.
  - `calendar-grid`: semestre, pk da sala, pk do docente, pk do curso, pk da turma, chave do nível, início e fim em ISO e a data de hoje em ISO.
  - `original-grid`: os mesmos, sem início e fim.
  - Forma canônica: `json.dumps` de um dicionário com chaves ordenadas e `None` explícito.
- O tamanho da chave é fixo (menos de 100 caracteres), qualquer que seja a URL.
- Colisão: os campos entram nomeados na forma canônica, e o recurso e a geração ficam fora do hash. Uma colisão de 128 bits de SHA-256 não é um risco prático.
- A data de hoje entra na chave da Grade porque o conteúdo muda com ela (semana padrão, destaque do dia). Uma entrada nunca atravessa a meia-noite.
- **Só se cacheia depois da normalização:** um parâmetro inválido vira `None` (sala inexistente, data inválida, semestre desconhecido), e as respostas de erro de data ou de "Escolha uma sala, um docente ou um curso" não são cacheadas, porque já não consultam o domínio. O conjunto de chaves possíveis é limitado pelo cadastro: um visitante não cria chaves arbitrárias mudando a URL.
- Todas as chaves saem de uma só função (`cache_key(resource, **params)`); nenhum outro código monta chave.

O formato sugerido `public:<recurso>:<versao>:<parametros>` foi adotado com duas mudanças: a versão é uma geração global, e os parâmetros entram por hash da forma normalizada, e não em texto, para limitar o tamanho e impedir que um valor da URL chegue à chave.

### D5. Invalidação por geração global

Uma chave `public:generation`, sem TTL, guarda um inteiro. Toda leitura de cache lê a geração e monta a chave com ela; toda invalidação faz `INCR`. As entradas da geração anterior deixam de ser lidas e saem pelo TTL ou pelo LRU.

**Por que global, e não por semestre ou por recurso.** Quase toda escrita relevante afeta mais de um cache: renomear um espaço muda as opções e todas as Grades em que ele aparece, em todos os semestres; trocar o e-mail de um usuário muda todo card do docente correspondente; uma importação muda as opções e as Grades do semestre. Um mapa fino de dependências teria de ser mantido junto de cada operação nova e erraria por omissão, o que é exatamente a inconsistência que o usuário quer evitar. As escritas são raras perto das leituras (D1), então invalidar tudo a cada escrita custa um miss por chave usada depois dela, poucas dezenas de requisições de 10 a 70 ms. A granularidade fina fica como melhoria futura, só se a medição mostrar taxa de hit baixa por excesso de invalidação (tarefa 4.3).

**Geração removida ou reiniciada.** Se `public:generation` não existir (Redis novo, reiniciado ou LRU), o primeiro acesso cria a chave com `add(key, time.time_ns())`, e não com zero. Assim uma geração recriada nunca coincide com uma geração antiga cujas entradas ainda estejam no Redis.

**Alternativas descartadas:**
- `delete` explícito das chaves: exige saber todas as combinações de filtro já cacheadas, ou `SCAN` por padrão, que é caro e não atômico.
- `cache.clear()`: apaga também chaves de outros usos e de outros ambientes no mesmo banco lógico.
- Só TTL: deixaria a tela desatualizada até o fim do TTL depois de uma confirmação, o que o critério principal proíbe.

### D6. Quando invalidar: sinais dos modelos e `transaction.on_commit`

`schedule/apps.py` (e `bookings/apps.py`, para `Booking` e `BookingRequest`) conecta, no `ready()`, `post_save` e `post_delete` destes modelos a um receptor que chama `public_cache.invalidate_on_commit()`:

| Modelo | Dado público que ele afeta | Operações que escrevem nele |
|---|---|---|
| `Semester` | semestre padrão, período, opções | `SemesterManager.resolve`, `Semester.define_period`, `apply_period` da importação |
| `Allocation` (`teachers` por invalidação explícita, ver abaixo) | opções (semestres, salas, docentes, cursos), Grade | importação (`AllocationManager.apply`, `update_details`), `change_recurrence`, `create_recurrence`, `end_recurrence`, `RecurrenceChange/Creation/Addition/Removal.execute` |
| `AllocationException` | ocorrências canceladas do calendário | `AllocationExceptionManager.cancel`, `RecurrenceChange.execute` |
| `TimeSlot` | faixas da Grade | `TimeSlotManager.resolve` |
| `Space` | opções de sala, nome no card | `register`, `update_details`, `add_name`/`remove_name` (salvam o espaço), `deactivate`, `reactivate`, `delete_space`, decisões de espaço da importação |
| `Teacher`, `Course`, `Subject`, `ClassGroup` | nomes no card e nas opções | `NamedManager.resolve`, `register`, `update_details`, `delete_*` |
| `ClassOffering`, `TeachingAssignment` | disciplina, curso, turma e docente do agendamento público | `record`, `record_many`, `sync_assignments` |
| `Booking`, `BookingRequest` | agendamentos aprovados no calendário | `approve`, `accept_suggestion`, `cancel`, exclusão |
| `User` | e-mail do docente e nome e e-mail de quem solicitou | cadastro, edição, desativação, reativação, importação de usuários |

`SpaceName` não aparece nas telas públicas e fica fora.

**Campos que não invalidam.** Um `post_save` com `update_fields` que não toca nenhum campo público do modelo não invalida. O caso concreto é `User`: o Django grava `last_login` com `save(update_fields=['last_login'])` em cada login, e a troca de senha grava só `password`. Para `User`, só `name`, `username`, `email` e `is_active` invalidam; um `save()` sem `update_fields` invalida sempre. Os campos públicos de cada modelo ficam numa constante de `public_cache`, ao lado da lista de modelos.

O receptor não apaga nada. Ele registra `transaction.on_commit(bump_generation)`:

```text
operação do model (transaction.atomic)
  → save()/delete() → post_save/post_delete → on_commit(bump_generation) registrado
  → commit           → bump_generation() → INCR public:generation
  → rollback         → o Django descarta o callback; a geração não muda; o cache anterior continua valendo
```

- Fora de transação (autocommit), o Django executa o callback na hora, depois da escrita já gravada.
- Na prévia e na atualização da prévia da importação, o `set_rollback(True)` descarta os callbacks. Na confirmação, o callback roda no `import_worker`, depois do commit, e a geração vai para o Redis compartilhado, que o `web` lê.
- Uma linha recusada da importação desfaz o seu savepoint, e o Django descarta os callbacks registrados nele.
- **Um callback por transação:** a importação salva milhares de objetos. O receptor só registra o callback quando ele ainda não está pendente na conexão (`connection.run_on_commit`), o que o Django mantém correto nos savepoints desfeitos. Se a verificação se mostrar frágil na implementação, a alternativa aceita é registrar sempre: o `INCR` custa menos de 1 ms e o resultado é o mesmo.
- `on_commit(..., robust=True)`: uma falha do callback não quebra os outros callbacks da transação, como o aviso em tempo real e o outbox.

**Escritas que não disparam sinais.** `QuerySet.update`, `bulk_create`, `bulk_update` e SQL direto. O levantamento atual:

| Ponto | Situação |
|---|---|
| `RecurrenceChange.execute`: `AllocationException...update(allocation=version)` | Na mesma transação há `save()` de `Allocation`; coberto. |
| `Space.register`: `SpaceName.objects.bulk_create` | `SpaceName` não é público, e o `Space` é salvo; coberto. |
| `ClassOfferingManager.record_many`: `bulk_create`; `sync_assignments`: `bulk_create` e `update(is_current=...)` | Chamar `invalidate_on_commit()` explicitamente nesses métodos. |
| `set_passwords`: `User.objects.bulk_update(users, ['password'])` | A senha não é pública; não precisa. |
| `clear_data`: `TRUNCATE` | Chamar `invalidate_on_commit()` explicitamente depois do `TRUNCATE`. |
| `Allocation.teachers`: `add` em `AllocationManager.apply`, `set` em `RecurrenceChange.execute` e `RecurrenceCreation.execute` | Na mesma transação a alocação é criada; coberto. |
| `Allocation.teachers.set` em `Allocation.update_details`, quando só os docentes mudam | Chamar `invalidate_on_commit()` explicitamente. |

**Por que não `m2m_changed` (desvio registrado na implementação).** O plano era ouvir `m2m_changed` de `Allocation.teachers`. Com um receptor nesse sinal, o Django desliga o caminho rápido de `teachers.add()`/`set()` e passa a ler os vínculos existentes antes de inserir: o teste de orçamento da importação (`schedule/tests/test_import_queries.py`) subiu de até 6 para 7 consultas por linha. Como toda mudança de docentes já acontece junto da gravação da alocação, exceto em `update_details`, o sinal foi trocado pela chamada explícita nesse único ponto, e as chamadas a `teachers.*` entraram na varredura.

Toda escrita em massa nova num modelo da tabela acima deve chamar `invalidate_on_commit()`. A tarefa 2.6 cria um teste que procura `bulk_create`, `bulk_update`, `.update(` e `cursor` nos módulos desses modelos e falha se um ponto novo aparecer fora de uma lista revisada.

### D7. Atomicidade e corridas

Dois casos de leitura concorrente com escrita:

1. **Leitura antes do commit, gravação depois.** A requisição A lê a geração `g`, consulta o banco (dados antigos, a escrita de B ainda não foi confirmada) e grava em `g`. B confirma e incrementa para `g+1`. A entrada de A fica em `g`, que ninguém mais lê. Correto.
2. **Leitura depois do commit, gravação depois do `INCR`.** A lê a geração `g` antes do commit de B, B confirma e incrementa, A consulta o banco já com os dados novos e grava em `g`. A entrada fica em `g`, que ninguém mais lê. Correto, sem perda.

A geração é lida **antes** das consultas e reaproveitada para gravar; nunca relida depois. A versão por geração resolve a corrida clássica de `delete` seguido de recarga com dado antigo, que uma invalidação por exclusão não resolveria.

**`INCR` perdido.** Se o Redis estiver inacessível no momento do callback, o `INCR` falha (D8). Dois casos:
- Redis reiniciado: sem persistência, as entradas antigas sumiram. Correto.
- Rede interrompida só entre o processo que escreveu e o Redis, com o Redis vivo: as entradas da geração atual continuam e podem ser lidas pelo `web`. O TTL de cada cache limita esse tempo (D10), e a falha é registrada em log como `WARNING`. É o único caso em que o conteúdo pode ficar desatualizado, e por no máximo um TTL.

### D8. Redis indisponível

```text
Redis disponível   → lê a geração, lê ou grava a entrada
Redis indisponível → consulta o PostgreSQL, monta como hoje, cabeçalho X-Public-Cache: bypass
```

- Toda chamada ao Redis passa por `public_cache`, que captura as exceções de conexão e de tempo limite do cliente (`redis.exceptions.ConnectionError`, `TimeoutError` e `RedisError`) e trata como miss sem gravação.
- **Pausa após falha:** depois de uma falha, o processo deixa de chamar o Redis por 30 segundos (variável no módulo, por processo, sem lock). Sem a pausa, cada requisição esperaria até 2 × 100 ms pela leitura da geração e da entrada. Com ela, o custo da indisponibilidade é uma requisição lenta a cada 30 segundos por processo.
- Uma falha no `INCR` da invalidação também é registrada e ativa a pausa; ela nunca propaga exceção para a operação que escreveu, que já foi confirmada.
- Erro de serialização ou de dado corrompido na leitura é tratado como miss.

### D9. Concorrência entre requisições (stampede)

Duas requisições que encontram o mesmo miss consultam o banco as duas e gravam o mesmo valor. Não há lock, `SET NX`, stale-while-revalidate nem jitter:

- O custo de um miss é de 4 a 10 consultas e de 10 a 70 ms; o PostgreSQL atende algumas requisições simultâneas assim sem esforço.
- A audiência é a de um campus, e a maior concentração prevista é o início do semestre, depois da importação.
- A invalidação por geração é o único momento em que todas as chaves expiram juntas, e ele é raro.
- Jitter resolve expiração simultânea de muitas chaves por TTL, que aqui não acontece em volume: as chaves nascem em momentos diferentes.

O benchmark da tarefa 4.2 mede requisições concorrentes logo depois de uma invalidação. A proteção só entra se ele mostrar consultas ou p95 acima do sem cache.

### D10. TTL por cache

O TTL é proteção adicional, não o mecanismo de consistência (D5 e D6).

| Cache | TTL | Justificativa |
|---|---|---|
| `public:generation` | sem TTL | É o contador; se for removido, D5 recria. |
| `options` | 1 hora | Muda só com importação e cadastros. A consulta é barata, mas acontece em toda requisição. O risco de desatualização só existe no caso de `INCR` perdido (D7), e opções antigas só mostram uma sala ou docente a mais ou a menos no filtro. |
| `calendar-grid` | 10 minutos | Contém agendamentos aprovados, que mudam ao longo do dia. No caso de `INCR` perdido, um agendamento aprovado ou cancelado aparece com até 10 minutos de atraso. A chave já expira na troca de data. |
| `original-grid` | 30 minutos | Só muda com importação e cadastros; a tela é a menos acessada, e o ganho de um TTL maior é pequeno. |

**TTLs finais**, definidos na implementação e menores que os do plano (6 h e 1 h): opções do semestre, 1 hora; Grade do calendário público, 10 minutos; Grade do horário original, 30 minutos. Eles só limitam o caso de `INCR` perdido; a consistência continua vindo da invalidação.

Os TTL ficam em constantes de `public_cache`, e não em variáveis de ambiente, para ficarem junto da justificativa.

### D11. Medição e critério de adoção

**Ambiente:** banco `perf_check` criado a partir de uma cópia do banco de desenvolvimento com as 1.498 alocações confirmadas, como na Change `otimizar-consultas-do-sistema`, e o Redis do Compose no banco lógico `/1`. Nunca o banco de desenvolvimento. O banco é apagado no fim.

**Instrumento:** comando de gerenciamento `measure_public_pages`, só para a Change e removido depois, como os auxiliares da otimização de consultas. Ele usa `django.test.Client` anônimo e `CaptureQueriesContext`, com um conjunto fixo de URLs:

1. `/` sem filtro
2. `/?sala=<sala mais usada>` (semana padrão)
3. `/?docente=<docente com mais aulas>&inicio=<1º dia útil do mês>&fim=<último dia útil do mês>`
4. `/?curso=<curso>&turma=<turma>`
5. `/horario-original/?sala=<sala mais usada>`

Para cada URL e cenário: 200 requisições sequenciais depois de 10 de aquecimento, com média, p50, p95 e consultas por requisição, e o cabeçalho `X-Public-Cache` contado como hit, miss e bypass.

**Cenários:** (a) linha de base sem a Change; (b) cache frio (primeira requisição depois de `INCR`); (c) cache quente; (d) Redis parado; (e) 20 requisições concorrentes logo depois de um `INCR`, em threads.

**Critério de adoção:**
- P0 (opções): consultas por requisição caem em 4 no cache quente, e o p95 do cache frio e do Redis parado não sobe mais de 5 ms sobre a linha de base.
- P1 (Grade): entra só se o p95 do cache quente cair pelo menos 50% sobre o resultado do P0, nas URLs 2 a 5, com o mesmo limite de 5 ms no frio e no Redis parado. Uma Grade que não passar fica fora e o resultado é registrado aqui.
- Os números de cada cenário são registrados neste `design.md`. "Usa Redis" não conta como melhoria; só os números.

### D12. Observabilidade

- Logger `schedule.public_cache`:
  - `INFO` em cada invalidação confirmada: `CACHE INVALIDATED generation=<n>`. Uma linha por transação, e não por objeto (D6).
  - `WARNING` na falha de conexão: `REDIS UNAVAILABLE <operação>: <erro>`. No máximo uma por pausa de 30 segundos por processo (D8).
  - `DEBUG` em hit e miss: `CACHE HIT|MISS <recurso>`. Desligado por padrão; ligado só na medição.
- Cabeçalho `X-Public-Cache: hit | miss | bypass` nas duas views públicas, com o estado da Grade quando ela é cacheada e o das opções enquanto só elas são. Não expõe chave, geração nem dado.
- Contagem agregada: o comando `make manage cmd="public_cache_stats"` (P2) mostra a geração atual e `keyspace_hits`, `keyspace_misses` e `evicted_keys` do `INFO stats` do Redis.

### D13. Dados públicos e segurança

- Só entram no cache valores que a tela já mostra a qualquer visitante: nomes de semestre, sala, docente, curso e turma com o pk usado na chave, e o HTML da Grade. O HTML da Grade é renderizado só a partir de `calendar` e `week`, sem `request`, usuário, sessão, CSRF ou mensagens.
- O cache é lido só pelas duas views públicas, que não leem `request.user`. Um usuário autenticado que abra `/` recebe o mesmo conteúdo de um anônimo, como hoje.
- **Cache poisoning:** a chave é o hash dos valores normalizados contra o banco, e não de cabeçalhos ou da query string; `Host`, cookies e cabeçalhos não entram na chave nem no conteúdo. O conteúdo cacheado é o mesmo que seria renderizado sem cache.
- **Crescimento de chaves:** limitado ao produto dos registros cadastrados pelas datas válidas (31 dias no máximo, dentro do semestre) e pelo dia; `maxmemory` e LRU limitam a memória.
- **Rede:** sem porta publicada; senha e TLS em produção (D3).
- Nenhuma senha ou URL de Redis aparece em log: o `WARNING` registra a operação e a classe do erro.

### D14. Onde o cache é lido

```text
schedule.public.read_filters(params, today, lookup)
  → published_semesters(lookup)           options {'semester': '*'}: (pk, code, start_date, end_date)
  → cached_semester_options(semester, lookup)
                                          options {'semester': code}: (pk, name) de salas e docentes,
                                          (pk, name, stage) de cursos
      as tuplas voltam a ser instâncias de Semester, Space, Teacher e Course só com esses
      campos, sem consulta, e o resto do código continua recebendo os mesmos objetos
schedule.public.public_calendar / original_timetable(..., lookup, deferred=True)
  → calendar.assemble e calendar.grid_params, sem montar a Grade
schedule.public_views.grid_html
  → lookup.fetch('calendar-grid' ou 'original-grid', grid_params, render)
      render executa calendar.assemble() e renderiza schedule/public/grid.html
      o template da página escreve {{ grid_html }}
```

`public_cache.Lookup` reúne as leituras da requisição: a geração é lida uma vez, e o cabeçalho é `hit` só quando todas as leituras foram hits, `bypass` quando o cache não foi usado (sem Redis, Redis com falha ou em pausa) e `miss` nos demais casos. As turmas do curso escolhido (`course_groups`) continuam numa consulta, fora do cache: só existem com o filtro de curso.

Os testes nunca usam o Redis do ambiente: com `manage.py test`, o alias `public` é `DummyCache`, e os testes do cache trocam por `LocMemCache` com `override_settings`.

A leitura da geração acontece uma vez por requisição e é reaproveitada pelas duas chaves.

`imported_semesters()` entra no cache `options` com uma chave de semestre fixa (`*`), porque a lista de semestres é igual para todos os códigos.

## Risks / Trade-offs

- **Escrita em massa nova sem invalidação** → teste de varredura da tarefa 2.6 e regra registrada nas convenções.
- **`INCR` perdido com o Redis vivo** → desatualização limitada ao TTL (D7, D10) e `WARNING` no log.
- **Taxa de hit baixa por invalidação global** → medir na tarefa 4.3; granularidade por semestre só com evidência.
- **Diferença de conteúdo entre cache e banco por troca de objetos de model por objetos leves** → testes de equivalência do contexto e do HTML com e sem cache (tarefas 2.4 e 3.3).
- **Ganho pequeno**: as telas já são rápidas. A Change pode concluir que só o P0 se justifica; isso é um resultado aceito, e a medição fica registrada.
- **Mais um serviço no Compose** → sem healthcheck obrigatório para a aplicação subir; a aplicação funciona sem ele.

## Migration Plan

1. Subir o Redis e a configuração sem nenhum uso (tarefa 1), com `make up`.
2. Ativar o cache das opções (P0). Reversão: remover `DJANGO_REDIS_URL`, que troca o alias para `DummyCache`, sem novo deploy de código.
3. P1 condicionado à medição.
4. Sem migration de banco.

## Open Questions

- **Cache HTTP no proxy de produção: não é possível determinar pelo repositório.** As duas views públicas passaram a responder com `Cache-Control: no-cache`, como medida defensiva para caches que respeitam o cabeçalho. A consistência não depende dele, e a configuração do proxy de produção precisa ser conferida na infraestrutura (README, seção "Cache das telas públicas"). Investigação feita em 07/10/2026:
  - Não há configuração de proxy, CDN ou deploy versionada: nenhum arquivo de Nginx, Traefik, Apache, Caddy, Varnish, Cloudflare, Kubernetes, `Procfile`, Gunicorn ou uWSGI, nem `.env`. O histórico do Git não tem nenhum desses arquivos, e o repositório não tem remoto configurado. Só existem o `compose.yaml` de desenvolvimento (com `runserver` na porta 8000 e nenhum serviço de proxy) e o `Dockerfile`.
  - A aplicação não emite cabeçalho de cache: nenhuma ocorrência de `Cache-Control`, `Expires`, `ETag`, `Surrogate-Control`, `cache_page`, `never_cache`, `patch_cache_control`, `ConditionalGetMiddleware` nem dos middlewares de cache do Django, e `MIDDLEWARE` não tem nenhum deles. As respostas de `/` e `/horario-original/` saem sem cabeçalho de validade.
  - O cache no proxy aparece só como recomendação: na Change arquivada `calendario-publico` ("aplicar cache curto no proxy, na rota `calendario/`", rota que hoje é `/`) e na seção 4 de `openspec/conventions.md`. A Change `processar-importacao-em-segundo-plano` registra "Proxy de produção: ausente do repositório".
  - Consequência: se o proxy de produção tiver cache configurado por regra própria (por exemplo, `proxy_cache_valid` no Nginx, que vale mesmo sem `Cache-Control` na resposta), ele pode servir HTML antigo depois de uma invalidação no Redis, até o TTL dele. Isso só pode ser confirmado na configuração do servidor, fora do repositório.
  - Pendente de decisão, fora do escopo atual: as views públicas passarem a enviar `Cache-Control: no-cache` (ou `max-age` curto), para que um cache intermediário que respeite os cabeçalhos revalide a cada requisição. Isso não impede um proxy configurado para ignorar os cabeçalhos.

## Resultados da implementação

### Benchmark (D11)

Feito em 07/10/2026 no banco `perf_check`, cópia do banco de desenvolvimento por `pg_dump` (1.498 alocações confirmadas em 2026/2, sem agendamentos), com o Redis do Compose no banco lógico `/1` e `DJANGO_DEBUG=0`. A linha de base roda o código anterior à Change (commit `0e66717`, num `git worktree`). O instrumento foi um script fora do repositório, no lugar do comando `measure_public_pages`, para não criar e remover código: `django.test.Client` anônimo, `CaptureQueriesContext`, 10 requisições de aquecimento e 200 medidas por URL. O cache frio incrementa a geração antes de cada requisição. Tempos em ms. O banco e o banco lógico foram apagados no fim.

URLs: (1) `/` sem filtro; (2) `/?sala=<sala com mais aulas>`; (3) `/?docente=<docente com mais aulas>&inicio=2026-10-01&fim=2026-10-30`; (4) `/?curso=<curso>&turma=<turma com mais aulas>`; (5) `/horario-original/?sala=<sala com mais aulas>`.

| URL | Linha de base: média / p95 / consultas | Só P0 quente: p95 / consultas | P0+P1 quente: média / p95 / consultas | Frio: p95 / consultas | Redis recusando conexão: p95 | Redis sem resposta (timeout): p95 |
|---|---|---|---|---|---|---|
| 1 | 7,5 / 8,0 / 4 | 6,3 / 0 | 5,8 / 6,6 / 0 | 9,5 / 4 | 9,1 | 9,1 |
| 2 | 19,8 / 20,3 / 10 | 20,4 / 6 | 5,9 / 6,8 / 0 | 23,6 / 10 | 23,1 | 22,3 |
| 3 | 30,3 / 33,5 / 10 | 30,3 / 6 | 6,0 / 6,9 / 0 | 35,9 / 10 | 33,2 | 32,9 |
| 4 | 17,8 / 18,4 / 10 | 17,8 / 6 | 6,5 / 7,0 / 1 | 21,2 / 10 | 20,0 | 19,9 |
| 5 | 17,7 / 18,9 / 8 | 17,6 / 4 | 5,8 / 6,6 / 0 | 24,2 / 8 | 19,9 | 20,2 |

O cabeçalho conferiu com o cenário em todas as requisições: 200 `hit` no quente, 200 `miss` no frio e 200 `bypass` nos cenários sem Redis. A linha de base e o frio foram repetidos mais duas vezes, porque o p95 da URL 5 no frio passou do limite na primeira medida: a linha de base teve p95 de 18,2 e 18,7, e o frio, de 21,2 e 21,3 (+2,6 a +3,1 ms). Os 73 ms do calendário sem filtro, medidos na Change `otimizar-consultas-do-sistema`, eram de aquecimento: a linha de base mediu 7,5 ms.

**Critério do P0 (opções), cumprido.** No quente, as consultas caem exatamente 4 em todas as URLs (de 10 para 6, de 8 para 4 e de 4 para 0). O p95 no frio só com o P0 ficou entre +1,3 e +3 ms sobre a linha de base, e com o Redis indisponível entre +0,9 e +2 ms. O ganho de tempo do P0 sozinho é pequeno (de 0 a 1,7 ms), como previsto: o custo está na montagem da Grade.

**Critério do P1 (Grade), cumprido nas duas Grades.** O p95 do quente caiu de 20,4 para 6,8 (−67%), de 30,3 para 6,9 (−77%), de 17,8 para 7,0 (−61%) e, no horário original, de 17,6 para 6,6 (−62%) sobre o resultado do P0, acima dos 50% exigidos. As duas Grades foram mantidas. O custo de um miss sobre a linha de base ficou entre +1,5 e +3 ms (leitura da geração, leitura e gravação no Redis), exceto na primeira medida da URL 5 (+5,3 ms), que as duas repetições não confirmaram.

**Concorrência (cenário e), sem proteção contra stampede.** 20 requisições simultâneas em threads de um mesmo processo, logo depois de um `INCR`, repetidas três vezes, contra 20 simultâneas da linha de base:

| URL | Linha de base: p95 / consultas | Com cache, 3 rodadas: p95 / consultas médias / misses |
|---|---|---|
| 1 | 108 / 104 / 119; 4 | 101 / 130 / 125; 0,2 a 0,9; 1 a 5 |
| 2 | 359 / 357 / 354; 10 | 252 / 377 / 351; 2,6 a 6,5; 8 a 19 |
| 3 | 920 / 876 / 908; 10 | 326 / 911 / 432; 2,9 a 6,3; 9 a 20 |
| 4 | 301 / 311 / 311; 10 | 368 / 262 / 224; 3 a 6,7; 6 a 19 |
| 5 | 300 / 321 / 302; 8 | 191 / 134 / 304; 0,8 a 3,5; 2 a 15 |

As requisições simultâneas a um miss consultam o banco todas, como previsto em D9. As consultas por requisição ficaram sempre abaixo da linha de base. O p95 passou da linha de base em 4 das 15 medidas, de 1% a 22%, nas rodadas em que quase todas as 20 requisições foram misses: é o custo da própria consulta mais o acesso ao Redis, e a variação fica na mesma ordem da variação da própria linha de base entre rodadas (URL 3: de 876 a 920; URL 1: de 104 a 119). O pior caso é equivalente a não ter cache, sem carga extra no banco. Nenhuma proteção foi adicionada; a reavaliação fica na tarefa 4.2.

### Outros pontos da implementação

- `web` e `import_worker` usam o mesmo Redis: conferido nos containers, com o `import_worker` incrementando a geração e o `web` lendo o valor novo, e no teste `ImportInvalidationTests`, em que a confirmação pelo worker incrementa a geração do mesmo alias que a tela lê.
- `outbox/tests/test_worker.py` (`ConcurrencyTests`) passou a declarar `serialized_rollback = True`, como as demais classes `TransactionTestCase` do projeto. Sem ele, o `flush` dessa classe recriava os tipos de conteúdo pelo `post_migrate`, e as classes seguintes com `serialized_rollback` (as desta Change, por ordem alfabética) falhavam ao recarregar os dados.
- `docker compose port redis 6379` não devolve porta publicada, e o `web` e os workers dependem de `redis` com `service_started`.
