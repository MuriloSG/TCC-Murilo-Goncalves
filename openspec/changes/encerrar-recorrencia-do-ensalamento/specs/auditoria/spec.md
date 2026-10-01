## ADDED Requirements

### Requirement: Auditoria do encerramento da recorrência
O encerramento da recorrência DEVE (MUST) gravar, na mesma transação, um registro `ALTERAR` no módulo `ENSALAMENTO` por alocação encerrada, com o identificador dela, o fim da vigência anterior e o novo, e nos metadados a identificação da aula, a data a partir da qual o encerramento vale e a quantidade de aulas encerradas. O usuário e o momento vêm do registro, como nas demais ações. Um encerramento recusado NÃO DEVE (MUST NOT) gravar registro nenhum.

#### Scenario: Encerramento registrado
- **WHEN** um usuário encerra a aula de `Química Orgânica` a partir de 05/10/2026
- **THEN** existe um registro `ALTERAR` em `ENSALAMENTO` com o usuário, o fim da vigência em 04/10/2026, a data 05/10/2026 e a quantidade de aulas encerradas

#### Scenario: Recusa sem registro
- **WHEN** o encerramento é recusado
- **THEN** nenhum registro de `ENSALAMENTO` é gravado
