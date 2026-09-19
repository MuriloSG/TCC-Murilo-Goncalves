# autenticacao Specification

## Purpose
TBD - created by archiving change gerenciar-usuarios-e-controle-de-acesso. Update Purpose after archive.
## Requirements
### Requirement: Fluxos de autenticação e rotas expostas
O login, o logout e a recuperação de senha DEVEM (MUST) ser oferecidos pelo mecanismo de autenticação definido no design (django-allauth). A criação inicial da senha DEVE (MUST) usar o mesmo fluxo da recuperação de senha, sem um segundo fluxo paralelo de definição de senha. As únicas rotas de autenticação expostas DEVEM (MUST) ser as de login, logout e as quatro etapas da recuperação de senha: solicitação, aviso de envio, redefinição pelo link e conclusão.

#### Scenario: Rotas de autenticação disponíveis
- **GIVEN** a aplicação em execução
- **WHEN** um visitante acessa as rotas de login, de solicitação de recuperação de senha e de aviso de envio
- **THEN** cada rota responde com a página correspondente do fluxo

#### Scenario: Rotas de autenticação fora do escopo não expostas
- **GIVEN** a aplicação em execução
- **WHEN** um visitante ou um usuário autenticado tenta acessar rotas de cadastro, de gestão de e-mails, de troca de senha ou de definição de senha fora do fluxo de recuperação
- **THEN** a rota não existe e a resposta é 404

#### Scenario: Criação inicial e recuperação usam o mesmo link
- **GIVEN** um usuário recém-cadastrado que recebeu o e-mail de criação de senha
- **AND** um usuário existente que solicitou a recuperação de senha
- **WHEN** os links recebidos pelos dois são comparados
- **THEN** ambos apontam para a mesma rota de redefinição de senha

### Requirement: E-mail como identificador de login
O usuário DEVE (MUST) se autenticar pelo e-mail, sem campo de username. A comparação do e-mail no login NÃO DEVE (MUST NOT) diferenciar maiúsculas de minúsculas. O e-mail cadastrado no usuário DEVE (MUST) ser o único e-mail aceito para login, e o login NÃO DEVE (MUST NOT) exigir etapa de verificação de e-mail.

#### Scenario: Formulário de login sem username
- **GIVEN** um visitante não autenticado
- **WHEN** ele abre a página de login
- **THEN** o formulário solicita apenas e-mail e senha, sem campo de username

#### Scenario: E-mail informado com maiúsculas
- **GIVEN** um usuário ativo com e-mail `joao@ifnmg.edu.br` e senha definida
- **WHEN** ele informa `Joao@IFNMG.edu.br` e a senha correta
- **THEN** a autenticação é concluída com sucesso

#### Scenario: Login sem etapa de verificação de e-mail
- **GIVEN** um usuário ativo que definiu a senha pelo link recebido após o cadastro
- **WHEN** ele informa e-mail e senha corretos pela primeira vez
- **THEN** a autenticação é concluída sem exigir confirmação adicional do e-mail

#### Scenario: E-mail antigo não autentica após a troca
- **GIVEN** um usuário ativo cujo e-mail foi alterado de `antigo@ifnmg.edu.br` para `novo@ifnmg.edu.br`
- **WHEN** ele tenta se autenticar com `antigo@ifnmg.edu.br` e a senha correta
- **THEN** a autenticação é recusada e nenhuma sessão autenticada é criada

#### Scenario: Novo e-mail autentica após a troca
- **GIVEN** um usuário ativo cujo e-mail foi alterado para `novo@ifnmg.edu.br`
- **WHEN** ele se autentica com `novo@ifnmg.edu.br` e a senha correta
- **THEN** a autenticação é concluída com sucesso

### Requirement: Login com e-mail e senha
O sistema DEVE (MUST) autenticar um usuário ativo que informe e-mail e senha corretos, criar uma sessão autenticada com uma nova chave de sessão e redirecioná-lo para a página inicial autenticada.

#### Scenario: Login bem-sucedido
- **GIVEN** um usuário ativo com senha definida
- **WHEN** ele informa e-mail e senha corretos na página de login
- **THEN** uma sessão autenticada é criada para ele
- **AND** ele é redirecionado para a página inicial autenticada

#### Scenario: Chave da sessão renovada no login
- **GIVEN** um visitante com uma sessão anônima já existente
- **WHEN** ele se autentica com e-mail e senha corretos
- **THEN** a chave da sessão autenticada é diferente da chave da sessão anônima anterior

### Requirement: Recusa de credenciais inválidas
O sistema DEVE (MUST) recusar a autenticação quando o e-mail não estiver cadastrado, quando a senha estiver incorreta ou quando o usuário ainda não tiver definido a senha. Nesses casos, a resposta NÃO DEVE (MUST NOT) revelar se o e-mail está cadastrado. Quando houver um número excessivo de tentativas de login com falha em um curto período, o sistema DEVE (MUST) recusar temporariamente novas tentativas, sem autenticar, e informar que houve tentativas demais. Os valores concretos do limite ficam definidos no design.

#### Scenario: Senha incorreta
- **GIVEN** um usuário ativo com senha definida
- **WHEN** alguém informa o e-mail desse usuário com uma senha incorreta
- **THEN** a autenticação é recusada, nenhuma sessão autenticada é criada e a página de login exibe uma mensagem de erro

#### Scenario: E-mail não cadastrado
- **GIVEN** que não existe usuário com o e-mail `inexistente@ifnmg.edu.br`
- **WHEN** alguém informa esse e-mail com qualquer senha
- **THEN** a autenticação é recusada e nenhuma sessão autenticada é criada

#### Scenario: Mesma resposta para e-mail inexistente e senha incorreta
- **GIVEN** um usuário ativo cadastrado e um e-mail não cadastrado
- **WHEN** uma tentativa usa o e-mail cadastrado com senha incorreta e outra usa o e-mail não cadastrado
- **THEN** as duas tentativas exibem a mesma mensagem de erro, sem indicar qual dado está incorreto

#### Scenario: Usuário que ainda não definiu a senha
- **GIVEN** um usuário ativo recém-cadastrado que ainda não definiu a senha pelo link
- **WHEN** alguém tenta se autenticar com o e-mail desse usuário e qualquer senha
- **THEN** a autenticação é recusada e nenhuma sessão autenticada é criada

#### Scenario: Limite de tentativas de login excedido
- **GIVEN** que tentativas de login com falha excederam o limite de tentativas configurado
- **WHEN** uma nova tentativa de login é feita dentro do período do limite
- **THEN** a tentativa é recusada sem autenticar o usuário e a página informa que houve tentativas demais

### Requirement: Bloqueio de autenticação de usuário inativo
Um usuário com `is_active = False` NÃO DEVE (MUST NOT) conseguir se autenticar, mesmo informando credenciais corretas e mesmo que tenha `is_superadmin = True`. A recusa NÃO DEVE (MUST NOT) criar sessão autenticada nem conceder acesso a funcionalidades protegidas. O texto exato da mensagem exibida não é fixado por esta spec.

#### Scenario: Usuário inativo com credenciais corretas
- **GIVEN** um usuário com `is_active = False` e senha definida
- **WHEN** ele informa e-mail e senha corretos
- **THEN** a autenticação é recusada e nenhuma sessão autenticada é criada

#### Scenario: Superadmin inativo com credenciais corretas
- **GIVEN** um usuário com `is_superadmin = True`, `is_active = False` e senha definida
- **WHEN** ele informa e-mail e senha corretos
- **THEN** a autenticação é recusada e nenhuma sessão autenticada é criada

#### Scenario: Reativação restaura o login
- **GIVEN** um usuário desativado que tinha senha definida
- **WHEN** ele é reativado e informa e-mail e a mesma senha de antes
- **THEN** a autenticação é concluída com sucesso

### Requirement: Logout
O logout DEVE (MUST) ser feito somente por requisição POST, encerrar a sessão autenticada e redirecionar o usuário para a página de login. Uma requisição GET à rota de logout NÃO DEVE (MUST NOT) encerrar a sessão.

#### Scenario: Logout por POST
- **GIVEN** um usuário autenticado
- **WHEN** ele envia uma requisição POST à rota de logout
- **THEN** a sessão autenticada é encerrada
- **AND** ele é redirecionado para a página de login

#### Scenario: GET na rota de logout
- **GIVEN** um usuário autenticado
- **WHEN** ele acessa a rota de logout por GET
- **THEN** a sessão autenticada continua ativa

#### Scenario: Acesso autenticado após logout
- **GIVEN** um usuário que acabou de fazer logout
- **WHEN** ele acessa a página inicial autenticada
- **THEN** ele é tratado como visitante não autenticado e redirecionado para a página de login

### Requirement: Encerramento de sessões
Uma sessão autenticada DEVE (MUST) deixar de valer na requisição seguinte quando o usuário for desativado ou quando sua senha for redefinida. Nesses casos, o usuário DEVE (MUST) passar a ser tratado como visitante não autenticado, sem precisar fazer logout.

#### Scenario: Sessão aberta de usuário desativado
- **GIVEN** um usuário autenticado com uma sessão aberta
- **WHEN** ele é desativado e, em seguida, faz uma nova requisição com a mesma sessão
- **THEN** a requisição é tratada como de um visitante não autenticado

#### Scenario: Outras sessões após redefinição de senha
- **GIVEN** um usuário autenticado com uma sessão aberta em um navegador
- **WHEN** ele redefine a senha pelo link de recuperação em outro navegador e, em seguida, faz uma nova requisição com a sessão do primeiro navegador
- **THEN** a requisição é tratada como de um visitante não autenticado

### Requirement: Ausência de cadastro público
O sistema NÃO DEVE (MUST NOT) permitir que visitantes criem a própria conta. Nenhuma rota de cadastro DEVE (MUST) ser exposta, e o mecanismo de autenticação DEVE (MUST) tratar o cadastro como fechado para qualquer fluxo que verifique essa possibilidade.

#### Scenario: Tentativa de acessar o cadastro
- **GIVEN** um visitante não autenticado
- **WHEN** ele tenta acessar uma rota de cadastro de conta
- **THEN** a resposta é 404 e nenhum usuário é criado

#### Scenario: Página de login sem convite para cadastro
- **GIVEN** um visitante não autenticado
- **WHEN** ele abre a página de login
- **THEN** a página não oferece link nem formulário para criar conta

#### Scenario: Cadastro fechado no mecanismo de autenticação
- **GIVEN** a configuração de autenticação da aplicação
- **WHEN** qualquer fluxo de autenticação verifica se o cadastro de contas está aberto
- **THEN** a resposta é que o cadastro não está aberto

### Requirement: Criação inicial da senha pelo próprio usuário
Todo usuário cadastrado pela interface DEVE (MUST) ser criado ativo e sem senha que permita autenticação, até que ele mesmo a defina. Na mesma transação do cadastro, o sistema DEVE (MUST) registrar no outbox o envio do link do fluxo de recuperação de senha ao e-mail do novo usuário, conforme a spec `envio-emails`, pelo qual ele define a própria senha. O envio NÃO DEVE (MUST NOT) acontecer durante a requisição do cadastro, e quem cadastrou DEVE (MUST) ser informado de que o link será enviado. Uma falha no envio NÃO DEVE (MUST NOT) desfazer o cadastro e DEVE (MUST) ser tratada pelas novas tentativas do outbox. Nenhuma operação da aplicação DEVE (MUST) permitir que um usuário defina, altere ou redefina a senha de outro. Ao concluir a definição, o usuário NÃO DEVE (MUST NOT) ser autenticado automaticamente.

#### Scenario: E-mail enviado após o cadastro
- **GIVEN** um usuário autenticado com permissão para cadastrar usuários
- **WHEN** ele cadastra um novo usuário com o e-mail `novo@ifnmg.edu.br`
- **THEN** o cadastro registra no outbox o envio do link de definição de senha para o novo usuário
- **AND** a mensagem exibida informa que o link será enviado para `novo@ifnmg.edu.br`
- **AND** depois que o worker processa o envio, um e-mail com o link de definição de senha é enviado para `novo@ifnmg.edu.br`

#### Scenario: Cadastro sem campo de senha
- **GIVEN** um usuário autenticado com permissão para cadastrar usuários
- **WHEN** ele abre o formulário de cadastro de usuário
- **THEN** o formulário não contém campo para definir ou informar a senha do novo usuário

#### Scenario: Definição da senha pelo link
- **GIVEN** um usuário recém-cadastrado que recebeu o link de definição de senha
- **WHEN** ele abre o link e informa uma nova senha válida
- **THEN** a senha é gravada
- **AND** ele não é autenticado automaticamente e é levado para a página de login

#### Scenario: Primeiro login após definir a senha
- **GIVEN** um usuário que definiu a senha pelo link
- **WHEN** ele informa e-mail e a senha definida na página de login
- **THEN** a autenticação é concluída com sucesso

#### Scenario: Falha no envio do e-mail de criação
- **GIVEN** um usuário cadastrado cujo envio do link falha no servidor de e-mail
- **WHEN** o worker processa o envio
- **THEN** o novo usuário permanece cadastrado
- **AND** o envio é tentado de novo conforme a spec `envio-emails` e, no limite de tentativas, a falha é registrada no log

#### Scenario: Novo link após falha ou expiração
- **GIVEN** um usuário ativo que ainda não definiu a senha e não tem um link válido
- **WHEN** ele solicita a recuperação de senha informando o próprio e-mail
- **THEN** ele recebe um novo link e consegue definir a senha por ele

### Requirement: Recuperação de senha
Qualquer usuário ativo, inclusive um superadmin, DEVE (MUST) poder recuperar o acesso pelo fluxo de recuperação de senha, acessível a partir da página de login. A resposta à solicitação DEVE (MUST) ser a mesma, exista ou não um usuário com o e-mail informado. O e-mail DEVE (MUST) ser enviado somente quando existir um usuário ativo com aquele endereço. Endereços não cadastrados e usuários inativos NÃO DEVEM (MUST NOT) receber e-mail. Ao concluir a redefinição, o usuário NÃO DEVE (MUST NOT) ser autenticado automaticamente. Quando houver um número excessivo de solicitações de recuperação em um curto período, o sistema DEVE (MUST) recusar temporariamente novas solicitações, sem enviar e-mail. Os valores concretos do limite ficam definidos no design.

#### Scenario: Acesso à recuperação pela página de login
- **GIVEN** um visitante não autenticado
- **WHEN** ele abre a página de login
- **THEN** a página oferece o link "Esqueci minha senha" para a solicitação de recuperação

#### Scenario: Solicitação para usuário ativo
- **GIVEN** um usuário ativo com e-mail `docente@ifnmg.edu.br`
- **WHEN** alguém solicita a recuperação de senha informando `docente@ifnmg.edu.br`
- **THEN** um e-mail com o link de redefinição é enviado para `docente@ifnmg.edu.br`
- **AND** a página de aviso de envio é exibida

#### Scenario: Solicitação para e-mail não cadastrado
- **GIVEN** que não existe usuário com o e-mail `inexistente@ifnmg.edu.br`
- **WHEN** alguém solicita a recuperação de senha informando esse e-mail
- **THEN** nenhum e-mail é enviado
- **AND** a resposta exibida é a mesma de uma solicitação para um e-mail cadastrado

#### Scenario: Solicitação para usuário inativo
- **GIVEN** um usuário com `is_active = False`
- **WHEN** alguém solicita a recuperação de senha informando o e-mail desse usuário
- **THEN** nenhum e-mail é enviado
- **AND** a resposta exibida é a mesma de uma solicitação para um e-mail cadastrado

#### Scenario: Redefinição pelo link
- **GIVEN** um usuário ativo que recebeu um link de redefinição válido
- **WHEN** ele abre o link e informa uma nova senha válida
- **THEN** a nova senha é gravada e a senha anterior deixa de autenticar
- **AND** ele não é autenticado automaticamente e é levado para a página de login

#### Scenario: Superadmin recupera o acesso
- **GIVEN** um usuário ativo com `is_superadmin = True` que esqueceu a senha
- **WHEN** ele solicita a recuperação de senha, abre o link recebido e define uma nova senha válida
- **THEN** ele consegue se autenticar com a nova senha

#### Scenario: Limite de solicitações de recuperação excedido
- **GIVEN** que as solicitações de recuperação excederam o limite de tentativas configurado
- **WHEN** uma nova solicitação é feita dentro do período do limite
- **THEN** a solicitação é recusada e nenhum e-mail é enviado

### Requirement: Validade dos links de senha
O link de criação e de recuperação de senha DEVE (MUST) expirar 3 dias após ser emitido. Ele DEVE (MUST) ser de uso único, DEVE (MUST) perder a validade quando o e-mail do usuário mudar e NÃO DEVE (MUST NOT) redefinir a senha de um usuário inativo, mesmo que tenha sido emitido antes da desativação. Um link inválido NÃO DEVE (MUST NOT) alterar a senha, e o sistema DEVE (MUST) informar que o link não é mais válido.

#### Scenario: Link expirado
- **GIVEN** um link de redefinição emitido há mais de 3 dias e ainda não usado
- **WHEN** o usuário abre o link e tenta definir uma nova senha
- **THEN** a senha não é alterada e o sistema informa que o link não é mais válido

#### Scenario: Link reutilizado
- **GIVEN** um link de redefinição já usado para definir uma senha
- **WHEN** alguém abre o mesmo link novamente e tenta definir outra senha
- **THEN** a senha não é alterada e o sistema informa que o link não é mais válido

#### Scenario: Chave adulterada
- **GIVEN** um link de redefinição válido
- **WHEN** alguém altera a chave presente no link e o abre
- **THEN** nenhuma senha é alterada e o sistema informa que o link não é mais válido

#### Scenario: Link emitido antes da troca de e-mail
- **GIVEN** um link de redefinição emitido para um usuário ativo
- **WHEN** o e-mail do usuário é alterado e o link é aberto em seguida
- **THEN** a senha não é alterada e o sistema informa que o link não é mais válido

#### Scenario: Link emitido antes da desativação
- **GIVEN** um link de redefinição emitido para um usuário que estava ativo
- **WHEN** o usuário é desativado e o link é aberto em seguida para definir uma nova senha
- **THEN** a senha não é alterada

### Requirement: Validação e armazenamento da senha
Toda senha definida pelo link de criação ou de recuperação DEVE (MUST) atender à política de senha do sistema, que recusa senhas curtas demais, senhas comuns, senhas compostas só por números e senhas muito semelhantes ao e-mail ou ao nome do usuário. A senha DEVE (MUST) ser armazenada somente como hash.

#### Scenario: Senha fraca recusada
- **GIVEN** um usuário com um link de redefinição válido
- **WHEN** ele informa uma senha recusada pela política de senha, como uma senha só com números
- **THEN** a senha não é gravada, o formulário exibe o motivo da recusa e o link continua válido

#### Scenario: Senha parecida com os dados do usuário
- **GIVEN** um usuário com um link de redefinição válido
- **WHEN** ele informa uma senha muito semelhante ao próprio e-mail ou nome
- **THEN** a senha não é gravada e o formulário exibe o motivo da recusa

#### Scenario: Senha armazenada como hash
- **GIVEN** um usuário que definiu a senha pelo link
- **WHEN** o registro do usuário é consultado no banco de dados
- **THEN** o valor armazenado é um hash e não contém a senha em texto puro

### Requirement: Proteção CSRF nos formulários de autenticação
As requisições POST de login, logout, solicitação de recuperação e redefinição de senha DEVEM (MUST) exigir um token CSRF válido.

#### Scenario: Login sem token CSRF
- **GIVEN** um usuário ativo com senha definida
- **WHEN** uma requisição POST de login com e-mail e senha corretos é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e nenhuma sessão autenticada é criada

#### Scenario: Logout sem token CSRF
- **GIVEN** um usuário autenticado
- **WHEN** uma requisição POST de logout é enviada sem token CSRF válido
- **THEN** a requisição é recusada com 403 e a sessão autenticada continua ativa

