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
O cadastro DEVE (MUST) exigir nome, e-mail e exatamente um perfil, escolhido entre os perfis existentes no sistema, do sistema ou personalizados. Esta spec não define restrição sobre quais perfis o executor pode escolher em relação às suas próprias permissões: esse ponto (escalonamento de privilégio na atribuição de perfis) está pendente de decisão no design. O usuário cadastrado DEVE (MUST) ser gravado ativo, com `is_superadmin = False`, sem senha utilizável e vinculado ao perfil informado. O cadastro DEVE (MUST) aceitar só e-mails do domínio institucional `@ifnmg.edu.br`, sem diferenciar maiúsculas e minúsculas. Um cadastro que não seja concluído NÃO DEVE (MUST NOT) deixar gravado usuário sem perfil. O envio do link para o novo usuário definir a própria senha segue a spec `autenticacao`.

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

#### Scenario: E-mail fora do domínio institucional
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro com o e-mail `maria@gmail.com`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail deve terminar em `@ifnmg.edu.br`

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
Um usuário DEVE (MUST) ser considerado com capacidade administrativa se, e somente se, tiver `is_active = True` e, além disso, tiver `is_superadmin = True` ou perfis que concedam todas as permissões do conjunto de capacidade administrativa definido no design. Nesta versão, esse conjunto são as permissões `USUARIO.VISUALIZAR`, `USUARIO.CRIAR`, `USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL` e `USUARIO.ALTERAR_SITUACAO`. Ele NÃO DEVE (MUST NOT) incluir `USUARIO.IMPORTAR` nem as permissões reservadas do recurso `PERFIL`. A capacidade pelo perfil DEVE (MUST) ser avaliada pelas permissões que o perfil concede no momento da avaliação, e não pelo código ou pelo nome do perfil. Um usuário inativo NÃO DEVE (MUST NOT) ter capacidade administrativa, inclusive quando for superadmin. NÃO DEVE (MUST NOT) existir exigência de haver sempre um superadmin ativo.

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

#### Scenario: Capacidade sem a permissão de importar
- **GIVEN** um usuário ativo, sem superadmin, com um perfil que concede as cinco permissões do conjunto, mas não `USUARIO.IMPORTAR`
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
O sistema DEVE (MUST) manter sempre pelo menos um usuário com capacidade administrativa. A desativação, a troca de perfil, a remoção de `is_superadmin`, a retirada de permissões do conjunto de capacidade administrativa de um perfil e a confirmação de uma importação de usuários DEVEM (MUST) ser recusadas quando deixariam o sistema sem nenhum usuário nessa condição, qualquer que seja a origem da operação (interface, comando de gerenciamento ou chamada direta à operação) e inclusive quando o executor for superadmin. As regras específicas da retirada de permissões de um perfil seguem a spec `gestao-perfis`. Na importação de usuários, a continuidade DEVE (MUST) ser verificada uma única vez, depois de aplicadas todas as linhas, e o estado intermediário entre as linhas NÃO DEVE (MUST NOT) ser considerado. A falha dessa verificação DEVE (MUST) ser um erro do arquivo, e não de uma linha, e DEVE (MUST) aparecer já na prévia. Uma operação recusada NÃO DEVE (MUST NOT) alterar nenhum dado e DEVE (MUST) informar o motivo ao executor. Operações concorrentes NÃO DEVEM (MUST NOT) conseguir, juntas, deixar o sistema sem usuário com capacidade administrativa. Um usuário DEVE (MUST) poder desativar a si mesmo somente quando outro usuário mantiver a capacidade administrativa.

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

#### Scenario: Importação que rebaixa e promove
- **GIVEN** que o único usuário com capacidade administrativa, sem superadmin, tem o perfil `ADMINISTRADOR`
- **AND** um arquivo cuja linha 3 troca o perfil dele para `DOCENTE` e cuja linha 7 troca o perfil de outro usuário ativo para `ADMINISTRADOR`
- **WHEN** a prévia é gerada e a importação é confirmada
- **THEN** a importação é concluída e o segundo usuário passa a ter capacidade administrativa

#### Scenario: Importação que deixaria o sistema sem administrador
- **GIVEN** que o único usuário com capacidade administrativa, sem superadmin, tem o perfil `ADMINISTRADOR`
- **AND** um arquivo que troca o perfil dele para `DOCENTE` sem promover outro usuário
- **WHEN** a prévia é gerada
- **THEN** a importação fica `COM_ERROS`, com o erro no arquivo, e nenhum perfil muda

#### Scenario: Desativações simultâneas
- **GIVEN** exatamente dois usuários ativos com capacidade administrativa
- **WHEN** cada um deles tenta desativar o outro ao mesmo tempo
- **THEN** no máximo uma das desativações é concluída
- **AND** pelo menos um usuário ativo continua com capacidade administrativa

#### Scenario: Continuidade preservada após uma sequência de operações
- **GIVEN** um sistema com pelo menos um usuário ativo com capacidade administrativa
- **WHEN** qualquer sequência de desativações, reativações, trocas de perfil, remoções de superadmin, alterações de permissões de perfis, exclusões de perfis e importações de usuários é aplicada pelas operações do sistema
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

### Requirement: Busca e filtro na lista de usuários
A lista de usuários DEVE (MUST) aceitar uma busca por trecho do nome ou do e-mail, sem diferenciar maiúsculas de minúsculas, e um filtro por situação com as opções todas, ativos e inativos. Busca e filtro DEVEM (MUST) valer juntos e ser recebidos como parâmetros da URL da lista (`busca` e `situacao`), de modo que o mesmo endereço reproduza o mesmo resultado. Um valor de `situacao` fora das opções DEVE (MUST) ser tratado como todas. A lista DEVE (MUST) manter a ordem por nome e ser paginada conforme a spec `interface`, com a página combinada à busca e ao filtro. Mudar a busca ou o filtro DEVE (MUST) voltar para a primeira página. O título do cartão DEVE (MUST) informar quantos usuários existem no total, e o rodapé DEVE (MUST) informar o intervalo exibido dentro do resultado da busca. Quando nenhum usuário atender à busca, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar a busca. A busca, o filtro e a paginação NÃO DEVEM (MUST NOT) alterar dados nem mudar quem pode acessar a lista.

#### Scenario: Busca por trecho do nome
- **GIVEN** os usuários "Ana Souza", "Bruno Lima" e "Carla Mendes"
- **WHEN** a lista é acessada com `busca=SOU`
- **THEN** só "Ana Souza" é exibida, o título informa 3 usuários e o rodapé informa "Exibindo 1 a 1 de 1 usuário"

#### Scenario: Busca por trecho do e-mail
- **GIVEN** o usuário "Bruno Lima" com o e-mail `bruno.lima@ifnmg.edu.br`
- **WHEN** a lista é acessada com `busca=bruno.lima`
- **THEN** "Bruno Lima" é exibido

#### Scenario: Filtro por situação
- **GIVEN** dois usuários ativos e um inativo
- **WHEN** a lista é acessada com `situacao=inativos`
- **THEN** só o usuário inativo é exibido

#### Scenario: Busca e filtro combinados
- **GIVEN** "Ana Souza" ativa e "Ana Clara" inativa
- **WHEN** a lista é acessada com `busca=ana&situacao=ativos`
- **THEN** só "Ana Souza" é exibida

#### Scenario: Situação inválida
- **WHEN** a lista é acessada com `situacao=qualquer`
- **THEN** todos os usuários são exibidos

#### Scenario: Busca sem resultado
- **WHEN** a lista é acessada com uma busca que não corresponde a nenhum usuário
- **THEN** a lista mostra "Nenhum usuário encontrado para a busca." e um link "Limpar busca" para a lista sem parâmetros

#### Scenario: Busca paginada
- **GIVEN** 11 usuários com "Silva" no nome
- **WHEN** a lista é acessada com `busca=silva&pagina=2`
- **THEN** são exibidos os usuários 6 a 10 do resultado e o link "Próxima" leva a `?busca=silva&pagina=3`

#### Scenario: Atualização pelo htmx
- **WHEN** a lista recebe um GET com `busca=ana` e o cabeçalho `HX-Request` vindo do formulário de filtros ou da navegação entre páginas
- **THEN** a resposta contém só o fragmento da tabela e do rodapé com o resultado filtrado

#### Scenario: Busca sem a permissão
- **GIVEN** um usuário ativo autenticado sem a permissão de visualizar usuários
- **WHEN** ele acessa a lista com `busca=ana`
- **THEN** a requisição é recusada com 403

### Requirement: Importação de usuários por planilha
Um usuário ativo autenticado com a permissão `USUARIO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder cadastrar e atualizar usuários em lote por meio de um arquivo CSV, conforme a spec `importacao-planilhas`, com o tipo `USUARIO`. O arquivo DEVE (MUST) ter as colunas obrigatórias `E-mail`, `Nome` e `Perfil`. O e-mail DEVE (MUST) ser a coluna identificadora, normalizado como no cadastro (sem espaços nas bordas e em minúsculas). O perfil DEVE (MUST) ser informado pelo código, sem espaços nas bordas e convertido para maiúsculas, e resolvido entre os perfis existentes. Um código sem perfil correspondente DEVE (MUST) ser um erro na coluna `Perfil`, e a importação NÃO DEVE (MUST NOT) criar perfis. Para cada linha, a importação DEVE (MUST) decidir:
- `create`, quando não existe usuário com o e-mail, cadastrando-o pela mesma operação do cadastro, com o nome e o perfil da linha;
- `update`, quando o usuário existe e o nome ou o perfil são diferentes, alterando só o que difere, pelas mesmas operações da edição e da troca de perfil, sem exigir o domínio institucional do e-mail de um usuário já existente;
- `unchanged`, quando o usuário existe e nada difere, sem executar nenhuma operação.

A importação NÃO DEVE (MUST NOT) alterar o e-mail, a senha, a situação nem `is_superadmin` de nenhum usuário, e nenhuma coluna do arquivo DEVE (MUST) definir esses dados. Um superadmin DEVE (MUST) ser tratado como qualquer outro usuário. Um usuário inativo presente no arquivo DEVE (MUST) ser atualizado normalmente, continuar inativo e receber o aviso de usuário inativo na prévia.

#### Scenario: Cadastro de usuário novo
- **GIVEN** que não existe usuário com o e-mail `ana@ifnmg.edu.br`
- **AND** um arquivo com a linha `ana@ifnmg.edu.br;Ana Souza;DOCENTE`
- **WHEN** a importação é confirmada
- **THEN** a usuária é cadastrada, ativa, sem senha utilizável e com exatamente o perfil `DOCENTE`

#### Scenario: Troca de perfil pela importação
- **GIVEN** o usuário `bruno@ifnmg.edu.br`, com o nome "Bruno Lima" e o perfil `DOCENTE`
- **AND** um arquivo com a linha `bruno@ifnmg.edu.br;Bruno Lima;ADMINISTRADOR`
- **WHEN** a prévia é gerada
- **THEN** a linha tem a ação `update` com a mudança de perfil de `DOCENTE` para `ADMINISTRADOR` e nenhuma mudança de nome

#### Scenario: Linha sem alteração
- **GIVEN** o usuário `carla@ifnmg.edu.br`, com o nome "Carla Mendes" e o perfil `DOCENTE`
- **WHEN** a prévia de um arquivo com a linha ` Carla@IFNMG.edu.br ;Carla Mendes;docente` é gerada
- **THEN** a linha tem a ação `unchanged`

#### Scenario: Perfil inexistente
- **WHEN** a prévia de um arquivo com a linha `davi@ifnmg.edu.br;Davi Rocha;COORDENACAO` é gerada, sem existir o perfil `COORDENACAO`
- **THEN** a linha recebe erro na coluna `Perfil` e a importação fica `COM_ERROS`

#### Scenario: E-mail inválido
- **WHEN** a prévia de um arquivo com a linha `davi-ifnmg;Davi Rocha;DOCENTE` é gerada
- **THEN** a linha recebe erro na coluna `E-mail`, com a mesma mensagem do cadastro pela tela

#### Scenario: E-mail fora do domínio institucional na importação
- **GIVEN** que não existe usuário com o e-mail `davi@gmail.com`
- **WHEN** a prévia de um arquivo com a linha `davi@gmail.com;Davi Rocha;DOCENTE` é gerada
- **THEN** a linha recebe erro na coluna `E-mail`, com a mesma mensagem do cadastro pela tela, e ninguém é cadastrado

#### Scenario: Usuário inativo
- **GIVEN** o usuário inativo `eva@ifnmg.edu.br`, com o perfil `DOCENTE`
- **AND** um arquivo que troca o perfil dele para `ADMINISTRADOR`
- **WHEN** a importação é confirmada
- **THEN** o perfil passa a `ADMINISTRADOR`, o usuário continua inativo e a prévia mostrou o aviso de usuário inativo

#### Scenario: Superadmin no arquivo
- **GIVEN** um superadmin com o perfil `ADMINISTRADOR`
- **AND** um arquivo que altera o nome dele e troca o perfil para `DOCENTE`
- **WHEN** a importação é confirmada por quem tem as permissões dessas ações
- **THEN** o nome e o perfil mudam e ele continua com `is_superadmin = True`

### Requirement: Permissões das ações da importação de usuários
O acesso ao envio, à prévia, à confirmação, ao descarte, ao histórico, ao detalhe e ao modelo da importação de usuários DEVE (MUST) exigir `USUARIO.IMPORTAR`. Além disso, cada ação de linha DEVE (MUST) exigir do executor a permissão da operação equivalente: `create` exige `USUARIO.CRIAR`, mudança de nome exige `USUARIO.EDITAR` e mudança de perfil exige `USUARIO.ALTERAR_PERFIL`. Uma linha `unchanged` NÃO DEVE (MUST NOT) exigir permissão além de `USUARIO.IMPORTAR`. A falta de uma permissão DEVE (MUST) ser um erro da linha no plano. O plano DEVE (MUST) ser calculado com as permissões de quem gera a prévia e, na confirmação, com as de quem confirma. Qualquer usuário com `USUARIO.IMPORTAR` DEVE (MUST) poder confirmar ou descartar uma importação de usuários, qualquer que seja quem a enviou.

#### Scenario: Cadastro sem a permissão de cadastrar
- **GIVEN** um usuário com `USUARIO.IMPORTAR`, mas sem `USUARIO.CRIAR`
- **WHEN** ele gera a prévia de um arquivo com um e-mail novo
- **THEN** a linha recebe erro de permissão e a importação fica `COM_ERROS`

#### Scenario: Linha sem alteração sem outras permissões
- **GIVEN** um usuário com somente `USUARIO.IMPORTAR`
- **WHEN** ele gera a prévia de um arquivo em que todas as linhas são `unchanged`
- **THEN** a importação fica `VALIDADA`

#### Scenario: Confirmação por quem tem menos permissões
- **GIVEN** uma importação `VALIDADA`, gerada por quem tem todas as permissões de gestão de usuários, que troca o perfil de um usuário
- **AND** um segundo usuário com `USUARIO.IMPORTAR`, mas sem `USUARIO.ALTERAR_PERFIL`
- **WHEN** o segundo usuário confirma a importação
- **THEN** nada é aplicado e a importação fica `COM_ERROS`, com o erro de permissão na linha

#### Scenario: Confirmação por outro administrador
- **GIVEN** uma importação `VALIDADA` enviada por um administrador
- **WHEN** outro usuário com as mesmas permissões a confirma sem mudança nos dados
- **THEN** a importação é aplicada e registra quem enviou e quem confirmou

#### Scenario: Acesso sem a permissão de importar
- **GIVEN** um usuário ativo autenticado com todas as permissões de gestão de usuários, exceto `USUARIO.IMPORTAR`
- **WHEN** ele acessa o envio ou o histórico da importação de usuários
- **THEN** o acesso é recusado com 403

#### Scenario: Visitante não autenticado na importação
- **WHEN** um visitante não autenticado acessa qualquer rota da importação de usuários
- **THEN** ele é redirecionado para a página de login

### Requirement: Link de definição de senha dos usuários importados
Na confirmação de uma importação de usuários, DEVE (MUST) ser registrado no outbox, na mesma transação, o envio do link de definição de senha para cada usuário cadastrado pela importação. Usuários atualizados ou sem alteração NÃO DEVEM (MUST NOT) gerar registro no outbox. A prévia NÃO DEVE (MUST NOT) gerar registro no outbox. Depois da confirmação, a mensagem exibida DEVE (MUST) informar que o link será enviado aos usuários cadastrados.

#### Scenario: Envio registrado só para os cadastrados
- **GIVEN** uma importação `VALIDADA` com dois cadastros, uma atualização e uma linha sem alteração
- **WHEN** ela é confirmada
- **THEN** o outbox recebe exatamente dois registros de envio do link, um para cada usuário cadastrado

#### Scenario: Confirmação recusada sem envio
- **GIVEN** uma importação `VALIDADA` com um cadastro, cujo plano diverge na confirmação
- **WHEN** ela é confirmada
- **THEN** nenhum registro é criado no outbox

### Requirement: Equivalência entre a importação e as telas de usuários
A importação de usuários DEVE (MUST) usar as mesmas operações do model que o cadastro, a edição e a troca de perfil pela tela. Ela NÃO DEVE (MUST NOT) permitir uma alteração que a tela recusaria nem recusar uma alteração que a tela aceitaria para o mesmo executor, salvo a verificação da continuidade administrativa, que na importação é feita no fim. As recusas das regras de negócio DEVEM (MUST) aparecer na prévia com as mesmas mensagens das telas. A restrição sobre quais perfis o executor pode atribuir, pendente de decisão no design, DEVE (MUST) valer também para a importação quando for definida, sem regra própria da importação.

#### Scenario: E-mail duplicado ignorando maiúsculas
- **GIVEN** que a tela recusa o cadastro de `ANA@ifnmg.edu.br` quando já existe `ana@ifnmg.edu.br`
- **WHEN** um arquivo traz `ANA@ifnmg.edu.br`
- **THEN** a linha é tratada como o usuário existente `ana@ifnmg.edu.br`, e não como um cadastro novo

#### Scenario: Nome acima do tamanho
- **WHEN** um arquivo traz um nome com mais caracteres que o permitido no cadastro
- **THEN** a linha recebe erro na coluna `Nome` com a mesma mensagem da tela

