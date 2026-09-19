## MODIFIED Requirements

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
