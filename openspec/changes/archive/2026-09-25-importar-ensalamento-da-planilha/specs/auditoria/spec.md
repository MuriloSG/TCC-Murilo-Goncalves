## MODIFIED Requirements

### Requirement: Auditoria das alterações de dados
Toda operação que altere dados persistidos DEVE (MUST) gerar um registro com o contexto da alteração, salvo as operações de carga em lote tratadas no parágrafo seguinte. As operações auditadas DEVEM (MUST) ser, no mínimo: cadastro, alteração de dados, troca de perfil, desativação e reativação de usuário; criação, alteração de dados, alteração de permissões e exclusão de perfil; envio da prévia, confirmação e descarte de uma importação; e download do modelo de importação, registrado como exportação. Numa alteração, os valores anteriores e posteriores DEVEM (MUST) conter somente os campos que mudaram. Numa criação, os valores posteriores DEVEM (MUST) descrever o registro criado, e numa exclusão os valores anteriores DEVEM (MUST) descrever o registro excluído. Uma operação que não altere nada NÃO DEVE (MUST NOT) gerar registro. Uma operação recusada por regra de negócio ou por validação NÃO DEVE (MUST NOT) gerar registro.

Uma importação específica PODE (MAY) ser declarada como carga em lote, e nesse caso as operações de domínio executadas pelas suas linhas NÃO DEVEM (MUST NOT) gerar registro próprio: o registro da carga DEVE (MUST) ser o da confirmação da importação, e ele DEVE (MUST) conter quem confirmou, a data e a hora, o arquivo, a chave da importação, a situação final, os totais de registros criados, atualizados e preservados, o total de linhas com erro e os metadados que a importação específica declarar, como o recorte a que a carga se aplica. A exceção DEVE (MUST) valer somente para a importação declarada como carga em lote, e uma importação que não se declare assim DEVE (MUST) continuar registrando cada operação das suas linhas. A prévia de uma carga em lote NÃO DEVE (MUST NOT) gerar registro de operação de domínio, porque nenhuma alteração é mantida.

#### Scenario: Criação
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra `ana@ifnmg.edu.br` com o perfil `DOCENTE`
- **THEN** existe um registro com a ação `CRIAR`, o recurso `USUARIO`, o identificador do usuário criado e os valores posteriores com o e-mail, o nome e o código do perfil

#### Scenario: Alteração
- **GIVEN** o usuário "Ana Souza" com o e-mail `ana@ifnmg.edu.br`
- **WHEN** um usuário com a permissão de editar altera o nome para "Ana Souza Lima", sem mudar o e-mail
- **THEN** existe um registro com a ação `ALTERAR` cujos valores anteriores e posteriores contêm apenas o nome, com "Ana Souza" e "Ana Souza Lima"

#### Scenario: Alteração sem mudança
- **WHEN** o formulário de edição é enviado com exatamente os mesmos dados do usuário
- **THEN** nenhum registro de auditoria é criado

#### Scenario: Exclusão
- **GIVEN** um perfil personalizado sem usuários vinculados
- **WHEN** o superadmin o exclui
- **THEN** existe um registro com a ação `EXCLUIR`, o recurso `PERFIL` e os valores anteriores com o código e o nome do perfil excluído

#### Scenario: Desativação e reativação
- **WHEN** um usuário é desativado e depois reativado
- **THEN** existem dois registros, um com a ação `DESATIVAR` e outro com a ação `ATIVAR`, ambos com o identificador desse usuário

#### Scenario: Alteração de permissões de um perfil
- **GIVEN** um perfil que concede `USUARIO.VISUALIZAR`
- **WHEN** o superadmin passa a conceder também `USUARIO.CRIAR`
- **THEN** existe um registro com a ação `ALTERAR` e o recurso `PERFIL`, com a lista de permissões antes e depois

#### Scenario: Operação recusada
- **GIVEN** o único usuário ativo com capacidade administrativa
- **WHEN** a desativação dele é recusada pela continuidade administrativa
- **THEN** nenhum registro de auditoria é criado

#### Scenario: Importação confirmada
- **GIVEN** uma importação de usuários validada com duas linhas de cadastro
- **WHEN** ela é confirmada
- **THEN** existe um registro com a ação `IMPORTAR` e o recurso da importação de usuários, com os totais aplicados
- **AND** existe um registro de cadastro para cada um dos dois usuários, com a origem `IMPORTACAO`

#### Scenario: Prévia não registra as linhas
- **GIVEN** uma planilha com duas linhas de cadastro
- **WHEN** a prévia é gerada, sem confirmação
- **THEN** existe um registro da prévia da importação
- **AND** não existe registro de cadastro de usuário, porque nenhum usuário foi criado

#### Scenario: Carga em lote registrada pelo resumo
- **GIVEN** uma importação declarada como carga em lote, validada, que cria e atualiza milhares de registros
- **WHEN** ela é confirmada
- **THEN** existe um registro com a ação `IMPORTAR`, com quem confirmou, a data e a hora, o arquivo, a chave da importação, a situação final, os totais de criados, atualizados e preservados, o total de linhas com erro e os metadados declarados pela importação
- **AND** não existe registro de auditoria das entidades criadas ou alteradas pelas linhas

#### Scenario: Importação em lote não afeta as demais
- **GIVEN** uma importação declarada como carga em lote e a importação de usuários, que não se declara assim
- **WHEN** as duas são confirmadas
- **THEN** a carga em lote tem só o registro do resumo
- **AND** a importação de usuários continua com um registro por usuário cadastrado

#### Scenario: Exportação do modelo
- **WHEN** um usuário com a permissão de importar baixa o modelo da planilha
- **THEN** existe um registro com a ação `EXPORTAR` e o nome do arquivo nas informações adicionais
