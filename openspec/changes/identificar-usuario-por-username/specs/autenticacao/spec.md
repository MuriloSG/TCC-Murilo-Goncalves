## MODIFIED Requirements

### Requirement: E-mail como identificador de login
O usuário DEVE (MUST) se autenticar pelo e-mail. A comparação do e-mail no login NÃO DEVE (MUST NOT) diferenciar maiúsculas de minúsculas. O e-mail cadastrado no usuário DEVE (MUST) ser o único e-mail aceito para login, e o login NÃO DEVE (MUST NOT) exigir etapa de verificação de e-mail.

O formulário de login NÃO DEVE (MUST NOT) oferecer campo de identificação além do e-mail. O campo `username` do usuário, definido pela spec `gestao-usuarios`, é um identificador de domínio e NÃO DEVE (MUST NOT) ser aceito como credencial: informá-lo no lugar do e-mail NÃO DEVE (MUST NOT) autenticar, e nenhuma configuração do sistema DEVE (MUST) tratá-lo como campo de login.

#### Scenario: Formulário de login só com e-mail e senha
- **GIVEN** um visitante não autenticado
- **WHEN** ele abre a página de login
- **THEN** o formulário solicita apenas e-mail e senha, sem nenhum outro campo de identificação

#### Scenario: `username` não autentica
- **GIVEN** um usuário ativo com o e-mail `aldo@ifnmg.edu.br`, o `username` `Aldo Gomes` e senha definida
- **WHEN** ele informa `Aldo Gomes` no campo de identificação e a senha correta
- **THEN** a autenticação é recusada com a mesma mensagem de credencial inválida

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
