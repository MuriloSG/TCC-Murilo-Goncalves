## 1. Outbox

- [x] 1.1 Criar o app `outbox`, registrá-lo em `INSTALLED_APPS` e acrescentar ao `settings.py` `SITE_URL` e as configurações do outbox, lidas de variáveis de ambiente (D1, D5)
- [x] 1.2 Criar o model `OutboxEntry` com o índice único parcial e o índice de busca, e a migration `0001_initial` (D1)
- [x] 1.3 Implementar `OutboxEntry.objects.enqueue` com `ignore_conflicts` e o registro de tratadores em `outbox/handlers.py` (D2, D3)
- [x] 1.4 Implementar o processamento de um envio e o comando `process_outbox` com `--once`, `skip_locked`, uma transação por envio, novas tentativas, `FALHOU`, `DESCARTADO`, log e parada por sinal (D4)
- [x] 1.5 Escrever os testes do outbox com um tratador de teste: registro na transação, rollback, registro repetido, próxima tentativa não vencida, envio, falha temporária com o intervalo, último intervalo repetido, limite de tentativas, `FALHOU` não retomado, descarte, tipo sem tratador e outbox sem importar `accounts`
- [x] 1.6 Testar com `TransactionTestCase` que um envio travado por outra conexão não é processado
- [x] 1.7 Commit

## 2. Link de definição de senha

- [x] 2.1 Criar `accounts/emails.py` com `PASSWORD_LINK` e o tratador `password_link`, e registrá-lo em `AccountsConfig.ready` (D6)
- [x] 2.2 Fazer `UserManager.register` chamar `OutboxEntry.objects.enqueue(PASSWORD_LINK, user.pk)` dentro da transação (D7)
- [x] 2.3 Simplificar `UserCreateView.perform` com a nova mensagem e remover o `on_commit`, o método de envio da view e `accounts.adapters.send_password_link` (D8)
- [x] 2.4 Escrever os testes do tratador: link com a URL base, link que define a senha pela rota atual, e-mail atual, descarte de usuário inexistente, inativo e com senha definida, e limite da recuperação pública não consumido
- [x] 2.5 Atualizar os testes do cadastro pela tela: um envio `A_ENVIAR` na mesma transação, nenhum e-mail durante a requisição, nova mensagem, cadastro recusado sem envio, e `create_superadmin` sem envio
- [x] 2.6 Rodar `make test` com a suíte inteira passando, incluindo o teste de texto da interface
- [x] 2.7 Commit

## 3. Ambiente

- [ ] 3.1 Acrescentar o serviço `worker` ao `compose.yaml`, com as variáveis compartilhadas por âncora e `DJANGO_SITE_URL` (D9)
- [ ] 3.2 Atualizar o README com o worker, os logs dos e-mails, o reinício após alterar o código e as novas variáveis
- [ ] 3.3 Subir o ambiente com `make up`, cadastrar um usuário pela interface, conferir o e-mail em `make logs` e definir a senha pelo link recebido
- [ ] 3.4 Commit

## 4. Verificação

- [ ] 4.1 Validar a Change com `openspec validate enviar-emails-por-outbox --strict`
