## ADDED Requirements

### Requirement: Importação de usuários por planilha
Um usuário ativo autenticado com a permissão `USUARIO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder cadastrar e atualizar usuários em lote por meio de um arquivo CSV, conforme a spec `importacao-planilhas`, com o tipo `USUARIO`. O arquivo DEVE (MUST) ter as colunas obrigatórias `E-mail`, `Nome` e `Perfil`. O e-mail DEVE (MUST) ser a coluna identificadora, normalizado como no cadastro (sem espaços nas bordas e em minúsculas). O perfil DEVE (MUST) ser informado pelo código, sem espaços nas bordas e convertido para maiúsculas, e resolvido entre os perfis existentes. Um código sem perfil correspondente DEVE (MUST) ser um erro na coluna `Perfil`, e a importação NÃO DEVE (MUST NOT) criar perfis. Para cada linha, a importação DEVE (MUST) decidir:
- `create`, quando não existe usuário com o e-mail, cadastrando-o pela mesma operação do cadastro, com o nome e o perfil da linha;
- `update`, quando o usuário existe e o nome ou o perfil são diferentes, alterando só o que difere, pelas mesmas operações da edição e da troca de perfil;
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

## MODIFIED Requirements

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
