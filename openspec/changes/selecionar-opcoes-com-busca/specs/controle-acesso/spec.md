## MODIFIED Requirements

### Requirement: Correspondência entre operações e permissões
Cada funcionalidade protegida por permissão DEVE (MUST) exigir exatamente a permissão correspondente. Para as operações de gestão de usuários descritas na spec `gestao-usuarios`, a correspondência DEVE (MUST) ser: listar e consultar usuários exige `USUARIO.VISUALIZAR`; cadastrar usuário exige `USUARIO.CRIAR`; alterar nome e e-mail exige `USUARIO.EDITAR`; trocar o perfil exige `USUARIO.ALTERAR_PERFIL`; desativar e reativar exige `USUARIO.ALTERAR_SITUACAO`; enviar, confirmar e descartar importações de usuários, consultar o histórico e o detalhe delas e baixar o modelo exige `USUARIO.IMPORTAR`. Na importação de usuários, cada ação de linha DEVE (MUST) exigir também a permissão da operação equivalente, conforme a spec `gestao-usuarios`, e a falta dela DEVE (MUST) ser um erro da linha, e não uma recusa de acesso à rota. Para as operações de gestão de perfis descritas na spec `gestao-perfis`, a correspondência DEVE (MUST) ser: listar e consultar perfis exige `PERFIL.VISUALIZAR`; criar perfil exige `PERFIL.CRIAR`; alterar nome e descrição de perfil exige `PERFIL.EDITAR`; definir as permissões de um perfil exige `PERFIL.ALTERAR_PERMISSOES`; excluir perfil exige `PERFIL.EXCLUIR`. Consultar a lista de registros de auditoria e o detalhe de um registro, conforme a spec `auditoria`, exige `AUDITORIA.VISUALIZAR`. As rotas de opções que alimentam os campos de escolha, definidas na spec `interface`, DEVEM (MUST) exigir autenticação e a permissão da tela que consome as opções, declarada na view. A rota de opções de usuários exige `AUDITORIA.VISUALIZAR`, porque só a consulta da auditoria a usa. Uma rota de opções cujos dados não são restritos e que serve a formulários de telas diferentes, como a de perfis, DEVE (MUST) exigir somente autenticação, pela mesma razão que a escolha do perfil não exige `PERFIL.VISUALIZAR`. A escolha do perfil no cadastro e na troca de perfil de um usuário, e a resolução do código do perfil na importação, fazem parte dessas operações e NÃO DEVEM (MUST NOT) exigir `PERFIL.VISUALIZAR`. A página inicial autenticada DEVE (MUST) exigir somente autenticação, sem permissão específica. As funcionalidades de módulos futuros DEVEM (MUST) ser protegidas por permissões próprias, no mesmo formato, introduzidas pelas Changes desses módulos. Os comandos de gerenciamento `create_superadmin` e `set_superadmin`, definidos no design, são executados pelo servidor e NÃO DEVEM (MUST NOT) passar pela autorização por permissão da interface web. Eles continuam sujeitos às respectivas regras de negócio da spec `gestao-usuarios`.

#### Scenario: Permissão da listagem
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `USUARIO.VISUALIZAR`
- **WHEN** ele acessa a lista de usuários
- **THEN** o acesso é concedido

#### Scenario: Permissão da troca de perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `USUARIO.ALTERAR_PERFIL`
- **WHEN** ele acessa a troca de perfil de outro usuário
- **THEN** o acesso é concedido
- **AND** a troca oferece os perfis existentes para escolha, sem exigir `PERFIL.VISUALIZAR`

#### Scenario: Permissão da importação de usuários
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `USUARIO.IMPORTAR`
- **WHEN** ele acessa o envio e o histórico da importação de usuários
- **THEN** o acesso é concedido

#### Scenario: Permissão da gestão de perfis
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True`
- **WHEN** ele acessa a criação de perfil
- **THEN** o acesso é concedido pela posse de `PERFIL.CRIAR` decorrente do acesso irrestrito

#### Scenario: Página inicial sem permissão específica
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`, que não concede nenhuma permissão
- **WHEN** ele acessa a página inicial autenticada
- **THEN** o acesso é concedido

#### Scenario: Permissão da consulta da auditoria
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `AUDITORIA.VISUALIZAR`
- **WHEN** ele acessa a lista de registros de auditoria e o detalhe de um registro
- **THEN** o acesso é concedido nas duas telas
- **AND** o acesso à lista de usuários continua recusado com 403

#### Scenario: Permissão da rota de opções de usuários
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `AUDITORIA.VISUALIZAR`
- **WHEN** ele acessa diretamente a rota de opções de usuários
- **THEN** a requisição é recusada com 403

#### Scenario: Rota de opções exige autenticação
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa diretamente qualquer rota de opções
- **THEN** ele é redirecionado para a página de login e nenhuma opção é devolvida
