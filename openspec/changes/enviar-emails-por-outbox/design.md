## Context

Hoje o `UserCreateView` chama `User.objects.register`, que grava o usuário numa transação própria (o projeto não usa `ATOMIC_REQUESTS`). Em seguida, ele agenda no `transaction.on_commit` a função `accounts.adapters.send_password_link(request, email)`, que:
- consome o limite de tentativas `reset_password` do allauth, por IP e por e-mail;
- chama `ResetPasswordForm.save(request)`, que gera o token, monta o link a partir do host da requisição e envia o e-mail.

Quando o envio falha, a tela mostra um aviso, conforme o cenário "Falha no envio do e-mail de criação" da spec `autenticacao`. `send_password_link` só é usada pelo `UserCreateView`. "Esqueci minha senha" usa as views do allauth diretamente.

Verificado no allauth 65.19 instalado:
- `DefaultAccountAdapter.send_mail` chama `get_current_site(request)`, que falha sem `request` porque `django.contrib.sites` não está instalado;
- `DefaultAccountAdapter.render_mail(template_prefix, email, context)` funciona sem `request`;
- o link é `reverse('account_reset_password_from_key', kwargs={'uidb36': uid, 'key': token})`, com `uid = user_pk_to_url_str(user)` e o token do gerador configurado em `ACCOUNT_PASSWORD_RESET_TOKEN_GENERATOR` (`accounts.tokens.PasswordResetTokenGenerator`).

Decisões fechadas com o autor antes da proposal:
- guardar a intenção (tipo e referência), e nunca o token;
- no máximo um envio pendente por tipo e referência;
- 5 tentativas com intervalos crescentes, configuráveis;
- `FALHOU` final;
- sem interface nova;
- "Esqueci minha senha" continua síncrono.

## Goals / Non-Goals

**Goals:**

- Gravar a intenção de envio na transação da operação, para que a prévia da importação possa desfazê-la.
- Enviar fora da requisição, com novas tentativas.
- Manter o link idêntico ao da recuperação de senha, sem gravar token.
- Um mecanismo reaproveitável pelo RF09 e pelo RF10.

**Non-Goals:**

- Painel, reenvio manual, limpeza de envios antigos e envio da recuperação pública pelo outbox.
- Celery, Redis ou agendador externo.

## Decisions

### D1. App `outbox` e model `OutboxEntry`

```text
OutboxEntry
  kind            CharField(30)                 'LINK_SENHA'
  reference       CharField(64)                 chave do objeto, em texto
  status          CharField(choices)            A_ENVIAR | ENVIADO | DESCARTADO | FALHOU
  attempts        PositiveSmallIntegerField(0)
  next_attempt_at DateTimeField(default=now)
  last_error      TextField(blank=True)         até 500 caracteres
  created_at      DateTimeField(auto_now_add)
  sent_at         DateTimeField(null=True)
  UniqueConstraint(kind, reference, condition=status='A_ENVIAR', name='outbox_entry_pending_unique')
  Index(status, next_attempt_at)
```

O app `outbox` depende só do Django e nunca importa `accounts`. A referência é texto porque o outbox não conhece o tipo da chave de cada model.

Alternativa considerada: **`GenericForeignKey`**. Traria `contenttypes` para um dado que só o tratador precisa interpretar.

### D2. Registro do envio

`outbox.enqueue(kind, reference)` grava com `OutboxEntry.objects.bulk_create([...], ignore_conflicts=True)`. No PostgreSQL, isso gera `ON CONFLICT DO NOTHING`, que respeita o índice único parcial. Com isso, um envio `A_ENVIAR` existente não é duplicado nem tem as tentativas reiniciadas. A função não abre transação: ela participa da transação de quem chama, e é por isso que o rollback da operação desfaz o envio.

Alternativa considerada: **`transaction.on_commit`**, como hoje. O Django descarta os callbacks de um savepoint desfeito, então a prévia não enviaria nada. Mas o envio continuaria acontecendo dentro da requisição, sem novas tentativas, e a intenção se perderia se o processo caísse entre o commit e o envio.

### D3. Registro central de tratadores

`outbox.handlers.register(kind, handler)` guarda num dicionário do módulo. O tratador é uma função `handler(reference)` que devolve uma `EmailMessage` pronta para enviar, ou `None` quando o envio não faz mais sentido. Cada app registra os seus tratadores no `AppConfig.ready`. Registrar duas vezes o mesmo tipo com funções diferentes é erro de programação e lança `ImproperlyConfigured`.

Diferente do motor de importação, aqui o registro é necessário: o worker só conhece o tipo gravado.

### D4. Worker

Comando `python manage.py process_outbox [--once]`:

```text
enquanto não receber SIGTERM/SIGINT:
    processados = 0
    repetir até OUTBOX_BATCH_SIZE:
        atomic:
            entry = A_ENVIAR com next_attempt_at <= agora, ordem (next_attempt_at, pk),
                    select_for_update(skip_locked=True), primeira
            se não houver: sai do lote
            processa(entry)          ← tratador, envio e gravação do resultado
        processados += 1
    se --once: termina
    se processados == 0: espera OUTBOX_POLL_INTERVAL
```

- **Uma transação por envio:** a trava dura só o envio de um e-mail, e uma queda afeta um registro só.
- **`skip_locked`:** dois workers nunca processam o mesmo envio.
- **Sem estado "processando":** se o processo cair depois do envio SMTP e antes do commit, a trava é liberada, o registro continua `A_ENVIAR` e o e-mail pode sair de novo (entrega pelo menos uma vez).
- **Parada:** SIGTERM e SIGINT param o laço entre um envio e outro, para que o `docker compose down` não interrompa um envio no meio.
- **Log:** o logger é `outbox`. Registra `FALHOU` com o erro e cada falha temporária em nível `WARNING`.

`processa(entry)`:
1. procura o tratador do tipo. Sem tratador, o registro fica `FALHOU` imediatamente;
2. chama o tratador. Com `None`, fica `DESCARTADO`;
3. `message.send()`. Com sucesso, fica `ENVIADO` e `sent_at = agora`;
4. qualquer exceção nos passos 2 e 3: `attempts += 1` e `last_error = f'{type}: {mensagem}'[:500]`. Se `attempts >= OUTBOX_MAX_ATTEMPTS`, fica `FALHOU`. Senão, `next_attempt_at = agora + intervalo[attempts - 1]`, repetindo o último intervalo.

Alternativas consideradas:
- **Celery com Redis:** duas dependências e um container a mais para um volume de dezenas de e-mails por semestre.
- **Travar o lote inteiro numa transação:** reduz consultas, mas um envio lento seguraria as travas de todo o lote.

### D5. Configuração

Lidas de variáveis de ambiente no `settings.py`, com os padrões iniciais:

| Setting | Variável | Padrão |
|---|---|---|
| `SITE_URL` | `DJANGO_SITE_URL` | `http://localhost:8000` |
| `OUTBOX_MAX_ATTEMPTS` | `DJANGO_OUTBOX_MAX_ATTEMPTS` | `5` |
| `OUTBOX_RETRY_DELAYS` | `DJANGO_OUTBOX_RETRY_DELAYS` | `60,300,900,3600` (segundos) |
| `OUTBOX_POLL_INTERVAL` | `DJANGO_OUTBOX_POLL_INTERVAL` | `5` (segundos) |
| `OUTBOX_BATCH_SIZE` | `DJANGO_OUTBOX_BATCH_SIZE` | `20` |

Esses valores são um ponto de partida, e não regra: podem ser ajustados por ambiente sem mudar o código.

### D6. Tratador `LINK_SENHA`

Em `accounts/emails.py`, registrado em `AccountsConfig.ready`:

```text
password_link(reference):
    user = User.objects.filter(pk=reference).first()
    se user é None, inativo ou has_usable_password(): devolve None
    token = default_token_generator do allauth .make_token(user)
    path  = reverse('account_reset_password_from_key', uidb36=user_pk_to_url_str(user), key=token)
    url   = settings.SITE_URL sem a barra final + path
    devolve get_adapter().render_mail('account/email/password_reset_key', user.email,
                                      {'user': user, 'password_reset_url': url})
```

- Usa os mesmos templates `password_reset_key_subject.txt` e `password_reset_key_message.txt`, o mesmo prefixo de assunto e o mesmo remetente da recuperação.
- O token é o do gerador configurado. Por isso a validade de 3 dias, o uso único, a invalidação pela troca de e-mail e a recusa de usuário inativo continuam valendo, e a validade conta a partir do envio.
- Não chama `ratelimit.consume`, então o limite da recuperação pública não é afetado.
- `has_usable_password()` verdadeiro significa que o usuário já definiu a senha, e o link de "definir senha" não faz mais sentido.

Alternativas consideradas:
- **`ResetPasswordForm.save(None)`:** exige `request` para a URL e o site.
- **Instalar `django.contrib.sites`:** acrescenta um model e uma configuração guardada no banco só para obter o domínio, que já vem melhor de uma variável de ambiente.

### D7. Registro no `register`

`UserManager.register` chama `enqueue(PASSWORD_LINK, user.pk)` dentro da própria transação, depois de gravar o usuário e o vínculo com o perfil. Enviar o link a quem é cadastrado é regra da spec `autenticacao`, e a convenção põe regra de negócio no model. Com isso:
- o cadastro pela tela e a importação de usuários registram o envio sem código repetido;
- dentro da prévia da importação, o envio fica no mesmo savepoint do usuário e é desfeito junto;
- `create_superadmin` não passa por `register` e não registra envio, porque o superadmin é criado já com senha.

A constante `PASSWORD_LINK = 'LINK_SENHA'` fica em `accounts/emails.py`.

Alternativa considerada: **registrar na view**, embrulhando `register` e `enqueue` numa transação. A importação teria que repetir a mesma chamada.

### D8. Cadastro pela tela

- `UserCreateView.perform` passa a só chamar `register` e mostrar "Usuário X cadastrado. O link para definir a senha será enviado para X."
- Saem o `on_commit`, o método `send_password_link` da view e as mensagens de envio e de falha.
- `accounts.adapters.send_password_link` é removida, porque não tem mais uso.

### D9. Container `worker`

No `compose.yaml`, um serviço `worker` com `build: .`, o mesmo volume de código e as mesmas variáveis do `web` (as variáveis passam para uma âncora YAML compartilhada), `command: python manage.py process_outbox` e `depends_on: db: condition: service_healthy`. Não expõe porta. O `make up` já o inicia, e `make logs` mostra os e-mails do backend de console. O README ganha uma linha sobre o worker e a variável `DJANGO_SITE_URL`.

O worker não recarrega o código sozinho como o `runserver`. Depois de alterar um tratador, é preciso `docker compose restart worker`, e isso fica documentado no README.

### D10. Efeito na Change `importar-usuarios-por-planilha`

Com a D7, a importação de usuários não chama o outbox diretamente: `register` já registra o envio. A D12 daquela Change é ajustada nesta mesma Change para refletir isso.

## Risks / Trade-offs

- **[E-mail repetido]** Uma queda entre o SMTP e o commit reenvia o e-mail. → Aceito para o link de senha, porque os dois links funcionam até um ser usado. Fica documentado para os próximos tipos.
- **[Worker parado sem aviso]** Os envios se acumulam em `A_ENVIAR`. → O `restart` do Compose e o log. Um alerta fica para a hospedagem definitiva.
- **[Transação aberta durante o SMTP]** Uma conexão lenta segura a trava de um envio. → Uma transação por envio. O servidor SMTP tem o timeout do Django.
- **[Aviso de falha perdido na tela]** O administrador deixa de ver na hora que o e-mail não saiu. → Novas tentativas e o "Esqueci minha senha". O selo e o reenvio ficam como evolução.
- **[Worker com código antigo]** Sem recarga automática. → Instrução no README.
- **[`register` com efeito colateral]** Todo usuário criado por `register` passa a ter um envio. → É o comportamento exigido pela spec. Testes que usam `register` só ganham um registro a mais no outbox.

## Migration Plan

1. `make up` reconstrói e sobe o `worker`. `make migrate` cria a tabela do outbox.
2. Usuários cadastrados antes da Change não são afetados. Quem não recebeu o link usa "Esqueci minha senha".
3. Rollback: reverter o código e a migration `outbox.0001`. Envios `A_ENVIAR` não enviados se perdem, e os usuários afetados usam "Esqueci minha senha".

## Open Questions

Nenhuma. Os valores de D5 podem ser ajustados por ambiente.
