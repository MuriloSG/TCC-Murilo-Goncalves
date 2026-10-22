# Requisitos de deploy e de envio de e-mails

O que uma hospedagem precisa oferecer para rodar o IFAgenda, o que é preciso para os e-mails saírem e o passo a passo no Railway. A imagem e os processos estão em [deploy](deploy.md); as variáveis, em [configuração](configuracao.md); o funcionamento do envio, em [e-mails](../funcionalidades/emails.md).

## Requisitos da hospedagem

| # | Requisito | Por quê |
|---|---|---|
| 1 | Build de imagem pelo `Dockerfile` | A imagem sai completa, com o CSS e os estáticos |
| 2 | Processo `web` (Daphne, porta 8000) | HTTP e WebSocket na mesma porta |
| 3 | WebSocket repassado pelo proxy | Notificações em tempo real no sino |
| 4 | Processo `worker` sempre ligado (`python manage.py process_outbox`) | Sem ele, nenhum e-mail sai |
| 5 | Processo `import_worker` sempre ligado (`python manage.py process_imports`) | Sem ele, as importações ficam em processamento |
| 6 | PostgreSQL 15 ou superior | Usa `nulls_distinct` |
| 7 | Extensão `btree_gist` | Criada pela primeira migration de `bookings` (restrição de conflito de horários) |
| 8 | Redis com senha, em rede privada | Cache público, limites de tentativa e notificações do `import_worker`. Sem ele, o sistema roda sem essas funções (`notices.W001`) |
| 9 | Rede privada entre aplicação, banco e Redis | Banco e Redis não ficam expostos |
| 10 | HTTPS com proxy reverso | O proxy termina o TLS e envia `X-Forwarded-For` e `X-Forwarded-Proto` |
| 11 | Variáveis de ambiente com segredos | `DJANGO_SECRET_KEY`, `DJANGO_CREDENTIALS_KEY`, senhas do banco e do Redis |
| 12 | `migrate` a cada atualização | Cria o catálogo de permissões e os perfis iniciais |
| 13 | Shell interativo | `create_superadmin` pede a senha no terminal; `check --deploy` |
| 14 | Processos 24h, sem hibernar | Os workers consultam as filas continuamente |
| 15 | Coleta dos logs do `stdout` | Todos os logs vão para o `stdout` |
| 16 | Backup do PostgreSQL | O banco é o único estado do sistema |
| 17 | Saída de rede para o servidor SMTP | Ver [requisitos dos e-mails](#requisitos-dos-e-mails) |

Não é preciso armazenamento de arquivos: o sistema não grava mídia.

## Requisitos dos e-mails

O sistema envia dois e-mails: o link para definir a senha de um usuário novo e o link de recuperação de senha. Sem eles, um usuário cadastrado não consegue entrar.

| # | Requisito | Onde |
|---|---|---|
| 1 | Conta num servidor SMTP (e-mail institucional, Gmail, Brevo, Amazon SES etc.) | Externo |
| 2 | Saída liberada para a porta do servidor (587 com STARTTLS ou 465 com SSL) | Hospedagem |
| 3 | `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` | Variável de ambiente. O padrão é o console, que só escreve nos logs |
| 4 | `DJANGO_SITE_URL` com o endereço público | Variável de ambiente. Sem ela, os links apontam para `localhost` |
| 5 | `DJANGO_CREDENTIALS_KEY` estável | Variável de ambiente. Cifra a senha SMTP; trocá-la exige informar a senha de novo |
| 6 | Servidor, porta, segurança, usuário, senha e remetente cadastrados | Interface, **Configurações > E-mail**, com `CONFIGURACAO.EDITAR` |
| 7 | Processo `worker` rodando | Hospedagem. Os e-mails ficam na fila até ele enviar |

Sem o item 6, nenhum e-mail sai, nem para o console: os envios ficam `A_ENVIAR` sem gastar tentativas e saem quando o servidor for cadastrado.

### Escolha do servidor SMTP

| Servidor | Configuração | Observação |
|---|---|---|
| Gmail ou Google Workspace | `smtp.gmail.com`, 587, STARTTLS | Exige verificação em duas etapas e uma senha de app no lugar da senha da conta. Limite diário de envios da conta |
| E-mail institucional | Dados fornecidos pela TI do campus | Remetente com o domínio `ifnmg.edu.br`, menor chance de cair no spam |
| Serviço transacional (Brevo, Amazon SES, Mailgun) | Host e credenciais SMTP do serviço | Exige verificar o domínio ou o remetente no serviço |

- O remetente pode ter nome: `IFAgenda <agenda@ifnmg.edu.br>`.
- O domínio do remetente precisa autorizar o servidor de envio (SPF e DKIM). Sem isso, os e-mails tendem a cair no spam.

## Railway

Conferido em 22/10/2026 na [documentação do Railway](https://docs.railway.com) e, no caso do PostgreSQL, rodando a imagem do template (`ghcr.io/railwayapp-templates/postgres-ssl:17`): PostgreSQL 17.11, `btree_gist` 1.7 disponível, usuário `postgres` superusuário e `CREATE EXTENSION btree_gist` executado sem erro.

### Atendimento dos requisitos

| Requisito | Railway | Como |
|---|---|---|
| Build pelo `Dockerfile` | Sim | Usa o `Dockerfile` sempre que encontra um no diretório raiz do serviço |
| `web`, `worker`, `import_worker` | Sim | Três serviços do mesmo repositório, cada um com o seu start command |
| WebSocket | Sim | HTTP/1.1, sem limite de inatividade para conexões WebSocket |
| PostgreSQL 15+ | Sim | Template oficial, PostgreSQL 17, sobre a imagem oficial do Docker Hub |
| `btree_gist` | Sim | Incluída na imagem; o usuário do template é superusuário |
| Redis com senha | Sim | Template oficial; expõe `REDIS_URL` com a senha |
| Rede privada | Sim | Bancos são privados por padrão; acesso pelos nomes `*.railway.internal` |
| HTTPS e proxy | Sim | Domínio `*.up.railway.app` com TLS, ou domínio próprio |
| Variáveis e segredos | Sim | Com referência entre serviços (`${{Postgres.PGHOST}}`) |
| `migrate` a cada deploy | Sim | Pre-deploy command, executado entre o build e o deploy, com as variáveis e a rede privada |
| Shell interativo | Sim | `railway ssh` |
| Processos 24h | Sim | Cobrança por uso |
| Logs | Sim | Painel por serviço |
| Backup do PostgreSQL | Sim | Aba **Backups** do volume: diário (mantido 6 dias), semanal (27 dias) ou mensal (89 dias), e backup manual |
| Saída SMTP | Só no plano Pro | Nos planos Free, Trial e Hobby o SMTP é bloqueado ([outbound networking](https://docs.railway.com/reference/outbound-networking)) |

Plano para homologação com e-mails: **Pro**. No Hobby, todo o resto funciona e os e-mails aparecem nos logs do `worker` com o backend de console.

### Passo a passo

#### 1. Preparar

1. Ter o repositório no GitHub e uma conta no Railway ligada ao GitHub.
2. Gerar dois segredos, um para `DJANGO_SECRET_KEY` e outro para `DJANGO_CREDENTIALS_KEY`:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   Guarde o segundo: trocá-lo depois invalida a senha SMTP gravada.

#### 2. Criar o projeto e o serviço `web`

1. **New Project > Deploy from GitHub repo** e escolha o repositório. O serviço criado será o `web`; renomeie-o em **Settings**.
2. Em **Settings > Source > Root Directory**, informe `/implementacao-tcc`.
3. Ainda em **Settings**, deixe o start command vazio: vale o `CMD` da imagem (Daphne na porta 8000).
4. Em **Settings > Networking > Public Networking**, clique em **Generate Domain** e informe a porta **8000**. Anote o domínio gerado (`<app>.up.railway.app`).

O primeiro build falha por falta de variáveis; isso se resolve no passo 4.

#### 3. Adicionar o banco e o Redis

1. No canvas do projeto, **+ New > Database > PostgreSQL**. O nome do serviço deve ser `Postgres`.
2. **+ New > Database > Redis**. O nome do serviço deve ser `Redis`.

Os nomes importam: são eles que aparecem nas referências `${{Postgres...}}` e `${{Redis...}}`.

#### 4. Variáveis do `web`

Em **Variables > Raw Editor** do `web`, cole e troque `<app>` e os segredos:

```
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
DJANGO_REDIS_URL=${{Redis.REDIS_URL}}
DJANGO_SECRET_KEY=<segredo 1>
DJANGO_CREDENTIALS_KEY=<segredo 2>
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=<app>.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://<app>.up.railway.app
DJANGO_SITE_URL=https://<app>.up.railway.app
DJANGO_TRUSTED_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO
DJANGO_TRUSTED_PROXY_COUNT=1
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_LOG_LEVEL=INFO
DJANGO_CACHE_KEY_PREFIX=ifagenda
```

- No plano Hobby, use `DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`.
- Não defina `DJANGO_ENVIRONMENT` nem `DJANGO_LOCAL_DATABASE`: liberam comandos destrutivos.
- O projeto lê o banco por variáveis separadas, e não por `DATABASE_URL`.

#### 5. Migrations a cada deploy

No `web`, em **Settings > Deploy**, defina o **Pre-deploy Command**:

```
python manage.py migrate
```

Só no `web`: os workers não rodam o `migrate`, para não haver duas migrações ao mesmo tempo. Se o comando falhar, o deploy não acontece e a versão anterior continua no ar.

#### 6. Serviços `worker` e `import_worker`

Para cada um:

1. **+ New > GitHub Repo**, o mesmo repositório. Renomeie para `worker` ou `import_worker`.
2. **Settings > Source > Root Directory**: `/implementacao-tcc`.
3. **Settings > Deploy > Custom Start Command**:
   - `worker`: `python manage.py process_outbox`
   - `import_worker`: `python manage.py process_imports`
4. **Settings > Deploy > Restart Policy**: **Always**.
5. Sem domínio público.
6. **Variables > Raw Editor**: as mesmas variáveis do passo 4.

#### 7. Primeiro deploy

1. Clique em **Deploy** nos serviços com alterações pendentes.
2. Nos logs do `web`, confira o `migrate` do pre-deploy e a linha do Daphne escutando em `0.0.0.0:8000`.
3. Nos logs dos workers, confira a mensagem de worker iniciado (loggers `outbox` e `imports`).

#### 8. Conferência e primeiro acesso

Com o [Railway CLI](https://docs.railway.com/guides/cli) instalado e logado:

```bash
railway link                                   # escolha o projeto e o serviço web
railway ssh
python manage.py check --deploy                # só os avisos security.W004 e W008 são esperados
python manage.py create_superadmin             # pede e-mail, nome e senha
```

Depois, em `https://<app>.up.railway.app/contas/login/`, entre com o superadmin.

#### 9. E-mail

1. Em **Configurações > E-mail**, cadastre o servidor SMTP ([escolha do servidor](#escolha-do-servidor-smtp)).
2. Use "Esqueci minha senha" com um usuário existente.
3. Confira nos logs do `worker` se o envio saiu ou qual falha ocorreu.

#### 10. Backup

No serviço `Postgres`, aba **Backups**, ative o agendamento diário. Backups só podem ser restaurados no mesmo projeto e ambiente, e apagar o volume apaga os backups.

#### 11. Ensalamento

Importe o ensalamento do semestre, com o período definido, como nos [passos depois de subir uma instância](deploy.md#passos-depois-de-subir-uma-instância).

### Atualizações

Um push no branch configurado reconstrói os três serviços. O `web` roda o `migrate` antes de subir; os workers sobem com o código novo, porque cada deploy recria o container. Para não reconstruir tudo a cada mudança só em `docs/`, configure em **Settings > Source > Watch Paths** de cada serviço `/implementacao-tcc/**` e `!/implementacao-tcc/docs/**`.
