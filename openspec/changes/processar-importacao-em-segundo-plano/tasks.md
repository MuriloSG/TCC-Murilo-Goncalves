## 1. Modelo e máquina de estados

- [x] 1.1 Acrescentar `RECEBIDA` e `FALHOU` a `Import.Status` e criar os campos `operation`, `requested_by`, `requested_at`, `attempts`, `next_attempt_at`, `last_error`, `outcome` e `outcome_message`, com a `CheckConstraint` entre operação e situação e o índice parcial da fila (D2)
- [x] 1.2 Criar `ImportBusy` e fazer `lock_pending`, `remove` e as decisões de espaço travarem com `nowait`, recusando operação pendente e trava ocupada (D5)
- [x] 1.3 Separar pedido e execução: `request_preview`, `request_refresh` e `request_confirmation` na requisição, e `execute_pending` com a pré-condição sob a trava, a recusa de quem foi desativado e o corpo atual de `preview`, `refresh` e `confirm` (D3)
- [x] 1.4 Gravar `outcome` na divergência, na recusa da verificação própria e no esgotamento, e limpá-lo no próximo pedido (D2, D6)
- [x] 1.5 Incluir `FALHOU` em `is_deletable` e no selo da situação
- [x] 1.6 Testar a restrição entre operação e situação, a situação inalterada durante a operação, transições, recusas com `ImportBusy`, pedido de confirmação recusado pela verificação própria e a primeira prévia recebendo a importação em `definition.execution`

## 2. Worker

- [x] 2.1 Implementar `imports/worker.py` com reserva (tentativa contada e próxima tentativa adiada) e execução em transações separadas, `skip_locked`, `lock_timeout`, ator com `requested_by` e tratamento de falha com tentativas e intervalos, sem gravar a situação (D4, D6, D8)
- [x] 2.2 Criar o comando `process_imports` com `close_old_connections` a cada ciclo, `--once`, intervalo de espera e parada por sinal, no padrão do `process_outbox`
- [x] 2.3 Acrescentar `IMPORT_MAX_ATTEMPTS`, `IMPORT_RETRY_DELAYS`, `IMPORT_POLL_INTERVAL`, `IMPORT_STATUS_POLL_SECONDS`, `IMPORT_LOCK_TIMEOUT` (60) e `IMPORT_STALE_AFTER` (60) ao `settings.py`, lidos do ambiente (D13)
- [x] 2.4 Criar o auxiliar de teste que pede a operação e roda o worker, e adaptar `imports/tests/test_models.py`, `accounts/tests/test_user_import.py` e os testes da importação de ensalamento sem mudar as asserções de plano
- [x] 2.5 Testar com `TransactionTestCase`: dois workers, dois pedidos simultâneos, queda entre a reserva e a execução, queda durante a execução, espera de trava acima de `IMPORT_LOCK_TIMEOUT` sem limitar uma execução longa que já tem as travas, tentativa restante, esgotamento de cada operação e recusa de regra sem nova tentativa

## 3. Telas do motor

- [x] 3.1 Envio e confirmação passam a pedir a operação e redirecionar ao detalhe com a mensagem do pedido (D9)
- [x] 3.2 Detalhe e lista com o selo da situação e o de "Em processamento", o quadro de processamento com o aviso de demora calculado de `requested_at`, sem situação nem campo gravado e sem termos técnicos (D13), o resultado da última operação e a ausência de controles com operação pendente, a partir de `ui/components/` e com a imagem de referência pedida antes
- [x] 3.3 Rota `<prefixo>_status` nas importações de usuários e de ensalamento, com 204 e `HttpResponseClientRefresh`, e entrada em `PROTECTED_ROUTES`
- [x] 3.4 Testar as views, os textos pelo `context` e as varreduras do app `ui`
- [ ] 3.5 Conferir no navegador com o banco `visual_check` (tentada em 07/10/2026: os containers do Playwright não conseguiram instalar o pacote `playwright`, sem acesso ao PyPI; banco e container de conferência removidos)

## 4. Ensalamento

- [x] 4.1 `refresh_after_decision` e `SpaceRefreshView` pedem a atualização em vez de executá-la; o quadro esconde os controles com operação pendente e mostra "Tentar novamente" pelo `outcome` de falha, e não pela inferência atual
- [x] 4.2 Conferir que `panel/indicators.py` continua contando a importação com operação pendente pela situação
- [x] 4.3 Testar decisão durante o processamento, última decisão, decisão intermediária e falha da atualização

## 5. Ambiente e documentação

- [x] 5.1 Serviço `import_worker` no `compose.yaml`, com `restart: unless-stopped`
- [x] 5.2 Atualizar `imports/README.md`: estados, diagrama, transições, garantias e "O que não existe nesta versão"
- [x] 5.3 Medir de novo o envio e a confirmação do ensalamento e registrar no `design.md` o tempo da resposta
- [x] 5.4 Rodar `make test` e `openspec validate --all --strict`
- [x] 5.5 Commit
