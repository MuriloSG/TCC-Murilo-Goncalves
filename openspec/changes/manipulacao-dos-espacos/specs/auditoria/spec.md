## ADDED Requirements

### Requirement: Auditoria do cadastro de espaços
Toda alteração real do cadastro de espaços DEVE (MUST) gerar um registro do módulo `ESPACO`, exibido como "Espaços", com a chave do espaço como identificador do registro: o cadastro, com a ação `CRIAR` e os valores posteriores com o nome, os outros nomes, a origem e a importação de origem; a alteração do nome ou dos outros nomes, com a ação `ALTERAR` e somente os campos que mudaram; a desativação, com `DESATIVAR`; a reativação, com `ATIVAR`; e a exclusão, com `EXCLUIR` e os valores anteriores com o nome, os outros nomes e a origem. Uma operação que não altera nada ou que é recusada NÃO DEVE (MUST NOT) gerar registro.

A exceção da carga em lote NÃO DEVE (MUST NOT) alcançar o cadastro de espaços: as alterações do cadastro feitas pela confirmação de uma importação de ensalamento DEVEM (MUST) gerar um registro por espaço cadastrado, por espaço que recebeu ou perdeu outro nome e por espaço reativado, gravados na mesma transação da confirmação, com a origem de importação, quem confirmou como responsável e, nas informações adicionais, a chave da importação e quem tomou a decisão, quando a alteração veio de uma decisão. A prévia e a atualização da prévia NÃO DEVEM (MUST NOT) deixar registro de espaço, porque as alterações são desfeitas. A origem do espaço, gravada no próprio espaço, NÃO DEVE (MUST NOT) ser confundida com a origem do registro de auditoria, que diz por onde a ação foi feita.

Gravar e desfazer uma decisão de espaço numa importação NÃO DEVE (MUST NOT) gerar registro do módulo `ESPACO`, porque não altera o cadastro. Essas operações DEVEM (MUST) gerar um registro `ALTERAR` do módulo da importação de ensalamento, com a chave da importação e o nome encontrado, a decisão e o espaço escolhido, porque alteram dados gravados da importação.

#### Scenario: Cadastro manual registrado
- **GIVEN** um usuário com `ESPACO.CRIAR`
- **WHEN** ele cadastra o espaço `Sala 101` pela tela
- **THEN** existe um registro `CRIAR` do módulo `ESPACO`, com a origem de auditoria de interface, o responsável e os valores `Sala 101`, sem outros nomes, a origem `MANUAL` e nenhuma importação de origem

#### Scenario: Renomeação registrada
- **GIVEN** o espaço `HV 5` sem outros nomes
- **WHEN** ele é renomeado para `Sala HV 05`
- **THEN** existe um registro `ALTERAR` com o nome de `HV 5` para `Sala HV 05` e os outros nomes de nenhum para `HV 5`

#### Scenario: Espaços da confirmação registrados
- **GIVEN** uma importação de ensalamento `VALIDADA` que cadastra `Zoo I`, por decisão de Ana, e associa `HV5` a `HV 5`
- **WHEN** Bruno a confirma
- **THEN** existem um registro `CRIAR` de `Zoo I` e um registro `ALTERAR` de `HV 5`, ambos com a origem de importação, Bruno como responsável e a chave da importação
- **AND** o registro de `Zoo I` informa Ana como quem decidiu

#### Scenario: Decisão registrada na importação
- **WHEN** um usuário grava a decisão "É o mesmo que HV 5" para `HV5` numa importação `PENDENTE`
- **THEN** existe um registro `ALTERAR` do módulo da importação de ensalamento com o nome encontrado `HV5`, a decisão e o espaço `HV 5`
- **AND** não existe registro do módulo `ESPACO`

#### Scenario: Prévia sem registro de espaço
- **WHEN** a prévia de uma importação que cadastra 62 espaços é gerada
- **THEN** não existe nenhum registro do módulo `ESPACO`
