## MODIFIED Requirements

### Requirement: Catálogo de permissões e perfis do sistema
As permissões DEVEM (MUST) ser definidas pelo sistema, com código único no formato `RECURSO.ACAO`, com exatamente dois níveis separados por ponto, e DEVEM (MUST) entrar no catálogo somente por migrations. A aplicação NÃO DEVE (MUST NOT) oferecer interface nem operação para criar, editar ou excluir permissões, inclusive para o superadmin. O catálogo DEVE (MUST) conter somente as seis permissões do recurso `USUARIO` (`USUARIO.VISUALIZAR`, `USUARIO.CRIAR`, `USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL`, `USUARIO.ALTERAR_SITUACAO` e `USUARIO.IMPORTAR`) e as cinco permissões do recurso `PERFIL` (`PERFIL.VISUALIZAR`, `PERFIL.CRIAR`, `PERFIL.EDITAR`, `PERFIL.ALTERAR_PERMISSOES` e `PERFIL.EXCLUIR`). Permissões de outros recursos DEVEM (MUST) entrar no catálogo somente pelas Changes dos seus módulos. Um perfil DEVE (MUST) servir somente como agrupador das permissões que concede, e não há hierarquia nem herança de permissões entre perfis. A carga inicial DEVE (MUST) criar os perfis do sistema `ADMINISTRADOR` e `DOCENTE`, com a seguinte configuração inicial: `ADMINISTRADOR` concede as seis permissões de `USUARIO`, `DOCENTE` não concede nenhuma permissão, e nenhum perfil concede permissões de `PERFIL`. A migration que acrescenta `USUARIO.IMPORTAR` DEVE (MUST) concedê-la ao perfil `ADMINISTRADOR` sem alterar as demais permissões concedidas pelos perfis existentes. Depois da instalação, os perfis e as permissões que concedem DEVEM (MUST) ser gerenciados pelo superadmin conforme a spec `gestao-perfis`, o que inclui perfis personalizados além dos perfis do sistema. O acesso público do Visualizador NÃO DEVE (MUST NOT) depender de perfil nem de autenticação, e a carga inicial NÃO DEVE (MUST NOT) criar perfil nem usuário para o Visualizador.

Convenções dos cenários desta spec:
- Quando um cenário cita os perfis `ADMINISTRADOR` ou `DOCENTE` sem descrever as permissões que concedem, refere-se à configuração inicial da carga. Essa configuração pode ser alterada pelo superadmin, conforme a spec `gestao-perfis`.
- `COORDENACAO` é um exemplo de perfil personalizado criado pelo superadmin. Ele não é criado pela carga do sistema.
- Códigos de outros recursos, como `ESPACO.CRIAR` e `RESERVA.APROVAR`, são apenas exemplos conceituais de permissões que poderão existir no futuro. Eles não fazem parte do catálogo e não criam nenhum requisito de implementação para esses recursos.

#### Scenario: Catálogo inicial instalado
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** as permissões e os perfis existentes são consultados
- **THEN** existem exatamente as seis permissões do recurso `USUARIO` e as cinco permissões do recurso `PERFIL`
- **AND** não existe permissão de nenhum outro recurso
- **AND** existem exatamente os perfis `ADMINISTRADOR` e `DOCENTE`, ambos marcados como perfis do sistema
- **AND** `ADMINISTRADOR` concede as seis permissões de `USUARIO`, `DOCENTE` não concede nenhuma e nenhum perfil concede permissões de `PERFIL`

#### Scenario: Permissão de importar acrescentada a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta `USUARIO.IMPORTAR` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder `USUARIO.IMPORTAR` e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Código de permissão fora do formato
- **GIVEN** o catálogo de permissões
- **WHEN** uma gravação tenta criar uma permissão com o código `usuario.criar` ou `USUARIO`
- **THEN** a gravação é recusada

#### Scenario: Carga sem perfil para o Visualizador
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** os perfis e os usuários existentes são consultados
- **THEN** a carga não criou perfil nem usuário que represente o Visualizador

#### Scenario: Interface sem cadastro de permissões
- **GIVEN** um superadmin ativo autenticado
- **WHEN** ele procura na interface uma forma de criar, editar ou excluir uma permissão do catálogo
- **THEN** não existe essa ação

#### Scenario: Superadmin gerencia os perfis sem criar permissões
- **GIVEN** um superadmin ativo autenticado
- **WHEN** ele cria o perfil personalizado `COORDENACAO` e concede a ele `USUARIO.VISUALIZAR`, conforme a spec `gestao-perfis`
- **THEN** o perfil passa a existir e a conceder `USUARIO.VISUALIZAR`
- **AND** o catálogo de permissões continua com as mesmas onze permissões

### Requirement: Correspondência entre operações e permissões
Cada funcionalidade protegida por permissão DEVE (MUST) exigir exatamente a permissão correspondente. Para as operações de gestão de usuários descritas na spec `gestao-usuarios`, a correspondência DEVE (MUST) ser: listar e consultar usuários exige `USUARIO.VISUALIZAR`; cadastrar usuário exige `USUARIO.CRIAR`; alterar nome e e-mail exige `USUARIO.EDITAR`; trocar o perfil exige `USUARIO.ALTERAR_PERFIL`; desativar e reativar exige `USUARIO.ALTERAR_SITUACAO`; enviar, confirmar e descartar importações de usuários, consultar o histórico e o detalhe delas e baixar o modelo exige `USUARIO.IMPORTAR`. Na importação de usuários, cada ação de linha DEVE (MUST) exigir também a permissão da operação equivalente, conforme a spec `gestao-usuarios`, e a falta dela DEVE (MUST) ser um erro da linha, e não uma recusa de acesso à rota. Para as operações de gestão de perfis descritas na spec `gestao-perfis`, a correspondência DEVE (MUST) ser: listar e consultar perfis exige `PERFIL.VISUALIZAR`; criar perfil exige `PERFIL.CRIAR`; alterar nome e descrição de perfil exige `PERFIL.EDITAR`; definir as permissões de um perfil exige `PERFIL.ALTERAR_PERMISSOES`; excluir perfil exige `PERFIL.EXCLUIR`. A escolha do perfil no cadastro e na troca de perfil de um usuário, e a resolução do código do perfil na importação, fazem parte dessas operações e NÃO DEVEM (MUST NOT) exigir `PERFIL.VISUALIZAR`. A página inicial autenticada DEVE (MUST) exigir somente autenticação, sem permissão específica. As funcionalidades de módulos futuros DEVEM (MUST) ser protegidas por permissões próprias, no mesmo formato, introduzidas pelas Changes desses módulos. Os comandos de gerenciamento `create_superadmin` e `set_superadmin`, definidos no design, são executados pelo servidor e NÃO DEVEM (MUST NOT) passar pela autorização por permissão da interface web. Eles continuam sujeitos às respectivas regras de negócio da spec `gestao-usuarios`.

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
