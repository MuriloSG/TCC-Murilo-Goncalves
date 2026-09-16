## ADDED Requirements

### Requirement: Catálogo de permissões e perfis do sistema
As permissões DEVEM (MUST) ser definidas pelo sistema, com código único no formato `RECURSO.ACAO`, com exatamente dois níveis separados por ponto, e DEVEM (MUST) entrar no catálogo somente por migrations. A aplicação NÃO DEVE (MUST NOT) oferecer interface nem operação para criar, editar ou excluir permissões, inclusive para o superadmin. O catálogo definido por esta Change DEVE (MUST) conter somente as cinco permissões do recurso `USUARIO` (`USUARIO.VISUALIZAR`, `USUARIO.CRIAR`, `USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL` e `USUARIO.ALTERAR_SITUACAO`) e as cinco permissões do recurso `PERFIL` (`PERFIL.VISUALIZAR`, `PERFIL.CRIAR`, `PERFIL.EDITAR`, `PERFIL.ALTERAR_PERMISSOES` e `PERFIL.EXCLUIR`), previstas na proposal e no design. Esta Change NÃO DEVE (MUST NOT) acrescentar ao catálogo permissões de nenhum outro recurso. Um perfil DEVE (MUST) servir somente como agrupador das permissões que concede, e não há hierarquia nem herança de permissões entre perfis. A carga inicial DEVE (MUST) criar os perfis do sistema `ADMINISTRADOR` e `DOCENTE`, com a seguinte configuração inicial: `ADMINISTRADOR` concede as cinco permissões de `USUARIO`, `DOCENTE` não concede nenhuma permissão, e nenhum perfil concede permissões de `PERFIL`. Depois da instalação, os perfis e as permissões que concedem DEVEM (MUST) ser gerenciados pelo superadmin conforme a spec `gestao-perfis`, o que inclui perfis personalizados além dos perfis do sistema. O acesso público do Visualizador NÃO DEVE (MUST NOT) depender de perfil nem de autenticação, e a carga inicial NÃO DEVE (MUST NOT) criar perfil nem usuário para o Visualizador.

Convenções dos cenários desta spec:
- Quando um cenário cita os perfis `ADMINISTRADOR` ou `DOCENTE` sem descrever as permissões que concedem, refere-se à configuração inicial da carga. Essa configuração pode ser alterada pelo superadmin, conforme a spec `gestao-perfis`.
- `COORDENACAO` é um exemplo de perfil personalizado criado pelo superadmin. Ele não é criado pela carga do sistema.
- Códigos de outros recursos, como `ESPACO.CRIAR` e `RESERVA.APROVAR`, são apenas exemplos conceituais de permissões que poderão existir no futuro. Eles não fazem parte do catálogo desta Change e não criam nenhum requisito de implementação para esses recursos.

#### Scenario: Catálogo inicial instalado
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** as permissões e os perfis existentes são consultados
- **THEN** existem exatamente as cinco permissões do recurso `USUARIO` e as cinco permissões do recurso `PERFIL`
- **AND** não existe permissão de nenhum outro recurso
- **AND** existem exatamente os perfis `ADMINISTRADOR` e `DOCENTE`, ambos marcados como perfis do sistema
- **AND** `ADMINISTRADOR` concede as cinco permissões de `USUARIO`, `DOCENTE` não concede nenhuma e nenhum perfil concede permissões de `PERFIL`

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
- **AND** o catálogo de permissões continua com as mesmas dez permissões

### Requirement: Permissões reservadas ao superadmin
As permissões do recurso `PERFIL` DEVEM (MUST) formar o conjunto de permissões reservadas ao superadmin. Uma permissão reservada NÃO DEVE (MUST NOT) ser concedida a nenhum perfil, do sistema ou personalizado, nem pela carga, nem por migrations futuras, nem pelas operações da spec `gestao-perfis`. Um superadmin ativo DEVE (MUST) possuir as permissões reservadas pela regra de acesso irrestrito. Para um usuário que não é superadmin ativo, o ponto único de decisão de acesso NÃO DEVE (MUST NOT) conceder uma permissão reservada, mesmo que ela esteja registrada em um perfil dele por uma gravação que não passou pelas operações da aplicação. A reserva DEVE (MUST) ser decidida pelo código da permissão, sem consultar o perfil, o nome do perfil ou `is_superadmin` fora do ponto único de decisão de acesso. As permissões reservadas NÃO DEVEM (MUST NOT) fazer parte do conjunto de capacidade administrativa definido na spec `gestao-usuarios`.

#### Scenario: Superadmin ativo possui as permissões reservadas
- **GIVEN** um usuário ativo com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** é avaliado se ele possui `PERFIL.CRIAR` e `PERFIL.EXCLUIR`
- **THEN** as duas permissões são concedidas

#### Scenario: Usuário com todas as permissões concedíveis não possui reservadas
- **GIVEN** um usuário ativo, sem superadmin, cujo perfil concede todas as permissões do recurso `USUARIO`
- **WHEN** é avaliado se ele possui `PERFIL.VISUALIZAR`
- **THEN** a permissão não é concedida

#### Scenario: Permissão reservada gravada diretamente em um perfil
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `COORDENACAO`
- **AND** uma gravação que não passou pelas operações da aplicação vinculou `PERFIL.ALTERAR_PERMISSOES` a `COORDENACAO`
- **WHEN** é avaliado se esse usuário possui `PERFIL.ALTERAR_PERMISSOES`
- **THEN** a permissão não é concedida

#### Scenario: Carga sem permissões reservadas concedidas
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** as permissões concedidas por todos os perfis são consultadas
- **THEN** nenhum perfil concede permissão do recurso `PERFIL`

### Requirement: Correspondência entre operações e permissões
Cada funcionalidade protegida por permissão DEVE (MUST) exigir exatamente a permissão correspondente. Para as operações de gestão de usuários descritas na spec `gestao-usuarios`, a correspondência DEVE (MUST) ser: listar e consultar usuários exige `USUARIO.VISUALIZAR`; cadastrar usuário exige `USUARIO.CRIAR`; alterar nome e e-mail exige `USUARIO.EDITAR`; trocar o perfil exige `USUARIO.ALTERAR_PERFIL`; desativar e reativar exige `USUARIO.ALTERAR_SITUACAO`. Para as operações de gestão de perfis descritas na spec `gestao-perfis`, a correspondência DEVE (MUST) ser: listar e consultar perfis exige `PERFIL.VISUALIZAR`; criar perfil exige `PERFIL.CRIAR`; alterar nome e descrição de perfil exige `PERFIL.EDITAR`; definir as permissões de um perfil exige `PERFIL.ALTERAR_PERMISSOES`; excluir perfil exige `PERFIL.EXCLUIR`. A escolha do perfil no cadastro e na troca de perfil de um usuário faz parte dessas operações e NÃO DEVE (MUST NOT) exigir `PERFIL.VISUALIZAR`. A página inicial autenticada DEVE (MUST) exigir somente autenticação, sem permissão específica. As funcionalidades de módulos futuros DEVEM (MUST) ser protegidas por permissões próprias, no mesmo formato, introduzidas pelas Changes desses módulos. Os comandos de gerenciamento `criar_superadmin` e `alterar_superadmin`, definidos no design, são executados pelo servidor e NÃO DEVEM (MUST NOT) passar pela autorização por permissão da interface web. Eles continuam sujeitos às respectivas regras de negócio da spec `gestao-usuarios`.

#### Scenario: Permissão da listagem
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `USUARIO.VISUALIZAR`
- **WHEN** ele acessa a lista de usuários
- **THEN** o acesso é concedido

#### Scenario: Permissão da troca de perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `USUARIO.ALTERAR_PERFIL`
- **WHEN** ele acessa a troca de perfil de outro usuário
- **THEN** o acesso é concedido
- **AND** a troca oferece os perfis existentes para escolha, sem exigir `PERFIL.VISUALIZAR`

#### Scenario: Permissão da gestão de perfis
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True`
- **WHEN** ele acessa a criação de perfil
- **THEN** o acesso é concedido pela posse de `PERFIL.CRIAR` decorrente do acesso irrestrito

#### Scenario: Página inicial sem permissão específica
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`, que não concede nenhuma permissão
- **WHEN** ele acessa a página inicial autenticada
- **THEN** o acesso é concedido

### Requirement: Autenticação exigida para funcionalidades protegidas
Toda funcionalidade protegida DEVE (MUST) exigir um usuário autenticado. Um visitante não autenticado NÃO DEVE (MUST NOT) acessar funcionalidade protegida, inclusive quando conhecer ou digitar diretamente a URL, e NÃO DEVE (MUST NOT) ter nenhuma permissão. Ao tentar acessar uma funcionalidade protegida, o visitante DEVE (MUST) ser redirecionado para a página de login, com a indicação da página solicitada, conforme o comportamento definido no design. Estar autenticado NÃO DEVE (MUST NOT) implicar a posse de qualquer permissão: a autenticação identifica o usuário, e a autorização decide, em seguida, se ele pode executar a funcionalidade. Os fluxos de login, logout e recuperação de senha seguem a spec `autenticacao`. As rotas públicas desse fluxo, isto é, o login e as etapas da recuperação de senha definidas no design, NÃO DEVEM (MUST NOT) ser tratadas como funcionalidades protegidas por permissão.

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

### Requirement: Autorização por permissão efetiva
O acesso a uma funcionalidade protegida por um usuário autenticado DEVE (MUST) ser decidido pelas permissões efetivas dele, em um único ponto de decisão de acesso da aplicação, conforme o design. A decisão DEVE (MUST) seguir esta ordem: usuário não autenticado não tem permissão; usuário inativo não tem permissão; superadmin ativo tem qualquer permissão; nos demais casos, a permissão é concedida somente se estiver entre as permissões efetivas. Possuir outra permissão, inclusive do mesmo recurso, NÃO DEVE (MUST NOT) conceder acesso. A verificação DEVE (MUST) ser feita no servidor e valer para todos os métodos HTTP da funcionalidade. Quando uma verificação exigir várias permissões, o acesso DEVE (MUST) ser concedido somente se todas forem concedidas.

#### Scenario: Usuário com a permissão exigida
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede `USUARIO.CRIAR`
- **WHEN** ele envia um cadastro válido de usuário
- **THEN** o acesso é concedido e o cadastro segue as regras da spec `gestao-usuarios`

#### Scenario: Outra permissão do mesmo recurso não concede acesso
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`, mas não `USUARIO.ALTERAR_SITUACAO`
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para desativar outro usuário
- **THEN** a requisição é recusada com 403

#### Scenario: Verificação também no POST
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `USUARIO.EDITAR`
- **WHEN** ele envia diretamente uma requisição POST de edição de outro usuário, com token CSRF válido, sem passar pelo formulário
- **THEN** a requisição é recusada com 403

#### Scenario: Várias permissões exigidas
- **GIVEN** um usuário ativo, sem superadmin, cujo perfil concede `USUARIO.VISUALIZAR`, mas não `USUARIO.CRIAR`
- **WHEN** é avaliado se ele possui ao mesmo tempo `USUARIO.VISUALIZAR` e `USUARIO.CRIAR`
- **THEN** o resultado é negativo

### Requirement: Permissões efetivas
As permissões efetivas de um usuário ativo, que não é superadmin, DEVEM (MUST) ser exatamente as permissões concedidas pelo perfil atual dele no momento da avaliação, sem as permissões reservadas ao superadmin, calculadas como a união das permissões dos perfis vinculados, que nesta versão são sempre um só. Permissões de um perfil que o usuário já teve, ou que o perfil dele já concedeu e deixou de conceder, NÃO DEVEM (MUST NOT) fazer parte das permissões efetivas. As permissões efetivas de um usuário inativo DEVEM (MUST) ser vazias, qualquer que seja o seu perfil ou o valor de `is_superadmin`. Para exibição, as permissões efetivas de um superadmin ativo DEVEM (MUST) corresponder a todo o catálogo de permissões existente, incluindo as reservadas, independentemente do seu perfil. A decisão de acesso de um superadmin ativo NÃO DEVE (MUST NOT) depender desse conjunto, porque ele tem acesso irrestrito, inclusive a permissões que ainda não existem no catálogo.

#### Scenario: Permissões vindas do perfil
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `ADMINISTRADOR` na configuração inicial
- **WHEN** as permissões efetivas dele são calculadas
- **THEN** elas são exatamente as cinco permissões de `USUARIO` concedidas por `ADMINISTRADOR`

#### Scenario: Perfil sem permissões
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `DOCENTE` na configuração inicial
- **WHEN** as permissões efetivas dele são calculadas
- **THEN** o conjunto é vazio

#### Scenario: Permissões efetivas acompanham a configuração atual do perfil
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `DOCENTE`
- **AND** que o superadmin concedeu `USUARIO.VISUALIZAR` ao perfil `DOCENTE`
- **WHEN** as permissões efetivas dele são calculadas
- **THEN** o conjunto é exatamente `USUARIO.VISUALIZAR`

#### Scenario: Usuário inativo com perfil que concede permissões
- **GIVEN** um usuário com `is_active = False`, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** as permissões efetivas dele são calculadas
- **THEN** o conjunto é vazio

#### Scenario: Superadmin ativo com perfil sem permissões
- **GIVEN** um usuário ativo com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** as permissões efetivas dele são calculadas
- **THEN** o conjunto exibido contém todas as permissões do catálogo, inclusive as do recurso `PERFIL`

### Requirement: Acesso irrestrito do superadmin ativo
Um usuário autenticado com `is_active = True` e `is_superadmin = True` DEVE (MUST) ter acesso a todas as funcionalidades protegidas da aplicação, incluindo a gestão de perfis, independentemente do seu perfil e das permissões que o perfil concede, inclusive permissões introduzidas no futuro. Esse acesso DEVE (MUST) ser uma exceção explícita tratada no ponto único de decisão de acesso. `is_superadmin` NÃO DEVE (MUST NOT) ser tratado como perfil nem como permissão, e NÃO DEVE (MUST NOT) aparecer no catálogo de permissões. A decisão de acesso NÃO DEVE (MUST NOT) depender de `is_superuser` do Django nem de outro mecanismo de autorização paralelo. O acesso irrestrito vale só para a autorização: as regras de negócio, como a continuidade administrativa, a proteção dos perfis do sistema e a proibição de conceder permissões reservadas, continuam valendo para o superadmin, conforme as specs `gestao-usuarios` e `gestao-perfis`. NÃO DEVE (MUST NOT) existir exigência de haver sempre um superadmin ativo.

#### Scenario: Superadmin com perfil sem a permissão
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** ele acessa a lista de usuários, o cadastro, a edição, a troca de perfil, as ações de situação e as funcionalidades de gestão de perfis
- **THEN** o acesso é concedido em todas elas

#### Scenario: Superadmin e permissão fora do catálogo atual
- **GIVEN** um usuário ativo com `is_superadmin = True`
- **WHEN** é avaliado se ele possui uma permissão de um recurso ainda não presente no catálogo, como o exemplo conceitual `RESERVA.APROVAR`
- **THEN** a permissão é concedida

#### Scenario: Superadmin não é permissão do catálogo
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** o catálogo de permissões é consultado
- **THEN** nenhuma permissão representa o superadmin

#### Scenario: Superadmin continua sujeito às regras de negócio
- **GIVEN** um superadmin ativo autenticado que é o único usuário com capacidade administrativa
- **WHEN** ele tenta desativar a própria conta
- **THEN** a autorização é concedida e a operação é recusada pela regra de continuidade administrativa da spec `gestao-usuarios`

#### Scenario: Superadmin sujeito à proteção dos perfis do sistema
- **GIVEN** um superadmin ativo autenticado
- **WHEN** ele tenta excluir o perfil do sistema `DOCENTE`
- **THEN** a autorização é concedida e a exclusão é recusada pela regra de perfil do sistema da spec `gestao-perfis`

### Requirement: Ausência de acesso de usuário inativo
Um usuário com `is_active = False` NÃO DEVE (MUST NOT) acessar nenhuma funcionalidade protegida, mesmo que o seu perfil conceda a permissão exigida e mesmo que tenha `is_superadmin = True`. Uma sessão aberta antes da desativação DEVE (MUST) ser tratada como não autenticada, conforme a spec `autenticacao`. Independentemente disso, o ponto único de decisão de acesso DEVE (MUST) recusar qualquer permissão a um usuário inativo.

#### Scenario: Usuário inativo com perfil que concede a permissão
- **GIVEN** um usuário com `is_active = False`, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** é avaliado se ele possui `USUARIO.VISUALIZAR`
- **THEN** a permissão não é concedida

#### Scenario: Superadmin inativo
- **GIVEN** um usuário com `is_superadmin = True` e `is_active = False`
- **WHEN** é avaliado se ele possui qualquer permissão
- **THEN** nenhuma permissão é concedida

#### Scenario: Sessão aberta de superadmin desativado
- **GIVEN** um superadmin ativo autenticado com uma sessão aberta
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** ele é desativado e, em seguida, acessa a lista de usuários com a mesma sessão
- **THEN** ele é redirecionado para a página de login e a lista não é exibida

### Requirement: Negação de acesso
Quando um usuário autenticado e ativo não for superadmin e não possuir a permissão exigida, a funcionalidade DEVE (MUST) ser negada com a resposta de acesso negado definida no design (403, com página de acesso negado). A negação DEVE (MUST) ocorrer antes da execução da operação: nenhuma regra de negócio é executada e nenhum dado é criado, alterado ou removido. A negação NÃO DEVE (MUST NOT) depender de a interface ter escondido o link ou o botão correspondente.

#### Scenario: Acesso negado a página protegida
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`
- **WHEN** ele acessa por GET o formulário de cadastro de usuário
- **THEN** a resposta é 403 com a página de acesso negado

#### Scenario: Acesso negado sem alteração de dados
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `USUARIO.ALTERAR_PERFIL`
- **AND** um usuário alvo com o perfil `DOCENTE`
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para trocar o perfil do alvo para `ADMINISTRADOR`
- **THEN** a resposta é 403
- **AND** o alvo continua com o perfil `DOCENTE` e nenhum outro dado muda

#### Scenario: Negação antes das regras de negócio
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `USUARIO.ALTERAR_SITUACAO`
- **AND** um alvo que é o único usuário ativo com capacidade administrativa
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para desativar o alvo
- **THEN** a resposta é 403, e não a mensagem de erro da regra de continuidade administrativa
- **AND** o alvo continua ativo

### Requirement: Autorização independente do nome do perfil
Nenhuma decisão de autorização DEVE (MUST) comparar o código, o nome ou a marca de perfil do sistema de um perfil, nem consultar `is_superadmin` fora do ponto único de decisão de acesso. A regra de continuidade administrativa e a proteção do e-mail de superadmin, definidas na spec `gestao-usuarios`, PODEM (MAY) considerar `is_superadmin`, por serem regras de negócio e não decisões genéricas de autorização. A proteção contra exclusão de perfis do sistema, definida na spec `gestao-perfis`, PODE (MAY) considerar a marca de perfil do sistema, pelo mesmo motivo. Views, templates e demais componentes DEVEM (MUST) decidir acesso somente pela permissão correspondente. O código do perfil PODE (MAY) ser usado apenas na criação do perfil, para localizar os perfis do sistema na carga e nas migrations, e para exibição. Dois perfis que concedam as mesmas permissões DEVEM (MUST) produzir exatamente as mesmas decisões de acesso, quaisquer que sejam seus códigos, nomes e marcas de perfil do sistema.

#### Scenario: Perfis diferentes com as mesmas permissões
- **GIVEN** um usuário ativo, sem superadmin, com o perfil do sistema `ADMINISTRADOR`
- **AND** outro usuário ativo, sem superadmin, com o perfil personalizado `COORDENACAO`, de outro código e outro nome, que concede exatamente as mesmas permissões
- **WHEN** as mesmas funcionalidades protegidas são avaliadas para os dois
- **THEN** as decisões de acesso são idênticas

#### Scenario: Perfil ADMINISTRADOR sem uma permissão
- **GIVEN** que o superadmin retirou `USUARIO.CRIAR` do perfil `ADMINISTRADOR`
- **AND** um usuário ativo, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** ele envia um cadastro válido de usuário, com token CSRF válido
- **THEN** a requisição é recusada com 403 e nenhum usuário é criado

#### Scenario: Perfil DOCENTE com uma permissão
- **GIVEN** que o superadmin concedeu `USUARIO.VISUALIZAR` ao perfil `DOCENTE`
- **AND** um usuário ativo, sem superadmin, com o perfil `DOCENTE`
- **WHEN** ele acessa a lista de usuários
- **THEN** o acesso é concedido

### Requirement: Menor privilégio
Um usuário que não é superadmin ativo DEVE (MUST) ter acesso somente às funcionalidades cujas permissões o seu perfil concede, e a nenhuma outra. Nenhum perfil DEVE (MUST) receber implicitamente uma permissão: uma permissão só é concedida a um perfil por concessão explícita, feita pelo superadmin conforme a spec `gestao-perfis` ou pela configuração padrão de uma migration. Um perfil novo NÃO DEVE (MUST NOT) conceder nenhuma permissão além das escolhidas na criação. Uma migration de uma Change futura PODE (MAY) conceder uma configuração padrão das permissões que ela introduz somente aos perfis do sistema, uma única vez, quando é aplicada. Essa configuração padrão NÃO DEVE (MUST NOT) alcançar perfis personalizados, NÃO DEVE (MUST NOT) incluir permissões reservadas, NÃO DEVE (MUST NOT) retirar concessões existentes e NÃO DEVE (MUST NOT) ser reaplicada depois, de forma a não desfazer alterações feitas pelo superadmin. Acrescentar uma permissão ao catálogo, em uma Change futura, NÃO DEVE (MUST NOT) exigir alteração nas regras de autorização existentes nem depender de nomes de perfis. Os cenários abaixo usam `ESPACO.CRIAR` só como exemplo conceitual, sem acrescentá-la ao catálogo desta Change.

#### Scenario: Nova permissão não concedida automaticamente
- **GIVEN** um cenário conceitual em que uma permissão futura, como o exemplo `ESPACO.CRIAR`, foi acrescentada ao catálogo sem configuração padrão para nenhum perfil
- **AND** um usuário ativo, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** é avaliado se ele possui `ESPACO.CRIAR`
- **THEN** a permissão não é concedida

#### Scenario: Configuração padrão concedida a perfil do sistema
- **GIVEN** um cenário conceitual em que a permissão futura de exemplo `ESPACO.CRIAR` foi acrescentada ao catálogo com configuração padrão para o perfil do sistema `DOCENTE`
- **AND** um usuário ativo, sem superadmin, com o perfil `DOCENTE`
- **WHEN** é avaliado se ele possui `ESPACO.CRIAR`
- **THEN** a permissão é concedida
- **AND** ele continua sem as permissões dos recursos `USUARIO` e `PERFIL`

#### Scenario: Configuração padrão não alcança perfil personalizado
- **GIVEN** o mesmo cenário conceitual, em que `ESPACO.CRIAR` foi acrescentada com configuração padrão para o perfil do sistema `DOCENTE`
- **AND** um usuário ativo, sem superadmin, com o perfil personalizado `COORDENACAO`
- **WHEN** é avaliado se ele possui `ESPACO.CRIAR`
- **THEN** a permissão não é concedida

#### Scenario: Configuração padrão não é reaplicada
- **GIVEN** o mesmo cenário conceitual, em que `ESPACO.CRIAR` foi concedida como configuração padrão ao perfil `DOCENTE`
- **AND** que depois o superadmin retirou `ESPACO.CRIAR` do perfil `DOCENTE`
- **WHEN** as migrations são aplicadas novamente, sem nenhuma migration nova
- **THEN** o perfil `DOCENTE` continua sem `ESPACO.CRIAR`

### Requirement: Interface reflete a autorização sem substituí-la
A interface PODE (MAY) mostrar ou esconder links, botões e atalhos de acordo com as permissões efetivas do usuário, usando o mesmo ponto único de decisão de acesso, inclusive para verificar se o usuário possui alguma permissão de um recurso. Esconder um elemento NÃO DEVE (MUST NOT) substituir a verificação de autorização da funcionalidade no servidor. A página inicial autenticada DEVE (MUST) mostrar somente os atalhos para funcionalidades que o usuário pode acessar.

#### Scenario: Atalhos conforme permissões
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`
- **WHEN** ele abre a página inicial autenticada
- **THEN** a página não mostra atalhos para a gestão de usuários nem para a gestão de perfis

#### Scenario: Administrador sem atalho para a gestão de perfis
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** ele abre a página inicial autenticada
- **THEN** a página mostra os atalhos para a gestão de usuários e não mostra atalhos para a gestão de perfis

#### Scenario: Atalhos do superadmin
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** ele abre a página inicial autenticada
- **THEN** a página mostra os atalhos para a gestão de usuários e para a gestão de perfis

#### Scenario: Elemento escondido não substitui a verificação no servidor
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `USUARIO.CRIAR`, e que não vê o botão de cadastro
- **WHEN** ele acessa diretamente a URL de cadastro
- **THEN** a requisição é recusada com 403

### Requirement: Consistência da autorização após mudanças
Alterações no perfil do usuário, nas permissões concedidas ao seu perfil ou no seu `is_superadmin` DEVEM (MUST) valer para as decisões de acesso a partir da requisição seguinte, sem exigir logout ou novo login, conforme o design. A desativação DEVE (MUST) retirar o acesso a partir da requisição seguinte. Após a reativação, o acesso DEVE (MUST) voltar conforme o perfil e as permissões que o perfil concede nesse momento, desde que o usuário consiga se autenticar novamente conforme a spec `autenticacao`. Nenhuma decisão de acesso DEVE (MUST) usar permissões guardadas de requisições anteriores, o que não impede reaproveitar, dentro da mesma requisição, um resultado já calculado nela. As operações que fazem essas alterações e as suas restrições seguem as specs `gestao-usuarios`, `gestao-perfis` e `autenticacao` e os comandos de gerenciamento definidos no design.

#### Scenario: Acesso perdido após desativação
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR` e uma sessão aberta
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** ele é desativado e, em seguida, acessa a lista de usuários com a mesma sessão
- **THEN** a lista não é exibida e ele é tratado como visitante não autenticado

#### Scenario: Acesso restaurado após reativação
- **GIVEN** um usuário desativado, sem superadmin, com o perfil `ADMINISTRADOR` e senha definida
- **WHEN** ele é reativado, se autentica e acessa a lista de usuários
- **THEN** o acesso é concedido conforme as permissões do seu perfil

#### Scenario: Troca de perfil retira permissões do perfil anterior
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR` e uma sessão aberta
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** o perfil dele é trocado para `DOCENTE` e, em seguida, ele acessa a lista de usuários com a mesma sessão
- **THEN** a requisição é recusada com 403

#### Scenario: Troca de perfil concede permissões do novo perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE` e uma sessão aberta
- **WHEN** o perfil dele é trocado para `ADMINISTRADOR` e, em seguida, ele acessa a lista de usuários com a mesma sessão
- **THEN** o acesso é concedido

#### Scenario: Permissão retirada do perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`, e uma sessão aberta
- **WHEN** o superadmin retira `USUARIO.VISUALIZAR` de `COORDENACAO` e, em seguida, o usuário acessa a lista de usuários com a mesma sessão
- **THEN** a requisição é recusada com 403

#### Scenario: Permissão acrescentada ao perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `COORDENACAO`, que não concede `USUARIO.VISUALIZAR`, e uma sessão aberta
- **WHEN** o superadmin concede `USUARIO.VISUALIZAR` a `COORDENACAO` e, em seguida, o usuário acessa a lista de usuários com a mesma sessão
- **THEN** o acesso é concedido

#### Scenario: Alteração de permissões afeta todos os usuários do perfil
- **GIVEN** dois usuários ativos, sem superadmin, com o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`
- **WHEN** o superadmin retira `USUARIO.VISUALIZAR` de `COORDENACAO`
- **THEN** nenhum dos dois possui mais `USUARIO.VISUALIZAR` na avaliação seguinte

#### Scenario: Superadmin concedido por comando
- **GIVEN** um usuário ativo autenticado com o perfil `DOCENTE`, sem superadmin, e uma sessão aberta
- **WHEN** o comando de gerenciamento concede `is_superadmin` a ele e, em seguida, ele acessa a lista de usuários com a mesma sessão
- **THEN** o acesso é concedido

#### Scenario: Superadmin removido por comando
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True`, o perfil `DOCENTE` e uma sessão aberta
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** o comando de gerenciamento remove o `is_superadmin` dele e, em seguida, ele acessa a lista de usuários com a mesma sessão
- **THEN** a requisição é recusada com 403
