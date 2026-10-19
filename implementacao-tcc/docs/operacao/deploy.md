# Deploy

**Situação: o sistema ainda não foi implantado.** Não existe instalação de homologação ou de produção, pipeline de CI/CD nem rotina de backup. O TCC (princípio P12) deixa a implantação definitiva com a direção do campus e os setores envolvidos, e a hospedagem não está definida.

O repositório já entrega uma imagem Docker autossuficiente, que roda em qualquer host com Docker (VPS, servidor do campus, PaaS que aceite imagem). Este documento descreve essa imagem, o que a instalação precisa fornecer e o que continua pendente.

## A imagem

O `Dockerfile` tem três estágios:

| Estágio | Função |
|---|---|
| `tailwind` | Node com as dependências do `package.json`. Também usado pelo container `tailwind` do desenvolvimento |
| `css` | Copia o código e gera `ui/static/ui/css/app.css` minificado |
| final | `python:3.13-slim` com o `requirements.txt`, o código, o CSS gerado e o `collectstatic` em `/app/staticfiles`. Roda como o usuário `app` (uid `APP_UID`, padrão 1000) |

- Comando padrão: `daphne --bind 0.0.0.0 --port 8000 --proxy-headers config.asgi:application` (HTTP e WebSocket das notificações).
- Os estáticos são servidos pelo próprio processo, com o WhiteNoise (comprimidos em gzip). Não é preciso proxy para eles, mas um proxy pode servi-los de `/app/staticfiles` se preferir.
- O `.dockerignore` deixa fora da imagem `.env`, `.git`, `node_modules`, `docs/` e `sources/`. Os testes não dependem de `sources/`: as planilhas que usam estão copiadas em `schedule/tests/fixtures/`.
- O `collectstatic` roda no build com valores fictícios só para importar as configurações; nenhum segredo entra na imagem.
- No desenvolvimento, o `compose.yaml` continua montando o código por volume e trocando o comando por `runserver`.

Construir:

```bash
docker build -t ifagenda .
```

## Processos de uma instalação

A mesma imagem roda os três processos, mudando só o comando:

| Processo | Comando | Observação |
|---|---|---|
| web | padrão da imagem | Porta 8000, atrás do proxy |
| worker | `python manage.py process_outbox` | Sem ele, os links de senha não saem |
| import_worker | `python manage.py process_imports` | Sem ele, as importações ficam em processamento |

Os três precisam das mesmas variáveis e reiniciam sempre (`restart: unless-stopped` ou equivalente). Também são necessários um PostgreSQL 15 ou superior e, recomendado, um Redis com senha.

## Variáveis

O modelo está em `.env.example`; a descrição de cada uma, em [configuração](configuracao.md). Em produção:

- `DJANGO_SECRET_KEY`, `DJANGO_CREDENTIALS_KEY`, `POSTGRES_PASSWORD` e `REDIS_PASSWORD` próprios. Gere com `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `DJANGO_DEBUG` vazio, `DJANGO_ALLOWED_HOSTS` com os nomes reais e `DJANGO_SITE_URL` com `https://`.
- `DJANGO_ENVIRONMENT` e `DJANGO_LOCAL_DATABASE` ausentes, e o banco sem a marca `ifagenda.environment`.
- `DJANGO_CREDENTIALS_KEY` estável: trocá-la invalida a senha SMTP gravada.

O `.env.example` traz valores de produção (`DJANGO_DEBUG` vazio, SMTP). Para o desenvolvimento, use `DJANGO_DEBUG=1`, o backend de console e as variáveis locais descritas em [configuração](configuracao.md).

## Conferência antes de implantar

```bash
docker run --rm --env-file .env ifagenda python manage.py check --deploy
```

Além das conferências do Django, recusa os segredos e a senha do Redis padrão do `compose.yaml`. Os avisos `security.W004` (HSTS) e `security.W008` (redirecionamento HTTPS) são esperados enquanto o proxy não estiver definido.

Conferido em 19/10/2026: a imagem constrói, o `check --deploy` passa só com esses avisos e o Daphne serve `/static/ui/css/app.css` com `DEBUG` desligado.

## Passos depois de subir uma instância

```bash
python manage.py migrate              # cria o catálogo de permissões e os perfis iniciais
python manage.py create_superadmin    # primeiro acesso, sem perfil
```

1. Entrar com o superadmin em `/contas/login/`.
2. Cadastrar o servidor SMTP em **Configurações > E-mail**, com `DJANGO_EMAIL_BACKEND` em SMTP.
3. Conferir `DJANGO_SITE_URL`, que monta os links dos e-mails.
4. Importar o ensalamento do semestre com o período definido.

## Atualizações

- Reconstruir a imagem, rodar `migrate` e reiniciar os três processos: os workers não recarregam o código.
- Depois de um módulo novo com permissões novas, o superadmin as concede aos perfis pela tela de perfis.

## Requisitos que dependem da hospedagem

| Tema | O que o código exige |
|---|---|
| Banco | PostgreSQL 15 ou superior (usa `nulls_distinct`), com permissão para `CREATE EXTENSION btree_gist` na primeira migration de `bookings` |
| Redis | Sem `DJANGO_REDIS_URL`, as telas públicas ficam sem cache, os limites de tentativa valem por processo e as notificações do `import_worker` não chegam ao sino em tempo real (`notices.W001`). Com ele, senha e rede privada |
| Proxy reverso | Termina o TLS, sobrescreve `X-Forwarded-For` e `X-Forwarded-Proto`, repassa o WebSocket (`Upgrade`), limita o corpo das requisições, aplica rate limit em `/`, `/horario-original/` e `/contas/*` e não guarda as páginas públicas em cache. Com ele definido, declare `DJANGO_TRUSTED_PROXY_COUNT` e `DJANGO_TRUSTED_PROXY_SSL_HEADER` e, servindo só HTTPS, ligue HSTS |
| Mídia | Nenhuma: o sistema não grava arquivos enviados |
| Logs | Tudo no `stdout`; quem coleta e guarda não está definido |
| Backup | Nenhuma rotina; deve cobrir o banco PostgreSQL |

## Instruções de desenvolvimento que não valem para produção

| Instrução | Motivo |
|---|---|
| `make up`, `make dev-network` e o `compose.yaml` | Montam o código por volume, rodam `runserver` com `DEBUG=1` e usam segredos padrão |
| `DJANGO_ENVIRONMENT=local`, `DJANGO_LOCAL_DATABASE` e `make mark-local-db` | Juntos, liberam os comandos destrutivos |
| `make clear-data`, `make delete-users`, `make set-passwords`, `make reset-db` | Apagam dados ou trocam todas as senhas |

## Pendente

A escolha da hospedagem, do proxy, da coleta de logs e da rotina de backup, e um arquivo de orquestração de produção (compose ou equivalente) para o destino escolhido. Nada disso foi feito porque o sistema ainda não foi implantado.
