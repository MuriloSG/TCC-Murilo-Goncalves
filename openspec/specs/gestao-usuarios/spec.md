# gestao-usuarios Specification

## Purpose
TBD - created by archiving change gerenciar-usuarios-e-controle-de-acesso. Update Purpose after archive.
## Requirements
### Requirement: Autorização das operações de gestão de usuários
Listar e consultar, cadastrar, editar nome e e-mail, alterar o perfil e alterar a situação (desativar e reativar) de usuários DEVEM (MUST) ser operações distintas, cada uma liberada somente ao usuário ativo autenticado que tenha a permissão correspondente, conforme a spec `controle-acesso`. Um usuário ativo com `is_superadmin = True` DEVE (MUST) ter acesso a todas essas operações, independentemente das permissões concedidas pelo seu perfil. Uma requisição de quem não tem a permissão da operação nem é superadmin ativo NÃO DEVE (MUST NOT) alterar nenhum dado. Fora a proteção do e-mail de superadmin, a possibilidade de executar uma operação NÃO DEVE (MUST NOT) depender do perfil do usuário alvo nem de uma hierarquia entre perfis.

#### Scenario: Cadastro por usuário com permissão
- **GIVEN** um usuário ativo autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia um cadastro válido
- **THEN** o novo usuário é gravado

#### Scenario: Cadastro sem a permissão adequada
- **GIVEN** um usuário ativo autenticado sem a permissão de cadastrar usuários
- **WHEN** ele envia uma requisição POST de cadastro com dados válidos
- **THEN** a requisição é recusada com 403 e nenhum usuário é criado

#### Scenario: Superadmin ativo sem as permissões no perfil
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True` e o perfil `DOCENTE`, que, na configuração inicial, não concede permissões de gestão de usuários
- **WHEN** ele envia um cadastro válido
- **THEN** o novo usuário é gravado

#### Scenario: Superadmin inativo
- **GIVEN** um usuário com `is_superadmin = True` e `is_active = False`
- **WHEN** ele tenta executar qualquer operação de gestão de usuários
- **THEN** a operação não é executada e nenhum dado é alterado

#### Scenario: Desativação sem a permissão adequada
- **GIVEN** um usuário ativo autenticado que tem permissão para editar usuários, mas não para alterar a situação
- **WHEN** ele envia uma requisição POST para desativar outro usuário
- **THEN** a requisição é recusada com 403 e o usuário alvo continua ativo

#### Scenario: Troca de perfil sem a permissão adequada
- **GIVEN** um usuário ativo autenticado sem a permissão de alterar perfil
- **WHEN** ele envia uma requisição POST para trocar o perfil de outro usuário
- **THEN** a requisição é recusada com 403 e o perfil do usuário alvo não muda

#### Scenario: Visitante não autenticado
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa qualquer rota de gestão de usuários
- **THEN** ele é redirecionado para a página de login e nenhum dado é alterado

#### Scenario: Operação sobre usuário de qualquer perfil
- **GIVEN** um usuário ativo autenticado com a permissão de editar usuários
- **AND** dois usuários alvo, um com perfil `ADMINISTRADOR` e outro com perfil `DOCENTE`, nenhum deles superadmin
- **WHEN** ele altera o nome de cada um
- **THEN** as duas alterações são gravadas

### Requirement: Cadastro de usuário
O cadastro DEVE (MUST) exigir nome, e-mail e exatamente um perfil, escolhido entre os perfis existentes no sistema, do sistema ou personalizados. Esta spec não define restrição sobre quais perfis o executor pode escolher em relação às suas próprias permissões: esse ponto (escalonamento de privilégio na atribuição de perfis) está pendente de decisão no design. O usuário cadastrado DEVE (MUST) ser gravado ativo, com `is_superadmin = False`, sem senha utilizável e vinculado ao perfil informado. Um cadastro que não seja concluído NÃO DEVE (MUST NOT) deixar gravado usuário sem perfil. O envio do link para o novo usuário definir a própria senha segue a spec `autenticacao`.

#### Scenario: Cadastro válido
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra o nome `Maria Souza`, o e-mail `maria@ifnmg.edu.br` e o perfil `DOCENTE`
- **THEN** o usuário é gravado com esse nome e esse e-mail, com `is_active = True` e `is_superadmin = False`
- **AND** ele tem exatamente um perfil, `DOCENTE`
- **AND** ele não tem senha que permita autenticação

#### Scenario: Nome ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem nome
- **THEN** nenhum usuário é criado e o formulário indica que o nome é obrigatório

#### Scenario: E-mail ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem e-mail
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail é obrigatório

#### Scenario: E-mail em formato inválido
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro com o e-mail `maria.ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail é inválido

#### Scenario: Perfil ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem perfil
- **THEN** nenhum usuário é criado e o formulário indica que o perfil é obrigatório

#### Scenario: Mais de um perfil
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele tenta cadastrar um usuário com os perfis `ADMINISTRADOR` e `DOCENTE` ao mesmo tempo
- **THEN** nenhum usuário é criado

#### Scenario: Superadmin enviado no cadastro
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia um cadastro válido acrescentando `is_superadmin = true` aos dados da requisição
- **THEN** o usuário é criado com `is_superadmin = False`

### Requirement: Formulários de gestão sem senha
Os formulários de cadastro e de edição de usuário NÃO DEVEM (MUST NOT) conter campo para definir, alterar ou exibir a senha do usuário, e nenhuma tela de gestão DEVE (MUST) mostrar a senha ou o seu hash. Uma senha enviada nos dados dessas requisições NÃO DEVE (MUST NOT) ser gravada.

#### Scenario: Formulário de cadastro sem senha
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele abre o formulário de cadastro
- **THEN** o formulário não contém campo de senha

#### Scenario: Formulário de edição sem senha
- **GIVEN** um usuário autenticado com a permissão de editar usuários
- **WHEN** ele abre o formulário de edição de outro usuário
- **THEN** o formulário não contém campo de senha nem exibe a senha ou o hash do usuário

#### Scenario: Senha enviada na requisição de cadastro
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia um cadastro válido acrescentando um campo de senha aos dados da requisição
- **THEN** o usuário é criado sem senha utilizável

#### Scenario: Senha enviada na requisição de edição
- **GIVEN** um usuário com senha definida
- **AND** um usuário autenticado com a permissão de editar usuários
- **WHEN** este envia a edição do primeiro acrescentando uma nova senha aos dados da requisição
- **THEN** a senha do usuário editado não muda

### Requirement: Unicidade e normalização do e-mail
O e-mail de todo usuário DEVE (MUST) ser gravado normalizado, sem espaços nas pontas e em minúsculas. NÃO DEVE (MUST NOT) existir dois usuários com o mesmo e-mail, sem diferenciar maiúsculas de minúsculas, e a unicidade DEVE (MUST) ser garantida também pelo banco de dados. A regra vale para o cadastro, para a edição e para os comandos de gerenciamento, e um e-mail pertencente a um usuário inativo continua indisponível para outro usuário.

#### Scenario: E-mail gravado normalizado
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra um usuário com o e-mail ` Maria@IFNMG.edu.br `
- **THEN** o e-mail é gravado como `maria@ifnmg.edu.br`

#### Scenario: E-mail duplicado no cadastro
- **GIVEN** um usuário existente com o e-mail `maria@ifnmg.edu.br`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `maria@ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail já está em uso

#### Scenario: E-mail que difere só em maiúsculas e minúsculas
- **GIVEN** um usuário existente com o e-mail `maria@ifnmg.edu.br`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `MARIA@ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail já está em uso

#### Scenario: E-mail de outro usuário na edição
- **GIVEN** dois usuários com os e-mails `ana@ifnmg.edu.br` e `bruno@ifnmg.edu.br`
- **WHEN** alguém com a permissão de editar usuários tenta alterar o e-mail de Bruno para `Ana@ifnmg.edu.br`
- **THEN** a alteração é recusada e os dois e-mails permanecem como estavam

#### Scenario: E-mail de usuário inativo
- **GIVEN** um usuário com `is_active = False` e e-mail `antigo@ifnmg.edu.br`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `antigo@ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail já está em uso

#### Scenario: Gravação direta com e-mail duplicado
- **GIVEN** um usuário existente com o e-mail `maria@ifnmg.edu.br`
- **WHEN** uma gravação que não passa pelo formulário tenta criar outro usuário com `Maria@ifnmg.edu.br`
- **THEN** o banco de dados recusa a gravação

### Requirement: Edição dos dados do usuário
Um usuário com a permissão de editar usuários DEVE (MUST) poder alterar o nome e o e-mail de outro usuário, ativo ou inativo, respeitando a obrigatoriedade dos campos, a unicidade do e-mail e a proteção do e-mail de superadmin. A edição de nome e e-mail NÃO DEVE (MUST NOT) alterar o perfil, a situação, a senha nem `is_superadmin`. Depois da troca de e-mail, o login passa a aceitar só o novo endereço e os links de senha já emitidos deixam de valer, conforme a spec `autenticacao`.

#### Scenario: Alteração do nome
- **GIVEN** um usuário com o nome `Maria Sousa`
- **WHEN** alguém com a permissão de editar usuários altera o nome para `Maria Souza`
- **THEN** o nome `Maria Souza` é gravado
- **AND** o e-mail, o perfil, a situação e a senha do usuário não mudam

#### Scenario: Alteração do e-mail
- **GIVEN** um usuário que não é superadmin, com o e-mail `maria@ifnmg.edu.br`
- **WHEN** alguém com a permissão de editar usuários altera o e-mail para `Maria.Souza@ifnmg.edu.br`
- **THEN** o e-mail `maria.souza@ifnmg.edu.br` é gravado
- **AND** o usuário continua com o mesmo perfil, a mesma situação e a mesma senha

#### Scenario: Nome apagado na edição
- **GIVEN** um usuário existente
- **WHEN** alguém com a permissão de editar usuários envia a edição com o nome vazio
- **THEN** a alteração é recusada e o nome anterior permanece

#### Scenario: Edição de usuário inativo
- **GIVEN** um usuário com `is_active = False`
- **WHEN** alguém com a permissão de editar usuários altera o nome dele
- **THEN** o novo nome é gravado e o usuário continua inativo

#### Scenario: Superadmin enviado na edição
- **GIVEN** um usuário com `is_superadmin = False`
- **WHEN** alguém com a permissão de editar usuários envia a edição acrescentando `is_superadmin = true` aos dados da requisição
- **THEN** o usuário continua com `is_superadmin = False`

### Requirement: Perfil do usuário
Todo usuário DEVE (MUST) ter exatamente um perfil nesta versão. Ao final de cada operação concluída que crie o usuário ou troque o seu perfil, ele DEVE (MUST) ter exatamente um perfil, e uma operação recusada ou com falha NÃO DEVE (MUST NOT) deixá-lo sem perfil ou com mais de um. A troca de perfil DEVE (MUST) substituir o perfil atual pelo novo, escolhido entre os perfis existentes, e respeitar a regra de continuidade administrativa. Assim como no cadastro, a restrição sobre quais perfis o executor pode atribuir em relação às suas próprias permissões está pendente de decisão no design. O banco de dados DEVE (MUST) impedir mais de um perfil para o mesmo usuário, e um perfil vinculado a qualquer usuário, ativo ou inativo, NÃO DEVE (MUST NOT) poder ser excluído, conforme a spec `gestao-perfis`. A exclusão de um perfil NÃO DEVE (MUST NOT) deixar nenhum usuário sem perfil.

#### Scenario: Troca de perfil
- **GIVEN** um usuário com o perfil `DOCENTE`
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** alguém com a permissão de alterar perfil troca o perfil do primeiro para `ADMINISTRADOR`
- **THEN** o usuário passa a ter exatamente um perfil, `ADMINISTRADOR`

#### Scenario: Troca de perfil recusada
- **GIVEN** um usuário cuja troca de perfil é recusada, por exemplo pela regra de continuidade administrativa
- **WHEN** a operação termina
- **THEN** ele continua com exatamente um perfil, o mesmo de antes

#### Scenario: Segundo perfil recusado pelo banco
- **GIVEN** um usuário com o perfil `DOCENTE`
- **WHEN** uma gravação tenta vinculá-lo também ao perfil `ADMINISTRADOR`
- **THEN** a gravação é recusada e ele continua só com o perfil `DOCENTE`

#### Scenario: Perfil com usuários vinculados
- **GIVEN** um perfil personalizado vinculado a pelo menos um usuário inativo
- **WHEN** uma operação tenta excluir esse perfil
- **THEN** a exclusão é recusada e o perfil e os vínculos permanecem
- **AND** o usuário continua com exatamente um perfil

#### Scenario: Troca para perfil personalizado
- **GIVEN** um usuário com o perfil `DOCENTE`
- **AND** um perfil personalizado `COORDENACAO` criado pelo superadmin
- **WHEN** alguém com a permissão de alterar perfil troca o perfil do usuário para `COORDENACAO`
- **THEN** o usuário passa a ter exatamente um perfil, `COORDENACAO`

### Requirement: Desativação lógica
A desativação DEVE (MUST) apenas marcar `is_active = False`. O registro do usuário, o nome, o e-mail, o perfil, a senha, `is_superadmin` e as referências de histórico DEVEM (MUST) permanecer armazenados. O usuário desativado NÃO DEVE (MUST NOT) autenticar nem ter acesso efetivo a funcionalidades protegidas, conforme as specs `autenticacao` e `controle-acesso`. A desativação DEVE (MUST) respeitar a regra de continuidade administrativa. NÃO DEVE (MUST NOT) existir operação ou rota da aplicação que exclua fisicamente um usuário.

#### Scenario: Desativação de usuário
- **GIVEN** um usuário ativo com o perfil `DOCENTE`
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** alguém com a permissão de alterar a situação desativa o primeiro
- **THEN** o usuário passa a ter `is_active = False`

#### Scenario: Dados preservados após a desativação
- **GIVEN** um usuário ativo com nome, e-mail, perfil e senha definidos
- **WHEN** ele é desativado
- **THEN** o registro continua armazenado com o mesmo nome, o mesmo e-mail, o mesmo perfil, a mesma senha e o mesmo valor de `is_superadmin`

#### Scenario: Usuário desativado sem acesso efetivo
- **GIVEN** um usuário com a permissão de cadastrar usuários e uma sessão aberta
- **WHEN** ele é desativado e, em seguida, tenta abrir o formulário de cadastro com a mesma sessão
- **THEN** ele é tratado como visitante não autenticado e não acessa o formulário

#### Scenario: Ausência de exclusão física
- **GIVEN** um usuário autenticado com todas as permissões de gestão de usuários
- **WHEN** ele procura na interface uma forma de excluir um usuário ou tenta acessar uma rota de exclusão
- **THEN** não existe essa ação e nenhum registro de usuário é apagado

### Requirement: Reativação
A reativação DEVE (MUST) marcar `is_active = True` e restaurar o usuário com o perfil, a senha e `is_superadmin` que tinha antes da desativação. A reativação NÃO DEVE (MUST NOT) passar pela verificação de continuidade administrativa, porque não retira capacidade de ninguém. O usuário reativado só DEVE (MUST) conseguir autenticar se tiver senha definida. Quem nunca definiu a senha continua sem autenticar até defini-la pelo fluxo da spec `autenticacao`.

#### Scenario: Reativação de usuário
- **GIVEN** um usuário com `is_active = False`, o perfil `ADMINISTRADOR` e senha definida
- **WHEN** alguém com a permissão de alterar a situação o reativa
- **THEN** o usuário passa a ter `is_active = True`, com o mesmo perfil e a mesma senha de antes

#### Scenario: Reativação de superadmin
- **GIVEN** um usuário com `is_superadmin = True` e `is_active = False`
- **WHEN** alguém com a permissão de alterar a situação o reativa
- **THEN** ele passa a ter `is_active = True` e continua com `is_superadmin = True`
- **AND** ele volta a contar para a regra de continuidade administrativa

#### Scenario: Reativação de usuário que nunca definiu a senha
- **GIVEN** um usuário desativado antes de definir a própria senha
- **WHEN** ele é reativado e alguém tenta se autenticar com o e-mail dele e qualquer senha
- **THEN** a autenticação é recusada até que ele defina a senha pelo fluxo de recuperação

### Requirement: Ações de situação por POST com CSRF
As ações de desativar e de reativar DEVEM (MUST) ser executadas somente por requisição POST, com token CSRF válido e após confirmação na interface. As requisições POST de cadastro, edição e troca de perfil DEVEM (MUST) exigir token CSRF válido.

#### Scenario: GET na rota de desativação
- **GIVEN** um usuário autenticado com a permissão de alterar a situação e um usuário ativo alvo
- **WHEN** ele acessa a rota de desativação do alvo por GET
- **THEN** o alvo continua ativo

#### Scenario: Desativação sem token CSRF
- **GIVEN** um usuário autenticado com a permissão de alterar a situação e um usuário ativo alvo
- **WHEN** uma requisição POST de desativação do alvo é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e o alvo continua ativo

#### Scenario: Cadastro sem token CSRF
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** uma requisição POST de cadastro com dados válidos é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e nenhum usuário é criado

### Requirement: Capacidade administrativa
Um usuário DEVE (MUST) ser considerado com capacidade administrativa se, e somente se, tiver `is_active = True` e, além disso, tiver `is_superadmin = True` ou perfis que concedam todas as permissões do conjunto de capacidade administrativa definido no design. Nesta versão, esse conjunto são as cinco permissões do recurso `USUARIO` (`USUARIO.VISUALIZAR`, `USUARIO.CRIAR`, `USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL` e `USUARIO.ALTERAR_SITUACAO`), e ele NÃO DEVE (MUST NOT) incluir as permissões reservadas do recurso `PERFIL`. A capacidade pelo perfil DEVE (MUST) ser avaliada pelas permissões que o perfil concede no momento da avaliação, e não pelo código ou pelo nome do perfil. Um usuário inativo NÃO DEVE (MUST NOT) ter capacidade administrativa, inclusive quando for superadmin. NÃO DEVE (MUST NOT) existir exigência de haver sempre um superadmin ativo.

#### Scenario: Superadmin ativo
- **GIVEN** um usuário ativo com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele tem capacidade administrativa

#### Scenario: Administrador ativo pelo perfil
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `ADMINISTRADOR`, que concede todas as permissões do conjunto
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele tem capacidade administrativa

#### Scenario: Capacidade por perfil personalizado
- **GIVEN** um usuário ativo, sem superadmin, com o perfil personalizado `COORDENACAO`, que concede todas as permissões do conjunto
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele tem capacidade administrativa

#### Scenario: Usuário com perfil sem as permissões administrativas
- **GIVEN** um usuário ativo, sem superadmin, com um perfil que não concede todas as permissões do conjunto, como o perfil `DOCENTE` na configuração inicial
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele não tem capacidade administrativa

#### Scenario: Perfil ADMINISTRADOR sem uma permissão do conjunto
- **GIVEN** um usuário ativo, sem superadmin, com o perfil `ADMINISTRADOR`
- **AND** que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR`
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele não tem capacidade administrativa

#### Scenario: Superadmin inativo
- **GIVEN** um usuário com `is_superadmin = True`, o perfil `ADMINISTRADOR` e `is_active = False`
- **WHEN** a capacidade administrativa dele é avaliada
- **THEN** ele não tem capacidade administrativa

### Requirement: Continuidade administrativa
O sistema DEVE (MUST) manter sempre pelo menos um usuário com capacidade administrativa. A desativação, a troca de perfil, a remoção de `is_superadmin` e a retirada de permissões do conjunto de capacidade administrativa de um perfil DEVEM (MUST) ser recusadas quando deixariam o sistema sem nenhum usuário nessa condição, qualquer que seja a origem da operação (interface, comando de gerenciamento ou chamada direta à operação) e inclusive quando o executor for superadmin. As regras específicas da retirada de permissões de um perfil seguem a spec `gestao-perfis`. Uma operação recusada NÃO DEVE (MUST NOT) alterar nenhum dado e DEVE (MUST) informar o motivo ao executor. Operações concorrentes NÃO DEVEM (MUST NOT) conseguir, juntas, deixar o sistema sem usuário com capacidade administrativa. Um usuário DEVE (MUST) poder desativar a si mesmo somente quando outro usuário mantiver a capacidade administrativa.

#### Scenario: Desativação do último usuário com capacidade administrativa
- **GIVEN** que um único usuário ativo tem capacidade administrativa
- **WHEN** alguém com a permissão de alterar a situação tenta desativá-lo
- **THEN** a desativação é recusada, o usuário continua ativo e uma mensagem de erro informa o motivo

#### Scenario: Usuário tenta desativar a si mesmo sendo o último
- **GIVEN** um usuário autenticado que é o único com capacidade administrativa
- **WHEN** ele tenta desativar a própria conta
- **THEN** a desativação é recusada e ele continua ativo

#### Scenario: Usuário desativa a si mesmo havendo outro com capacidade
- **GIVEN** dois usuários ativos com capacidade administrativa
- **WHEN** um deles desativa a própria conta
- **THEN** a desativação é concluída e o outro continua com capacidade administrativa

#### Scenario: Desativação permitida havendo outro usuário com capacidade
- **GIVEN** dois usuários ativos com capacidade administrativa
- **WHEN** alguém com a permissão de alterar a situação desativa um deles
- **THEN** a desativação é concluída

#### Scenario: Troca de perfil do último administrador pelo perfil
- **GIVEN** que o único usuário com capacidade administrativa não é superadmin e a tem pelo perfil `ADMINISTRADOR`
- **WHEN** alguém tenta trocar o perfil dele para `DOCENTE`
- **THEN** a troca é recusada e ele continua com o perfil `ADMINISTRADOR`

#### Scenario: Troca de perfil de superadmin que é o único com capacidade
- **GIVEN** que o único usuário com capacidade administrativa é um superadmin ativo com o perfil `ADMINISTRADOR`
- **WHEN** alguém troca o perfil dele para `DOCENTE`
- **THEN** a troca é concluída, porque ele mantém a capacidade administrativa como superadmin

#### Scenario: Superadmin inativo não conta para a continuidade
- **GIVEN** um superadmin inativo e um único usuário ativo com capacidade administrativa
- **WHEN** alguém tenta desativar esse usuário ativo
- **THEN** a desativação é recusada e ele continua ativo

#### Scenario: Remoção de superadmin do último usuário com capacidade
- **GIVEN** que o único usuário com capacidade administrativa é um superadmin ativo com o perfil `DOCENTE`
- **WHEN** o comando de gerenciamento tenta remover o `is_superadmin` dele
- **THEN** o comando termina com erro e o usuário continua com `is_superadmin = True`

#### Scenario: Desativações simultâneas
- **GIVEN** exatamente dois usuários ativos com capacidade administrativa
- **WHEN** cada um deles tenta desativar o outro ao mesmo tempo
- **THEN** no máximo uma das desativações é concluída
- **AND** pelo menos um usuário ativo continua com capacidade administrativa

#### Scenario: Continuidade preservada após uma sequência de operações
- **GIVEN** um sistema com pelo menos um usuário ativo com capacidade administrativa
- **WHEN** qualquer sequência de desativações, reativações, trocas de perfil, remoções de superadmin, alterações de permissões de perfis e exclusões de perfis é aplicada pelas operações do sistema
- **THEN** ao final de cada operação concluída existe pelo menos um usuário ativo com capacidade administrativa

### Requirement: `is_superadmin` fora da interface de gestão
Nenhum formulário, rota ou ação da interface web DEVE (MUST) conceder, remover ou alterar `is_superadmin`, e os dados enviados com esse campo DEVEM (MUST) ser ignorados. Todo usuário cadastrado pela interface DEVE (MUST) ter `is_superadmin = False`. O status de superadmin DEVE (MUST) ser controlado somente pelos comandos de gerenciamento definidos no design.

#### Scenario: Interface sem controle de superadmin
- **GIVEN** um usuário autenticado com todas as permissões de gestão de usuários
- **WHEN** ele abre os formulários de cadastro, de edição e de troca de perfil
- **THEN** nenhum deles contém campo ou ação para alterar `is_superadmin`

#### Scenario: Tentativa de conceder superadmin pela requisição
- **GIVEN** um usuário com `is_superadmin = False`
- **WHEN** alguém com todas as permissões de gestão envia requisições de edição e de troca de perfil desse usuário com `is_superadmin = true`
- **THEN** o usuário continua com `is_superadmin = False`

#### Scenario: Tentativa de remover superadmin pela requisição
- **GIVEN** um usuário com `is_superadmin = True`
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** alguém com todas as permissões de gestão envia requisições de edição e de troca de perfil desse usuário com `is_superadmin = false`
- **THEN** o usuário continua com `is_superadmin = True`

### Requirement: Comandos de gerenciamento do superadmin
O primeiro superadmin DEVE (MUST) ser criado por comando de gerenciamento, sem depender da interface web, de cadastro público ou do envio de e-mail. O comando de criação DEVE (MUST) pedir e-mail, nome e senha, aplicar a política de senha, recusar e-mail já cadastrado e criar o usuário ativo, com `is_superadmin = True`, o perfil `ADMINISTRADOR` e senha utilizável. Um comando de alteração DEVE (MUST) conceder ou remover `is_superadmin` de um usuário existente, identificado pelo e-mail, e a remoção DEVE (MUST) respeitar a regra de continuidade administrativa.

#### Scenario: Criação do primeiro superadmin
- **GIVEN** uma instalação sem nenhum usuário
- **WHEN** o comando de criação é executado com e-mail, nome e uma senha válida
- **THEN** o usuário é criado ativo, com `is_superadmin = True`, o perfil `ADMINISTRADOR` e o e-mail normalizado
- **AND** ele consegue se autenticar com essa senha

#### Scenario: Criação com e-mail já cadastrado
- **GIVEN** um usuário existente com o e-mail `maria@ifnmg.edu.br`
- **WHEN** o comando de criação é executado com `Maria@ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o comando indica o uso do comando de alteração

#### Scenario: Criação com senha fraca
- **GIVEN** uma instalação sem nenhum usuário
- **WHEN** o comando de criação é executado com uma senha recusada pela política de senha
- **THEN** nenhum usuário é criado

#### Scenario: Concessão de superadmin por comando
- **GIVEN** um usuário ativo com `is_superadmin = False`
- **WHEN** o comando de alteração é executado para conceder superadmin a ele
- **THEN** o usuário passa a ter `is_superadmin = True`

#### Scenario: Remoção de superadmin por comando
- **GIVEN** um usuário com `is_superadmin = True`
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** o comando de alteração é executado para remover o superadmin dele
- **THEN** o usuário passa a ter `is_superadmin = False`

### Requirement: Proteção do superadmin contra tomada de conta
Somente um superadmin ativo DEVE (MUST) poder alterar o e-mail de um usuário com `is_superadmin = True`, esteja esse usuário ativo ou inativo. A recusa DEVE (MUST) valer em qualquer origem da operação, e não só na tela, e NÃO DEVE (MUST NOT) alterar nenhum dado. Na edição de um superadmin por quem não é superadmin ativo, o e-mail DEVE (MUST) aparecer sem possibilidade de edição. O nome, o perfil e a situação de um superadmin DEVEM (MUST) poder ser alterados por quem tem a permissão correspondente, respeitando a regra de continuidade administrativa. Nenhuma operação da aplicação DEVE (MUST) permitir controlar a senha de outro usuário nem remover `is_superadmin` pela interface.

#### Scenario: Administrador comum tenta alterar o e-mail de um superadmin
- **GIVEN** um superadmin ativo com o e-mail `super@ifnmg.edu.br`
- **AND** um usuário autenticado sem superadmin, com a permissão de editar usuários
- **WHEN** este envia a edição do superadmin com o e-mail `outro@ifnmg.edu.br`
- **THEN** a alteração é recusada com mensagem de erro e o e-mail continua `super@ifnmg.edu.br`

#### Scenario: Administrador comum tenta alterar o e-mail de um superadmin inativo
- **GIVEN** um usuário com `is_superadmin = True` e `is_active = False`
- **AND** um usuário autenticado sem superadmin, com a permissão de editar usuários
- **WHEN** este tenta alterar o e-mail do superadmin inativo
- **THEN** a alteração é recusada e o e-mail não muda

#### Scenario: E-mail de superadmin somente leitura para administrador comum
- **GIVEN** um superadmin e um usuário autenticado sem superadmin, com a permissão de editar usuários
- **WHEN** este abre o formulário de edição do superadmin
- **THEN** o e-mail é exibido sem possibilidade de edição

#### Scenario: Administrador comum altera o nome de um superadmin
- **GIVEN** um superadmin e um usuário autenticado sem superadmin, com a permissão de editar usuários
- **WHEN** este altera apenas o nome do superadmin
- **THEN** o novo nome é gravado e o e-mail não muda

#### Scenario: Superadmin ativo altera o e-mail de outro superadmin
- **GIVEN** dois usuários ativos com `is_superadmin = True`
- **AND** que um deles, autenticado, tem a permissão de editar usuários
- **WHEN** ele altera o e-mail do outro para `novo.super@ifnmg.edu.br`
- **THEN** o e-mail `novo.super@ifnmg.edu.br` é gravado

#### Scenario: Administrador comum desativa um superadmin
- **GIVEN** um superadmin ativo e outro usuário ativo com capacidade administrativa
- **AND** um usuário autenticado sem superadmin, com a permissão de alterar a situação
- **WHEN** este desativa o superadmin
- **THEN** a desativação é concluída e o superadmin mantém `is_superadmin = True`

#### Scenario: Nenhum controle da senha de um superadmin por outro usuário
- **GIVEN** um superadmin e um usuário autenticado com todas as permissões de gestão de usuários
- **WHEN** este procura na interface uma forma de definir, alterar ou redefinir a senha do superadmin
- **THEN** não existe essa operação e a senha do superadmin não muda

