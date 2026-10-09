# E-mails e servidor SMTP

Implementação: apps `outbox` (fila e worker) e `system_settings` (configuração do servidor), mais `accounts/emails.py` e `accounts/adapters.py`.

## E-mails enviados

| E-mail | Quando | Caminho |
|---|---|---|
| Link para definir a senha (`LINK_SENHA`) | Cadastro de usuário pela tela, pela importação de usuários ou pela aba de usuários do ensalamento | Outbox, enviado pelo `worker` |
| Link de recuperação de senha (`REDEFINIR_SENHA`) | "Esqueci minha senha" | Outbox, enviado pelo `worker`; o link é gerado no envio |

As notificações do sistema não geram e-mail.

## Servidor SMTP

Configurado na interface, em **Configurações > E-mail** (`/configuracoes/email/`), com `CONFIGURACAO.EDITAR`. Model: `SystemSetting` com `kind = SMTP`, uma linha só, valor JSON validado por `SmtpSettings`.

| Campo | Regra |
|---|---|
| Servidor | Obrigatório |
| Porta | 1 a 65535 (padrão do formulário: 587) |
| Segurança | `STARTTLS`, `SSL` ou `NENHUMA` (padrão: STARTTLS). Com usuário, `NENHUMA` é recusada |
| Usuário e senha | Os dois juntos ou nenhum. Senha em branco na edição mantém a gravada só se servidor, porta, segurança e usuário não mudarem; mudando qualquer um deles, a senha precisa ser informada de novo, para a gravada nunca ir a outro destino. Sem usuário, a senha gravada é apagada |
| Remetente | E-mail válido, aceito no formato `IFAgenda <agenda@ifnmg.edu.br>` |

- A senha é cifrada com Fernet, com chave derivada (SHA-256) de `DJANGO_CREDENTIALS_KEY`, e nunca é exibida. Trocar a variável torna a senha gravada ilegível, e a configuração passa a ser inválida até a senha ser informada de novo.
- A auditoria registra os campos visíveis e só se a credencial foi alterada ou mantida.
- A conexão usa o backend de `DJANGO_EMAIL_BACKEND` com as credenciais daqui (`SmtpSettings.connection`). Com o backend padrão de console, os e-mails aparecem nos logs (`make logs`), mas a configuração SMTP continua obrigatória para que saiam.
- A configuração é lida a cada lote do worker e a cada envio do `web`: alterar não exige reiniciar containers.
- Excluir a configuração (`/configuracoes/email/excluir/`) retém os envios pendentes.

## Outbox

`OutboxEntry` guarda só a intenção: tipo, referência (o ID do usuário), situação, tentativas, próxima tentativa e último erro. O conteúdo é montado no envio pelo tratador do tipo (`outbox/handlers.py`), com os dados atuais; nenhum token ou link fica no banco.

- `OutboxEntry.objects.enqueue(kind, reference)` grava na transação de quem chama. Se a operação for desfeita, inclusive na prévia de uma importação, o envio também é.
- Um envio pendente do mesmo tipo e referência não é duplicado (índice único parcial `outbox_entry_pending_unique`).
- O worker (`process_outbox`) processa lotes de `OUTBOX_BATCH_SIZE`, cada envio na própria transação com `select_for_update(skip_locked=True)`. Sem envio vencido, espera `OUTBOX_POLL_INTERVAL`.
- Falha: soma a tentativa e agenda a próxima pelos intervalos de `OUTBOX_RETRY_DELAYS` (o último se repete). No limite de `OUTBOX_MAX_ATTEMPTS`, vai a `FALHOU` e registra a falha na auditoria e no log.
- O tratador devolve `None` quando o envio não faz mais sentido (usuário excluído, inativo ou que já definiu a senha), e o envio é `DESCARTADO`.
- Sem servidor configurado ou com configuração inválida, o lote não toca nos envios: eles ficam `A_ENVIAR` sem gastar tentativa, e o motivo vai ao log quando muda.
- Entrega pelo menos uma vez: se o processo cair depois do envio e antes do commit, o e-mail pode sair de novo.
- `SIGTERM` e `SIGINT` param o laço entre um envio e outro. `--once` processa um lote e termina.

## Testes

`outbox/tests/test_queue.py`, `test_worker.py`; `system_settings/tests/test_models.py`, `test_views.py`; `accounts/tests/test_emails.py`.
