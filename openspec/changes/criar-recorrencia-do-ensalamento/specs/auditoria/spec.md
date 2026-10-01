## ADDED Requirements

### Requirement: Auditoria da criação da recorrência
A criação de uma aula pela interface DEVE (MUST) gravar, na mesma transação, um registro `CRIAR` no módulo `ENSALAMENTO` por alocação criada, com o identificador dela, os valores novos da turma, da disciplina, do dia, do horário, do espaço e dos docentes, e nos metadados a vigência, a origem `MANUAL` e, quando a aula ocupa mais de uma faixa, os identificadores das demais alocações do bloco. O usuário e o momento vêm do registro, como nas demais ações. Uma criação recusada NÃO DEVE (MUST NOT) gravar registro nenhum.

#### Scenario: Criação registrada
- **WHEN** um usuário cadastra `Química Orgânica` para a turma `2º PERÍODO` na `HV 2`, às terças-feiras, das 13:20 às 14:10, a partir de 06/10/2026
- **THEN** existe um registro `CRIAR` em `ENSALAMENTO` com o usuário, a turma, a disciplina, o espaço `HV 2`, o horário e o início da vigência 06/10/2026

#### Scenario: Bloco de duas faixas
- **WHEN** a aula cadastrada ocupa duas faixas seguidas
- **THEN** existem dois registros `CRIAR`, um por alocação, e cada um traz nos metadados o identificador da outra

#### Scenario: Recusa sem registro
- **WHEN** a criação é recusada por conflito de espaço
- **THEN** nenhum registro de `ENSALAMENTO` é gravado e nenhuma alocação existe
