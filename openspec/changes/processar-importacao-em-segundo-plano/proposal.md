## Why

A prévia, a atualização da prévia e a confirmação de uma importação rodam hoje dentro da requisição HTTP que as dispara (`ImportUploadView.form_valid`, `ImportConfirmView.post`, `refresh_after_decision` e `SpaceRefreshView.post`). Isso era aceitável para a importação de usuários, com poucas centenas de linhas, e foi registrado como risco conhecido na Change arquivada `importar-ensalamento-da-planilha` ("1.706 linhas numa prévia síncrona"). A medição feita em 07/10/2026, no ambiente Docker do projeto, numa transação desfeita no fim, mostra o tamanho do problema na importação de ensalamento:

| Planilha | Linhas | Leitura do arquivo | Prévia | Consultas da prévia | Pico de memória |
|---|---|---|---|---|---|
| `sources/planilha_example.xlsx` | 1.706 | 2,2 s | 23,8 s | mais de 9.000 (limite do log) | 95 MB |
| `sources/planilha_example_sugerida_corrigida.xlsx` | 1.843 | 0,5 s | 27,2 s | 53.114 | 29 MB |

A confirmação reexecuta todas as linhas e custa o mesmo que a prévia, e cada decisão de espaço que deixa a importação pronta refaz a prévia inteira na mesma requisição. São, portanto, três requisições de cerca de 30 segundos no fluxo normal de um semestre, cada uma segurando uma transação com `select_for_update` sobre as alocações do semestre e os usuários da planilha. Um proxy de produção com o tempo limite comum de 30 a 60 segundos corta a resposta, o administrador não sabe se a importação foi criada ou confirmada, e fechar o navegador não tem efeito previsível.

A memória e a leitura do arquivo não são o gargalo. O gargalo é o tempo da execução linha a linha, que já é desenhada para rodar fora da tela: a prévia e a confirmação são operações do model (`Import.objects.preview`, `Import.refresh`, `Import.confirm`) e não dependem da requisição.

## What Changes

- **Execução em segundo plano** da prévia, da atualização da prévia e da confirmação. A requisição grava a importação e responde em seguida; um worker executa a operação.
- **Situação continua sendo só estado de negócio.** A execução fica num campo próprio, a operação pendente (`PREVIA`, `ATUALIZACAO` ou `CONFIRMACAO`), com quem pediu, tentativas e último erro. Uma `CheckConstraint` impede que ela contradiga a situação. Uma importação em confirmação continua `VALIDADA`, e o painel e o quadro de espaços, que leem a situação, não mudam de comportamento.
- **Situações novas `RECEBIDA` e `FALHOU`.** `RECEBIDA` ("Recebida") é a importação aceita cuja prévia ainda não foi gerada. `FALHOU` ("Falhou") é a final, excluível, da importação cuja prévia esgotou as tentativas. A falha da atualização e a da confirmação não mudam a situação, como hoje. O README previa `PROCESSANDO`; a revisão arquitetural do `design.md` explica por que ela não entra como situação.
- **A própria importação é a tarefa**: não há tabela de tarefa, fila externa nem biblioteca nova.
- **Worker `process_imports`**, comando de gerenciamento no padrão do `process_outbox` (`skip_locked`, `--once`, parada por sinal), num serviço novo `import_worker` do Docker Compose.
- **Novas tentativas** para erro inesperado, com quantidade e intervalos em configuração, como no outbox. Recusas de regra de negócio não são tentadas de novo.
- **Recusa imediata das ações** (confirmar, descartar, excluir, decidir espaço, atualizar a prévia) sobre uma importação com operação pendente, com a mensagem própria, sem esperar a trava do worker.
- **Acompanhamento na tela**: o detalhe de uma importação com operação pendente mostra a operação e desde quando ela espera, mostra, depois de 60 segundos, o aviso "O processamento está demorando mais que o esperado. Ele continua sendo executado em segundo plano." (calculado da hora do pedido, sem situação nova), e é atualizado pelo htmx a cada poucos segundos até a operação terminar. O resultado de uma confirmação que divergiu, que foi recusada pela verificação própria ou que falhou passa a ser mostrado no detalhe, e não só na mensagem da resposta.
- **Leitura do arquivo e conferência da estrutura continuam na requisição**: um arquivo recusado continua sem criar importação, e o arquivo continua sem ser guardado.

### Fora do escopo

- Percentual de progresso e contagem de linhas processadas durante a execução.
- Cancelamento de uma operação enfileirada ou em execução.
- Acompanhamento pelo Django Channels no lugar do polling, e aviso pelo canal de notificações (`notices`) quando a operação termina. O canal usa `InMemoryChannelLayer`, que não atravessa processos, e trocá-lo exigiria infraestrutura nova (D14 do `design.md`).
- Redução das consultas por linha (N+1) da importação de ensalamento e execução em lotes com várias transações.
- Celery, Redis, RabbitMQ ou outro sistema de filas.
- Mudança no plano, na comparação de planos, no contrato `ImportDefinition` e nas regras de cada importação específica.

## Capabilities

### Modified Capabilities

- `importacao-planilhas`: a importação passa a existir a partir do envio aceito, com a situação `RECEBIDA` até a prévia terminar; a operação pendente passa a ser registrada separada da situação; a prévia, a atualização da prévia e a confirmação passam a ser executadas por um worker, com novas tentativas e a situação `FALHOU` só para a prévia; as ações sobre uma importação com operação pendente são recusadas; e as telas passam a acompanhar a execução.
- `ensalamento`: a atualização da prévia depois das decisões de espaço passa a ser enfileirada, decidir ou desfazer uma decisão com operação pendente é recusado, e "Tentar novamente" passa a depender do resultado gravado da atualização.
- `ambiente-desenvolvimento`: o Docker Compose ganha o container `import_worker`.

Esta Change parte das specs com a Change `manipulacao-dos-espacos` arquivada (`2026-10-07-manipulacao-dos-espacos`). Os requisitos que ela criou ou alterou (`PENDENTE`, atualização da prévia, descarte, situações finais) são os modificados aqui.

## Impact

- **`imports/models.py`**: situações `RECEBIDA` e `FALHOU`, campos da operação pendente, `CheckConstraint`, `ImportBusy`, e a separação de cada operação em "pedir" (na requisição) e "executar" (`execute_pending`, chamado pelo worker). `preview`, `refresh` e `confirm` mantêm o corpo atual como a parte executada.
- **`imports/worker.py`** (novo) e **`imports/management/commands/process_imports.py`** (novo).
- **`imports/views.py`** e **`imports/templates/imports/`**: envio, confirmação e detail com o estado em processamento e o resultado da última operação.
- **`schedule/views.py`** e **`schedule/models.py`**: `refresh_after_decision`, `SpaceRefreshView` e `SpaceDecisionManager` passam a enfileirar e a recusar a importação em processamento.
- **`config/settings.py`**: `IMPORT_MAX_ATTEMPTS`, `IMPORT_RETRY_DELAYS`, `IMPORT_POLL_INTERVAL`, `IMPORT_STATUS_POLL_SECONDS`, `IMPORT_LOCK_TIMEOUT` (60 s, só a espera por trava) e `IMPORT_STALE_AFTER` (60 s, só o aviso de demora), lidos do ambiente.
- **`compose.yaml`**: serviço `import_worker`.
- **`imports/README.md`**: diagrama, transições e garantias.
- **`audit/catalog.py`**: ação de falha da importação, se o catálogo ainda não tiver uma que sirva.
- **`panel/indicators.py`**: sem mudança; continua contando pela situação, que não é mais sobrescrita durante a execução.
- **Sem impacto**: `imports/execution.py`, `imports/definitions.py`, `imports/reader.py`, `imports/workbook.py`, `accounts/imports.py`, `schedule/imports.py`, `outbox` e `notices`.

## Alinhamento com o TCC

- **P2:** as transições continuam sendo operações do model, numa transação, e o worker só as chama.
- **P3:** os campos novos entram por migration, e a fila é o próprio PostgreSQL pelo ORM.
- **RNF:** a resposta das telas de importação deixa de depender do tamanho da planilha.
