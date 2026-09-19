## Why

O cadastro de usuário envia o link de definição de senha durante a própria requisição, no `on_commit`, usando o `request` para o limite de tentativas e para montar o link. Isso não serve para a importação de usuários (Change `importar-usuarios-por-planilha`): a prévia precisa executar o cadastro e desfazê-lo sem enviar nada, e uma importação de dezenas de usuários faria a requisição esperar dezenas de envios SMTP, esbarrando no limite de tentativas. As notificações automáticas do RF09 e do RF10 terão a mesma necessidade. Esta Change cria um outbox: a intenção de envio é gravada na mesma transação da operação e um worker faz o envio depois.

## What Changes

- **App `outbox`**, genérico:
  - registro de um envio (tipo e referência) na transação corrente, com no máximo um envio `A_ENVIAR` por tipo e referência;
  - registro central de tratadores por tipo, que montam o e-mail no momento do envio;
  - estados `A_ENVIAR`, `ENVIADO`, `DESCARTADO` e `FALHOU`, com novas tentativas em intervalos crescentes e quantidade máxima definidas em configuração;
  - comando `process_outbox`, que processa os envios em laço ou em um único ciclo (`--once`).
- **Tipo `LINK_SENHA`** em `accounts`: o worker gera o token e o link no envio, pela mesma rota e o mesmo gerador da recuperação de senha, com a URL base configurada, e usa os templates de e-mail atuais. Usuário inexistente, inativo ou que já definiu a senha leva ao descarte.
- **BREAKING (comportamento)** Cadastro pela tela: o envio do link passa a ser registrado no outbox na mesma transação do cadastro. A mensagem passa a informar que o link será enviado, e o aviso de falha de envio na tela deixa de existir.
- **Serviço `worker`** no Docker Compose, iniciado com o ambiente.
- **Variável `DJANGO_SITE_URL`** para a URL base dos links enviados fora de uma requisição.

### Fora do escopo

- "Esqueci minha senha", que continua síncrono, com o limite de tentativas do allauth.
- Notificações do RF09 e do RF10.
- Interface de administração dos envios, reenvio de registros `FALHOU`, selo "Link não enviado" e ação de reenviar na lista de usuários.
- Limpeza de envios antigos.
- Celery, Redis ou outro sistema de filas.

## Capabilities

### New Capabilities
- `envio-emails`: outbox dos e-mails disparados pelo sistema, com registro na transação, tratadores por tipo, worker, novas tentativas, estados e descarte.

### Modified Capabilities
- `autenticacao`: a criação inicial da senha passa a ter o link enviado pelo outbox; o aviso imediato de falha de envio no cadastro é substituído pelas novas tentativas e pela recuperação de senha.
- `ambiente-desenvolvimento`: o ambiente ganha o container `worker`, e a URL base passa a ser configurada por variável de ambiente.

## Impact

- **App novo:** `outbox`, com model, migration, registro de tratadores e comando `process_outbox`.
- **`accounts`:** tratador `LINK_SENHA`, registro no `AppConfig.ready`, `UserCreateView` sem `on_commit` e sem mensagens de falha, remoção de `send_password_link`.
- **Ambiente:** serviço `worker` no `compose.yaml`, `DJANGO_SITE_URL` e as configurações do outbox no `settings.py`, README.
- **Testes:** outbox, worker, tratador, cadastro pela tela (mensagens mudam) e texto da interface.
- **Dependências:** nenhuma nova.

## Alinhamento com o TCC

- **RF04 e RNF02:** o link continua gerado pelo fluxo do allauth, com validade de 3 dias e uso único, e nenhum token é gravado.
- **RF09 e RF10:** o outbox é a base das notificações automáticas por e-mail.
- **P3:** a fila fica no PostgreSQL, pelo ORM, sem dependência externa.
- **P10:** o envio não depende de serviço externo além do SMTP já previsto no TCC.
