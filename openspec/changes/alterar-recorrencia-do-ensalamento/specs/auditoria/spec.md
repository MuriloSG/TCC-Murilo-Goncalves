## ADDED Requirements

### Requirement: Auditoria da alteração da recorrência
A alteração da recorrência DEVE (MUST) gravar, na mesma transação, um registro `ALTERAR` no módulo `ENSALAMENTO` por alocação encerrada, com o identificador dela, os valores anteriores e novos só dos campos alterados entre dia, horário, espaço e docentes, e nos metadados a identificação da aula, a data a partir da qual a mudança vale, o fim da vigência da original, o identificador da alocação nova e as datas das exceções transferidas. Cada exceção transferida DEVE (MUST) gerar um registro `ALTERAR` no módulo `EXCECAO_ENSALAMENTO`. O usuário e o momento vêm do registro, como nas demais ações. O histórico administrativo das alterações DEVE (MUST) ser a consulta da auditoria, sem tela própria.

#### Scenario: Alteração registrada
- **WHEN** um usuário muda a sala de uma aula da `HV 1` para a `HV 2` a partir de 05/10/2026
- **THEN** existe um registro `ALTERAR` em `ENSALAMENTO` com o usuário, o espaço anterior `HV 1`, o novo `HV 2`, a data 05/10/2026 e a alocação nova

#### Scenario: Recusa sem registro
- **WHEN** a alteração é recusada
- **THEN** nenhum registro de `ENSALAMENTO` é gravado
