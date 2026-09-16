## ADDED Requirements

### Requirement: Autorização das operações de gestão de perfis
Listar e consultar, criar, editar nome e descrição, alterar as permissões e excluir perfis DEVEM (MUST) ser operações distintas, cada uma protegida pela permissão correspondente do recurso `PERFIL`, conforme a spec `controle-acesso`, e verificada pelo mesmo ponto único de decisão de acesso das demais funcionalidades. Como as permissões `PERFIL.*` são reservadas e não podem ser concedidas a perfis, somente um usuário ativo autenticado com `is_superadmin = True` DEVE (MUST) conseguir executar essas operações, qualquer que seja o seu perfil. Um usuário que não é superadmin ativo DEVE (MUST) ter o acesso negado, mesmo que o seu perfil conceda todas as permissões do recurso `USUARIO`, e a negação NÃO DEVE (MUST NOT) alterar nenhum dado. A decisão de acesso NÃO DEVE (MUST NOT) consultar `is_superadmin` fora do ponto único de decisão de acesso nem comparar o código, o nome ou a marca de perfil do sistema.

Convenções dos cenários desta spec:
- `COORDENACAO` ("Coordenação") é um exemplo de perfil personalizado. Ele não é criado pela carga do sistema.
- Quando um cenário cita as permissões de `ADMINISTRADOR` ou `DOCENTE` sem descrevê-las, refere-se à configuração da carga inicial definida na spec `controle-acesso`.

#### Scenario: Superadmin acessa a gestão de perfis
- **GIVEN** um usuário ativo autenticado com `is_superadmin = True` e o perfil `DOCENTE`
- **WHEN** ele acessa a lista de perfis, a consulta de um perfil, a criação, a edição, a alteração de permissões e a exclusão
- **THEN** o acesso é concedido em todas elas

#### Scenario: Administrador comum sem acesso à gestão de perfis
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede todas as permissões do recurso `USUARIO`
- **WHEN** ele acessa a lista de perfis ou envia uma requisição POST, com token CSRF válido, para criar um perfil
- **THEN** a requisição é recusada com 403 e nenhum perfil é criado

#### Scenario: Usuário comum tenta alterar as permissões de um perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para conceder `USUARIO.CRIAR` ao perfil `DOCENTE`
- **THEN** a requisição é recusada com 403
- **AND** as permissões do perfil `DOCENTE` não mudam

#### Scenario: Usuário comum tenta excluir um perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR`
- **AND** o perfil personalizado `COORDENACAO` sem usuários vinculados
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para excluir `COORDENACAO`
- **THEN** a requisição é recusada com 403 e o perfil continua existindo

#### Scenario: Negação antes das regras de negócio de perfil
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `ADMINISTRADOR`
- **WHEN** ele envia uma requisição POST, com token CSRF válido, para excluir o perfil do sistema `DOCENTE`
- **THEN** a resposta é 403, e não a mensagem de erro de perfil do sistema

#### Scenario: Superadmin inativo
- **GIVEN** um usuário com `is_superadmin = True` e `is_active = False`
- **WHEN** ele tenta executar qualquer operação de gestão de perfis
- **THEN** a operação não é executada e nenhum dado é alterado

#### Scenario: Visitante não autenticado
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa qualquer rota de gestão de perfis
- **THEN** ele é redirecionado para a página de login e nenhum dado é alterado

### Requirement: Listagem e consulta de perfis
A listagem DEVE (MUST) apresentar todos os perfis existentes, do sistema e personalizados, com o código, o nome, a indicação de perfil do sistema e a quantidade de usuários vinculados, contando usuários ativos e inativos. A consulta de um perfil DEVE (MUST) apresentar também a descrição e as permissões que ele concede. A listagem e a consulta NÃO DEVEM (MUST NOT) alterar nenhum dado.

#### Scenario: Lista com perfis do sistema e personalizados
- **GIVEN** os perfis do sistema `ADMINISTRADOR` e `DOCENTE` e o perfil personalizado `COORDENACAO`
- **WHEN** o superadmin ativo abre a lista de perfis
- **THEN** os três perfis são exibidos
- **AND** `ADMINISTRADOR` e `DOCENTE` aparecem indicados como perfis do sistema e `COORDENACAO` não

#### Scenario: Quantidade de usuários vinculados
- **GIVEN** o perfil `COORDENACAO` vinculado a um usuário ativo e a um usuário inativo
- **WHEN** o superadmin ativo abre a lista de perfis
- **THEN** a quantidade de usuários vinculados exibida para `COORDENACAO` é 2

#### Scenario: Consulta das permissões de um perfil
- **GIVEN** o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`
- **WHEN** o superadmin ativo consulta esse perfil
- **THEN** são exibidos o código, o nome, a descrição e exatamente as permissões `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`

### Requirement: Criação de perfil personalizado
A criação DEVE (MUST) exigir código e nome, e PODE (MAY) receber descrição e um conjunto de permissões existentes no catálogo. O código DEVE (MUST) seguir o formato de código de perfil definido no design (letras maiúsculas sem acento, com palavras separadas por `_`) e ser único. O nome DEVE (MUST) ser único sem diferenciar maiúsculas de minúsculas. Todo perfil criado pela interface DEVE (MUST) ser personalizado, isto é, não ser marcado como perfil do sistema, mesmo que a requisição tente marcá-lo. A criação NÃO DEVE (MUST NOT) criar permissões novas. Uma criação recusada NÃO DEVE (MUST NOT) deixar perfil nem concessões gravados.

#### Scenario: Criação válida sem permissões
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele cria um perfil com o código `COORDENACAO`, o nome `Coordenação` e nenhuma permissão escolhida
- **THEN** o perfil é gravado como personalizado, com esse código e esse nome
- **AND** ele não concede nenhuma permissão

#### Scenario: Criação com permissões escolhidas
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele cria o perfil `COORDENACAO` escolhendo `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`
- **THEN** o perfil é gravado e concede exatamente `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`

#### Scenario: Código ausente
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele envia a criação de um perfil sem código
- **THEN** nenhum perfil é criado e o formulário indica que o código é obrigatório

#### Scenario: Código fora do formato
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele envia a criação de um perfil com o código `coordenacao` ou `COORD-1`
- **THEN** nenhum perfil é criado e o formulário indica que o código é inválido

#### Scenario: Código repetido
- **GIVEN** um perfil existente com o código `COORDENACAO`
- **WHEN** o superadmin ativo tenta criar outro perfil com o código `COORDENACAO`
- **THEN** nenhum perfil é criado e o formulário indica que o código já está em uso

#### Scenario: Nome ausente
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele envia a criação de um perfil sem nome
- **THEN** nenhum perfil é criado e o formulário indica que o nome é obrigatório

#### Scenario: Nome que difere só em maiúsculas e minúsculas
- **GIVEN** um perfil existente com o nome `Coordenação`
- **WHEN** o superadmin ativo tenta criar outro perfil com o nome `COORDENAÇÃO` e o código `COORDENACAO_GERAL`
- **THEN** nenhum perfil é criado e o formulário indica que o nome já está em uso

#### Scenario: Marca de perfil do sistema enviada na criação
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele envia uma criação válida acrescentando a marca de perfil do sistema aos dados da requisição
- **THEN** o perfil é criado como personalizado

#### Scenario: Gravação direta com nome repetido
- **GIVEN** um perfil existente com o nome `Coordenação`
- **WHEN** uma gravação que não passa pelo formulário tenta criar outro perfil com o nome `coordenação`
- **THEN** o banco de dados recusa a gravação

### Requirement: Código do perfil imutável
O código de um perfil DEVE (MUST) permanecer o mesmo depois da criação, para perfis personalizados e perfis do sistema. Nenhum formulário, rota ou operação da aplicação DEVE (MUST) permitir alterar o código, e um código enviado nos dados de uma requisição de edição DEVE (MUST) ser ignorado.

#### Scenario: Formulário de edição sem código editável
- **GIVEN** o superadmin ativo autenticado e o perfil `COORDENACAO`
- **WHEN** ele abre o formulário de edição desse perfil
- **THEN** o código é exibido sem possibilidade de edição

#### Scenario: Código enviado na edição
- **GIVEN** o perfil `COORDENACAO`
- **WHEN** o superadmin ativo envia a edição desse perfil com um nome válido e acrescenta o código `SECRETARIA` aos dados da requisição
- **THEN** o novo nome é gravado e o código continua `COORDENACAO`

#### Scenario: Código de perfil do sistema preservado
- **GIVEN** o perfil do sistema `ADMINISTRADOR`
- **WHEN** o superadmin ativo altera o nome dele para `Administração`
- **THEN** o nome é gravado e o código continua `ADMINISTRADOR`

### Requirement: Edição de nome e descrição do perfil
O superadmin ativo DEVE (MUST) poder alterar o nome e a descrição de qualquer perfil, do sistema ou personalizado, respeitando a obrigatoriedade e a unicidade do nome. A edição de nome e descrição NÃO DEVE (MUST NOT) alterar o código, a marca de perfil do sistema, as permissões concedidas nem os usuários vinculados, e NÃO DEVE (MUST NOT) alterar nenhuma decisão de acesso.

#### Scenario: Alteração de nome e descrição
- **GIVEN** o perfil `COORDENACAO` com o nome `Coordenação`
- **WHEN** o superadmin ativo altera o nome para `Coordenação de Curso` e a descrição
- **THEN** o novo nome e a nova descrição são gravados
- **AND** o código, as permissões e os usuários vinculados do perfil não mudam

#### Scenario: Nome apagado na edição
- **GIVEN** um perfil existente
- **WHEN** o superadmin ativo envia a edição com o nome vazio
- **THEN** a alteração é recusada e o nome anterior permanece

#### Scenario: Nome de outro perfil na edição
- **GIVEN** os perfis `COORDENACAO` ("Coordenação") e `DOCENTE` ("Docente")
- **WHEN** o superadmin ativo tenta alterar o nome de `COORDENACAO` para `docente`
- **THEN** a alteração é recusada e os dois nomes permanecem como estavam

#### Scenario: Marca de perfil do sistema enviada na edição
- **GIVEN** o perfil personalizado `COORDENACAO`
- **WHEN** o superadmin ativo envia a edição desse perfil acrescentando a marca de perfil do sistema aos dados da requisição
- **THEN** o perfil continua personalizado

### Requirement: Alteração das permissões do perfil
O superadmin ativo DEVE (MUST) poder definir quais permissões do catálogo um perfil concede, para perfis do sistema e personalizados, informando o conjunto final de permissões. Depois de uma alteração concluída, o perfil DEVE (MUST) conceder exatamente o conjunto informado. A alteração DEVE (MUST) usar somente permissões existentes no catálogo e NÃO DEVE (MUST NOT) criar, editar ou excluir permissões. Um conjunto vazio DEVE (MUST) ser aceito, sujeito à continuidade administrativa. Uma alteração recusada NÃO DEVE (MUST NOT) aplicar nenhuma parte do conjunto informado.

#### Scenario: Concessão e retirada no mesmo envio
- **GIVEN** o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR` e `USUARIO.EDITAR`
- **WHEN** o superadmin ativo define o conjunto `USUARIO.VISUALIZAR` e `USUARIO.CRIAR` para esse perfil
- **THEN** o perfil passa a conceder exatamente `USUARIO.VISUALIZAR` e `USUARIO.CRIAR`

#### Scenario: Permissões de perfil do sistema alteradas
- **GIVEN** o perfil do sistema `DOCENTE`, sem permissões
- **WHEN** o superadmin ativo concede `USUARIO.VISUALIZAR` a esse perfil
- **THEN** o perfil `DOCENTE` passa a conceder `USUARIO.VISUALIZAR`
- **AND** ele continua sendo perfil do sistema

#### Scenario: Retirada de todas as permissões
- **GIVEN** o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`, sem usuários vinculados
- **WHEN** o superadmin ativo define um conjunto vazio para esse perfil
- **THEN** o perfil passa a não conceder nenhuma permissão

#### Scenario: Permissão fora do catálogo
- **GIVEN** o perfil `COORDENACAO`
- **WHEN** o superadmin ativo envia a alteração de permissões incluindo um código que não existe no catálogo, como `RESERVA.APROVAR`
- **THEN** a alteração é recusada, nenhuma permissão é criada e as permissões do perfil não mudam

#### Scenario: Interface sem cadastro de permissões
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele procura na gestão de perfis uma forma de criar, editar ou excluir uma permissão do catálogo
- **THEN** não existe essa ação

### Requirement: Permissões reservadas não concedíveis
As permissões reservadas ao superadmin, definidas na spec `controle-acesso`, NÃO DEVEM (MUST NOT) ser concedidas a nenhum perfil, seja do sistema ou personalizado, por nenhuma operação da aplicação. O formulário de permissões de perfil NÃO DEVE (MUST NOT) oferecê-las. Uma criação ou alteração de permissões que as inclua DEVE (MUST) ser recusada por inteiro, sem gravar nenhuma parte do conjunto, e DEVE (MUST) informar o motivo, inclusive quando o executor for superadmin.

#### Scenario: Formulário sem permissões reservadas
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele abre o formulário de permissões de qualquer perfil
- **THEN** as permissões do recurso `PERFIL` não são oferecidas
- **AND** as permissões do recurso `USUARIO` são oferecidas

#### Scenario: Permissão reservada enviada na alteração
- **GIVEN** o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`
- **WHEN** o superadmin ativo envia a alteração de permissões desse perfil com `USUARIO.CRIAR` e `PERFIL.CRIAR`
- **THEN** a alteração é recusada com mensagem de erro
- **AND** o perfil continua concedendo somente `USUARIO.VISUALIZAR`

#### Scenario: Permissão reservada enviada na criação
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele envia a criação do perfil `COORDENACAO` com a permissão `PERFIL.ALTERAR_PERMISSOES`
- **THEN** nenhum perfil é criado e uma mensagem de erro informa o motivo

#### Scenario: Permissão reservada em perfil do sistema
- **GIVEN** o perfil do sistema `ADMINISTRADOR`
- **WHEN** o superadmin ativo tenta conceder `PERFIL.EXCLUIR` a esse perfil
- **THEN** a alteração é recusada e o `ADMINISTRADOR` não concede `PERFIL.EXCLUIR`

### Requirement: Perfis do sistema
Os perfis `ADMINISTRADOR` e `DOCENTE` DEVEM (MUST) ser perfis do sistema, criados pela carga inicial. Um perfil do sistema NÃO DEVE (MUST NOT) poder ser excluído, por nenhuma operação da aplicação e inclusive pelo superadmin, tenha ou não usuários vinculados. O nome, a descrição e as permissões de um perfil do sistema DEVEM (MUST) poder ser alterados pelo superadmin ativo, conforme os demais requisitos desta spec. Nenhuma operação da aplicação DEVE (MUST) marcar ou desmarcar um perfil como perfil do sistema.

#### Scenario: Perfis do sistema na instalação
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** os perfis existentes são consultados
- **THEN** existem os perfis `ADMINISTRADOR` e `DOCENTE`, ambos marcados como perfis do sistema

#### Scenario: Exclusão de perfil do sistema sem usuários
- **GIVEN** o perfil do sistema `DOCENTE` sem nenhum usuário vinculado
- **WHEN** o superadmin ativo tenta excluí-lo
- **THEN** a exclusão é recusada com mensagem de erro e o perfil `DOCENTE` continua existindo com as mesmas permissões

#### Scenario: Interface sem ação de marcar perfil do sistema
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele abre os formulários de criação, de edição e de permissões de perfil
- **THEN** nenhum deles contém campo ou ação para marcar ou desmarcar um perfil como perfil do sistema

### Requirement: Exclusão de perfil
O superadmin ativo DEVE (MUST) poder excluir um perfil personalizado que não tenha nenhum usuário vinculado. A exclusão DEVE (MUST) ser recusada quando o perfil for do sistema ou quando houver qualquer usuário vinculado a ele, ativo ou inativo, e a mensagem de recusa por usuários vinculados DEVE (MUST) informar quantos usuários estão vinculados. Uma exclusão recusada NÃO DEVE (MUST NOT) alterar o perfil, as suas permissões nem os vínculos. A exclusão concluída DEVE (MUST) remover o perfil e as concessões de permissões dele, sem remover nenhuma permissão do catálogo. O banco de dados DEVE (MUST) impedir a exclusão de um perfil vinculado a usuários mesmo quando a gravação não passar pela operação da aplicação. A exclusão NÃO DEVE (MUST NOT) trocar automaticamente o perfil dos usuários vinculados.

#### Scenario: Exclusão de perfil personalizado sem usuários
- **GIVEN** o perfil personalizado `COORDENACAO`, que concede `USUARIO.VISUALIZAR`, sem usuários vinculados
- **WHEN** o superadmin ativo o exclui
- **THEN** o perfil deixa de existir
- **AND** a permissão `USUARIO.VISUALIZAR` continua existindo no catálogo

#### Scenario: Exclusão com usuário ativo vinculado
- **GIVEN** o perfil personalizado `COORDENACAO` vinculado a um usuário ativo
- **WHEN** o superadmin ativo tenta excluí-lo
- **THEN** a exclusão é recusada com mensagem de erro que informa 1 usuário vinculado
- **AND** o perfil, as suas permissões e o vínculo permanecem

#### Scenario: Exclusão com usuário apenas inativo vinculado
- **GIVEN** o perfil personalizado `COORDENACAO` vinculado somente a um usuário com `is_active = False`
- **WHEN** o superadmin ativo tenta excluí-lo
- **THEN** a exclusão é recusada e o perfil e o vínculo permanecem
- **AND** o usuário inativo continua com o perfil `COORDENACAO`

#### Scenario: Exclusão depois de trocar o perfil dos usuários
- **GIVEN** o perfil personalizado `COORDENACAO` vinculado a um único usuário
- **AND** outro usuário ativo com capacidade administrativa
- **WHEN** o perfil desse usuário é trocado para `DOCENTE`, conforme a spec `gestao-usuarios`, e em seguida o superadmin ativo exclui `COORDENACAO`
- **THEN** a exclusão é concluída e o usuário continua com exatamente um perfil, `DOCENTE`

#### Scenario: Gravação direta excluindo perfil em uso
- **GIVEN** o perfil personalizado `COORDENACAO` vinculado a um usuário
- **WHEN** uma gravação que não passa pela operação da aplicação tenta apagar o perfil
- **THEN** o banco de dados recusa a exclusão e o vínculo permanece

### Requirement: Operações de alteração de perfil por POST com CSRF
A exclusão de perfil DEVE (MUST) ser executada somente por requisição POST, com token CSRF válido e após confirmação na interface. As requisições POST de criação, de edição de nome e descrição e de alteração de permissões de perfil DEVEM (MUST) exigir token CSRF válido. Uma requisição GET a qualquer rota de gestão de perfis NÃO DEVE (MUST NOT) alterar dados.

#### Scenario: GET na rota de exclusão
- **GIVEN** o superadmin ativo autenticado e o perfil personalizado `COORDENACAO` sem usuários
- **WHEN** ele acessa a rota de exclusão desse perfil por GET
- **THEN** o perfil continua existindo

#### Scenario: Exclusão sem token CSRF
- **GIVEN** o superadmin ativo autenticado e o perfil personalizado `COORDENACAO` sem usuários
- **WHEN** uma requisição POST de exclusão desse perfil é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e o perfil continua existindo

#### Scenario: Alteração de permissões sem token CSRF
- **GIVEN** o superadmin ativo autenticado e o perfil `COORDENACAO`, que não concede `USUARIO.CRIAR`
- **WHEN** uma requisição POST que concede `USUARIO.CRIAR` a esse perfil é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e o perfil continua sem `USUARIO.CRIAR`

#### Scenario: Criação sem token CSRF
- **GIVEN** o superadmin ativo autenticado
- **WHEN** uma requisição POST de criação de perfil com dados válidos é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e nenhum perfil é criado

### Requirement: Efeito das alterações de permissões nos usuários do perfil
Uma alteração concluída nas permissões de um perfil DEVE (MUST) valer para as decisões de acesso de todos os usuários vinculados a ele a partir da requisição seguinte de cada um, sem exigir logout ou novo login, conforme a spec `controle-acesso`. Usuários inativos vinculados ao perfil NÃO DEVEM (MUST NOT) ganhar acesso por causa da alteração. As decisões de acesso de um superadmin ativo vinculado ao perfil NÃO DEVEM (MUST NOT) mudar por causa da alteração.

#### Scenario: Permissão concedida vale na próxima requisição
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `COORDENACAO`, que não concede `USUARIO.VISUALIZAR`, e uma sessão aberta
- **WHEN** o superadmin ativo concede `USUARIO.VISUALIZAR` a `COORDENACAO` e, em seguida, esse usuário acessa a lista de usuários com a mesma sessão
- **THEN** o acesso é concedido

#### Scenario: Permissão retirada vale na próxima requisição
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`, e uma sessão aberta
- **WHEN** o superadmin ativo retira `USUARIO.VISUALIZAR` de `COORDENACAO` e, em seguida, esse usuário acessa a lista de usuários com a mesma sessão
- **THEN** a requisição é recusada com 403

#### Scenario: Alteração alcança todos os usuários do perfil
- **GIVEN** dois usuários ativos, sem superadmin, com o perfil `COORDENACAO`, que concede `USUARIO.VISUALIZAR`
- **WHEN** o superadmin ativo retira `USUARIO.VISUALIZAR` de `COORDENACAO`
- **THEN** nenhum dos dois possui `USUARIO.VISUALIZAR` na avaliação seguinte

#### Scenario: Usuário inativo do perfil não ganha acesso
- **GIVEN** um usuário com `is_active = False` e o perfil `COORDENACAO`
- **WHEN** o superadmin ativo concede `USUARIO.VISUALIZAR` a `COORDENACAO`
- **THEN** as permissões efetivas desse usuário continuam vazias

### Requirement: Continuidade administrativa na alteração de permissões de perfil
Uma alteração de permissões de perfil que retire uma ou mais permissões do conjunto de capacidade administrativa, definido na spec `gestao-usuarios`, DEVE (MUST) respeitar a regra de continuidade administrativa: ela DEVE (MUST) ser recusada quando deixaria o sistema sem nenhum usuário ativo com capacidade administrativa, qualquer que seja a origem da operação. Uma alteração recusada NÃO DEVE (MUST NOT) alterar nenhuma permissão do perfil e DEVE (MUST) informar o motivo. Acrescentar permissões, retirar permissões fora desse conjunto, criar perfil, editar nome ou descrição e excluir perfil NÃO DEVEM (MUST NOT) passar por essa verificação. O conjunto de capacidade administrativa NÃO DEVE (MUST NOT) incluir as permissões reservadas do recurso `PERFIL`, e NÃO DEVE (MUST NOT) existir exigência de haver sempre um superadmin ativo.

#### Scenario: Retirada permitida porque o superadmin ativo mantém a capacidade
- **GIVEN** o superadmin ativo autenticado
- **AND** um único outro usuário ativo com capacidade administrativa, que a tem pelo perfil `ADMINISTRADOR`
- **WHEN** o superadmin retira `USUARIO.EDITAR` do perfil `ADMINISTRADOR`
- **THEN** a alteração é concluída
- **AND** o outro usuário deixa de ter capacidade administrativa e o superadmin continua tendo

#### Scenario: Retirada recusada sem nenhum outro usuário com capacidade
- **GIVEN** que não existe superadmin ativo
- **AND** que o único usuário ativo com capacidade administrativa a tem pelo perfil `COORDENACAO`
- **WHEN** a operação de alteração de permissões é executada, por uma origem que não seja a interface, para retirar `USUARIO.ALTERAR_SITUACAO` de `COORDENACAO`
- **THEN** a alteração é recusada com o motivo informado
- **AND** `COORDENACAO` continua concedendo `USUARIO.ALTERAR_SITUACAO`

#### Scenario: Retirada permitida havendo outro usuário com capacidade pelo perfil
- **GIVEN** que não existe superadmin ativo
- **AND** um usuário ativo com capacidade administrativa pelo perfil `COORDENACAO` e outro pelo perfil `ADMINISTRADOR`
- **WHEN** a operação de alteração de permissões retira `USUARIO.EDITAR` de `COORDENACAO`
- **THEN** a alteração é concluída

#### Scenario: Acréscimo de permissão não é verificado
- **GIVEN** um perfil qualquer
- **WHEN** o superadmin ativo acrescenta permissões a esse perfil sem retirar nenhuma
- **THEN** a alteração é concluída sem verificação de continuidade administrativa

#### Scenario: Superadmin inativo não conta na alteração de permissões
- **GIVEN** um superadmin inativo, nenhum superadmin ativo e um único usuário ativo com capacidade administrativa pelo perfil `COORDENACAO`
- **WHEN** a operação de alteração de permissões retira `USUARIO.CRIAR` de `COORDENACAO`
- **THEN** a alteração é recusada e o perfil continua concedendo `USUARIO.CRIAR`

#### Scenario: Alteração de permissões concorrente com desativação
- **GIVEN** que não existe superadmin ativo
- **AND** exatamente dois usuários ativos com capacidade administrativa: um pelo perfil `ADMINISTRADOR` e outro pelo perfil `COORDENACAO`
- **WHEN** uma operação retira `USUARIO.EDITAR` de `COORDENACAO` ao mesmo tempo em que o usuário de `COORDENACAO` desativa o usuário de `ADMINISTRADOR`
- **THEN** no máximo uma das duas operações é concluída
- **AND** ao final, pelo menos um usuário ativo tem capacidade administrativa

### Requirement: Menor privilégio na gestão de perfis
Um perfil novo NÃO DEVE (MUST NOT) conceder nenhuma permissão além das escolhidas explicitamente na criação. Um perfil personalizado NÃO DEVE (MUST NOT) receber permissões automaticamente, inclusive quando novas permissões forem acrescentadas ao catálogo por Changes futuras: somente o superadmin as concede, pela alteração de permissões. A configuração padrão que migrations futuras podem conceder, conforme a spec `controle-acesso`, NÃO DEVE (MUST NOT) alcançar perfis personalizados.

#### Scenario: Perfil novo sem permissões implícitas
- **GIVEN** o superadmin ativo autenticado
- **WHEN** ele cria o perfil `COORDENACAO` sem escolher permissões
- **AND** um usuário ativo, sem superadmin, recebe esse perfil
- **THEN** as permissões efetivas desse usuário são vazias

#### Scenario: Permissão futura não chega ao perfil personalizado
- **GIVEN** um cenário conceitual em que uma Change futura acrescentou ao catálogo a permissão de exemplo `ESPACO.CRIAR` e a concedeu como configuração padrão ao perfil do sistema `ADMINISTRADOR`
- **AND** o perfil personalizado `COORDENACAO`, criado antes dessa Change
- **WHEN** as permissões de `COORDENACAO` são consultadas
- **THEN** `COORDENACAO` não concede `ESPACO.CRIAR`
