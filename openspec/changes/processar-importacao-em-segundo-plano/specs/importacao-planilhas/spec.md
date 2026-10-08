## MODIFIED Requirements

### Requirement: Importação como registro da prévia
Uma importação DEVE (MUST) ser o registro persistido de um arquivo cuja leitura e conferência da estrutura foram aceitas. Ela DEVE (MUST) ter um tipo, gravado como código em português (por exemplo, `USUARIO`), e uma situação entre `RECEBIDA`, `VALIDADA`, `PENDENTE`, `COM_ERROS`, `CONCLUIDA`, `DESCARTADA` e `FALHOU`, exibidas como "Recebida", "Validada", "Precisa de decisão", "Com erros", "Concluída", "Descartada" e "Falhou". A situação DEVE (MUST) representar só o estado de negócio da importação: `RECEBIDA` é a importação aceita cuja prévia ainda não foi gerada, e nenhuma situação DEVE (MUST) representar a execução de uma operação. Um arquivo recusado na leitura ou na conferência da estrutura NÃO DEVE (MUST NOT) criar importação. Cada envio aceito DEVE (MUST) criar uma importação nova, `RECEBIDA`, com a prévia pendente, e o reenvio de um arquivo corrigido NÃO DEVE (MUST NOT) alterar importações anteriores. O arquivo enviado NÃO DEVE (MUST NOT) ser guardado depois da leitura. A situação DEVE (MUST) valer para a importação inteira, e as linhas NÃO DEVEM (MUST NOT) ter situação própria.

#### Scenario: Arquivo que chega à prévia
- **GIVEN** um arquivo com estrutura válida
- **WHEN** ele é enviado
- **THEN** uma importação é criada com a situação `RECEBIDA`, a prévia pendente e as linhas com os valores lidos
- **WHEN** o worker executa a prévia
- **THEN** a importação fica `VALIDADA`, `PENDENTE` ou `COM_ERROS`, conforme o plano, sem operação pendente

#### Scenario: Arquivo recusado antes da prévia
- **GIVEN** um arquivo com uma coluna desconhecida
- **WHEN** ele é enviado
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Reenvio após correção
- **GIVEN** uma importação com a situação `COM_ERROS`
- **WHEN** o arquivo corrigido é enviado
- **THEN** uma nova importação é criada e a anterior continua com a situação `COM_ERROS`

### Requirement: Confirmação condicionada ao plano idêntico
A confirmação DEVE (MUST) ser aceita somente para uma importação com a situação `VALIDADA` e sem operação pendente. Ao pedir a confirmação, a requisição DEVE (MUST) travar a importação e aplicar a verificação própria da confirmação declarada pela importação específica, quando houver. Uma recusa dessa verificação DEVE (MUST) mostrar a mensagem da recusa e NÃO DEVE (MUST NOT) alterar a importação nem nenhum dado. Aceita a verificação, o pedido DEVE (MUST) registrar a confirmação como operação pendente, sem mudar a situação, que continua `VALIDADA`, e a requisição NÃO DEVE (MUST NOT) executar nenhuma linha. Na execução pelo worker, a confirmação DEVE (MUST) travar a importação, conferir de novo a situação e a operação pendente, repetir a verificação própria, travar os registros que a importação específica declara, reexecutar todas as linhas a partir dos valores lidos gravados, com o usuário que pediu a confirmação como executor e com a importação em curso, e comparar o plano obtido com o plano gravado, tudo numa única transação. Quando os planos forem idênticos, as alterações de domínio, os registros no outbox, a situação `CONCLUIDA` e o fim da operação pendente DEVEM (MUST) ser efetivados juntos, e quem confirmou e quando DEVEM (MUST) ser gravados. Quando os planos forem diferentes, nenhuma alteração de domínio nem registro no outbox DEVE (MUST) ser efetivado. Nesse caso, o novo plano DEVE (MUST) substituir o anterior, a quantidade de prévias refeitas DEVE (MUST) aumentar em um, a situação DEVE (MUST) ficar `VALIDADA`, `PENDENTE` ou `COM_ERROS` conforme o novo plano, e o detalhe da importação DEVE (MUST) mostrar "Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo." Quando a verificação própria recusar na execução, ou quando quem pediu estiver inativo, nenhuma linha DEVE (MUST) ser reexecutada, a situação e a quantidade de prévias refeitas NÃO DEVEM (MUST NOT) mudar, a operação pendente DEVE (MUST) terminar e o detalhe DEVE (MUST) mostrar o motivo. A falha de uma operação durante a confirmação NÃO DEVE (MUST NOT) deixar nenhuma linha aplicada.

#### Scenario: Confirmação com plano idêntico
- **GIVEN** uma importação `VALIDADA` que cadastra dois usuários
- **WHEN** ela é confirmada sem mudança nos dados
- **THEN** a resposta redireciona ao detalhe, a importação continua `VALIDADA` com a confirmação pendente e nenhum usuário é criado ainda
- **WHEN** o worker executa a confirmação
- **THEN** os dois usuários são criados, a importação fica `CONCLUIDA`, sem operação pendente, e registra quem confirmou e quando

#### Scenario: Dados alterados entre a prévia e a confirmação
- **GIVEN** uma importação `VALIDADA` cuja linha 2 troca o perfil de Ana de `DOCENTE` para `ADMINISTRADOR`
- **AND** que outro administrador fez essa troca pela tela depois da prévia
- **WHEN** a importação é confirmada e o worker executa a confirmação
- **THEN** nada é aplicado, a linha 2 passa a `unchanged` no novo plano, a importação continua `VALIDADA`, a quantidade de prévias refeitas passa a 1 e o detalhe mostra a mensagem de divergência

#### Scenario: Novo plano com erros
- **GIVEN** uma importação `VALIDADA` que cadastra `bruno@ifnmg.edu.br`
- **AND** que o perfil citado na linha foi excluído depois da prévia
- **WHEN** a importação é confirmada e o worker executa a confirmação
- **THEN** nada é aplicado e a importação fica `COM_ERROS`

#### Scenario: Novo plano com pendência
- **GIVEN** uma importação `VALIDADA` cujo novo plano, por mudança dos dados, tem uma pendência
- **WHEN** a importação é confirmada e o worker executa a confirmação
- **THEN** nada é aplicado e a importação fica `PENDENTE`

#### Scenario: Verificação própria recusa ao pedir
- **GIVEN** uma importação específica cuja verificação da confirmação recusa o executor com uma mensagem
- **WHEN** ele pede a confirmação de uma importação `VALIDADA` dela
- **THEN** a mensagem é exibida, nenhuma operação fica pendente, nenhuma linha é reexecutada, a importação continua `VALIDADA` e a quantidade de prévias refeitas não muda

#### Scenario: Quem pediu foi desativado antes da execução
- **GIVEN** uma confirmação pendente pedida por Ana
- **AND** que Ana foi desativada antes de o worker executar a confirmação
- **WHEN** o worker pega a operação
- **THEN** nenhuma linha é executada, a importação continua `VALIDADA`, sem operação pendente, e o detalhe informa que quem pediu a confirmação está desativado

#### Scenario: Falha no meio da aplicação
- **GIVEN** uma importação `VALIDADA` com dez linhas
- **WHEN** uma operação falha na execução da confirmação depois de executadas cinco linhas
- **THEN** nenhuma das linhas fica aplicada

### Requirement: Descarte da importação
Uma importação `VALIDADA` ou `PENDENTE` sem operação pendente DEVE (MUST) poder ser descartada. O descarte DEVE (MUST) mudar a situação para `DESCARTADA` e gravar quem descartou e quando, sem alterar dados de domínio. O descarte de uma importação com operação pendente DEVE (MUST) ser recusado conforme a execução única de cada operação.

#### Scenario: Descarte de importação validada
- **GIVEN** uma importação `VALIDADA`
- **WHEN** ela é descartada
- **THEN** a situação passa a `DESCARTADA`, com quem descartou e quando, e nenhum dado de domínio muda

#### Scenario: Descarte de importação que precisa de decisão
- **GIVEN** uma importação `PENDENTE`
- **WHEN** ela é descartada
- **THEN** a situação passa a `DESCARTADA` e nenhum dado de domínio muda

#### Scenario: Descarte com confirmação pendente
- **GIVEN** uma importação `VALIDADA` com a confirmação pendente
- **WHEN** alguém tenta descartá-la
- **THEN** a tentativa é recusada e a importação continua `VALIDADA` com a confirmação pendente

### Requirement: Situações finais
As situações `COM_ERROS`, `CONCLUIDA`, `DESCARTADA` e `FALHOU` DEVEM (MUST) ser finais, e uma importação numa situação final NÃO DEVE (MUST NOT) ter operação pendente. As situações `RECEBIDA`, `VALIDADA` e `PENDENTE` NÃO DEVEM (MUST NOT) ser finais. Confirmar, descartar ou atualizar a prévia de uma importação numa situação final DEVE (MUST) ser recusado com mensagem, sem alterar dados. Confirmar uma importação `PENDENTE` DEVE (MUST) ser recusado com mensagem, sem alterar dados. Duas confirmações da mesma importação, simultâneas ou repetidas, NÃO DEVEM (MUST NOT) aplicá-la duas vezes. Uma importação `VALIDADA` ou `PENDENTE` NÃO DEVE (MUST NOT) expirar.

#### Scenario: Confirmação repetida
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** alguém tenta confirmá-la de novo
- **THEN** a tentativa é recusada e nenhum dado muda

#### Scenario: Confirmações simultâneas
- **GIVEN** uma importação `VALIDADA` que cadastra um usuário
- **WHEN** duas confirmações dela são enviadas ao mesmo tempo
- **THEN** exatamente um pedido é aceito, o outro é recusado, e o usuário é criado uma vez

#### Scenario: Confirmação de importação com erros
- **GIVEN** uma importação `COM_ERROS`
- **WHEN** alguém tenta confirmá-la
- **THEN** a tentativa é recusada e nenhum dado muda

#### Scenario: Confirmação de importação que precisa de decisão
- **GIVEN** uma importação `PENDENTE`
- **WHEN** a confirmação é enviada por POST
- **THEN** a tentativa é recusada com mensagem e nenhum dado muda

#### Scenario: Descarte de importação concluída
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** alguém tenta descartá-la
- **THEN** a tentativa é recusada e a situação continua `CONCLUIDA`

### Requirement: Erros inesperados
Um erro que não seja uma recusa de regra, como a indisponibilidade do banco, uma espera de trava acima do limite configurado ou um defeito, DEVE (MUST) desfazer toda a execução da operação, sem mudar a situação, e ser registrado no log. A operação DEVE (MUST) continuar pendente e ser tentada de novo pelo worker, até a quantidade máxima de tentativas definida em configuração, com os intervalos definidos em configuração, repetindo o último intervalo quando houver mais tentativas que intervalos. Esgotadas as tentativas, a prévia de um envio DEVE (MUST) deixar a importação `FALHOU`. A atualização da prévia e a confirmação NÃO DEVEM (MUST NOT) mudar a situação: a operação DEVE (MUST) terminar, o plano anterior DEVE (MUST) continuar valendo, e o detalhe DEVE (MUST) informar que a operação não foi concluída e que nada foi aplicado. Uma recusa de regra (`ValidationError`) NÃO DEVE (MUST NOT) gerar nova tentativa nem produzir `FALHOU`.

#### Scenario: Erro inesperado com tentativa restante
- **GIVEN** uma importação `VALIDADA` com a confirmação pendente
- **WHEN** um erro inesperado interrompe a execução na primeira tentativa
- **THEN** nenhum dado de domínio muda, a importação continua `VALIDADA` com a confirmação pendente, as tentativas passam a 1 e a próxima tentativa é agendada pelo primeiro intervalo

#### Scenario: Confirmação esgota as tentativas
- **GIVEN** uma confirmação que falha em todas as tentativas
- **WHEN** a última tentativa falha
- **THEN** nenhum dado de domínio muda, a importação continua `VALIDADA`, sem operação pendente, e o detalhe mostra "A confirmação não foi concluída por uma falha do sistema. Nada foi aplicado. Confirme de novo."

#### Scenario: Prévia esgota as tentativas
- **GIVEN** um envio cuja prévia falha em todas as tentativas
- **WHEN** a última tentativa falha
- **THEN** a importação passa de `RECEBIDA` a `FALHOU` e o detalhe mostra "A prévia não foi gerada por uma falha do sistema. Envie o arquivo de novo."

#### Scenario: Erro de linha não é falha
- **GIVEN** um envio cuja linha 3 é recusada pelo model
- **WHEN** o worker executa a prévia
- **THEN** a importação fica `COM_ERROS`, sem nova tentativa

### Requirement: Importação que precisa de decisão
A situação `PENDENTE` DEVE (MUST) existir para a importação sem erro de linha nem de arquivo que tem pelo menos uma pendência, e DEVE (MUST) ser exibida como "Precisa de decisão", no histórico e no detalhe, com ícone e texto. Uma importação `PENDENTE` NÃO DEVE (MUST NOT) oferecer o controle de confirmar, DEVE (MUST) poder ser descartada e NÃO DEVE (MUST NOT) poder ser excluída, conforme a exclusão de importações, que fica limitada às situações `DESCARTADA`, `COM_ERROS` e `FALHOU`. A situação `COM_ERROS` DEVE (MUST) continuar reservada aos erros de linha e de arquivo, e uma pendência NÃO DEVE (MUST NOT) ser tratada como erro. Cada pendência DEVE (MUST) ser exibida na linha, com o rótulo declarado pela importação específica. Uma importação específica que não declara pendências NÃO DEVE (MUST NOT) ter o comportamento alterado.

#### Scenario: Rótulo da situação
- **GIVEN** uma importação `PENDENTE`
- **WHEN** o histórico de importações é exibido
- **THEN** a importação aparece com "Precisa de decisão"

#### Scenario: Importação que precisa de decisão não é excluída
- **GIVEN** uma importação `PENDENTE` e um usuário com a permissão de exclusão
- **WHEN** a exclusão é enviada por POST
- **THEN** a exclusão é recusada com mensagem e a importação continua existindo

#### Scenario: Importação de usuários sem mudança
- **GIVEN** a importação de usuários, que não declara pendências
- **WHEN** uma prévia sem erros é gerada
- **THEN** a importação fica `VALIDADA`, como antes

#### Scenario: Exclusão de importação que falhou
- **GIVEN** uma importação `FALHOU` e um usuário com a permissão de exclusão
- **WHEN** a exclusão é enviada por POST
- **THEN** a importação e as linhas são excluídas

### Requirement: Atualização da prévia
Uma importação `PENDENTE` ou `VALIDADA` sem operação pendente DEVE (MUST) poder ter a prévia atualizada, por uma operação do motor acionada pela importação específica. O pedido DEVE (MUST) registrar a atualização como operação pendente, sem mudar a situação, e a requisição NÃO DEVE (MUST NOT) executar nenhuma linha. Na execução pelo worker, a atualização DEVE (MUST) travar a importação, conferir de novo a situação e a operação pendente, reexecutar todas as linhas a partir dos valores lidos gravados, com o usuário que a pediu como executor e com a importação em curso, desfazer todas as alterações de domínio e registros no outbox, substituir o plano pelo novo e definir a situação pelo novo plano: `COM_ERROS`, `PENDENTE` ou `VALIDADA`, junto com o fim da operação pendente. A atualização NÃO DEVE (MUST NOT) aplicar nenhuma alteração de domínio, NÃO DEVE (MUST NOT) aumentar a quantidade de prévias refeitas, que continua contando só as divergências da confirmação, NÃO DEVE (MUST NOT) mudar quem enviou nem quando e NÃO DEVE (MUST NOT) gerar registro de auditoria, como a substituição do plano numa divergência. Um erro inesperado durante a atualização DEVE (MUST) desfazer tudo, deixar o plano e a situação como estavam e seguir as novas tentativas dos erros inesperados. A atualização de uma importação numa situação final DEVE (MUST) ser recusada com mensagem, sem alterar dados.

#### Scenario: Atualização deixa a importação pronta
- **GIVEN** uma importação `PENDENTE` cujo motivo da pendência deixou de existir
- **WHEN** a prévia é atualizada e o worker executa a atualização
- **THEN** o plano é substituído, a importação fica `VALIDADA`, sem operação pendente, e nenhum dado de domínio muda

#### Scenario: Pedido de atualização não muda a situação
- **GIVEN** uma importação `PENDENTE`
- **WHEN** a atualização da prévia é pedida
- **THEN** a importação continua `PENDENTE`, com a atualização pendente, e nenhuma linha é executada na requisição

#### Scenario: Atualização sem contar divergência
- **GIVEN** uma importação `PENDENTE` com 0 prévias refeitas
- **WHEN** a prévia é atualizada duas vezes
- **THEN** a importação continua com 0 prévias refeitas

#### Scenario: Erro inesperado na atualização
- **GIVEN** uma importação `PENDENTE` com a atualização pendente
- **WHEN** um erro inesperado interrompe a execução da atualização
- **THEN** o plano, a situação e os dados de domínio continuam como estavam

#### Scenario: Atualização de importação concluída
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** a atualização da prévia é acionada
- **THEN** a tentativa é recusada com mensagem e nada muda

## ADDED Requirements

### Requirement: Operação pendente separada da situação
A importação DEVE (MUST) registrar, separada da situação, a operação pendente (`PREVIA`, `ATUALIZACAO` ou `CONFIRMACAO`, ou nenhuma), quem a pediu e quando, as tentativas, a próxima tentativa, o último erro técnico e o resultado da última operação que não terminou como pedida. O banco DEVE (MUST) recusar combinações que contradigam a situação: `RECEBIDA` sempre com a prévia pendente; a prévia pendente só em `RECEBIDA`; a atualização pendente só em `VALIDADA` ou `PENDENTE`; a confirmação pendente só em `VALIDADA`; e nenhuma operação pendente nas situações finais. Pedir uma operação NÃO DEVE (MUST NOT) mudar a situação. Cada transição de situação DEVE (MUST) continuar sendo uma operação do model que confere a sua pré-condição sob a trava da importação, e o worker NÃO DEVE (MUST NOT) gravar a situação diretamente. O resultado de negócio e o fim da operação pendente DEVEM (MUST) ser gravados no mesmo commit.

#### Scenario: Situação preservada durante a confirmação
- **GIVEN** uma importação de ensalamento `VALIDADA` com a confirmação pendente
- **WHEN** o painel conta as importações abertas
- **THEN** a importação é contada como `VALIDADA`

#### Scenario: Combinação contraditória recusada pelo banco
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** um código grava nela uma confirmação pendente
- **THEN** o banco recusa a gravação

### Requirement: Execução das operações em segundo plano
A prévia de um envio, a atualização da prévia e a confirmação DEVEM (MUST) ser executadas por um worker, fora da requisição HTTP. A requisição DEVE (MUST) só registrar o pedido, numa transação curta. A fila DEVE (MUST) ser a própria tabela de importações no PostgreSQL, sem sistema de filas externo, de modo que não exista operação pendente sem importação nem pedido aceito sem operação pendente. O worker DEVE (MUST) executar a operação com as permissões de quem a pediu, registrar a auditoria em nome dele e recusar a operação de quem foi desativado depois do pedido. A tentativa DEVE (MUST) ser contada, e a próxima tentativa adiada, numa transação anterior à execução, para que uma queda do processo também consuma tentativa e para que outro worker não pegue a mesma operação entre as duas transações. Uma queda do worker em qualquer ponto DEVE (MUST) deixar a importação na situação anterior, com a operação pendente, para ser pega de novo. A espera pela aquisição de uma trava na execução DEVE (MUST) ter um limite definido em configuração, de 60 segundos por padrão; o limite DEVE (MUST) valer só para a espera por trava, e NÃO DEVE (MUST NOT) limitar o tempo total da execução. Esgotada a espera, a execução DEVE (MUST) ser tratada como erro inesperado. O worker DEVE (MUST) descartar conexões com o banco que não servem mais antes de cada ciclo.

#### Scenario: Requisição não executa linhas
- **GIVEN** um arquivo de ensalamento com 1.843 linhas
- **WHEN** ele é enviado
- **THEN** a resposta redireciona ao detalhe sem executar nenhuma linha, e a importação fica `RECEBIDA` com a prévia pendente

#### Scenario: Execução com as permissões de quem pediu
- **GIVEN** uma confirmação pedida por um usuário sem permissão de cadastrar usuários
- **WHEN** o worker a executa
- **THEN** as linhas de cadastro têm o erro de permissão, como teriam na requisição

#### Scenario: Worker cai no meio da execução
- **GIVEN** uma confirmação em execução pelo worker
- **WHEN** o processo do worker termina antes do commit
- **THEN** nenhum dado de domínio muda, a importação continua `VALIDADA` com a confirmação pendente e uma tentativa contada, e um worker a executa quando a próxima tentativa vencer

#### Scenario: Worker cai entre a reserva e a execução
- **GIVEN** uma operação reservada por um worker
- **WHEN** o processo termina antes da execução
- **THEN** nenhum outro worker a pega antes de a próxima tentativa vencer, e depois disso ela é executada

#### Scenario: Usuário fecha o navegador
- **GIVEN** uma confirmação pedida
- **WHEN** o usuário fecha o navegador antes do fim
- **THEN** o worker conclui a confirmação e o resultado aparece no detalhe quando a importação é aberta de novo

### Requirement: Execução única de cada operação
Cada importação DEVE (MUST) ser executada por um só worker de cada vez, pela trava da importação com `skip_locked`. Uma importação com operação pendente NÃO DEVE (MUST NOT) aceitar confirmação, descarte, exclusão, atualização da prévia nem decisão de espaço. Essas ações DEVEM (MUST) ser recusadas de imediato, sem esperar a trava do worker, com a mensagem "Esta importação está em processamento e não aceita outra ação até ele terminar. Confira o resultado no detalhe."

#### Scenario: Dois workers
- **GIVEN** duas instâncias do worker e uma importação com operação pendente
- **WHEN** as duas procuram uma operação ao mesmo tempo
- **THEN** só uma executa a importação

#### Scenario: Dois cliques em confirmar
- **GIVEN** uma importação `VALIDADA`
- **WHEN** a confirmação é pedida duas vezes seguidas
- **THEN** o segundo pedido é recusado com a mensagem de importação em processamento

#### Scenario: Descarte durante a execução
- **GIVEN** uma importação em execução pelo worker
- **WHEN** alguém tenta descartá-la
- **THEN** a tentativa é recusada na hora, com a mensagem de importação em processamento, e a execução continua

### Requirement: Acompanhamento da execução
O detalhe de uma importação com operação pendente DEVE (MUST) mostrar o selo da situação e o selo "Em processamento", sem frase com a operação e a hora do pedido e sem os controles de confirmar, descartar, excluir e decidir. Na prévia de um envio, a tabela de linhas NÃO DEVE (MUST NOT) ser mostrada; na atualização e na confirmação, o plano atual DEVE (MUST) ser mostrado como está. Quando o pedido tiver sido feito há mais tempo que o limite definido em configuração, de 60 segundos por padrão, o detalhe DEVE (MUST) mostrar o aviso "O processamento está demorando mais que o esperado. Ele continua sendo executado em segundo plano." seguido de "O sistema pode continuar sendo usado. Volte a esta tela depois para consultar o resultado." O aviso DEVE (MUST) ser calculado a partir da hora do pedido, NÃO DEVE (MUST NOT) ser uma situação nem ser gravado, e NÃO DEVE (MUST NOT) interromper, cancelar nem alterar a operação. Nenhum texto exibido sobre a execução DEVE (MUST) citar worker, processo, fila, banco de dados, nova tentativa ou trava. O detalhe DEVE (MUST) consultar o andamento periodicamente, por uma rota própria de cada importação específica, e recarregar a página quando a operação terminar; sem JavaScript, DEVE (MUST) oferecer o controle "Atualizar página". O resultado de uma operação que não terminou como pedida (divergência, recusa ou falha) DEVE (MUST) ser mostrado no detalhe até o próximo pedido. As tentativas e o último erro técnico NÃO DEVEM (MUST NOT) ser exibidos na tela.

#### Scenario: Detalhe durante a prévia
- **GIVEN** uma importação `RECEBIDA` com a prévia pedida às 14:30
- **WHEN** o detalhe é aberto às 14:30
- **THEN** aparece o selo "Em processamento", sem frase com a hora do pedido, sem o aviso de demora e sem nenhum controle de ação

#### Scenario: Fim da execução com a tela aberta
- **GIVEN** o detalhe aberto de uma importação com a prévia pendente
- **WHEN** o worker termina e a importação fica `VALIDADA`
- **THEN** a consulta seguinte recarrega a página, que mostra a prévia e o botão de confirmar

#### Scenario: Processamento demorando mais que o esperado
- **GIVEN** uma importação `VALIDADA` com a confirmação pedida há 90 segundos e o limite padrão
- **WHEN** o detalhe é aberto
- **THEN** aparece "O processamento está demorando mais que o esperado. Ele continua sendo executado em segundo plano."
- **AND** a importação continua `VALIDADA`, com a confirmação pendente, e a execução não é interrompida

#### Scenario: Rota do andamento protegida
- **GIVEN** um usuário sem a permissão da importação
- **WHEN** ele consulta a rota do andamento
- **THEN** a resposta é 403
