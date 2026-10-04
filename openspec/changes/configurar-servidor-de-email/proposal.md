## Why

As credenciais do servidor de e-mail ficam hoje em variáveis de ambiente (`DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_DEFAULT_FROM_EMAIL`), lidas uma vez na subida do processo. Trocar a conta, a senha de app ou o servidor exige acesso ao servidor, edição do ambiente e reinício do `web` e do `worker`. A administração do campus não tem como fazer isso pelo sistema, e uma senha de app expirada deixa todos os envios do outbox consumindo tentativas até ficarem `FALHOU`.

Esta Change cria um mecanismo de configurações do sistema guardadas no banco, validadas por tipo, e o usa primeiro para o servidor SMTP, com a senha cifrada e uma tela restrita por permissão. O worker do outbox passa a ler a configuração a cada lote e não tenta enviar quando ela falta ou é inválida, sem consumir tentativas.

## What Changes

- **Capability nova `configuracoes-sistema`**, com o app `system_settings`: model `SystemSetting` com o tipo (`TextChoices`, chave estável `smtp`), o valor em `JSONField` validado pelo esquema do tipo, datas de criação e alteração e um único registro por tipo. A configuração é global: o sistema atende a um único campus, sem tenants nem organizações.
- **Configuração SMTP**: servidor, porta, segurança (`STARTTLS`, `SSL` ou `NENHUMA`), usuário, senha e remetente. A senha é cifrada com Fernet (biblioteca `cryptography`, já presente na imagem e agora declarada no `requirements.txt`), com uma chave própria vinda do ambiente (`DJANGO_CREDENTIALS_KEY`), e nunca é exibida, registrada no log nem na auditoria.
- **Permissão `CONFIGURACAO.EDITAR`**, concedida ao perfil `ADMINISTRADOR` pela migration que a acrescenta, e menu "Configurações" com a página "Servidor de e-mail", que mostra o estado e abre o formulário em modal.
- **Worker do outbox** lê a configuração SMTP a cada lote. Sem configuração, ou com configuração inválida, não processa nenhum envio: os envios ficam `A_ENVIAR`, sem tentativa consumida, e o log registra o motivo uma vez por mudança de estado. Com a configuração válida, os e-mails saem com as credenciais e o remetente gravados. Falhas do servidor SMTP seguem a política de tentativas que já existe.
- **"Esqueci minha senha"** (síncrono pelo allauth) passa a usar a mesma configuração. Sem ela, o e-mail não é enviado, o log registra o motivo e a resposta da página continua a mesma.
- **BREAKING (ambiente)**: saem as variáveis `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS` e `DJANGO_DEFAULT_FROM_EMAIL`. O banco é a única fonte das credenciais e do remetente. `DJANGO_EMAIL_BACKEND` continua escolhendo o transporte (console no desenvolvimento, SMTP em produção, memória nos testes).

### Fora do escopo

- Outros tipos de configuração além de `smtp`. O modelo os comporta, mas cada um entra pela Change que o usa, com o próprio esquema.
- Botão de "enviar e-mail de teste", histórico de versões da configuração e rotação da chave de cifra.
- Reprocessamento de envios que já estão `FALHOU`, que continua final.

## Capabilities

### New Capabilities
- `configuracoes-sistema`: configurações do sistema persistidas por tipo, a configuração SMTP, a cifra da senha e a tela de gestão.

### Modified Capabilities
- `envio-emails`: o worker depende da configuração SMTP persistida e não processa envios sem ela; a recuperação de senha pública usa a mesma configuração.

## Impact

- Novo app `system_settings` (model, migration, formulário, views, URLs e templates).
- `accounts`: permissão no catálogo e migration de dados; o adaptador do allauth envia pela configuração.
- `outbox/worker.py` e o comando `process_outbox`.
- `audit/catalog.py`: módulo `CONFIGURACAO` e rótulos dos campos.
- `ui/navigation.py`: item "Configurações".
- `config/settings.py`, `compose.yaml`, `README.md` e `requirements.txt`.
