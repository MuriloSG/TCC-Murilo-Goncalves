# Deploy

O repositório contém só o ambiente de desenvolvimento em Docker Compose: não há configuração de produção, pipeline de CI/CD, rotina de backup nem infraestrutura de hospedagem. Isso não prova que esses recursos não existam fora do repositório. O TCC (princípio P12) deixa a implantação definitiva com a direção do campus e os setores envolvidos, e a hospedagem não está definida.

Este documento lista o que o código exige de qualquer instalação. Valores de produção, hosts, credenciais e políticas de backup não estão no repositório e não são sugeridos aqui.

## O que existe

| Item | Situação |
|---|---|
| Imagem da aplicação | `Dockerfile` com `python:3.13-slim` e as dependências do `requirements.txt`. Instala as dependências como root e roda como o usuário `app` (uid `APP_UID`, padrão 1000, sem shell nem sudo). O código é só lido; a escrita fica em `/tmp` (upload grande) e no home do usuário. Num host Linux cujo usuário não tenha uid 1000, construa com `--build-arg APP_UID=$(id -u)` para `makemigrations` conseguir gravar no repositório. O container `tailwind` continua como root: é ferramenta de desenvolvimento e não roda a aplicação. Não copia o código: depende do volume `.:/app` do `compose.yaml` |
| Servidor | `python manage.py runserver 0.0.0.0:8000` (Daphne via `runserver`, por causa do Channels) |
| Workers | `process_outbox` e `process_imports`, com `restart: unless-stopped` |
| Redis | `redis:8-alpine` sem senha, sem persistência, 64 MB, `allkeys-lru`, sem porta publicada |
| CSS | Gerado pelo container `tailwind` em modo watch, ou uma vez com `make css`. O arquivo gerado fica fora do Git |
| CI | Nenhum (não há `.github/`, `.gitlab-ci.yml` ou equivalente) |

## Requisitos conhecidos de uma instalação de produção

| Tema | O que o código exige ou deixa em aberto |
|---|---|
| `DEBUG` | `DJANGO_DEBUG` diferente de `1`. Com `DEBUG` desligado, `ALLOWED_HOSTS` vazio recusa todas as requisições |
| `SECRET_KEY` | `DJANGO_SECRET_KEY` própria; sem ela a aplicação não inicia. O padrão do `compose.yaml` é inseguro |
| `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` com os nomes reais da instalação |
| Identificação | `DJANGO_ENVIRONMENT` e `DJANGO_LOCAL_DATABASE` ausentes, e o banco sem a marca `ifagenda.environment`, para que `flush`, `clear_data`, `delete_users` e `set_passwords` sejam recusados |
| Banco | PostgreSQL 15 ou superior (usa `nulls_distinct`), com permissão para `CREATE EXTENSION btree_gist` na primeira migration de `bookings`. Variáveis `POSTGRES_*` |
| Cifra | `DJANGO_CREDENTIALS_KEY` estável: trocá-la invalida a senha SMTP gravada |
| Servidor ASGI | O WebSocket das notificações exige ASGI (`config.asgi.application`). `daphne` já está nas dependências; não há comando de produção definido |
| Workers | `process_outbox` e `process_imports` rodando o tempo todo |
| Redis | Opcional: sem `DJANGO_REDIS_URL` as telas públicas funcionam sem cache. Com ele, senha e rede privada |
| Estáticos | Sem `STATIC_ROOT` e sem `collectstatic`. Com `DEBUG` desligado o Django não serve `ui/static/`; o CSS precisa ser gerado (`make css`) antes. Quem serve os estáticos não está definido |
| Mídia | Nenhuma: o sistema não grava arquivos enviados |
| HTTPS e cookies | `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS` e HSTS não estão em `settings.py`. Ajustá-los exige alterar o settings, o que depende do proxy escolhido |
| Proxy reverso | Fora do repositório. Deve aplicar o rate limit de `/` e `/horario-original/` (convenção da seção 4) e não guardar essas páginas com cache próprio, que ignoraria a invalidação da aplicação |
| Vários processos web | `InMemoryChannelLayer` e o `LocMemCache` dos limites do allauth são por processo. Com mais de um processo, o sino só atualiza ao recarregar e os limites de tentativa não são compartilhados |
| Logs | Sem `LOGGING`; ver [configuração](configuracao.md#não-configurado-no-repositório) |
| Backup | Não há rotina no repositório |

## Instruções de desenvolvimento que não valem para produção

| Instrução | Motivo |
|---|---|
| `make up`, `make dev-network` e o `compose.yaml` | Montam o código por volume, rodam `runserver` com `DEBUG=1` e usam segredos padrão |
| `DJANGO_ENVIRONMENT=local` e `DJANGO_LOCAL_DATABASE` no `.env`, e `make mark-local-db` | Juntos, liberam os comandos destrutivos |
| `make clear-data`, `make delete-users`, `make set-passwords` | Apagam dados ou trocam todas as senhas; recusados fora de `local` |
| `make reset-db` | `docker compose down -v` apaga o volume do PostgreSQL do projeto Compose |
| `DJANGO_EMAIL_BACKEND` de console e servidor SMTP `localhost` | Os e-mails só aparecem nos logs |
| `sources/` | Planilhas de referência e logotipos, sem uso em execução |

## Passos depois de subir uma instância

Confirmados pelo código, valem para qualquer instalação:

```bash
python manage.py migrate              # cria o catálogo de permissões e os perfis do sistema
python manage.py create_superadmin    # primeiro acesso
```

1. Entrar com o superadmin em `/contas/login/`.
2. Cadastrar o servidor SMTP em **Configurações > E-mail** e definir `DJANGO_EMAIL_BACKEND` como SMTP. Sem isso nenhum e-mail sai e os links de senha ficam retidos.
3. Conferir `DJANGO_SITE_URL`, que monta os links dos e-mails.
4. Manter os dois workers rodando. Sem o `worker`, os links de senha não saem; sem o `import_worker`, as importações ficam em processamento.
5. Importar o ensalamento do semestre com o período definido.

## Atualizações

- `migrate` depois de cada atualização; nada roda sozinho.
- Reiniciar `worker` e `import_worker` depois de alterar o código: eles não recarregam.
- Depois de um módulo novo com permissões novas, o superadmin revisa os perfis personalizados, que não as recebem.

## Pendente

A escolha da hospedagem, do servidor ASGI, do proxy, de quem serve os estáticos e da rotina de backup. Com ela definida, os itens da tabela de requisitos viram configuração concreta.
