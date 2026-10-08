## Context

### Como a medição foi feita

Em 07/10/2026, no Docker do projeto (PostgreSQL 17, Django 5.2.17, `DEBUG=1`), num banco criado só para isso (`perf_check`, migrado do zero e apagado no fim). O banco de desenvolvimento `agendamento` não foi tocado. Os scripts ficaram fora do repositório e rodaram com `manage.py shell` no container `web`:

- **Importação:** leitura pelo `WorkbookSource` real, `Import.objects.request_preview`, e `execute_pending` chamado direto (o mesmo código do worker), dentro de `CaptureQueriesContext` com `connection.queries_limit` elevado para 10⁷. O limite padrão (9.000) truncava a contagem. As decisões de espaço pendentes foram tomadas como "novo" por `SpaceDecision.objects.decide`, para chegar à confirmação. A ordem foi: primeira importação (prévia, atualização, confirmação) e depois reimportação da mesma planilha (prévia, confirmação). O perfil foi tirado com `cProfile` numa rodada separada. O `cProfile` dobra o tempo, por isso os tempos das tabelas são da rodada sem ele.
- **Telas:** `django.test.Client` com um superadmin (e anônimo nas rotas públicas) contra o mesmo banco, já com as 1.498 alocações confirmadas, contando as consultas por página.
- **Índices:** `pg_indexes`, `pg_stat_user_tables` e `EXPLAIN`/`EXPLAIN ANALYZE` de leitura no `perf_check`. Nenhum `EXPLAIN ANALYZE` foi feito sobre escrita.

O tempo de SQL somado pelo `CaptureQueriesContext` não serve de medida: ele arredonda cada consulta para milissegundos e soma 0,1 s em execuções de 9 s. O que se mede é a quantidade de consultas e o tempo de parede da operação.

### Volumes envolvidos (planilha corrigida, 1.843 linhas)

| O quê | Quantidade |
|---|---|
| Linhas de atividade | 1.498 |
| Textos de atividade distintos | 585 |
| Cursos / turmas / disciplinas / faixas / docentes distintos | 15 / 56 / 276 / 15 / 129 |
| Espaços (e nomes de espaço) | 86 |
| Ofertas distintas (`ClassOffering`) | 563 |
| Vínculos de docente (`TeachingAssignment`) | 619 |
| Linhas de usuário | 129 |

### Resultado da importação

| Operação | Consultas | Tempo | `SAVEPOINT` + `RELEASE` |
|---|---|---|---|
| Prévia da `planilha_example.xlsx` (1.706 linhas, 121 com erro) | 49.951 | 8,1 s | não separado |
| Prévia, 1ª importação | 56.449 | 9,1 s | não separado |
| Atualização da prévia | 56.458 | 9,3 s | não separado |
| Pedido de confirmação (requisição) | 10 | 0,04 s | 2 |
| Confirmação, 1ª importação | 58.308 | 9,1 s | não separado |
| Prévia, reimportação | 42.288 | 7,2 s | 21.928 (52%) |
| Confirmação, reimportação | 42.294 | 6,6 s | não separado |

Distribuição da prévia da reimportação por instrução: 15.876 `SELECT`, 10.964 `SAVEPOINT`, 10.964 `RELEASE SAVEPOINT`, 2.990 `UPDATE`, 1.491 `INSERT`. Por tabela: `schedule_teachingassignment` 4.478, `schedule_teacher` 3.223, `schedule_allocation` 2.997, `schedule_space` 1.510, e `schedule_course`, `schedule_classgroup`, `schedule_subject`, `schedule_timeslot` e `schedule_classoffering` com 1.498 cada.

Perfil da prévia da 1ª importação (com `cProfile`, tempo acumulado de 18,8 s): `execute_activity` 15,5 s, dos quais `Allocation.objects.apply` 6,1 s, `ClassOffering.objects.record` 4,4 s (`sync_assignments` 3,2 s), `NamedManager.resolve` 2,1 s, `ClassGroupManager.resolve` 1,2 s e `TimeSlotManager.resolve` 1,2 s. `replace_plan` levou 1,9 s e `lock()` 0,4 s.

### Resultado das telas

| Tela | Consultas | Tempo |
|---|---|---|
| Grade do ensalamento, semana / mês | 17 / 17 | 92 / 39 ms |
| Agenda, semana / mês / "minha agenda" no mês | 17 / 17 / 17 | 25 / 64 / 32 ms |
| Calendário público, semana sem filtro / sala / docente no mês | 4 / 10 / 10 | 73 / 24 / 31 ms |
| Horário original, sem filtro / sala | 4 / 8 | 10 / 17 ms |
| Painel / mapa de calor / relatório de solicitações | 21 / 19 / 13 | 75 / 132 / 12 ms |
| Lista de importações / andamento | 12 / 6 | 15 / 5 ms |
| Detalhe da importação com erros / validada | 23 / 27 | 18 / 111 ms |
| Espaços, disciplinas, turmas, auditoria, exceções, solicitações, usuários | 11 a 17 | 6 a 15 ms |

Nenhuma tela tem consulta repetida por item. A quantidade não muda com o tamanho do mês, e a Grade e a Agenda já seguem o que as próprias docstrings prometem: quantidade fixa, com `select_related` e `prefetch_related` (`schedule/occupancy.py`, `schedule/timetable.py`, `bookings/occupancy.py`). As únicas repetições encontradas foram a consulta do perfil, 3 vezes em toda página autenticada, e a leitura das linhas da importação, 3 vezes no detalhe validado.

## Goals / Non-Goals

**Goals:**

- Reduzir as consultas da execução da importação do ensalamento, que é o gargalo confirmado, de forma que elas cresçam com os registros distintos da planilha, e não com as linhas.
- Manter o plano (`Plan.comparable()`) e o estado final do domínio idênticos aos de hoje, linha a linha, nas duas planilhas reais.
- Manter a trava, as transações, os savepoints por linha, a auditoria e o contrato do worker.
- Deixar a medição como teste: orçamento de consultas e plano idêntico.

**Non-Goals:**

- Otimizar telas que já têm quantidade fixa de consultas e respondem em menos de 150 ms.
- Índices novos, cache fora da execução, mudança de arquitetura, Celery ou Redis.
- Corrigir a ordenação da lista de importações (achado fora do escopo, ver Riscos).

## Achados

Cada achado é classificado como **Confirmado** (medido nesta análise), **Precisa de medição** (há indício, mas o ganho não foi isolado) ou **Preventivo** (sem custo medido hoje). A prioridade é a do `tasks.md`.

### A1. Buscas de catálogo repetidas em cada linha de atividade (Confirmado, P0)

Cadeia: `imports/worker.execute` → `Import.execute_pending` → `run_preview`/`run_refresh`/`run_confirmation` → `Import.execute_rows` → `imports/execution.run` → `execute_row` → `SpaceAllocationImport.execute_activity` (`schedule/imports.py:606`) → `Course.objects.resolve`, `ClassGroup.objects.resolve`, `Subject.objects.resolve`, `TimeSlot.objects.resolve` e `Teacher.objects.get(name__iexact=…)` para cada docente da célula.

Cada `resolve` abre `transaction.atomic()` (um `SAVEPOINT` e um `RELEASE`) e faz `filter(...).first()`:

```sql
SELECT ... FROM schedule_course WHERE UPPER(name::text) = UPPER(%s) ORDER BY name LIMIT 1
SELECT ... FROM schedule_classgroup INNER JOIN schedule_course ... WHERE course_id = %s AND UPPER(label::text) = UPPER(%s) ORDER BY ... LIMIT 1
SELECT ... FROM schedule_subject WHERE UPPER(name::text) = UPPER(%s) ORDER BY name LIMIT 1
SELECT ... FROM schedule_timeslot WHERE semester_id = %s AND start_time = %s AND end_time = %s ORDER BY ... LIMIT 1
SELECT ... FROM schedule_teacher WHERE UPPER(name::text) = UPPER(%s) LIMIT 1
```

Evidência: 1.498 consultas de cada uma das quatro primeiras e 1.596 de docente, mais 4 × 1.498 pares de savepoint, para 15 cursos, 56 turmas, 276 disciplinas, 15 faixas e 129 docentes. O `ORDER BY name` vem do `Meta.ordering` e é inútil num `.first()` sobre chave única. São 7.588 `SELECT` e 12.000 instruções de savepoint por execução, todas repetidas.

Na primeira importação, quando o registro não existe, o `full_clean()` do `NamedRecord` acrescenta `taken.exists()` (`UPPER`) e a validação da `UniqueConstraint(Lower('name'))` (`LOWER`): as 276 + 276 consultas de `schedule_subject` no topo da contagem.

### A2. `Allocation.objects.apply` consulta a identidade, o espaço e os docentes por linha (Confirmado, P0)

Cadeia: `execute_activity` → `AllocationManager.apply` (`schedule/models.py:847`) → `Allocation.update_details` (`:1743`).

- Busca da identidade: 1 `SELECT` de `schedule_allocation` por linha (1.498), mesmo depois de `lock()` já ter lido as alocações do semestre com `select_for_update().values_list('pk')`.
- Reimportação: `update_details` acessa `self.space` (FK preguiçosa: 1.510 `SELECT` de `schedule_space`) e `self.teachers.all()` (1.498 `SELECT` com `JOIN`). É um N+1 clássico dentro de um laço do motor.
- 1ª importação: `allocation.full_clean(exclude=['space'])` confere a existência de cada FK (`SELECT 1 FROM schedule_semester/classgroup/subject/timeslot WHERE id = %s`, 4 × 1.498) e a `allocation_unique` (`SELECT 1 FROM schedule_allocation WHERE ...`, 1.498). Os quatro objetos vieram do banco na mesma transação, e a identidade acabou de ser procurada sob a trava do semestre. Depois, `teachers.set()` faz `SELECT` dos atuais e `INSERT ... ON CONFLICT DO NOTHING` (1.498 + 1.408).

Ao todo são cerca de 4.500 consultas na reimportação e 10.500 na 1ª importação, mais 2 × 1.498 de savepoint.

### A3. Oferta e vínculos de docente sincronizados em cada linha (Confirmado, P0)

Cadeia: `execute_activity` → `ClassOffering.objects.record` (`schedule/models.py:1783`) → `get_or_create` → `ClassOffering.sync_assignments` (`:1840`).

Por linha: `atomic` do `record` e do `get_or_create` (2 pares de savepoint), `SELECT` da oferta, `SELECT` dos docentes das alocações atuais da oferta, `INSERT ... ON CONFLICT DO NOTHING` dos vínculos e dois `UPDATE` de `is_current`. São 1.498 chamadas para 563 ofertas distintas. Em números: 1.498 `SELECT` de oferta, 1.498 `SELECT` de docentes, 1.490 + 1.490 `UPDATE`, 1.371 `INSERT` de vínculo e 563 `INSERT` de oferta, cerca de 7.900 consultas mais 6.000 de savepoint. Pelo perfil, `record` responde por 4,4 s dos 9,1 s.

A sincronização de uma oferta só depende das alocações atuais dela. Rodá-la depois da última linha que toca a oferta dá o mesmo resultado que rodá-la a cada linha, e o plano das linhas não lê ofertas nem vínculos.

### A4. Savepoints aninhados (Confirmado, P0 como consequência)

São 21.928 das 42.288 instruções da prévia da reimportação. Por linha de atividade há cerca de 7 pares: o de `execute_row` (necessário, isola a recusa da linha) e os de `resolve` ×4, `apply`, `record` e `get_or_create`. A1 a A3 removem as chamadas repetidas, e com elas os savepoints. Fica um par por linha, mais os das operações que de fato gravam.

### A5. Confirmação grava `created_object` linha a linha (Confirmado, P1)

`Import.run_confirmation` (`imports/models.py:408`) faz `row.save(update_fields=['created_object'])` para cada linha com registro criado: 1.842 `UPDATE` na 1ª confirmação.

### A6. `replace_plan` com `bulk_update` de 1.843 linhas e 6 campos JSON (Precisa de medição, P1)

`Import.replace_plan` (`imports/models.py:272`) monta um `UPDATE ... SET campo = CASE WHEN id = ... THEN ...` para 6 campos e 1.843 linhas numa instrução. Ele levou 1,9 s acumulado com `cProfile`, cerca de 20% da prévia. Não foi isolado sem o perfilador, e não se sabe quanto é montagem da expressão no Python e quanto é banco. Precisa de medição antes de mudar (por exemplo, `batch_size`).

### A7. Espaços da classificação sem os outros nomes pré-carregados (Confirmado, P1)

Cadeia: `SpaceAllocationImport.lock` → `schedule/spaces.classify` → `registry()` (`SpaceName.objects.select_related('space')`) e `schedule/spaces.apply` → `space.other_names` (`self.names.all()`). Depois, `execute_space` → `space_changes` → `space.refresh_from_db()` e `other_names` de novo.

Evidência: 258 `SELECT` de `schedule_spacename WHERE space_id = %s` na confirmação da reimportação, para 86 espaços. Cada nome encontrado com espaço consulta os nomes uma vez em `apply`, e cada linha da lista de salas consulta de novo em `space_changes`. O número cresce com o cadastro de espaços, não com as aulas. O impacto é menor que A1–A3, mas é um N+1 confirmado.

### A8. Usuários da aba de usuários consultados linha a linha (Confirmado, P2)

`execute_user` (`schedule/imports.py:516`) faz `User.objects.filter(email__iexact=…).first()` e, para o existente, `user.role` (`self.roles.first()`), mais `USERS.clean_values`. Evidência: 130 `SELECT` de `accounts_user` e 258 de `accounts_role` para 129 linhas de usuário. `lock_users` já consulta esses mesmos usuários com `select_for_update().values_list('pk')`.

### A9. Classificação dos espaços recalculada na mesma requisição (Confirmado, P2)

- Detalhe da importação: `confirmation_refusal` → `check_confirmation` → `classify_import`, e `space_panel` → `classify_import`. São duas classificações por GET, cada uma lendo os valores JSON de todas as linhas, o cadastro de nomes e as decisões, e comparando nomes parecidos. Evidência: o detalhe validado faz 3 leituras da coluna `values` das linhas (27 consultas, 111 ms), contra 18 ms do detalhe com erros, que não classifica.
- Decisão: `SpaceDecision.objects.decide` classifica, e `refresh_after_decision` (`schedule/views.py:1278`) classifica de novo. São 2 classificações por clique.

O custo é moderado (cerca de 0,17 s por classificação no perfil) e não é N+1, mas é trabalho repetido dentro de uma requisição.

### A10. Perfil do usuário lido 3 vezes em toda página autenticada (Confirmado, P2)

`ui/templates/ui/layouts/app.html` usa `user.role.name` em três lugares (linhas 18, 39 e 69), e `User.role` (`accounts/models.py:375`) é uma `property` com `self.roles.first()`. São 3 consultas iguais em toda página autenticada, de 11 a 27 no total, ou seja, de 11% a 27% das consultas da página. O ganho absoluto é pequeno (milissegundos), mas vale em todas as telas.

### A11. `__iexact` não usa os índices `LOWER(...)` (Confirmado no plano de execução, P2 Preventivo)

O Django traduz `__iexact` no PostgreSQL como `UPPER(col::text) = UPPER(%s)`, e as restrições de unicidade sem caixa são índices de expressão `LOWER(name)` (`subject_name_unique_ci`, `teacher_name_unique_ci`, `course_name_unique_ci`, `space_name_unique_ci`, `space_alias_unique_ci`, `class_group_label_unique_ci`, `user_email_unique_ci`). Com `enable_seqscan = off`, `UPPER(name) = UPPER('Química I')` continua em `Seq Scan`, enquanto `LOWER(name) = LOWER(...)` usa `Index Scan using subject_name_unique_ci`. A turma usa o índice de `course_id` e filtra o rótulo depois.

Hoje o custo é desprezível (tabelas de 15 a 276 linhas, menos de 1 ms por consulta), e A1 tira estas consultas do laço. Fica como preventivo para as buscas que sobram fora dele: `SpaceManager.named`, `refuse_taken`, `NamedRecord.clean`, `schedule/views.py:474`, `User.objects.filter(email__iexact=…)`. A troca exige cuidado de compatibilidade, porque `UPPER` e `LOWER` não são simétricos para todo caractere Unicode. Não entra como índice novo.

### A12. `Import.summary()` agrega no Python (Precisa de medição, P2)

`Import.summary` (`imports/models.py:211`) lê `action`, `errors` e `pending` de todas as linhas e conta no Python. É chamado no detalhe, no andamento que percebe o fim e na auditoria da confirmação. A lista de importações já faz a mesma conta no banco (`with_summary`). É uma consulta só, mas transfere os JSON de erros de 1.843 linhas. O ganho não foi isolado.

### O que foi verificado e não precisa mudar

- **Grade e Agenda** (`schedule/views.py:145`, `bookings/views.py:72`, `schedule/occupancy.py`, `schedule/timetable.py`, `bookings/occupancy.py`): 17 consultas fixas na semana e no mês, com `select_related('subject', 'time_slot', 'class_group__course')` e `prefetch_related('teachers')`. As ocorrências são calculadas no Python a partir de uma consulta por fonte, que é o desenho documentado (D4, D6 e D12 da Change `visualizar-ocupacao-por-semana-e-mes`). Mover isso para o banco não tem evidência de ganho.
- **Calendário público e horário original** (`schedule/public.py`): de 4 a 10 consultas, com `only()` e `Prefetch`.
- **Conflitos da Agenda** (`bookings/occupancy.find_conflict`): duas consultas com `LIMIT 1`. A de agendamentos tem o índice GiST `booking_no_overlap`.
- **Fila do worker** (`ImportManager.due`): usa o índice parcial `import_pending_operation_idx`.
- **Filtros das linhas no detalhe** (`values__Tipo`): `EXPLAIN ANALYZE` de 0,46 ms pelo índice de `parent_id` com filtro de 345 linhas. Um índice sobre JSON não se justifica.
- **Trava das alocações** (`lock()`): `Index Scan` em `semester_id` com `ORDER BY id FOR UPDATE`, que é a garantia de serialização entre importações. Ela fica.
- **Painel, mapa de calor, relatório de solicitações, listas e auditoria:** quantidade fixa, sem N+1.

### Índices

**Nenhum índice novo.** O gargalo é a quantidade de idas ao banco, e cada consulta medida usa índice ou varre tabelas de algumas centenas de linhas em menos de 1 ms. Um índice novo aumentaria o custo de cada `INSERT` da importação sem diminuir nenhuma consulta medida.

**Índices redundantes** (prefixo de outro índice da mesma tabela, criados automaticamente pelo `ForeignKey`), registrados como candidatos e **não** removidos nesta Change:

| Índice | Coberto por |
|---|---|
| `schedule_allocation_semester_id_*` | `allocation_unique`, `allocation_group_idx`, `allocation_slot_idx`, `allocation_space_idx` (todos começam por `semester_id`) |
| `imports_importrow_parent_id_*` | `import_row_line_unique (parent_id, line_number)` |
| `schedule_classoffering_semester_id_*` | `class_offering_unique`, `class_offering_group_idx` |
| `schedule_classgroup_course_id_*` | `class_group_label_unique_ci (course_id, lower(label))` |
| `schedule_timeslot_semester_id_*` | `time_slot_unique (semester_id, start_time, end_time)` |
| `schedule_teachingassignment_offering_id_*` | `teaching_assignment_unique (offering_id, ...)` |
| `schedule_teachingassignment_teacher_id_*` | `assignment_teacher_idx (teacher_id, offering_id)` |
| `schedule_spacedecision_importation_id_*` | `space_decision_unique_ci (importation_id, lower(found_name))` |
| `accounts_userrole_user_id_*` | `user_role_one_per_user (user_id)` |

Removê-los diminuiria o custo de escrita da importação (a `schedule_allocation` mantém 9 índices em cada um dos 1.498 `INSERT`), mas o ganho não foi medido, e o planejador às vezes prefere o índice menor (o `EXPLAIN` da trava escolheu `schedule_allocation_semester_id_*`). A decisão depende de `pg_stat_user_indexes` em produção e de uma medição de escrita, e fica fora desta Change.

## Decisions

### D1. Memória de registros dentro de `RunState`, com a mesma chave da consulta

Os registros resolvidos ficam em dicionários do `RunState` da execução (que já é um `contextvar` descartado no fim de `execution()`), por modelo:

- curso pelo nome normalizado;
- turma por `(course.pk, rótulo normalizado)`;
- disciplina pelo nome normalizado;
- faixa por `(início, fim)`, porque o semestre é único na execução;
- docente pelo nome como vem do catálogo.

A chave é o **texto normalizado exato**, e não o `casefold()`. Duas grafias que diferem só na caixa fazem cada uma a sua consulta na primeira vez e caem no mesmo registro pelo `iexact`, como hoje. Assim a memória nunca decide uma igualdade que o banco decidiria de outro jeito (`UPPER` do PostgreSQL e `str.casefold` divergem em caracteres como `ß`). A falta na memória chama o mesmo `resolve` de hoje, com a mesma exceção.

Por que não pré-carregar tudo em `lock()` com uma consulta por tabela: o pré-carregamento precisaria repetir em Python a comparação do `iexact`, e é aí que mora a divergência. Com a chave exata, o custo é uma consulta por grafia distinta, cerca de 490 na planilha real, contra 7.588 hoje. Esse número cabe no orçamento.

Alternativa descartada: o framework de cache do Django. O contrato proíbe "uso de cache" como efeito externo, e um cache que sobrevive à execução veria registros desfeitos pelo rollback da prévia.

### D2. A memória acompanha o rollback da linha

Um registro criado dentro do savepoint de uma linha que depois é desfeita (erro, pendência ou `DatabaseError` em `imports/execution.execute_row`) deixa de existir no banco. Se ficasse na memória, a linha seguinte receberia uma chave inexistente. Por isso as entradas criadas durante uma linha são provisórias e só passam a valer quando a linha é mantida. `execute_row` já sabe se a linha foi desfeita. A importação específica recebe essa informação pelo próprio `RunState`: as entradas novas da linha ficam numa lista, que é confirmada ao fim de `SpaceAllocationImport.execute_row` quando o plano não tem erro nem pendência e o savepoint não falhou. A exceção que escapa de `execute_row` descarta a lista.

O teste obrigatório é uma linha que cria uma disciplina e depois é recusada, seguida de outra linha com a mesma disciplina: a segunda cria de novo, como hoje.

### D3. Alocações carregadas na trava, sem ampliar a trava

`lock()` já faz `Allocation.objects.filter(semester=…).order_by('pk').select_for_update()`. Ele passa a trazer os objetos inteiros, ainda com a trava só nas linhas de `schedule_allocation`, e a carregar em seguida, **sem** `FOR UPDATE`:

- o espaço, por `prefetch_related('space')`, e não por `select_related`, porque `FOR UPDATE` com `JOIN` travaria também as linhas de `schedule_space`, a menos que se use `of=('self',)`. A trava atual não pega espaços, e esta Change não muda o escopo da trava;
- os docentes, por `prefetch_related('teachers')`.

As alocações ficam no `RunState` indexadas pela identidade `(class_group_id, subject_id, weekday, time_slot_id)`, com as versões em ordem de `(valid_from, pk)`, que é a ordem de `apply` hoje. A alocação criada por uma linha mantida entra no índice. A desfeita não entra (D2).

`AllocationManager.apply` ganha um parâmetro opcional com as versões já conhecidas da identidade. Sem ele, continua consultando como hoje. A regra de negócio continua no manager (P2 da Constitution), e a importação só entrega o que já leu. `update_details` passa a usar os docentes e o espaço já carregados.

### D4. `full_clean` sem as consultas que a trava e o banco já garantem

Na criação da alocação pela importação:

- **Existência das FKs:** os quatro objetos vêm do banco na mesma transação, e uma FK inválida seria recusada pelo próprio banco. A conferência entra no `exclude` do `full_clean` dentro de `apply`.
- **`allocation_unique`:** a identidade acabou de ser procurada sob a trava das alocações do semestre, e a duplicidade dentro da planilha já é erro da linha por `state.duplicates`. Só uma importação concorrente do mesmo semestre poderia criar a mesma identidade, e ela espera a trava. Passa-se `validate_constraints=False`, e a `IntegrityError` improvável vira o `DATABASE_ERROR` da linha, que já existe.

As validações de campo (`weekday` nas escolhas, `origin`, `clean()` da faixa de outro semestre) continuam. Isso vale só para `apply`. O cadastro pela tela e a recorrência não mudam.

### D5. Sincronização das ofertas numa etapa final da execução

`ClassOffering.objects.record` continua como está, porque a recorrência o usa. Uma operação nova do manager, `record_many(semester, pairs)`, recebe os pares `(subject_id, class_group_id)` e faz, em conjunto:

1. um `SELECT` das ofertas existentes dos pares;
2. um `bulk_create` das que faltam;
3. um `SELECT` dos docentes das alocações atuais (`valid_until IS NULL`) de todas essas ofertas;
4. um `bulk_create(..., ignore_conflicts=True)` dos vínculos que faltam;
5. dois `UPDATE` em conjunto para `is_current`, cada um restrito às ofertas tocadas.

O resultado de cada oferta é o mesmo de `sync_assignments`, que deve passar a ser implementado sobre a mesma função, para que a regra exista uma vez só.

O motor ganha um ponto de extensão opcional no contrato, `ImportDefinition.finish(executor)`, chamado em `imports/execution.run` depois de todas as linhas e antes de `check_file`, dentro de `definition.execution()` e da transação da operação. O padrão não faz nada. A importação do ensalamento junta em `RunState` os pares das linhas **mantidas** e chama `record_many` ali. A prévia desfaz tudo junto com as linhas, e a confirmação grava junto.

Alternativa descartada: rodar a sincronização dentro de `check_file`. Funcionaria, mas `check_file` é o lugar das verificações do arquivo, e usá-lo para gravar esconderia a escrita.

A falha de banco nessa etapa deixa de ser erro de uma linha e passa a ser erro inesperado da execução (nova tentativa do worker). Hoje essa falha nunca foi observada, porque as gravações são `ignore_conflicts` e `UPDATE` sem restrição nova.

### D6. Confirmação e classificação em lote ou por requisição

- `run_confirmation` passa a usar `ImportRow.objects.bulk_update(rows, ['created_object'])` só nas linhas com registro criado (A5).
- `registry()` passa a ler `Space.objects.prefetch_related('names')` e a montar o mapa de nomes a partir dele, para que `other_names` não consulte (A7). `space_changes` mantém o `refresh_from_db()` do espaço, que lê o estado depois de `apply`, mas usa `previous_names` e o prefetch, sem nova consulta de nomes, quando o espaço não foi alterado por `apply`.
- A classificação vira um parâmetro opcional: `check_confirmation(importation, executor, resolution=None)` e `space_panel(importation, user, resolution=None)` recebem a classificação já calculada no detalhe, e `refresh_after_decision` recebe a da decisão (A9). Sem o parâmetro, calculam como hoje.

### D7. Perfil lido uma vez por instância do usuário

`User.role` passa a ser memorizado na instância, e `change_role` (e qualquer operação que troque o perfil) invalida a memória. O layout não muda (A10). O teste confere que `change_role` seguido de `user.role` devolve o perfil novo.

### D8. O critério de aceite é o plano idêntico mais o orçamento de consultas

Cada tarefa P0 só é aceita se:

1. o `comparable()` do plano for igual, linha a linha, ao gerado pelo código atual, para a `planilha_example.xlsx` (prévia com erros) e para a `planilha_example_sugerida_corrigida.xlsx` (1ª importação, decisões, atualização, confirmação, reimportação);
2. o estado final do domínio for igual: contagem e identidade de alocações, docentes de cada alocação, ofertas, vínculos com `is_current`, espaços com outros nomes e situação, e registros de auditoria da importação com os mesmos metadados;
3. os testes atuais passarem sem mudança nas asserções;
4. o orçamento de consultas da tarefa for cumprido.

A referência do item 1 e do item 2 é gerada **antes** da primeira mudança, com o código atual.

## Medição

### Antes e depois

| Medida | Como | Onde |
|---|---|---|
| Consultas por operação | `CaptureQueriesContext` com `connection.queries_limit` acima de 100.000 | teste de orçamento e procedimento manual |
| Instruções por tipo (`SELECT`, `SAVEPOINT`, ...) | contagem pelo primeiro verbo do SQL capturado | procedimento manual |
| Tempo de parede | `time.perf_counter` em volta de `execute_pending`, sem `cProfile` | procedimento manual |
| Resultado funcional | `comparable()` e o estado do domínio (D8) | teste de equivalência |
| Memória | `tracemalloc` do pico na prévia | só para D3, que passa a manter as alocações do semestre em memória (1.498 objetos com docentes) |

O procedimento manual repete o desta análise: banco `perf_check` criado e apagado no fim, as duas planilhas, primeira importação completa e reimportação, cinco operações medidas. O resultado vai para a tabela de "Resultado da importação" deste documento, com a coluna "depois".

### Orçamentos esperados (a confirmar na implementação)

| Operação (planilha corrigida) | Hoje | Meta depois de P0 |
|---|---|---|
| Prévia, reimportação | 42.288 | até 6.000 |
| Prévia, 1ª importação | 56.449 | até 12.000 |
| Confirmação, 1ª importação | 58.308 | até 12.000 (com A5) |

A meta é uma estimativa a partir da contagem por tabela: um par de savepoint por linha, cerca de 490 buscas de catálogo, o `INSERT` e os docentes de cada alocação criada, e a etapa final de ofertas. O teste de orçamento grava o número medido depois da implementação com uma folga de 10%. A falha do teste aponta regressão.

Os testes de orçamento usam a planilha gerada pelo auxiliar `workbook_file` de `schedule/tests/test_import.py`, com uma quantidade parametrizada de linhas, e conferem que **dobrar as linhas de atividade com os mesmos catálogos não dobra as consultas**. Esse é o requisito, independente do número absoluto.

## Risks / Trade-offs

- **[Memória com registro desfeito]** → D2: entradas provisórias por linha e teste da linha recusada que cria registro.
- **[Igualdade sem caixa divergente entre Python e PostgreSQL]** → D1: chave exata, e a falta na memória vai ao banco.
- **[Ampliar a trava]** → D3: `prefetch_related` sem `JOIN` sob `FOR UPDATE`. O teste de concorrência de `imports/tests/test_worker.py` precisa continuar passando, e o SQL da trava é conferido num teste.
- **[Erro de banco na etapa final deixa de ser erro de linha]** → D5: aceito, porque as gravações da etapa não têm restrição que a planilha possa violar. Documentado no `imports/README.md`.
- **[`validate_constraints=False` mascarar duplicidade]** → D4: a duplicidade dentro da planilha continua erro da linha por `state.duplicates`, e a concorrente é impedida pela trava. O teste de duplicidade atual precisa continuar passando com a mesma mensagem.
- **[Memória do processo]** → D3 mantém em memória as alocações do semestre. Com 1.498 alocações a medida fica em `tracemalloc`. A medição anterior registrou picos de 29 a 95 MB.
- **[Divergência na confirmação]** → a confirmação compara o plano com o da prévia. Uma otimização que mude o plano aparece como divergência em toda confirmação, e o teste de equivalência pega isso antes.

### Achado fora do escopo

A lista de importações (`ImportListView.get_queryset` + `with_summary`) não tem `ORDER BY`: `qs.ordered` é `False`, e o SQL termina em `GROUP BY "imports_import"."id"`, porque o Django 5.2 não aplica o `Meta.ordering` numa consulta agregada. O paginador avisa com `UnorderedObjectListWarning`. A ordem esperada pelo `Meta` é `-created_at, -pk`. A correção é um `order_by` explícito, que muda a ordem exibida, e por isso fica para uma Change própria, e não para esta, que não pode alterar a ordenação.

## Resultado da implementação

Medido em 07/10/2026 pelo mesmo procedimento da linha de base (banco `perf_check` criado e apagado a cada rodada, superadmin, decisões "novo"). O tempo é da rodada sem `tracemalloc`; a memória, da rodada com ele, e inclui o log de consultas capturado, igual nas duas medições.

| Operação (planilha corrigida, 1.843 linhas) | Consultas antes | Consultas depois | Tempo antes | Tempo depois | Pico antes | Pico depois |
|---|---|---|---|---|---|---|
| Prévia, 1ª importação | 56.449 | 15.464 | 9,12 s | 2,53 s | 64,9 MB | 46,5 MB |
| Atualização da prévia | 56.458 | 15.473 | 9,33 s | 2,56 s | 64,6 MB | 46,2 MB |
| Confirmação, 1ª importação | 58.308 | 15.482 | 9,17 s | 2,12 s | 37,6 MB | 20,4 MB |
| Prévia, reimportação | 42.288 | 5.464 | 7,17 s | 1,32 s | 58,1 MB | 41,4 MB |
| Confirmação, reimportação | 42.294 | 5.471 | 6,63 s | 0,71 s | 28,5 MB | 17,2 MB |
| Prévia da `planilha_example.xlsx` (1.706 linhas) | 49.951 | 12.984 | 8,1 s | 2,14 s | n/d | n/d |

Consultas por linha de atividade a mais (teste `test_import_queries`): de 33,8, 33,0 e 27,0 para no máximo 6 na prévia, na confirmação e na reimportação.

O plano de cada linha e o estado do domínio (alocações, docentes, ofertas, vínculos, espaços, usuários, decisões, auditoria e outbox) ficaram iguais à referência gravada antes da primeira mudança, nas cinco etapas da planilha corrigida e na prévia da planilha com erros (comparação feita durante a implementação; o teste e a referência não ficaram no repositório).

**O que ainda resta.** Na reimportação, 4.692 das 5.464 consultas são `SAVEPOINT`/`RELEASE`: 1.843 pares do savepoint de cada linha, que isola a recusa da linha, e cerca de 500 dos `resolve` de cada grafia distinta e do cadastro dos docentes da lista. Na 1ª importação, somam-se a gravação de cada alocação (`INSERT` da alocação e dos docentes, num `atomic` próprio) e os cadastros. Diminuir mais exigiria tirar o savepoint por linha ou gravar as alocações em lote, o que muda o isolamento da recusa de cada linha e fica fora desta Change.

**Ajustes em relação às decisões.**

- D4: além das consultas do `full_clean`, o `atomic()` de `apply` passou a envolver só a criação. A leitura das versões e o `unchanged` não gravam nada e não precisam de savepoint; a atualização continua na transação própria de `update_details`. Foram 2.996 instruções a menos na reimportação.
- A7: cada nome do cadastro continua com o seu objeto de espaço. Compartilhar um objeto por espaço mudaria o resultado, porque `reactivate()` faz `refresh_from_db()` no objeto e a reativação passaria a valer para os outros nomes do mesmo espaço.
- D6: a classificação da decisão não pode ser reaproveitada em `refresh_after_decision`, porque ela é calculada antes de gravar a decisão e a segunda precisa do estado depois dela. No detalhe, o reaproveitamento economizaria 40 ms e exigiria mudar o contrato do motor; não foi aplicado.
- D7: o perfil passou a ser lido uma vez no template do layout, com `{% with %}`, e não memorizado no model, o que evita perfil desatualizado depois de `change_role`.
- A8: os usuários vêm da trava que já existia; as 129 buscas de perfil pelo código em `UserImport.clean_values` continuam, porque o código é compartilhado com a importação de usuários.
- Avaliadas e não aplicadas por falta de ganho medido: `batch_size` em `replace_plan` (0,05 s de 0,6 s), `summary()` no banco (3,1 ms) e buscas por `Lower()` (nenhuma ficou em laço).
- Índices: nenhum criado nem removido; nada na implementação contradisse a análise.
- A lista de importações sem `ORDER BY` continua como estava, para uma Change própria.

## Migration Plan

Sem migration. Cada tarefa é um commit com a suíte passando, na ordem do `tasks.md`. Para reverter, basta reverter o commit, porque nenhum dado gravado muda de formato.

## Open Questions

- O ganho de A6 (`replace_plan`) justifica `batch_size` ou outra estratégia? Depende da medição isolada da tarefa 1.3.
- Vale remover os índices redundantes? Depende de `pg_stat_user_indexes` em produção, fora desta Change.
