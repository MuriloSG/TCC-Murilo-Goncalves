# Calendário público

Consulta sem login da ocupação dos espaços. Implementação: `schedule/public.py` (consulta e montagem), `schedule/public_views.py` (views), `schedule/public_cache.py` (cache) e `ui/layouts/public.html`. Regras em [regras de negócio](../regras/regras-de-negocio.md#calendário-público).

| Tela | Rota | Nome | Conteúdo |
|---|---|---|---|
| Calendário | `/` | `public_calendar` | Ocorrências datadas do ensalamento, sem as canceladas, e os agendamentos aprovados |
| Horário original | `/horario-original/` | `public_original_timetable` | Semana típica só com as alocações importadas, sem versões alteradas, cancelamentos e agendamentos |

As duas telas alternam entre si mantendo os filtros (exceto as datas).

## Filtros

- Semestre, sala, docente, curso, nível (`graduacao`, `ensino-medio`) e turma do curso.
- É preciso escolher uma sala, um docente ou um curso. Sem isso, a tela mostra "Escolha uma sala, um docente ou um curso." e não consulta as aulas.
- Data inicial e final (só no calendário, com o período do semestre definido): intervalo de até 31 dias. Sem datas, vale a semana de hoje, levada para dentro do período do semestre.
- Semestre sem período: mostra a semana típica com aviso.
- Agendamentos entram só na consulta por sala ou por docente, não na consulta por curso ou nível.
- A célula vazia é "disponível" na consulta só por sala e "sem aula" nas demais.

## O que a página expõe

- Aula: disciplina, horário, curso, turma, sala e nome dos docentes.
- Agendamento, nas faixas que cruza: selo "Agendamento", disciplina, curso, turma, sala e o nome do docente do vínculo ou, sem vínculo, o nome de quem solicitou. A descrição e o e-mail não aparecem.
- Nenhum ID de registro.

## Comportamento HTTP

- Só GET e HEAD. As rotas são `csrf_exempt` apenas para que um POST receba 405, e não 403.
- As views não declaram `permission_required` nem `audit_resource` e não leem `request.user`: não exigem login e não entram na auditoria.
- A resposta traz `X-Public-Cache` (`hit`, `miss` ou `bypass`) e `Cache-Control: no-cache`.
- Não há limite de requisições na aplicação. A convenção prevê o rate limit no proxy de produção, que não está no repositório.

## Visual

- Abre no modo escuro, com botão para o claro; a escolha fica no `localStorage` (`tema`). As telas autenticadas são só claras.
- Abaixo de 640 px, a Grade mostra dois dias por vez, rola na horizontal e abre em "Hoje".

## Cache

O alias `public` de `CACHES` aponta para o Redis (`DJANGO_REDIS_URL`). Sem a variável, ou durante os testes, usa `DummyCache` e as telas consultam o banco.

| Recurso | Conteúdo | TTL |
|---|---|---|
| `options` | Opções dos filtros do semestre | 1 hora |
| `calendar-grid` | HTML da Grade do calendário | 10 minutos |
| `original-grid` | HTML da Grade do horário original | 30 minutos |

- Chave: `public:<recurso>:g<geração>:<hash>`, com o hash SHA-256 dos parâmetros já normalizados contra o cadastro. Nenhum valor da URL entra em texto na chave.
- Invalidação: `invalidate_on_commit()` agenda, depois do commit, o incremento da geração global (`public:generation`). As chaves de gerações antigas deixam de ser lidas e expiram pelo TTL. Um rollback descarta o agendamento.
- Gatilhos: `post_save` e `post_delete` de `Semester`, `Allocation`, `AllocationException`, `TimeSlot`, `Space`, `Teacher`, `Course`, `Subject`, `ClassGroup`, `ClassOffering`, `TeachingAssignment`, `Booking`, `BookingRequest` e dos campos `name`, `username`, `email`, `is_active` de `User`. Escritas que não disparam sinais (`bulk_create`, `bulk_update`, `QuerySet.update`, `teachers.set`, SQL direto) chamam `invalidate_on_commit()` explicitamente. O teste `BulkWriteScanTests` (`schedule/tests/test_public_cache.py`) falha diante de uma escrita nova não revisada.
- Falha do Redis: o processo deixa de chamá-lo por 30 segundos, registra `REDIS UNAVAILABLE` no log e responde do banco.
- Só as telas públicas usam cache. As autenticadas sempre consultam o banco.

## Testes

`schedule/tests/test_public_calendar.py`, `test_public_cache.py`.
