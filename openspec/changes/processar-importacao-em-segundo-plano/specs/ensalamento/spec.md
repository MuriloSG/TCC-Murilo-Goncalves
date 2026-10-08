## MODIFIED Requirements

### Requirement: Atualização automática da prévia após as decisões
Depois de gravar ou desfazer uma decisão, o sistema DEVE (MUST) recalcular o quadro de espaços pela classificação, sem executar as linhas, e mostrá-lo atualizado na mesma resposta, com e sem JavaScript. Quando, depois da decisão, nenhum nome precisar de decisão, ou quando a importação estava `VALIDADA`, a mesma requisição DEVE (MUST) pedir a atualização da prévia, conforme a spec `importacao-planilhas`, deixando-a pendente, sem mudar a situação e sem executar nenhuma linha; ao fim da execução pelo worker, a importação DEVE (MUST) ficar `VALIDADA`, "Pronta para confirmar", ou `PENDENTE`, quando surgir nova pendência, ou `COM_ERROS`, conforme o novo plano. O fluxo normal NÃO DEVE (MUST NOT) ter um controle "Conferir de novo". Gravar ou desfazer uma decisão numa importação com operação pendente DEVE (MUST) ser recusado com a mensagem de importação em processamento, sem gravar a decisão. Quando a atualização da prévia esgotar as tentativas, as decisões gravadas DEVEM (MUST) ser mantidas, a situação NÃO DEVE (MUST NOT) mudar, e o quadro DEVE (MUST) mostrar "Não foi possível atualizar a prévia." com o controle "Tentar novamente", que pede a atualização de novo; esse controle DEVE (MUST) aparecer somente quando a última atualização da prévia terminou por falha e a importação está sem operação pendente.

#### Scenario: Última decisão deixa a importação pronta
- **GIVEN** uma importação `PENDENTE` em que só `HV5` precisa de decisão
- **WHEN** um usuário com `ESPACO.EDITAR` escolhe "É o mesmo que HV 5"
- **THEN** a resposta mostra o quadro atualizado e a importação continua `PENDENTE`, com a atualização pendente
- **WHEN** o worker executa a atualização
- **THEN** a importação fica `VALIDADA` e o quadro mostra "Pronta para confirmar."

#### Scenario: Decisão intermediária não refaz a prévia
- **GIVEN** uma importação `PENDENTE` com 3 nomes que precisam de decisão
- **WHEN** um deles é decidido
- **THEN** o quadro mostra 2 nomes que precisam de decisão, nada é enfileirado e a importação continua `PENDENTE`

#### Scenario: Decisão durante o processamento
- **GIVEN** uma importação `PENDENTE` com a atualização pendente
- **WHEN** alguém tenta decidir um nome de espaço
- **THEN** a decisão é recusada com a mensagem de importação em processamento e não é gravada

#### Scenario: Falha ao atualizar a prévia
- **GIVEN** uma importação `PENDENTE` com uma única pendência
- **WHEN** ela é decidida e a atualização da prévia esgota as tentativas
- **THEN** a decisão continua gravada, a importação continua `PENDENTE` e o quadro mostra "Não foi possível atualizar a prévia." com "Tentar novamente"
- **WHEN** "Tentar novamente" é acionado e o worker conclui a atualização
- **THEN** a importação fica `VALIDADA`
