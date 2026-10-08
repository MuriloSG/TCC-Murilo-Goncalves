## ADDED Requirements

### Requirement: Permissões do cadastro de espaços
O catálogo DEVE (MUST) conter também as permissões do recurso `ESPACO`: `ESPACO.VISUALIZAR`, `ESPACO.CRIAR`, `ESPACO.EDITAR`, `ESPACO.ALTERAR_SITUACAO` e `ESPACO.EXCLUIR`, seguindo a divisão por operação das permissões do recurso `USUARIO`, em que desativar e reativar formam uma única permissão de situação. Para as operações da spec `gestao-espacos`, a correspondência DEVE (MUST) ser: listar e consultar espaços exige `ESPACO.VISUALIZAR`; cadastrar espaço exige `ESPACO.CRIAR`; alterar o nome e os outros nomes de um espaço exige `ESPACO.EDITAR`; desativar e reativar exige `ESPACO.ALTERAR_SITUACAO`; excluir espaço exige `ESPACO.EXCLUIR`. Na importação de ensalamento, as decisões e a confirmação que alteram o cadastro de espaços DEVEM (MUST) exigir, além de `ENSALAMENTO.IMPORTAR`, a permissão de espaço da operação equivalente, conforme a spec `ensalamento`, e a falta dela DEVE (MUST) recusar a decisão ou a confirmação com mensagem, e não recusar o acesso à rota nem virar erro de linha. `ENSALAMENTO.IMPORTAR` NÃO DEVE (MUST NOT) conceder por si só nenhuma alteração do cadastro de espaços, e nenhuma permissão de espaço DEVE (MUST) dar acesso às telas da importação. A migration que acrescenta as permissões de `ESPACO` DEVE (MUST) concedê-las ao perfil `ADMINISTRADOR` sem alterar as demais permissões concedidas pelos perfis existentes. Elas NÃO DEVEM (MUST NOT) ser reservadas ao superadmin.

#### Scenario: Permissões acrescentadas a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta as permissões de `ESPACO` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder as cinco permissões de `ESPACO` e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Consulta de espaços sem alteração
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `ESPACO.VISUALIZAR`
- **WHEN** ele acessa a lista de espaços e depois o cadastro de espaço
- **THEN** a lista é exibida e o cadastro é recusado com 403

#### Scenario: Cadastro sem a permissão
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `ESPACO.CRIAR`
- **WHEN** ele envia por POST o cadastro de um espaço
- **THEN** a requisição é recusada com 403 e nenhum espaço é criado

#### Scenario: Visitante não autenticado
- **WHEN** um visitante não autenticado acessa a lista de espaços ou qualquer operação do cadastro de espaços
- **THEN** ele é redirecionado para a página de login, com o endereço de retorno

#### Scenario: Alteração sem CSRF
- **GIVEN** um usuário com `ESPACO.ALTERAR_SITUACAO`
- **WHEN** a desativação de um espaço é enviada por POST sem o token CSRF
- **THEN** a requisição é recusada com 403 e o espaço não muda

#### Scenario: Importar não concede o cadastro de espaços
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `ENSALAMENTO.IMPORTAR`
- **WHEN** ele acessa a lista de espaços
- **THEN** o acesso é recusado com 403

#### Scenario: Espaços concedidos a um perfil personalizado
- **GIVEN** um superadmin ativo autenticado e o perfil personalizado `COORDENACAO`
- **WHEN** ele concede `ESPACO.CRIAR` a `COORDENACAO`
- **THEN** a permissão é concedida, por não ser reservada ao superadmin
