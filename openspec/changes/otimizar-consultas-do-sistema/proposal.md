## Why

A Change `processar-importacao-em-segundo-plano` tirou a importação da requisição HTTP, mas deixou fora do escopo, de propósito, a "redução das consultas por linha (N+1) da importação de ensalamento". O custo continua o mesmo, só mudou de lugar: o worker segura por vários segundos uma transação com `select_for_update` sobre as alocações do semestre, três vezes por semestre (prévia, atualização depois das decisões e confirmação).

A medição de 07/10/2026, feita para esta Change num banco isolado (`perf_check`) no Docker do projeto, mostra onde está o custo:

| Planilha | Linhas | Operação | Consultas | Tempo |
|---|---|---|---|---|
| `planilha_example.xlsx` | 1.706 | prévia (com erros) | 49.951 | 8,1 s |
| `planilha_example_sugerida_corrigida.xlsx` | 1.843 | prévia, 1ª importação | 56.449 | 9,1 s |
| idem | 1.843 | atualização da prévia | 56.458 | 9,3 s |
| idem | 1.843 | confirmação | 58.308 | 9,1 s |
| idem | 1.843 | prévia, reimportação sem mudança | 42.288 | 7,2 s |
| idem | 1.843 | confirmação, reimportação | 42.294 | 6,6 s |

O "mais de 9.000" registrado antes para a primeira planilha era o limite do log de consultas do Django, e não o total: o número real é 49.951. A segunda planilha subiu de 53.114 para 56.449 consultas desde a medição anterior, com a sincronização dos vínculos de docente da Change `relacionar-professor-disciplina-turma`.

A memória e a leitura do arquivo não pesam (leitura em 0,12 s). O banco também não: as tabelas são pequenas, e cada consulta custa menos de 1 ms. O tempo vem da quantidade de idas e voltas ao banco. São cerca de 30 consultas por linha de atividade, e 52% das instruções são `SAVEPOINT`/`RELEASE SAVEPOINT` de transações aninhadas. A maior parte são buscas repetidas: a planilha tem 15 cursos, 56 turmas, 276 disciplinas, 15 faixas e 129 docentes, e cada um é procurado de novo em cada uma das 1.498 linhas de atividade.

As telas de leitura foram medidas também (Grade do ensalamento, Agenda semanal e mensal, calendário público, horário original, painel, relatórios e listas). Elas já trabalham com uma quantidade fixa de consultas, entre 1 e 27 por página, sem N+1. Lá só há ganhos pequenos e localizados.

## What Changes

- **Execução da importação do ensalamento sem consultas repetidas por linha.** Os cursos, turmas, disciplinas, faixas e docentes já resolvidos numa execução são guardados no estado dessa execução (`RunState`) e não são procurados de novo. Um registro criado por uma linha desfeita sai da memória junto com o rollback dela.
- **Alocações do semestre carregadas uma vez.** A trava que a execução já faz em `lock()` passa a carregar as alocações com espaço e docentes, sem ampliar o escopo da trava. `Allocation.objects.apply` deixa de buscar a identidade, o espaço e os docentes linha a linha, e as validações do `full_clean` que o banco e a trava já garantem deixam de consultar.
- **Ofertas e vínculos de docente sincronizados uma vez por execução.** `ClassOffering.objects.record` deixa de rodar a cada linha (1.498 chamadas para 563 ofertas). Uma operação nova do model sincroniza, numa etapa final, as ofertas das linhas mantidas, com poucas consultas em conjunto. O contrato `ImportDefinition` ganha essa etapa opcional depois das linhas, dentro da mesma transação.
- **Confirmação grava o registro criado de cada linha em lote** (`bulk_update`), em vez de 1.842 `UPDATE`s.
- **Ganhos secundários medidos:** os espaços da classificação com os outros nomes pré-carregados; os usuários da aba de usuários carregados com o perfil na trava que já existe; a classificação dos espaços calculada uma vez por requisição no detalhe da importação e na decisão; o perfil do usuário lido uma vez por requisição no layout (hoje são 3 consultas em toda página autenticada).
- **Medição como critério de aceite.** Testes de orçamento de consultas e uma comparação do plano (`comparable()`) antes e depois, com as duas planilhas reais. Toda otimização precisa manter o plano idêntico.

Nenhuma regra de negócio, permissão, filtro, ordenação, trava, auditoria ou texto exibido muda. Nenhuma migration é prevista nas tarefas P0 e P1.

### Fora do escopo

- Trocar o banco, introduzir Redis, Celery, cache distribuído ou o framework de cache do Django.
- Reescrever o ORM, criar uma camada de repositório ou de persistência paralela.
- Alterar o worker de importação, as tentativas, os tempos limite ou a máquina de estados da importação.
- Dividir a execução em lotes com várias transações, executar linhas em paralelo ou trocar `full_clean` por SQL manual.
- Mudar o comportamento de `savepoint` das operações do model (`atomic(savepoint=False)`): a queda dos savepoints vem da eliminação das chamadas repetidas.
- Criar índices novos para a importação: o gargalo é a quantidade de idas ao banco, e não varreduras (ver o `design.md`).
- Remover índices redundantes sem a estatística de uso do banco de produção (`pg_stat_user_indexes`).
- A lista de importações sem `ORDER BY` (o `Meta.ordering` é ignorado numa consulta com `GROUP BY` no Django 5.2). É um defeito de ordenação, e não de desempenho, e fica registrado no `design.md` para uma Change própria.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `importacao-planilhas`: o contrato das importações específicas ganha uma etapa opcional depois de todas as linhas, na mesma transação, que só recebe as linhas mantidas. Fica explícito que a memória de registros restrita a uma execução não é efeito externo.
- `ensalamento`: a execução da importação do ensalamento passa a ter custo de consultas limitado pelos registros distintos da planilha, e não pela quantidade de linhas, com o mesmo plano e o mesmo resultado no domínio.

## Impact

- **Código:** `schedule/imports.py` (`RunState`, `lock`, `execute_activity`, `execute_user`, `execute_space`), `schedule/models.py` (`NamedManager.resolve`, `ClassGroupManager.resolve`, `TimeSlotManager.resolve`, `AllocationManager.apply`, `Allocation.update_details`, `ClassOfferingManager`), `schedule/spaces.py` (`registry`, `apply`), `imports/definitions.py` e `imports/execution.py` (etapa final), `imports/models.py` (`run_confirmation`), `schedule/views.py` e `imports/views.py` (classificação por requisição), `accounts/models.py` e `ui/templates/ui/layouts/app.html` (perfil).
- **Testes:** testes novos de orçamento de consultas e de plano idêntico. Os testes atuais de importação, de ensalamento e de recorrência continuam passando sem mudança nas asserções.
- **Banco:** nenhuma migration nas tarefas P0 e P1.
- **Dependências:** nenhuma.
