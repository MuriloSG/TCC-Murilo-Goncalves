## ADDED Requirements

### Requirement: Permissões de consulta do ensalamento e de exclusão das importações
O catálogo DEVE (MUST) conter também `ENSALAMENTO.VISUALIZAR`, `ENSALAMENTO.EXCLUIR_IMPORTACAO` e `USUARIO.EXCLUIR_IMPORTACAO`. Consultar a grade do ensalamento exige `ENSALAMENTO.VISUALIZAR`; excluir uma importação de ensalamento exige `ENSALAMENTO.EXCLUIR_IMPORTACAO`; excluir uma importação de usuários exige `USUARIO.EXCLUIR_IMPORTACAO`. A migration que as acrescenta DEVE (MUST) concedê-las ao perfil `ADMINISTRADOR` sem alterar as demais permissões concedidas pelos perfis existentes. Elas NÃO DEVEM (MUST NOT) ser reservadas ao superadmin.

#### Scenario: Permissões acrescentadas a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta as três permissões é aplicada
- **THEN** `ADMINISTRADOR` passa a concedê-las e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Exclusão de importação de usuários
- **GIVEN** um usuário cujo perfil concede `USUARIO.IMPORTAR` e `USUARIO.EXCLUIR_IMPORTACAO`
- **WHEN** ele exclui uma importação de usuários com erros
- **THEN** o acesso é concedido
