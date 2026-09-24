## MODIFIED Requirements

### Requirement: Auditoria das alterações de dados
Toda operação que altere dados persistidos DEVE (MUST) gerar um registro com o contexto da alteração. As operações auditadas DEVEM (MUST) ser, no mínimo: cadastro, alteração de dados, troca de perfil, desativação e reativação de usuário; criação, alteração de dados, alteração de permissões e exclusão de perfil; envio da prévia, confirmação e descarte de uma importação; download do modelo de importação, registrado como exportação; e publicação manual de uma notificação. O registro da publicação DEVE (MUST) ter a ação `PUBLICAR` e o módulo `NOTIFICACAO`, com o título, o tipo, a forma de destinar e a quantidade de destinatários alcançados nas informações adicionais, de modo que a consulta identifique quem publicou o quê e para quantas pessoas, e NÃO DEVE (MUST NOT) gerar um registro por destinatário. A entrega das notificações de uma operação já auditada, gerada por um evento do sistema conforme a spec `notificacoes`, NÃO DEVE (MUST NOT) gerar registro próprio, porque a operação que a originou já é registrada. A marcação de uma notificação como lida NÃO DEVE (MUST NOT) ser auditada: ela é o estado de leitura do próprio usuário sobre a própria notificação, acontece a cada abertura do painel e não altera dado de nenhum outro usuário. Numa alteração, os valores anteriores e posteriores DEVEM (MUST) conter somente os campos que mudaram. Numa criação, os valores posteriores DEVEM (MUST) descrever o registro criado, e numa exclusão os valores anteriores DEVEM (MUST) descrever o registro excluído. Uma operação que não altere nada NÃO DEVE (MUST NOT) gerar registro. Uma operação recusada por regra de negócio ou por validação NÃO DEVE (MUST NOT) gerar registro.

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

#### Scenario: Notificação publicada
- **GIVEN** a usuária Ana autenticada, com a permissão de publicar notificações, e 8 usuários ativos
- **WHEN** ela publica um comunicado para todos os usuários elegíveis
- **THEN** existe um registro com a ação `PUBLICAR`, o módulo `NOTIFICACAO`, Ana como responsável e a quantidade 8 de destinatários nas informações adicionais
- **AND** existe um único registro dessa publicação, e não um por destinatário

#### Scenario: Publicação recusada
- **GIVEN** uma publicação para um perfil sem nenhum usuário ativo
- **WHEN** ela é recusada por não haver destinatários
- **THEN** nenhum registro de auditoria é criado

#### Scenario: Notificação de evento não gera registro próprio
- **GIVEN** um usuário que tem o perfil trocado, com a notificação da troca criada
- **WHEN** os registros de auditoria são consultados
- **THEN** existe o registro da ação `ALTERAR` no módulo `USUARIO`
- **AND** não existe registro no módulo `NOTIFICACAO` para essa troca

#### Scenario: Leitura não é auditada
- **GIVEN** um usuário com 4 notificações não lidas
- **WHEN** ele abre uma delas e depois marca todas como lidas
- **THEN** nenhum registro de auditoria é criado por essas marcações

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

#### Scenario: Exportação do modelo
- **WHEN** um usuário com a permissão de importar baixa o modelo da planilha
- **THEN** existe um registro com a ação `EXPORTAR` e o nome do arquivo nas informações adicionais
