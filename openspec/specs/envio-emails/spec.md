# envio-emails Specification

## Purpose
TBD - created by archiving change enviar-emails-por-outbox. Update Purpose after archive.
## Requirements
### Requirement: Registro do envio na transação da operação
Os e-mails disparados pelo sistema por conta própria DEVEM (MUST) ser registrados como envios no outbox, na mesma transação da operação que os origina, e NÃO DEVEM (MUST NOT) ser enviados durante a requisição. Um envio DEVE (MUST) guardar o tipo (código em português, como `LINK_SENHA`) e a referência do objeto a que se refere, e NÃO DEVE (MUST NOT) guardar o conteúdo do e-mail, tokens nem links. Se a transação da operação for desfeita, o envio DEVE (MUST) ser desfeito junto. DEVE (MUST) existir no máximo um envio `A_ENVIAR` para o mesmo tipo e referência, garantido pelo banco de dados, e registrar de novo um envio que já está `A_ENVIAR` NÃO DEVE (MUST NOT) criar outro envio nem reiniciar as tentativas do existente.

#### Scenario: Envio registrado com a operação
- **WHEN** uma operação registra um envio `LINK_SENHA` para um usuário e a transação é confirmada
- **THEN** existe um envio `A_ENVIAR` com esse tipo e essa referência e nenhum e-mail foi enviado

#### Scenario: Envio desfeito com a operação
- **WHEN** uma operação registra um envio e a transação é desfeita
- **THEN** o envio não existe

#### Scenario: Registro repetido
- **GIVEN** um envio `A_ENVIAR` do tipo `LINK_SENHA` para um usuário, com uma tentativa já feita
- **WHEN** um novo envio do mesmo tipo e para o mesmo usuário é registrado
- **THEN** continua existindo um único envio `A_ENVIAR`, com uma tentativa

#### Scenario: Conteúdo não gravado
- **WHEN** um envio `LINK_SENHA` é registrado e depois enviado
- **THEN** nenhum registro do banco contém o token nem o link enviado

### Requirement: Tratadores por tipo
Cada tipo de envio DEVE (MUST) ter um tratador registrado pelo app que o define, e o outbox NÃO DEVE (MUST NOT) importar código de apps de domínio. No momento do envio, o tratador DEVE (MUST) carregar os dados atuais da referência e montar o e-mail, ou informar que o envio não faz mais sentido. Um envio de tipo sem tratador registrado DEVE (MUST) ficar `FALHOU` na primeira tentativa, com registro no log.

#### Scenario: Tipo sem tratador
- **GIVEN** um envio `A_ENVIAR` de um tipo sem tratador registrado
- **WHEN** o worker processa esse envio
- **THEN** o envio fica `FALHOU` e o erro é registrado no log

#### Scenario: Outbox sem dependência de domínio
- **WHEN** os módulos do outbox são inspecionados
- **THEN** nenhum deles importa módulos de `accounts` ou de outro app de domínio

### Requirement: Processamento pelo worker
Um processo separado da aplicação web DEVE (MUST) processar os envios `A_ENVIAR` cuja próxima tentativa já venceu, em lotes de tamanho definido em configuração, e repetir o ciclo no intervalo definido em configuração. O processamento DEVE (MUST) travar cada envio de forma que dois workers simultâneos não processem o mesmo envio. Um envio entregue ao servidor de e-mail DEVE (MUST) ficar `ENVIADO`, com a data do envio. O worker DEVE (MUST) poder executar um único ciclo e terminar. A entrega DEVE (MUST) ser feita pelo menos uma vez: uma interrupção entre o envio e a gravação do estado pode repetir o e-mail.

#### Scenario: Envio bem-sucedido
- **GIVEN** um envio `A_ENVIAR` do tipo `LINK_SENHA` para um usuário ativo sem senha definida
- **WHEN** o worker executa um ciclo
- **THEN** o e-mail é enviado e o envio fica `ENVIADO`, com a data do envio

#### Scenario: Próxima tentativa ainda não vencida
- **GIVEN** um envio `A_ENVIAR` com a próxima tentativa agendada para daqui a 5 minutos
- **WHEN** o worker executa um ciclo agora
- **THEN** o envio não é processado

#### Scenario: Workers simultâneos
- **GIVEN** um envio `A_ENVIAR`
- **WHEN** dois workers executam um ciclo ao mesmo tempo
- **THEN** o e-mail é enviado uma única vez

### Requirement: Novas tentativas e falha
Uma exceção durante o envio DEVE (MUST) ser tratada como falha temporária: o envio DEVE (MUST) continuar `A_ENVIAR`, com as tentativas aumentadas em um, o último erro resumido gravado e a próxima tentativa agendada conforme os intervalos definidos em configuração, em que o último intervalo se repete quando houver mais tentativas que intervalos. Ao atingir a quantidade máxima de tentativas definida em configuração, o envio DEVE (MUST) ficar `FALHOU` e o erro DEVE (MUST) ser registrado no log. `FALHOU` DEVE (MUST) ser final nesta versão. Os valores iniciais DEVEM (MUST) ser 5 tentativas, com intervalos de 1, 5, 15 e 60 minutos, e DEVEM (MUST) poder ser alterados sem mudar o código.

#### Scenario: Falha temporária
- **GIVEN** um envio `A_ENVIAR` sem tentativas e o servidor de e-mail indisponível
- **WHEN** o worker executa um ciclo
- **THEN** o envio continua `A_ENVIAR`, com uma tentativa, o erro gravado e a próxima tentativa agendada para 1 minuto depois

#### Scenario: Limite de tentativas
- **GIVEN** um envio `A_ENVIAR` com quatro tentativas e o limite de cinco
- **WHEN** a quinta tentativa falha
- **THEN** o envio fica `FALHOU` e o erro é registrado no log

#### Scenario: Envio que falhou não é retomado
- **GIVEN** um envio `FALHOU`
- **WHEN** o worker executa um ciclo
- **THEN** o envio não é processado

### Requirement: Descarte de envio sem sentido
Quando o tratador informar que o envio não faz mais sentido, o envio DEVE (MUST) ficar `DESCARTADO`, sem enviar e-mail, sem nova tentativa e sem ser contado como erro.

#### Scenario: Descarte
- **GIVEN** um envio `A_ENVIAR` cujo tratador informa que não há mais o que enviar
- **WHEN** o worker processa o envio
- **THEN** nenhum e-mail é enviado e o envio fica `DESCARTADO`

### Requirement: Link de definição de senha pelo outbox
O tipo `LINK_SENHA` DEVE (MUST) ter como referência o usuário. No momento do envio, o tratador DEVE (MUST) gerar o token e o link com o mesmo gerador de token e a mesma rota do fluxo de recuperação de senha, com a URL base definida em configuração, e enviar o e-mail com os mesmos templates desse fluxo, para o e-mail atual do usuário. A validade do link DEVE (MUST) contar a partir do envio. O envio DEVE (MUST) ser descartado quando o usuário não existir mais, estiver inativo ou já tiver uma senha utilizável. O envio pelo worker NÃO DEVE (MUST NOT) consumir o limite de tentativas da recuperação de senha pública.

#### Scenario: Link funcional
- **GIVEN** um envio `LINK_SENHA` enviado para um usuário ativo sem senha
- **WHEN** o usuário abre o link recebido e define uma senha válida
- **THEN** a senha é gravada

#### Scenario: Link com a URL base configurada
- **GIVEN** a URL base `https://agendamento.exemplo.edu.br`
- **WHEN** um envio `LINK_SENHA` é enviado
- **THEN** o link do e-mail começa com `https://agendamento.exemplo.edu.br/`

#### Scenario: E-mail alterado antes do envio
- **GIVEN** um envio `LINK_SENHA` registrado para um usuário com o e-mail `ana@ifnmg.edu.br`
- **AND** que o e-mail dele foi alterado para `ana.souza@ifnmg.edu.br` antes do envio
- **WHEN** o worker processa o envio
- **THEN** o e-mail é enviado para `ana.souza@ifnmg.edu.br`

#### Scenario: Usuário desativado antes do envio
- **GIVEN** um envio `LINK_SENHA` para um usuário que foi desativado
- **WHEN** o worker processa o envio
- **THEN** nenhum e-mail é enviado e o envio fica `DESCARTADO`

#### Scenario: Senha definida antes do envio
- **GIVEN** um envio `LINK_SENHA` para um usuário que definiu a senha pelo "Esqueci minha senha"
- **WHEN** o worker processa o envio
- **THEN** nenhum e-mail é enviado e o envio fica `DESCARTADO`

#### Scenario: Limite de tentativas da recuperação pública preservado
- **GIVEN** que o worker enviou o link para `ana@ifnmg.edu.br`
- **WHEN** Ana pede a recuperação de senha na página de login
- **THEN** o pedido é tratado como se o worker não tivesse enviado nada, em relação ao limite de tentativas

