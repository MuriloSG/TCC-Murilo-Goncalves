## MODIFIED Requirements

### Requirement: Autenticação exigida para funcionalidades protegidas
Toda funcionalidade protegida DEVE (MUST) exigir um usuário autenticado. Um visitante não autenticado NÃO DEVE (MUST NOT) acessar funcionalidade protegida, inclusive quando conhecer ou digitar diretamente a URL, e NÃO DEVE (MUST NOT) ter nenhuma permissão. Ao tentar acessar uma funcionalidade protegida, o visitante DEVE (MUST) ser redirecionado para a página de login, com a indicação da página solicitada, conforme o comportamento definido no design. Estar autenticado NÃO DEVE (MUST NOT) implicar a posse de qualquer permissão: a autenticação identifica o usuário, e a autorização decide, em seguida, se ele pode executar a funcionalidade. Os fluxos de login, logout e recuperação de senha seguem a spec `autenticacao`. As rotas públicas desse fluxo, isto é, o login e as etapas da recuperação de senha definidas no design, NÃO DEVEM (MUST NOT) ser tratadas como funcionalidades protegidas por permissão. O calendário público do ensalamento, na rota `calendario/`, também é rota pública: NÃO DEVE (MUST NOT) exigir autenticação nem permissão, e segue a spec `calendario-publico`. Nenhuma outra rota DEVE (MUST) deixar de ser protegida por causa dele.

#### Scenario: Visitante acessa URL protegida diretamente
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa diretamente a URL da lista de usuários
- **THEN** ele é redirecionado para a página de login com a indicação da página solicitada
- **AND** a lista de usuários não é exibida

#### Scenario: Visitante envia POST para funcionalidade protegida
- **GIVEN** um visitante não autenticado
- **WHEN** ele envia uma requisição POST com dados válidos e token CSRF válido para a rota de cadastro de usuário
- **THEN** ele é redirecionado para a página de login e nenhum usuário é criado

#### Scenario: Visitante sem permissões
- **GIVEN** um visitante não autenticado
- **WHEN** a posse de qualquer permissão é avaliada para ele
- **THEN** nenhuma permissão é concedida

#### Scenario: Autenticado não significa autorizado
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`
- **WHEN** ele acessa a lista de usuários
- **THEN** a requisição é recusada com 403

#### Scenario: Calendário público sem autenticação
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa `calendario/`
- **THEN** o calendário público é exibido, sem redirecionamento para a página de login
- **AND** o acesso a `ensalamento/` continua redirecionando para a página de login
