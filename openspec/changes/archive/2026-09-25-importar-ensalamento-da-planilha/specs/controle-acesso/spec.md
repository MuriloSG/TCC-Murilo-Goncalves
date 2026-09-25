## MODIFIED Requirements

### Requirement: Catálogo de permissões e perfis do sistema
As permissões DEVEM (MUST) ser definidas pelo sistema, com código único no formato `RECURSO.ACAO`, com exatamente dois níveis separados por ponto, e DEVEM (MUST) entrar no catálogo somente por migrations. A aplicação NÃO DEVE (MUST NOT) oferecer interface nem operação para criar, editar ou excluir permissões, inclusive para o superadmin. O catálogo DEVE (MUST) conter somente as seis permissões do recurso `USUARIO` (`USUARIO.VISUALIZAR`, `USUARIO.CRIAR`, `USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL`, `USUARIO.ALTERAR_SITUACAO` e `USUARIO.IMPORTAR`), as cinco permissões do recurso `PERFIL` (`PERFIL.VISUALIZAR`, `PERFIL.CRIAR`, `PERFIL.EDITAR`, `PERFIL.ALTERAR_PERMISSOES` e `PERFIL.EXCLUIR`), a permissão `AUDITORIA.VISUALIZAR` do recurso `AUDITORIA` e a permissão `ENSALAMENTO.IMPORTAR` do recurso `ENSALAMENTO`. Permissões de outros recursos DEVEM (MUST) entrar no catálogo somente pelas Changes dos seus módulos. Um perfil DEVE (MUST) servir somente como agrupador das permissões que concede, e não há hierarquia nem herança de permissões entre perfis. A carga inicial DEVE (MUST) criar os perfis do sistema `ADMINISTRADOR` e `DOCENTE`, com a seguinte configuração inicial: `ADMINISTRADOR` concede as seis permissões de `USUARIO`, `AUDITORIA.VISUALIZAR` e `ENSALAMENTO.IMPORTAR`, `DOCENTE` não concede nenhuma permissão, e nenhum perfil concede permissões de `PERFIL`. A migration que acrescenta `USUARIO.IMPORTAR` DEVE (MUST) concedê-la ao perfil `ADMINISTRADOR` sem alterar as demais permissões concedidas pelos perfis existentes, e as migrations que acrescentam `AUDITORIA.VISUALIZAR` e `ENSALAMENTO.IMPORTAR` DEVEM (MUST) fazer o mesmo. `AUDITORIA.VISUALIZAR` e `ENSALAMENTO.IMPORTAR` NÃO DEVEM (MUST NOT) ser permissões reservadas ao superadmin: o superadmin PODE (MAY) concedê-las a qualquer perfil, conforme a spec `gestao-perfis`. Depois da instalação, os perfis e as permissões que concedem DEVEM (MUST) ser gerenciados pelo superadmin conforme a spec `gestao-perfis`, o que inclui perfis personalizados além dos perfis do sistema. O acesso público do Visualizador NÃO DEVE (MUST NOT) depender de perfil nem de autenticação, e a carga inicial NÃO DEVE (MUST NOT) criar perfil nem usuário para o Visualizador.

Convenções dos cenários desta spec:
- Quando um cenário cita os perfis `ADMINISTRADOR` ou `DOCENTE` sem descrever as permissões que concedem, refere-se à configuração inicial da carga. Essa configuração pode ser alterada pelo superadmin, conforme a spec `gestao-perfis`.
- `COORDENACAO` é um exemplo de perfil personalizado criado pelo superadmin. Ele não é criado pela carga do sistema.
- Códigos de outros recursos, como `ESPACO.CRIAR` e `RESERVA.APROVAR`, são apenas exemplos conceituais de permissões que poderão existir no futuro. Eles não fazem parte do catálogo e não criam nenhum requisito de implementação para esses recursos.

#### Scenario: Catálogo inicial instalado
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** as permissões e os perfis existentes são consultados
- **THEN** existem exatamente as seis permissões do recurso `USUARIO`, as cinco permissões do recurso `PERFIL`, a permissão `AUDITORIA.VISUALIZAR` e a permissão `ENSALAMENTO.IMPORTAR`
- **AND** não existe permissão de nenhum outro recurso
- **AND** existem exatamente os perfis `ADMINISTRADOR` e `DOCENTE`, ambos marcados como perfis do sistema
- **AND** `ADMINISTRADOR` concede as seis permissões de `USUARIO`, `AUDITORIA.VISUALIZAR` e `ENSALAMENTO.IMPORTAR`, `DOCENTE` não concede nenhuma e nenhum perfil concede permissões de `PERFIL`

#### Scenario: Permissão de importar acrescentada a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta `USUARIO.IMPORTAR` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder `USUARIO.IMPORTAR` e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Permissão de ensalamento acrescentada a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta `ENSALAMENTO.IMPORTAR` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder `ENSALAMENTO.IMPORTAR` e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Ensalamento concedido a um perfil personalizado
- **GIVEN** um superadmin ativo autenticado e o perfil personalizado `COORDENACAO`
- **WHEN** ele concede `ENSALAMENTO.IMPORTAR` a `COORDENACAO`
- **THEN** a permissão é concedida, por não ser reservada ao superadmin

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
- **AND** o catálogo de permissões continua com as mesmas treze permissões

#### Scenario: Permissão de auditoria acrescentada a uma instalação existente
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR` e concedeu `USUARIO.VISUALIZAR` ao perfil `COORDENACAO`
- **WHEN** a migration que acrescenta `AUDITORIA.VISUALIZAR` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder `AUDITORIA.VISUALIZAR` e continua sem `USUARIO.EDITAR`
- **AND** `COORDENACAO` continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Auditoria concedida a um perfil personalizado
- **GIVEN** um superadmin ativo autenticado e o perfil personalizado `COORDENACAO`
- **WHEN** ele concede `AUDITORIA.VISUALIZAR` a `COORDENACAO`
- **THEN** a permissão é concedida, por não ser reservada ao superadmin
