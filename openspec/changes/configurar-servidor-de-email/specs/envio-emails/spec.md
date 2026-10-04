## MODIFIED Requirements

### Requirement: Processamento pelo worker
Um processo separado da aplicação web DEVE (MUST) processar os envios `A_ENVIAR` cuja próxima tentativa já venceu, em lotes de tamanho definido em configuração, e repetir o ciclo no intervalo definido em configuração. O processamento DEVE (MUST) travar cada envio de forma que dois workers simultâneos não processem o mesmo envio. Cada lote DEVE (MUST) carregar a configuração SMTP persistida antes de processar qualquer envio, e os e-mails do lote DEVEM (MUST) sair com as credenciais e o remetente dessa configuração. Um envio entregue ao servidor de e-mail DEVE (MUST) ficar `ENVIADO`, com a data do envio. O worker DEVE (MUST) poder executar um único ciclo e terminar. A entrega DEVE (MUST) ser feita pelo menos uma vez: uma interrupção entre o envio e a gravação do estado pode repetir o e-mail.

#### Scenario: Envio bem-sucedido
- **GIVEN** um envio `A_ENVIAR` do tipo `LINK_SENHA` para um usuário ativo sem senha definida
- **AND** uma configuração SMTP válida
- **WHEN** o worker executa um ciclo
- **THEN** o e-mail é enviado e o envio fica `ENVIADO`, com a data do envio

#### Scenario: Credenciais da configuração persistida
- **GIVEN** uma configuração SMTP com o servidor `smtp.ifnmg.edu.br`, o usuário `agenda` e o remetente `IFAgenda <agenda@ifnmg.edu.br>`
- **WHEN** o worker envia um e-mail
- **THEN** a conexão usa esse servidor e esse usuário, com a senha decifrada, e o remetente do e-mail é `IFAgenda <agenda@ifnmg.edu.br>`

#### Scenario: Configuração alterada entre lotes
- **GIVEN** que o worker enviou um lote com o servidor `a.ifnmg.edu.br`
- **WHEN** a configuração passa a usar `b.ifnmg.edu.br` e o worker executa o próximo ciclo
- **THEN** os envios desse ciclo usam `b.ifnmg.edu.br`

#### Scenario: Próxima tentativa ainda não vencida
- **GIVEN** um envio `A_ENVIAR` com a próxima tentativa agendada para daqui a 5 minutos
- **WHEN** o worker executa um ciclo agora
- **THEN** o envio não é processado

#### Scenario: Workers simultâneos
- **GIVEN** um envio `A_ENVIAR`
- **WHEN** dois workers executam um ciclo ao mesmo tempo
- **THEN** o e-mail é enviado uma única vez

## ADDED Requirements

### Requirement: Envios retidos sem configuração SMTP
Sem configuração SMTP, ou com uma configuração inválida, o worker NÃO DEVE (MUST NOT) tentar enviar nenhum e-mail nem alterar os envios: eles DEVEM (MUST) continuar `A_ENVIAR`, com as mesmas tentativas e a mesma próxima tentativa, e o motivo DEVE (MUST) ser registrado no log quando mudar. O registro de novos envios NÃO DEVE (MUST NOT) depender da configuração. Quando uma configuração válida passar a existir, o ciclo seguinte DEVE (MUST) processar os envios retidos normalmente.

#### Scenario: Registro sem configuração
- **GIVEN** que não existe configuração SMTP
- **WHEN** um usuário é cadastrado
- **THEN** existe um envio `LINK_SENHA` `A_ENVIAR` para ele

#### Scenario: Worker sem configuração
- **GIVEN** um envio `A_ENVIAR` sem tentativas e nenhuma configuração SMTP
- **WHEN** o worker executa vários ciclos
- **THEN** nenhum e-mail é enviado, o envio continua `A_ENVIAR` sem tentativas e o motivo aparece no log

#### Scenario: Configuração inválida
- **GIVEN** um envio `A_ENVIAR` e uma configuração SMTP cuja senha não pode ser decifrada
- **WHEN** o worker executa um ciclo
- **THEN** nenhum e-mail é enviado e o envio continua `A_ENVIAR` sem tentativas

#### Scenario: Envios retidos liberados
- **GIVEN** envios `A_ENVIAR` retidos por falta de configuração
- **WHEN** uma configuração SMTP válida é salva e o worker executa um ciclo
- **THEN** os envios ficam `ENVIADO`

#### Scenario: Falha do servidor configurado
- **GIVEN** uma configuração SMTP válida e o servidor recusando a autenticação
- **WHEN** o worker processa um envio sem tentativas
- **THEN** o envio continua `A_ENVIAR`, com uma tentativa e a próxima agendada, e o erro gravado não contém a senha

### Requirement: Recuperação de senha pela configuração SMTP
O e-mail de "Esqueci minha senha" DEVE (MUST) ser enviado com as credenciais e o remetente da configuração SMTP. Sem configuração válida, o e-mail NÃO DEVE (MUST NOT) ser enviado, o motivo DEVE (MUST) ser registrado no log e a resposta da página DEVE (MUST) ser a mesma de um envio feito.

#### Scenario: Recuperação sem configuração
- **GIVEN** que não existe configuração SMTP
- **WHEN** um usuário ativo pede a recuperação de senha
- **THEN** a página de pedido enviado é exibida e nenhum e-mail é enviado
