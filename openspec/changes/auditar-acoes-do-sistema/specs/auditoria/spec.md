## ADDED Requirements

### Requirement: Registro centralizado das ações
Toda ação auditável DEVE (MUST) gerar um registro numa única tabela de auditoria do sistema, criada por migration. A gravação DEVE (MUST) acontecer por um único ponto da aplicação, e nenhuma funcionalidade DEVE (MUST) implementar a própria lógica de persistência de log nem tabela de log própria. O ponto único de gravação DEVE (MUST) completar o registro com o ator da ação, a data e a hora, e recusar uma ação ou um recurso que não estejam no catálogo de auditoria. Acrescentar um tipo de ação NÃO DEVE (MUST NOT) exigir estrutura de log específica, tabela nova nem alteração do esquema: DEVE (MUST) bastar acrescentar o código e o rótulo ao catálogo.

#### Scenario: Tabela única
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** a estrutura do banco é consultada
- **THEN** existe uma tabela de auditoria que recebe os registros de todos os módulos
- **AND** não existe tabela de log específica de usuários, de perfis, de importações ou de autenticação

#### Scenario: Ação fora do catálogo
- **WHEN** uma gravação de auditoria é tentada com um código de ação ou de recurso que não está no catálogo
- **THEN** a gravação é recusada e nenhum registro é criado

#### Scenario: Ação nova sem estrutura nova
- **GIVEN** o catálogo de auditoria com uma ação acrescentada
- **WHEN** essa ação é registrada
- **THEN** o registro é gravado na mesma tabela, sem migration de esquema

### Requirement: Conteúdo de cada registro
Cada registro de auditoria DEVE (MUST) conter identificador único, usuário responsável quando houver, ação realizada, recurso relacionado, identificador do recurso quando aplicável, valores anteriores e posteriores quando aplicáveis, informações adicionais da operação quando necessárias, origem da operação, endereço IP quando disponível, identificação do cliente quando disponível e data e hora da ação. A ação, o recurso e a origem DEVEM (MUST) ser gravados como códigos, e os rótulos correspondentes DEVEM (MUST) aparecer somente na interface. O identificador do recurso DEVE (MUST) aceitar identificadores que não sejam números. A data e a hora DEVEM (MUST) ser definidas pelo sistema no momento da gravação e NÃO DEVEM (MUST NOT) ser informadas por quem registra.

#### Scenario: Registro de uma alteração
- **GIVEN** a usuária Ana autenticada, com a permissão de editar usuários, no endereço IP `192.168.0.10`
- **WHEN** ela altera o nome do usuário de identificador 25
- **THEN** existe um registro com a ação `ALTERAR`, o recurso `USUARIO`, o identificador `25`, a usuária Ana como responsável, o endereço IP `192.168.0.10`, a identificação do cliente, a origem `INTERFACE` e a data e a hora da alteração

#### Scenario: Data e hora do próprio sistema
- **WHEN** uma ação é registrada
- **THEN** a data e a hora do registro são as do momento da gravação, no fuso configurado no projeto

### Requirement: Ator e origem da ação
O registro DEVE (MUST) identificar quem realizou a ação. Numa requisição de um usuário autenticado, o responsável DEVE (MUST) ser esse usuário, e a origem DEVE (MUST) ser a interface. Numa ação executada por processo automático, sem usuário associado, o registro NÃO DEVE (MUST NOT) ter usuário responsável e a origem DEVE (MUST) identificar o sistema. Nas ações executadas a partir das linhas de uma importação, o responsável DEVE (MUST) ser o usuário que confirmou a importação e a origem DEVE (MUST) identificar a importação. Na ausência de qualquer ator definido, o registro DEVE (MUST) ficar com a origem do sistema e sem usuário responsável. As operações de negócio NÃO DEVEM (MUST NOT) receber o ator, o endereço IP nem o cliente como parâmetro para poder registrar a ação.

#### Scenario: Ação da interface
- **GIVEN** um usuário autenticado
- **WHEN** ele executa uma ação auditável pela interface
- **THEN** o registro tem esse usuário como responsável e a origem `INTERFACE`

#### Scenario: Ação do sistema
- **GIVEN** o worker de e-mails em execução, fora de qualquer requisição
- **WHEN** ele envia um e-mail
- **THEN** o registro não tem usuário responsável e tem a origem `SISTEMA`
- **AND** a interface exibe "Sistema" como responsável

#### Scenario: Ação vinda de uma importação
- **GIVEN** uma importação de usuários confirmada por Ana
- **WHEN** um usuário do arquivo é cadastrado pela importação
- **THEN** o registro do cadastro tem Ana como responsável e a origem `IMPORTACAO`

### Requirement: Auditoria da autenticação
O sistema DEVE (MUST) registrar o login realizado, o login recusado, o logout, a solicitação de recuperação de senha e a redefinição de senha. No login recusado, inclusive o de um usuário inativo com a senha correta, o registro DEVE (MUST) guardar o e-mail informado na tentativa, o endereço IP e o cliente, e NÃO DEVE (MUST NOT) ter usuário responsável. O registro da solicitação de recuperação DEVE (MUST) ser o mesmo para um e-mail cadastrado e para um e-mail não cadastrado, de modo que a auditoria não revele quais e-mails existem. A senha informada NÃO DEVE (MUST NOT) ser gravada em nenhuma hipótese, nem em texto, nem transformada.

#### Scenario: Login bem-sucedido
- **GIVEN** um usuário ativo com senha definida
- **WHEN** ele informa e-mail e senha corretos e o login é realizado
- **THEN** existe um registro com a ação `LOGIN` e o recurso `AUTENTICACAO`, com ele como responsável

#### Scenario: Login recusado
- **GIVEN** a página de login
- **WHEN** uma tentativa de autenticação com `ana@ifnmg.edu.br` é recusada por senha incorreta
- **THEN** existe um registro com a ação `LOGIN_RECUSADO`, sem usuário responsável, com o e-mail informado, o endereço IP e o cliente
- **AND** nenhum campo do registro contém a senha informada

#### Scenario: Login recusado de usuário inativo
- **GIVEN** um usuário inativo com a senha correta
- **WHEN** ele tenta entrar
- **THEN** existe um registro com a ação `LOGIN_RECUSADO` e o e-mail informado

#### Scenario: Logout
- **GIVEN** um usuário autenticado
- **WHEN** ele encerra a sessão
- **THEN** existe um registro com a ação `LOGOUT` e ele como responsável

#### Scenario: Recuperação de senha solicitada
- **WHEN** a recuperação de senha é solicitada para `ana@ifnmg.edu.br`
- **THEN** existe um registro com a ação `SENHA_SOLICITADA` e o e-mail informado

#### Scenario: Solicitação para e-mail não cadastrado
- **WHEN** a recuperação de senha é solicitada para um e-mail que não existe
- **THEN** existe um registro com a ação `SENHA_SOLICITADA` e o e-mail informado, igual ao de um e-mail cadastrado

#### Scenario: Senha redefinida
- **GIVEN** um usuário que recebeu o link de definição de senha
- **WHEN** ele define a senha pelo link
- **THEN** existe um registro com a ação `SENHA_REDEFINIDA` e ele como responsável
- **AND** nenhum campo do registro contém a senha nem o token do link

### Requirement: Auditoria do acesso às funcionalidades
O sistema DEVE (MUST) registrar o acesso às funcionalidades que fazem parte do fluxo de utilização. A funcionalidade auditável DEVE (MUST) declarar o recurso correspondente, e o registro DEVE (MUST) permitir identificar qual funcionalidade foi acessada e qual usuário a acessou. O registro DEVE (MUST) acontecer somente em requisições GET com resposta bem-sucedida. NÃO DEVEM (MUST NOT) ser registradas como acesso as requisições internas de renderização da interface, isto é, as requisições feitas pelo htmx para trocar um fragmento da tela atual ou abrir um modal, nem o carregamento de arquivos estáticos, nem as requisições recusadas por falta de permissão. A página inicial autenticada NÃO DEVE (MUST NOT) registrar acesso, por não ser uma funcionalidade.

#### Scenario: Acesso a uma funcionalidade
- **GIVEN** um usuário autenticado com a permissão de visualizar usuários
- **WHEN** ele abre a lista de usuários
- **THEN** existe um registro com a ação `ACESSO`, o recurso `USUARIO` e ele como responsável, com a rota acessada nas informações adicionais

#### Scenario: Busca na lista não é acesso novo
- **GIVEN** um usuário autenticado na lista de usuários
- **WHEN** o formulário de filtros dispara requisições pelo htmx a cada trecho digitado
- **THEN** nenhum registro de acesso é criado por essas requisições

#### Scenario: Abertura de modal não é acesso novo
- **GIVEN** um usuário autenticado na lista de usuários
- **WHEN** ele abre o modal de cadastro pelo htmx
- **THEN** nenhum registro de acesso é criado por essa requisição

#### Scenario: Acesso recusado não é registrado como acesso
- **GIVEN** um usuário autenticado sem a permissão de visualizar usuários
- **WHEN** ele acessa a lista de usuários e recebe 403
- **THEN** nenhum registro com a ação `ACESSO` é criado

#### Scenario: Página inicial
- **WHEN** um usuário autenticado abre a página inicial
- **THEN** nenhum registro de acesso é criado

### Requirement: Auditoria das alterações de dados
Toda operação que altere dados persistidos DEVE (MUST) gerar um registro com o contexto da alteração. As operações auditadas DEVEM (MUST) ser, no mínimo: cadastro, alteração de dados, troca de perfil, desativação e reativação de usuário; criação, alteração de dados, alteração de permissões e exclusão de perfil; envio da prévia, confirmação e descarte de uma importação; e download do modelo de importação, registrado como exportação. Numa alteração, os valores anteriores e posteriores DEVEM (MUST) conter somente os campos que mudaram. Numa criação, os valores posteriores DEVEM (MUST) descrever o registro criado, e numa exclusão os valores anteriores DEVEM (MUST) descrever o registro excluído. Uma operação que não altere nada NÃO DEVE (MUST NOT) gerar registro. Uma operação recusada por regra de negócio ou por validação NÃO DEVE (MUST NOT) gerar registro.

#### Scenario: Criação
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra `ana@ifnmg.edu.br` com o perfil `DOCENTE`
- **THEN** existe um registro com a ação `CRIAR`, o recurso `USUARIO`, o identificador do usuário criado e os valores posteriores com o e-mail, o nome e o código do perfil

#### Scenario: Alteração
- **GIVEN** o usuário "Ana Souza" com o e-mail `ana@ifnmg.edu.br`
- **WHEN** um usuário com a permissão de editar altera o nome para "Ana Souza Lima", sem mudar o e-mail
- **THEN** existe um registro com a ação `ALTERAR` cujos valores anteriores e posteriores contêm apenas o nome, com "Ana Souza" e "Ana Souza Lima"

#### Scenario: Alteração sem mudança
- **WHEN** o formulário de edição é enviado com exatamente os mesmos dados do usuário
- **THEN** nenhum registro de auditoria é criado

#### Scenario: Exclusão
- **GIVEN** um perfil personalizado sem usuários vinculados
- **WHEN** o superadmin o exclui
- **THEN** existe um registro com a ação `EXCLUIR`, o recurso `PERFIL` e os valores anteriores com o código e o nome do perfil excluído

#### Scenario: Desativação e reativação
- **WHEN** um usuário é desativado e depois reativado
- **THEN** existem dois registros, um com a ação `DESATIVAR` e outro com a ação `ATIVAR`, ambos com o identificador desse usuário

#### Scenario: Alteração de permissões de um perfil
- **GIVEN** um perfil que concede `USUARIO.VISUALIZAR`
- **WHEN** o superadmin passa a conceder também `USUARIO.CRIAR`
- **THEN** existe um registro com a ação `ALTERAR` e o recurso `PERFIL`, com a lista de permissões antes e depois

#### Scenario: Operação recusada
- **GIVEN** o único usuário ativo com capacidade administrativa
- **WHEN** a desativação dele é recusada pela continuidade administrativa
- **THEN** nenhum registro de auditoria é criado

#### Scenario: Importação confirmada
- **GIVEN** uma importação de usuários validada com duas linhas de cadastro
- **WHEN** ela é confirmada
- **THEN** existe um registro com a ação `IMPORTAR` e o recurso da importação de usuários, com os totais aplicados
- **AND** existe um registro de cadastro para cada um dos dois usuários, com a origem `IMPORTACAO`

#### Scenario: Prévia não registra as linhas
- **GIVEN** uma planilha com duas linhas de cadastro
- **WHEN** a prévia é gerada, sem confirmação
- **THEN** existe um registro da prévia da importação
- **AND** não existe registro de cadastro de usuário, porque nenhum usuário foi criado

#### Scenario: Exportação do modelo
- **WHEN** um usuário com a permissão de importar baixa o modelo da planilha
- **THEN** existe um registro com a ação `EXPORTAR` e o nome do arquivo nas informações adicionais

### Requirement: Auditoria das ações automáticas
As ações executadas automaticamente pelo sistema DEVEM (MUST) ser auditadas com a identificação de que foram realizadas pelo próprio sistema. O envio de um e-mail pelo worker DEVE (MUST) gerar um registro, e o encerramento de um envio em falha definitiva também. As tentativas intermediárias de um envio NÃO DEVEM (MUST NOT) gerar registro de auditoria. O conteúdo do e-mail e os links enviados NÃO DEVEM (MUST NOT) ser gravados.

#### Scenario: E-mail enviado pelo worker
- **GIVEN** um envio pendente do link de definição de senha
- **WHEN** o worker o envia
- **THEN** existe um registro com a ação `ENVIAR`, o recurso `EMAIL`, sem usuário responsável, com a origem `SISTEMA` e com o tipo e a referência do envio nas informações adicionais
- **AND** o registro não contém o corpo do e-mail nem o link

#### Scenario: Envio encerrado em falha
- **GIVEN** um envio que atingiu o limite de tentativas
- **WHEN** o worker encerra o envio em falha
- **THEN** existe um registro com a ação `FALHAR` e o recurso `EMAIL`

#### Scenario: Nova tentativa não registra
- **GIVEN** um envio que falhou e será tentado de novo
- **WHEN** a tentativa falha sem atingir o limite
- **THEN** nenhum registro de auditoria é criado para essa tentativa

### Requirement: Ausência de dados sensíveis nos registros
Senhas, tokens, credenciais e demais segredos NÃO DEVEM (MUST NOT) ser gravados nos registros de auditoria, em nenhum campo. O ponto único de gravação DEVE (MUST) retirar dos valores anteriores, dos valores posteriores e das informações adicionais qualquer campo cujo nome indique senha, token, segredo, chave ou resumo criptográfico, mesmo que quem registrou a ação o tenha incluído.

#### Scenario: Campo sensível descartado
- **WHEN** uma gravação de auditoria inclui um campo de senha ou de token nos valores ou nas informações adicionais
- **THEN** o registro é criado sem esse campo, e os demais campos são mantidos

#### Scenario: Nenhuma senha na base de auditoria
- **GIVEN** um usuário cadastrado, que definiu a senha pelo link, entrou, errou a senha uma vez e teve o nome alterado
- **WHEN** todos os registros de auditoria são consultados
- **THEN** nenhum deles contém a senha, o resumo da senha ou o token do link

### Requirement: Integridade dos registros de auditoria
Os registros de auditoria DEVEM (MUST) formar um histórico somente de inclusão. A aplicação DEVE (MUST) recusar qualquer alteração e qualquer exclusão de um registro já gravado, tanto de um registro isolado quanto de um conjunto deles. NÃO DEVE (MUST NOT) existir rota, formulário, comando de gerenciamento nem ação de interface que altere ou exclua registros de auditoria, inclusive para o superadmin. O registro de uma alteração de dados DEVE (MUST) ser gravado na mesma transação da operação registrada, de modo que uma operação desfeita não deixe registro e uma operação aplicada nunca fique sem registro.

#### Scenario: Alteração recusada
- **WHEN** uma gravação tenta alterar um registro de auditoria existente
- **THEN** a gravação é recusada e o registro permanece como estava

#### Scenario: Exclusão recusada
- **WHEN** uma exclusão de um registro de auditoria, isolada ou em conjunto, é tentada
- **THEN** a exclusão é recusada e os registros permanecem

#### Scenario: Interface sem alteração da auditoria
- **GIVEN** um superadmin ativo autenticado
- **WHEN** ele procura na interface uma forma de alterar ou excluir um registro de auditoria
- **THEN** não existe essa ação, e a consulta é somente leitura

#### Scenario: Operação desfeita não deixa registro
- **GIVEN** uma operação de alteração de dados que falha depois de gravar
- **WHEN** a transação é desfeita
- **THEN** nem a alteração nem o registro de auditoria dela permanecem

### Requirement: Consulta dos registros de auditoria
Usuários autorizados DEVEM (MUST) poder consultar os registros de auditoria numa tela própria. A consulta DEVE (MUST) permitir filtrar por usuário responsável, ação, recurso, identificador do recurso, período e origem da operação, com os filtros combináveis entre si e recebidos como parâmetros da URL, de modo que o mesmo endereço reproduza o mesmo resultado. Um valor de filtro fora das opções DEVE (MUST) ser tratado como ausência do filtro. Os registros DEVEM (MUST) ser apresentados em ordem cronológica, do mais recente para o mais antigo, paginados conforme a spec `interface`, com a página combinada aos filtros. A lista DEVE (MUST) exibir, de cada registro, a data e a hora, o responsável, a ação, o recurso e a origem, com os rótulos em português, e "Sistema" como responsável quando não houver usuário. Cada registro DEVE (MUST) ter uma ação que exiba os detalhes dele, incluindo o identificador do recurso, os valores anteriores e posteriores campo a campo, as informações adicionais, o endereço IP e o cliente. Quando nenhum registro atender aos filtros, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar os filtros. A consulta NÃO DEVE (MUST NOT) alterar dados.

#### Scenario: Lista em ordem cronológica
- **GIVEN** registros de auditoria de datas diferentes
- **WHEN** a tela de auditoria é acessada sem filtros
- **THEN** os registros aparecem do mais recente para o mais antigo, com a data e a hora no formato dd/mm/aaaa e 24 horas

#### Scenario: Filtro por usuário e por ação
- **GIVEN** registros de Ana e de Bruno, de ações diferentes
- **WHEN** a consulta é feita com o filtro de usuário igual a Ana e o filtro de ação igual a `LOGIN`
- **THEN** só os registros de login de Ana são exibidos

#### Scenario: Filtro por recurso e identificador
- **GIVEN** registros de vários usuários alterados
- **WHEN** a consulta é feita pelo recurso `USUARIO` e pelo identificador `25`
- **THEN** só os registros do usuário de identificador 25 são exibidos

#### Scenario: Filtro por período
- **GIVEN** registros de 20/09/2026 e de 24/09/2026
- **WHEN** a consulta é feita com o período de 24/09/2026 até 24/09/2026
- **THEN** só os registros de 24/09/2026 são exibidos

#### Scenario: Filtro por origem
- **GIVEN** registros com as origens `INTERFACE`, `SISTEMA` e `IMPORTACAO`
- **WHEN** a consulta é feita com a origem `SISTEMA`
- **THEN** só os registros das ações automáticas são exibidos

#### Scenario: Filtro inválido
- **WHEN** a consulta é feita com uma ação que não existe no catálogo ou com uma data fora do formato
- **THEN** o filtro correspondente é ignorado e a lista é exibida sem erro

#### Scenario: Detalhe de um registro
- **GIVEN** um registro de alteração de usuário
- **WHEN** os detalhes dele são exibidos
- **THEN** aparecem o responsável, a ação, o recurso, o identificador, a data e a hora, o endereço IP, o cliente, a origem e cada campo alterado com o valor anterior e o posterior

#### Scenario: Consulta sem resultado
- **WHEN** a consulta é feita com filtros que não correspondem a nenhum registro
- **THEN** a lista informa que nenhum registro foi encontrado e oferece um link para limpar os filtros

### Requirement: Autorização da consulta da auditoria
A consulta dos registros de auditoria DEVE (MUST) exigir autenticação e a permissão `AUDITORIA.VISUALIZAR`, conforme a spec `controle-acesso`. Um visitante não autenticado DEVE (MUST) ser redirecionado para o login, e um usuário autenticado sem a permissão DEVE (MUST) receber 403, tanto na lista quanto no detalhe de um registro. O item "Auditoria" da navegação DEVE (MUST) aparecer somente para quem tem a permissão. O acesso à própria consulta DEVE (MUST) ser auditado, como o das demais funcionalidades.

#### Scenario: Visitante não autenticado
- **WHEN** um visitante acessa diretamente a URL da auditoria
- **THEN** ele é redirecionado para a página de login com a indicação da página solicitada

#### Scenario: Usuário sem a permissão
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `AUDITORIA.VISUALIZAR`
- **WHEN** ele acessa a lista de auditoria ou o detalhe de um registro
- **THEN** a requisição é recusada com 403
- **AND** a navegação não contém o item "Auditoria"

#### Scenario: Usuário com a permissão
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede `AUDITORIA.VISUALIZAR`
- **WHEN** ele acessa a lista de auditoria
- **THEN** o acesso é concedido e um registro com a ação `ACESSO` e o recurso `AUDITORIA` é criado
