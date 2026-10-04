## Context

O envio de e-mails segue a Change `enviar-emails-por-outbox`:

| Peça | Onde | Comportamento atual |
|---|---|---|
| Registro do envio | `OutboxEntry.objects.enqueue`, chamado por `UserManager.register` | grava `kind` e `reference` na transação da operação, sem conteúdo |
| Estados | `OutboxEntry.Status` | `A_ENVIAR`, `ENVIADO`, `DESCARTADO`, `FALHOU` (final) |
| Tratadores | `outbox.handlers`, registrados no `AppConfig.ready` | `LINK_SENHA` monta o e-mail com `get_adapter().render_mail` |
| Worker | `outbox.worker` e o comando `process_outbox` (container `worker`) | lote de `OUTBOX_BATCH_SIZE`, `select_for_update(skip_locked=True)`, `message.send()` pela conexão padrão |
| Falhas | `OutboxEntry.register_failure` | tentativa +1, próximo intervalo de `OUTBOX_RETRY_DELAYS`, `FALHOU` ao atingir `OUTBOX_MAX_ATTEMPTS` |
| Credenciais | `config/settings.py` | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` e `DEFAULT_FROM_EMAIL`, do ambiente |
| Recuperação pública | views do allauth | envio síncrono na requisição, pela conexão padrão |

Não existe mecanismo de configuração dinâmica nem de segredos no projeto. A biblioteca `cryptography` 50.0.1 já está instalada na imagem como dependência indireta. O sistema atende a um único campus: não há tenant, organização nem outro contexto isolado em nenhum model.

## Goals / Non-Goals

**Goals:**
- Credenciais SMTP alteráveis pela interface, por quem tem permissão, sem reiniciar processos.
- Senha recuperável para o SMTP, mas nunca em texto puro no banco nem exposta.
- Nenhum envio perdido nem tentativa consumida enquanto o SMTP não estiver configurado.

**Non-Goals:**
- Configurações arbitrárias sem esquema, cofre de segredos externo e rotação de chave.

## Decisions

### D1. Um model genérico com esquema por tipo
`SystemSetting(kind, value, created_at, updated_at)`, com `kind` em `TextChoices` (`smtp`) e `unique=True`. O valor é `JSONField`, e cada tipo tem uma classe que conhece o esquema, valida e converte (`SmtpSettings`). `SystemSetting.clean()` recusa chaves fora do esquema do tipo. Um tipo novo é uma escolha nova e uma classe nova, sem tabela nova.
*Alternativa:* uma tabela por integração. Recusada pelo pedido de extensibilidade.

### D2. Escopo global
Não há tenant nem organização no sistema, então existe no máximo uma configuração por tipo, garantida pelo `unique` de `kind`. O isolamento entre contextos não se aplica; o acesso é controlado só pela permissão (D6).

### D3. Senha cifrada com Fernet e chave própria
A senha é gravada como token Fernet (AES-128-CBC com HMAC-SHA256) em `value['password']`. A chave vem de `DJANGO_CREDENTIALS_KEY`, transformada em chave Fernet pelo SHA-256, para não depender da `SECRET_KEY`: trocar a `SECRET_KEY` (que invalida sessões) não deve tornar as credenciais ilegíveis. Hash irreversível não serve, porque o SMTP exige a senha. Um token que não decifra (chave trocada) torna a configuração inválida (D5), e a tela pede uma senha nova.
*Alternativa:* derivar da `SECRET_KEY`. Recusada pelo acoplamento citado.

### D4. Regras da configuração SMTP
- Servidor obrigatório; porta entre 1 e 65535; remetente obrigatório e e-mail válido (aceita `Nome <endereco>`).
- Segurança é uma escolha única entre `STARTTLS`, `SSL` e `NENHUMA`, o que impede combinar TLS e SSL.
- Usuário e senha andam juntos: ou os dois, ou nenhum (relay sem autenticação).
- Credenciais com segurança `NENHUMA` são recusadas, para a senha não trafegar sem cifra.
- Na atualização, senha em branco mantém a gravada. Sem usuário, a senha gravada é apagada.
- Timeout fixo de 30 segundos na conexão, para que um servidor lento não segure a trava de um envio.

### D5. Worker sem configuração não processa
`process_batch` carrega a configuração antes de travar qualquer envio. Ausente ou inválida, lança `SmtpUnavailable` sem tocar nos envios: eles continuam `A_ENVIAR`, sem tentativa consumida e sem mudar `next_attempt_at`. O comando registra o motivo no log (`warning`) só quando ele muda, e espera o intervalo normal; quando a configuração passa a valer, o próximo ciclo envia os pendentes na ordem de sempre. Assim não há ciclo de falhas nem descarte.
*Alternativas:* contar como falha temporária (esgotaria as tentativas e levaria a `FALHOU`, que é final) ou um estado novo (exigiria migração de estado e reprocessamento). Recusadas.
Falhas do servidor SMTP (autenticação, conexão, recusa) continuam pela política de tentativas existente. O erro gravado em `last_error` é o da exceção do `smtplib`, que não contém a senha.

### D6. Configuração lida a cada lote
O worker carrega a configuração no início de cada lote e entrega ao envio uma conexão criada com `get_connection(backend=settings.EMAIL_BACKEND, host=..., ...)`. Uma alteração vale a partir do lote seguinte, sem reiniciar o container. O remetente da configuração substitui o `from_email` montado pelo tratador.

### D7. Uma única fonte para as credenciais
As variáveis `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS` e `DJANGO_DEFAULT_FROM_EMAIL` saem do `settings.py`, do `compose.yaml` e do `README.md`. Regra de precedência: credenciais e remetente vêm só do banco; o transporte (`DJANGO_EMAIL_BACKEND`) vem só do ambiente. Com o backend de console, o desenvolvimento continua sem SMTP real, mas exige a configuração cadastrada para o worker imprimir os e-mails.

### D8. Recuperação de senha pública
`AccountAdapter.send_mail` passa a enviar pela mesma configuração. Sem configuração válida, o e-mail não sai, o log registra o motivo, e a página responde como sempre, sem revelar o estado do servidor a quem não está autenticado.

### D9. Permissão, tela e auditoria
`CONFIGURACAO.EDITAR` libera a página e o formulário, concedida ao `ADMINISTRADOR` pela migration, como as demais. A página `configuracoes/email/` mostra o estado (selo "Configurado" ou "Não configurado"), os dados sem a senha (só "Definida" ou "Não definida") e quantos envios aguardam. O formulário abre em modal (`OperationFormView`), com a senha em `PasswordInput` sem `render_value`. A auditoria registra `CRIAR` ou `ALTERAR` no módulo `CONFIGURACAO`, com os campos visíveis e `credencial` como "alterada" ou "mantida", nunca o valor (a chave não pode conter "senha", que o `sanitize` da auditoria descarta).

### D10. Referência visual
A tela não teve imagem de referência nesta Change. Ela reaproveita só componentes existentes (`page-head`, `card`, `detail-grid`, `badge`, modal do formulário), no mesmo arranjo da página de detalhe do perfil. Fica registrado como pendência a conferência com uma referência do autor (seção 9.8 das convenções).

## Risks / Trade-offs

- **[Implantação sem configuração]** Ao atualizar, as variáveis de ambiente deixam de valer e os e-mails ficam parados até o cadastro na tela. → Nenhum envio é perdido (D5); o README orienta cadastrar a configuração logo após a migration.
- **[Perda da chave]** Sem `DJANGO_CREDENTIALS_KEY` correta, a senha não decifra. → A configuração fica inválida e o worker para sem consumir tentativas; basta informar a senha de novo.
- **[Chave no ambiente]** Quem lê o ambiente e o banco decifra a senha. → Mesmo nível de proteção da `SECRET_KEY`; o banco sozinho não basta.
- **[Envio pelo ADMINISTRADOR]** Quem tem a permissão pode apontar o remetente para outro servidor. → A alteração é auditada; o superadmin pode retirar a permissão do perfil.
