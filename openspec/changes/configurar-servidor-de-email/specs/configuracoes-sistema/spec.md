## ADDED Requirements

### Requirement: Configurações do sistema por tipo
O sistema DEVE (MUST) guardar suas configurações no banco, uma por tipo, com o tipo identificado por uma chave estável (a primeira é `smtp`), o valor em JSON e as datas de criação e de alteração. O escopo DEVE (MUST) ser global, porque o sistema atende a um único campus. DEVE (MUST) existir no máximo uma configuração por tipo, garantida pelo banco de dados. Cada tipo DEVE (MUST) ter um esquema definido, e um valor com campos fora do esquema ou inválidos DEVE (MUST) ser recusado.

#### Scenario: Cadastro de uma configuração SMTP válida
- **GIVEN** que não existe configuração `smtp`
- **WHEN** uma configuração SMTP válida é salva
- **THEN** existe uma configuração `smtp` com os dados informados

#### Scenario: Atualização sem duplicata
- **GIVEN** uma configuração `smtp` gravada
- **WHEN** a configuração SMTP é salva de novo com outro servidor
- **THEN** continua existindo uma única configuração `smtp`, com o servidor novo

#### Scenario: Duplicata recusada pelo banco
- **GIVEN** uma configuração `smtp` gravada
- **WHEN** outro registro do tipo `smtp` é inserido diretamente
- **THEN** o banco recusa a inserção

#### Scenario: Campo fora do esquema
- **WHEN** uma configuração `smtp` com um campo que o esquema não conhece é validada
- **THEN** a configuração é recusada

### Requirement: Dados da configuração SMTP
A configuração SMTP DEVE (MUST) ter servidor, porta, segurança, usuário, senha e remetente. Servidor e remetente DEVEM (MUST) ser obrigatórios, o remetente DEVE (MUST) ser um e-mail válido e a porta DEVE (MUST) estar entre 1 e 65535. A segurança DEVE (MUST) ser uma única escolha entre `STARTTLS`, `SSL` e `NENHUMA`. Usuário e senha DEVEM (MUST) ser informados juntos ou omitidos juntos, e credenciais com a segurança `NENHUMA` DEVEM (MUST) ser recusadas. Numa atualização, a senha em branco DEVE (MUST) manter a senha gravada; sem usuário, a senha gravada DEVE (MUST) ser apagada.

#### Scenario: Dados inválidos
- **WHEN** uma configuração SMTP sem servidor, com porta 70000, com remetente inválido, com usuário sem senha ou com credenciais e segurança `NENHUMA` é salva
- **THEN** a configuração é recusada com a mensagem do campo e nada é gravado

#### Scenario: Senha mantida
- **GIVEN** uma configuração `smtp` com a senha `segredo`
- **WHEN** a configuração é atualizada com outra porta e a senha em branco
- **THEN** a senha usada no envio continua `segredo`

### Requirement: Proteção da senha SMTP
A senha DEVE (MUST) ser gravada cifrada de forma reversível, com uma chave vinda do ambiente e diferente da `SECRET_KEY`, e NÃO DEVE (MUST NOT) aparecer em texto puro no banco, na interface, em respostas, no log nem na auditoria. Uma senha que não pode ser decifrada DEVE (MUST) tornar a configuração inválida.

#### Scenario: Senha cifrada no banco
- **WHEN** uma configuração com a senha `segredo` é salva
- **THEN** o valor gravado no banco não contém `segredo` e a senha decifrada é `segredo`

#### Scenario: Senha fora da tela e da auditoria
- **GIVEN** uma configuração `smtp` com a senha `segredo`
- **WHEN** a página e o formulário da configuração são abertos e a alteração é auditada
- **THEN** nenhuma resposta e nenhum registro de auditoria contém `segredo`

#### Scenario: Chave trocada
- **GIVEN** uma configuração `smtp` gravada com outra chave de cifra
- **WHEN** a configuração é carregada para envio
- **THEN** ela é tratada como inválida

### Requirement: Tela do servidor de e-mail
A página "Servidor de e-mail" DEVE (MUST) exigir autenticação e a permissão `CONFIGURACAO.EDITAR`, concedida ao perfil `ADMINISTRADOR` pela migration que a acrescenta. Ela DEVE (MUST) mostrar se o servidor está configurado, os dados da configuração sem a senha (só se ela está definida) e quantos envios aguardam. O cadastro e a alteração DEVEM (MUST) abrir em modal, validar antes de gravar, mostrar o erro no campo e, no sucesso, a mensagem "Servidor de e-mail salvo.". A gravação DEVE (MUST) ser auditada no módulo `CONFIGURACAO`, sem o valor da senha.

#### Scenario: Cadastro pela tela
- **GIVEN** um usuário com `CONFIGURACAO.EDITAR`
- **WHEN** ele envia o formulário com dados válidos
- **THEN** a configuração é gravada, a mensagem "Servidor de e-mail salvo." aparece e a auditoria registra `CRIAR` no módulo `CONFIGURACAO`

#### Scenario: Usuário sem permissão
- **GIVEN** um usuário autenticado sem `CONFIGURACAO.EDITAR`
- **WHEN** ele abre a página ou envia o formulário
- **THEN** a resposta é 403 e nada é exibido nem alterado
