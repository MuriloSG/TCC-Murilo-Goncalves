# IFAgenda

**Sistema de Agendamento de Espaços do IFNMG – Campus Salinas**

Sistema web para agendamento de espaços físicos do IFNMG – Campus Salinas, desenvolvido com Django e PostgreSQL como Trabalho de Conclusão de Curso do Bacharelado em Sistemas de Informação.

A documentação do sistema (funcionalidades, regras, arquitetura, operação e decisões) está em [`docs/`](docs/README.md). Este arquivo cobre o ambiente de desenvolvimento.

Todo o ambiente roda em Docker. Não é preciso instalar Python, Node.js nem PostgreSQL na máquina.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) com Docker Compose v2 (comando `docker compose`)
- `make`
  - **macOS:** vem com as Command Line Tools do Xcode (`xcode-select --install`).
  - **Linux:** normalmente já está instalado; no Debian e no Ubuntu, pacote `make`.
  - **Windows:** use o WSL. Sem `make`, execute diretamente os comandos Docker Compose da tabela de comandos.

## Primeira execução

Na raiz do projeto:

```bash
make up                                # constrói as imagens, sobe os containers e gera o CSS
make migrate                           # aplica as migrations e cria os perfis e as permissões
make manage cmd="create_superadmin"    # cria o primeiro superadmin (pede e-mail, nome e senha)
```

Depois:

- `http://localhost:8000/` abre o calendário público, sem login.
- `http://localhost:8000/contas/login/` é a entrada do sistema, com o e-mail e a senha do superadmin.
- Cadastre um servidor de e-mail em **Configurações > E-mail** (veja [E-mails no desenvolvimento](#e-mails-no-desenvolvimento)). Sem isso nenhum e-mail sai, nem nos logs.

Para conceder ou retirar o superadmin de um usuário existente: `make manage cmd="set_superadmin maria@ifnmg.edu.br --grant"` (ou `--revoke`).

## Comandos

| Comando | Equivalente Docker Compose | O que faz |
|---|---|---|
| `make` ou `make help` | — | Lista os comandos disponíveis |
| `make up` | `docker compose up -d --build --renew-anon-volumes` | Sobe o ambiente em segundo plano, reconstruindo as imagens e reinstalando as dependências de Node.js se necessário |
| `make dev-network` | `DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,<IP>" DJANGO_SITE_URL="http://<IP>:8000" docker compose up -d --build --renew-anon-volumes` | Sobe o ambiente aceitando acessos de outros aparelhos da mesma rede local |
| `make down` | `docker compose down` | Para e remove os containers; os dados do banco são mantidos |
| `make logs` | `docker compose logs -f` | Acompanha os logs dos containers |
| `make migrate` | `docker compose run --rm web python manage.py migrate` | Aplica as migrations pendentes |
| `make makemigrations` | `docker compose run --rm web python manage.py makemigrations` | Gera migrations a partir das alterações nos models |
| `make test` | `docker compose run --rm web python manage.py test` | Executa a suíte de testes |
| `make shell` | `docker compose run --rm web python manage.py shell` | Abre o shell do Django |
| `make manage cmd="<comando>"` | `docker compose run --rm web python manage.py <comando>` | Executa qualquer outro comando do `manage.py` |
| `make css` | `docker compose run --rm tailwind npx @tailwindcss/cli -i ui/styles/app.css -o ui/static/ui/css/app.css --minify` | Gera o CSS da interface minificado |
| `make npm cmd="<comando>"` | `docker compose run --rm tailwind npm <comando>` | Executa um comando do npm no container `tailwind` |
| `make psql` | `docker compose up -d --wait db` e depois `docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'` | Abre o `psql` no banco de dados |
| `make reset-db` | `docker compose down -v` | **Apaga todos os dados do banco** e remove os containers |
| `make mark-local-db` | `ALTER DATABASE "$POSTGRES_DB" SET ifagenda.environment = 'local'` no container `db` | Marca o banco de desenvolvimento como local, condição dos comandos destrutivos. Rodar uma vez, e de novo depois de `make reset-db` |
| `make clear-data` | `docker compose run --rm web python manage.py clear_data` | **Apaga todos os dados**, inclusive a auditoria, mantendo usuários, perfis e permissões |
| `make delete-users` | `docker compose run --rm web python manage.py delete_users` | **Exclui os usuários que não são superadmin** e os registros que dependem deles |
| `make set-passwords` | `docker compose run --rm web python manage.py set_passwords` | Define a mesma senha de desenvolvimento (`DEFAULT_PASSWORD` em `set_passwords.py`) para todos os usuários, inclusive superadmins |

- Os comandos baseados em `run --rm` funcionam com o ambiente parado ou em execução. O Compose sobe o banco quando necessário e remove o container do comando ao final.
- As migrations não são aplicadas automaticamente na subida do ambiente. Execute `make migrate` sempre que houver migrations novas.
- Os testes rodam num banco de testes criado no próprio PostgreSQL e removido ao final. Detalhes em [docs/desenvolvimento/testes.md](docs/desenvolvimento/testes.md).
- `clear-data`, `delete-users` e `set-passwords` (e `make manage cmd="flush"`) só rodam com `DJANGO_ENVIRONMENT=local` e `DJANGO_LOCAL_DATABASE=db:5432/agendamento` no `.env` e com o banco marcado uma vez por `make mark-local-db`, e pedem confirmação. Sem isso, são recusados antes de qualquer pergunta ou escrita. Não defina essas variáveis nem grave a marca em nenhuma instalação que não seja a máquina de desenvolvimento. Ver [configuração](docs/operacao/configuracao.md#identificação-da-instalação-e-do-banco-local).
- O `make up` usa `--renew-anon-volumes` porque as dependências de Node.js ficam num volume anônimo do container `tailwind`. Sem a opção, o Compose reaproveitaria o volume antigo, e um `package-lock.json` alterado não chegaria ao container.

## Serviços

| Serviço | Imagem | Função |
|---|---|---|
| `web` | construída a partir do `Dockerfile` (Python 3.13) | Aplicação Django com o servidor de desenvolvimento na porta 8000 |
| `worker` | a mesma do `web` | Envia os e-mails registrados no outbox (`process_outbox`) |
| `import_worker` | a mesma do `web` | Executa a prévia, a atualização da prévia e a confirmação das importações (`process_imports`) |
| `db` | `postgres:17` | Banco de dados PostgreSQL, sem porta publicada no host |
| `redis` | `redis:8-alpine` | Cache das telas públicas e camada do Channels, sem porta publicada no host e sem gravar em disco |
| `tailwind` | estágio `tailwind` do `Dockerfile` (Node.js 22) | Compila o CSS da interface e o recompila a cada alteração |

- O código é montado em `/app`. O `web` recarrega sozinho ao alterar o código; o `worker` e o `import_worker` não. Depois de alterar o código de e-mails ou de importações, rode `docker compose restart worker` ou `docker compose restart import_worker`.
- O `worker` e o `import_worker` reiniciam sozinhos se encerrarem, por exemplo quando sobem antes do `make migrate`.
- `web`, `worker` e `import_worker` só iniciam depois que o healthcheck do `db` indica que o banco está pronto. A aplicação não espera o `redis`: sem ele, as telas públicas consultam o banco e os avisos do sino falham (ficam no log) até ele voltar.
- Os dados do PostgreSQL ficam no volume `postgres_data`, que `make down` preserva e `make reset-db` remove.
- O `tailwind` grava `ui/static/ui/css/app.css`, que fica fora do Git. Uma classe nova num template aparece no CSS sem reiniciar containers. As dependências de Node.js ficam num volume anônimo em `/app/node_modules`; a imagem do `web` não tem Node.js.

## Variáveis de ambiente

| Variável | Valor padrão | Uso |
|---|---|---|
| `DJANGO_SECRET_KEY` | `django-insecure-somente-para-desenvolvimento-local` | Chave secreta do Django |
| `DJANGO_DEBUG` | `1` | Modo de depuração, ativo somente com o valor `1` |
| `DJANGO_ENVIRONMENT` | vazio | Declara a instalação. Só o valor exato `local`, junto com `DJANGO_LOCAL_DATABASE` e a marca no banco, libera `flush`, `clear_data`, `delete_users` e `set_passwords`; vazio ou qualquer outro valor os recusa |
| `DJANGO_LOCAL_DATABASE` | vazio | Banco local esperado, em `host:porta/nome` (`db:5432/agendamento`). Precisa ser igual ao banco configurado para liberar os comandos destrutivos |
| `DJANGO_ALLOWED_HOSTS` | vazio | Hosts aceitos, separados por vírgula; vazio com `DJANGO_DEBUG=1` aceita apenas `localhost` e `127.0.0.1` |
| `DJANGO_SITE_URL` | `http://localhost:8000` | Endereço usado nos links dos e-mails enviados pelo `worker` |
| `POSTGRES_DB` | `agendamento` | Nome do banco de dados |
| `POSTGRES_USER` | `agendamento` | Usuário do banco de dados |
| `POSTGRES_PASSWORD` | `agendamento` | Senha do banco de dados |
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Forma de envio dos e-mails |
| `DJANGO_CREDENTIALS_KEY` | `chave-de-credenciais-somente-para-desenvolvimento-local` | Cifra as senhas guardadas no banco, como a do servidor de e-mail. Trocá-la exige informar essas senhas de novo |
| `DJANGO_REDIS_URL` | `redis://:<REDIS_PASSWORD>@redis:6379/0` | Conexão dos limites de tentativa, do cache das telas públicas e da camada do Channels. Vazia, as telas públicas funcionam sem cache, os limites ficam por processo e a camada fica em memória, com o aviso `notices.W001` |
| `REDIS_PASSWORD` | senha só para desenvolvimento | Senha do container `redis`, usada na URL padrão |
| `DJANGO_REDIS_TIMEOUT` | `0.1` | Tempo limite, em segundos, de conexão e de leitura dos caches e de conexão da camada do Channels |
| `DJANGO_CACHE_KEY_PREFIX` | `ifagenda` | Prefixo das chaves do cache; a camada do Channels usa `<prefixo>:channels`. Ambientes que dividem um Redis usam prefixos diferentes |
| `DJANGO_OUTBOX_MAX_ATTEMPTS` | `5` | Tentativas de envio de um e-mail antes de desistir |
| `DJANGO_OUTBOX_RETRY_DELAYS` | `60,300,900,3600` | Intervalos, em segundos, entre as tentativas. O último se repete |
| `DJANGO_OUTBOX_POLL_INTERVAL` | `5` | Segundos que o `worker` espera quando não há e-mail para enviar |
| `DJANGO_OUTBOX_BATCH_SIZE` | `20` | E-mails enviados pelo `worker` a cada ciclo |
| `DJANGO_IMPORT_MAX_ROWS` | `1000` | Linhas de dados aceitas numa importação, quando a importação não define limite próprio (o ensalamento aceita 5000) |
| `DJANGO_IMPORT_MAX_FILE_SIZE` | `1048576` | Tamanho máximo, em bytes, do arquivo, quando a importação não define limite próprio (o ensalamento aceita 10 MiB) |
| `DJANGO_IMPORT_MAX_ATTEMPTS` | `3` | Tentativas de uma operação de importação com erro inesperado antes de desistir |
| `DJANGO_IMPORT_RETRY_DELAYS` | `30,120` | Intervalos, em segundos, entre as tentativas. O último se repete |
| `DJANGO_IMPORT_POLL_INTERVAL` | `2` | Segundos que o `import_worker` espera quando não há operação pendente |
| `DJANGO_IMPORT_STATUS_POLL_SECONDS` | `3` | Intervalo, em segundos, da consulta do andamento feita pelo detalhe da importação |
| `DJANGO_IMPORT_LOCK_TIMEOUT` | `60` | Segundos que uma operação espera por uma trava. Não limita a duração da importação |
| `DJANGO_IMPORT_STALE_AFTER` | `60` | Segundos depois do pedido a partir dos quais o detalhe mostra o aviso de demora |

`POSTGRES_HOST` (`db`) e `POSTGRES_PORT` (`5432`) são fixadas no `compose.yaml`. As variáveis do outbox e da importação não estão no `compose.yaml`: sem elas, valem os padrões da tabela.

Para sobrescrever um valor, crie um arquivo `.env` na raiz do projeto, ignorado pelo Git, e recrie os containers com `make up`:

```dotenv
DJANGO_SECRET_KEY=outra-chave-local
DJANGO_ENVIRONMENT=local
DJANGO_LOCAL_DATABASE=db:5432/agendamento
```

- O PostgreSQL só lê `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` ao criar o banco. Se alterá-las depois da primeira execução, rode `make reset-db`.
- Sem uma variável obrigatória, a aplicação não inicia e o erro indica o nome da variável.

> **Atenção:** os valores padrão são inseguros e servem apenas ao desenvolvimento local. Não os reutilize em nenhum ambiente acessível externamente. Ver [docs/operacao/configuracao.md](docs/operacao/configuracao.md).

## E-mails no desenvolvimento

O backend padrão é o de console: as mensagens aparecem em `make logs`. Mesmo assim, o servidor de e-mail precisa estar cadastrado em **Configurações > E-mail**; sem ele, nenhum e-mail sai e os envios do outbox ficam retidos. Para ver os e-mails nos logs, cadastre qualquer servidor (por exemplo `localhost`, porta `25`, segurança "Nenhuma", sem usuário).

Para enviar de verdade, por exemplo pelo Gmail, defina no `.env` o backend SMTP e cadastre na tela o servidor `smtp.gmail.com`, a porta `587`, a segurança STARTTLS, a conta e uma senha de app:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

Os dois links de senha, o do usuário cadastrado e o de "Esqueci minha senha", saem pelo `worker` em alguns segundos. Detalhes em [docs/funcionalidades/emails.md](docs/funcionalidades/emails.md).

## Acesso pelo celular na rede local

```bash
make dev-network
```

O comando descobre o IPv4 do computador na rede local, sobe o ambiente aceitando esse endereço em `DJANGO_ALLOWED_HOSTS` e mostra a URL para o celular, como `http://192.168.0.10:8000/`. O celular precisa estar no mesmo Wi-Fi. Pare o ambiente com `make down`.

- Se o IPv4 não for detectado, descubra-o com `ipconfig getifaddr en0` no macOS ou `hostname -I` no Linux e informe-o: `make dev-network LOCAL_IP=192.168.0.10`.
- Firewall, VPN ativa ou redes que isolam os aparelhos (Wi-Fi de visitantes) podem impedir a conexão.
- O comando não publica o sistema na internet e não expõe o banco de dados.

## Dependências

As dependências Python ficam no `requirements.txt`, com versões fixas, e são instaladas na construção da imagem. Para adicionar ou atualizar uma:

1. Edite o `requirements.txt`, fixando a versão com `==`.
2. Execute `make up` para reconstruir a imagem e recriar os containers.

As dependências de Node.js servem só para compilar o CSS. Ficam no `package.json`, com versões exatas, travadas no `package-lock.json`, e são instaladas na construção da imagem do `tailwind`:

```bash
make npm cmd="install --save-exact pacote@1.2.3"
make up
```

## Permissões de arquivos em hosts Linux

A imagem da aplicação roda como o usuário `app`, com uid 1000 (`APP_UID` no `Dockerfile`), e o container `tailwind` como o usuário `node`, também com uid 1000. Num host Linux cujo usuário tenha outro uid, os arquivos gravados pelo container no repositório, como migrations geradas com `makemigrations`, falham por permissão. Reconstrua a imagem com o seu uid:

```bash
docker compose build --build-arg APP_UID="$(id -u)" web
```

No macOS e no Windows com Docker Desktop, isso não é necessário.

## Organização do repositório

Apps Django: `accounts`, `ui`, `audit`, `outbox`, `system_settings`, `notices`, `imports`, `schedule`, `bookings`, `panel`, `reports` e `tutorials`. A configuração fica em `config/`, a documentação em `docs/` e o texto do TCC com as planilhas de referência em `sources/`. Detalhes em [docs/arquitetura/estrutura-do-projeto.md](docs/arquitetura/estrutura-do-projeto.md).

As convenções de código estão em [docs/desenvolvimento/convencoes.md](docs/desenvolvimento/convencoes.md).
