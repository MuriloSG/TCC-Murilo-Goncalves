# Sistema de Agendamento de Espaços Físicos – IFNMG Campus Salinas

Sistema web para agendamento de espaços físicos do IFNMG – Campus Salinas, desenvolvido com Django e PostgreSQL como Trabalho de Conclusão de Curso do Bacharelado em Sistemas de Informação.

Todo o ambiente de desenvolvimento roda em Docker. Não é preciso instalar Python nem PostgreSQL na máquina.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) com Docker Compose v2 (comando `docker compose`)
- `make`
  - **macOS:** vem com as Command Line Tools do Xcode (`xcode-select --install`).
  - **Linux:** normalmente já está instalado; no Debian e no Ubuntu, pacote `make`.
  - **Windows:** use o WSL. Sem `make`, execute diretamente os comandos Docker Compose da tabela de comandos.

## Primeira execução

Depois de clonar o repositório, na raiz do projeto:

```bash
make up                                # constrói a imagem e sobe os containers
make migrate                           # aplica as migrations no PostgreSQL
make manage cmd="create_superadmin"    # cria o primeiro superadmin
```

Depois disso, entre em <http://localhost:8000/contas/login/> com o e-mail e a senha do superadmin. A raiz `/` ainda responde 404: ela está reservada para a consulta pública de disponibilidade.

## Superadmin

O superadmin tem acesso irrestrito e é o único que configura os perfis. Ele não é um perfil nem uma permissão, mas uma característica do usuário, e só é controlado pelos comandos abaixo, nunca pela interface.

**Criar o primeiro superadmin:**

```bash
make manage cmd="create_superadmin"
```

O comando pede o e-mail, o nome e a senha, duas vezes e sem exibi-la. A senha passa pela mesma política da interface. O usuário é criado ativo, com o perfil `ADMINISTRADOR`, sem depender do envio de e-mail. O comando recusa um e-mail já cadastrado: nesse caso, use o `set_superadmin`.

**Conceder ou remover o superadmin de um usuário existente:**

```bash
make manage cmd="set_superadmin maria@ifnmg.edu.br --grant"
make manage cmd="set_superadmin maria@ifnmg.edu.br --revoke"
```

A remoção é recusada se deixar o sistema sem nenhum usuário ativo com capacidade administrativa, isto é, sem superadmin ativo nem usuário cujo perfil conceda todas as permissões de `USUARIO`.

## Usuários e perfis

- Os perfis do sistema, `ADMINISTRADOR` e `DOCENTE`, são criados pelas migrations e não podem ser excluídos.
- Usuários são cadastrados pela interface, em **Usuários**, por quem tem a permissão. O novo usuário recebe por e-mail um link para definir a própria senha. Ninguém define a senha de outra pessoa.
- Qualquer usuário ativo recupera o acesso em **Esqueci minha senha**, na página de login. O link vale por 3 dias e pode ser usado uma única vez.
- Só o superadmin acessa **Perfis**, onde cria perfis personalizados e define as permissões de cada um. Um perfil novo não concede nenhuma permissão até que ele as escolha.
- **Depois de cada módulo novo**, o superadmin deve revisar os perfis personalizados: as permissões novas chegam apenas aos perfis do sistema, conforme a configuração padrão do módulo.

## Comandos

| Comando | Equivalente Docker Compose | O que faz |
|---|---|---|
| `make` ou `make help` | — | Lista os comandos disponíveis |
| `make up` | `docker compose up -d --build` | Sobe o ambiente em segundo plano, reconstruindo a imagem se necessário |
| `make down` | `docker compose down` | Para e remove os containers; os dados do banco são mantidos |
| `make logs` | `docker compose logs -f` | Acompanha os logs dos containers |
| `make migrate` | `docker compose run --rm web python manage.py migrate` | Aplica as migrations pendentes |
| `make makemigrations` | `docker compose run --rm web python manage.py makemigrations` | Gera migrations a partir das alterações nos models |
| `make test` | `docker compose run --rm web python manage.py test` | Executa a suíte de testes |
| `make shell` | `docker compose run --rm web python manage.py shell` | Abre o shell do Django |
| `make manage cmd="<comando>"` | `docker compose run --rm web python manage.py <comando>` | Executa qualquer outro comando do `manage.py` |
| `make psql` | `docker compose up -d --wait db` e depois `docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'` | Abre o `psql` no banco de dados |
| `make reset-db` | `docker compose down -v` | **Apaga todos os dados do banco** e remove os containers |

- Os comandos baseados em `run --rm` funcionam com o ambiente parado ou em execução. O Compose sobe o banco quando necessário e remove o container do comando ao final.
- As migrations não são aplicadas automaticamente na subida do ambiente. Execute `make migrate` sempre que houver migrations novas.
- Os testes rodam em um banco de testes criado temporariamente no próprio PostgreSQL e removido ao final da execução.

## Serviços

| Serviço | Imagem | Função |
|---|---|---|
| `web` | construída a partir do `Dockerfile` (Python 3.13) | Aplicação Django com o servidor de desenvolvimento na porta 8000 |
| `db` | `postgres:17` | Banco de dados PostgreSQL, sem porta publicada no host |

- O código do projeto é montado em `/app` no container `web`. Alterações feitas na máquina recarregam o servidor automaticamente, e arquivos gerados no container, como migrations, aparecem no repositório.
- Os dados do PostgreSQL ficam no volume `postgres_data`, que `make down` preserva e `make reset-db` remove.
- O `web` só é iniciado depois que o healthcheck do `db` indica que o banco está pronto para receber conexões.

## Variáveis de ambiente

| Variável | Valor padrão | Uso |
|---|---|---|
| `DJANGO_SECRET_KEY` | `django-insecure-somente-para-desenvolvimento-local` | Chave secreta do Django |
| `DJANGO_DEBUG` | `1` | Modo de depuração, ativo somente com o valor `1` |
| `POSTGRES_DB` | `agendamento` | Nome do banco de dados |
| `POSTGRES_USER` | `agendamento` | Usuário do banco de dados |
| `POSTGRES_PASSWORD` | `agendamento` | Senha do banco de dados |
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Forma de envio dos e-mails |
| `DJANGO_DEFAULT_FROM_EMAIL` | `Agendamento IFNMG Salinas <nao-responda@localhost>` | Remetente dos e-mails |
| `DJANGO_EMAIL_HOST` | vazio | Servidor SMTP |
| `DJANGO_EMAIL_PORT` | `587` | Porta do servidor SMTP |
| `DJANGO_EMAIL_HOST_USER` | vazio | Usuário do servidor SMTP |
| `DJANGO_EMAIL_HOST_PASSWORD` | vazio | Senha do servidor SMTP |
| `DJANGO_EMAIL_USE_TLS` | `1` | Uso de TLS no SMTP, ativo somente com o valor `1` |

`POSTGRES_HOST` (`db`) e `POSTGRES_PORT` (`5432`) são fixadas no `compose.yaml`, pois apontam para o serviço de banco.

Os valores padrão estão no `compose.yaml` e permitem subir o ambiente sem nenhuma configuração. Para sobrescrever um valor, crie um arquivo `.env` na raiz do projeto, que é ignorado pelo Git:

```dotenv
DJANGO_SECRET_KEY=outra-chave-local
```

- O PostgreSQL só lê `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` ao criar o banco. Se alterá-las depois da primeira execução, rode `make reset-db` para recriar o banco com os novos valores.
- Se uma variável obrigatória estiver ausente, a aplicação não inicia e o erro indica o nome da variável.

> **Atenção:** os valores padrão são inseguros e servem apenas ao desenvolvimento local. Não os reutilize em nenhum ambiente acessível externamente.

## E-mail

No desenvolvimento, nenhum e-mail sai de fato: o backend padrão é o de console, e cada mensagem aparece nos logs do container `web`. Para ver o link de definição ou de recuperação de senha, acompanhe:

```bash
make logs
```

Para enviar e-mails de verdade, por exemplo pelo Gmail, defina no `.env` o backend SMTP e as credenciais. No Gmail, use uma senha de app, e não a senha da conta:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=1
DJANGO_EMAIL_HOST_USER=conta@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=senha-de-app
DJANGO_DEFAULT_FROM_EMAIL=Agendamento IFNMG Salinas <conta@gmail.com>
```

Depois de alterar o `.env`, recrie o container com `make up`. Se o envio falhar durante um cadastro, o usuário continua cadastrado, quem cadastrou é avisado e o próprio usuário pode pedir um novo link em **Esqueci minha senha**.

## Dependências

As dependências Python ficam no `requirements.txt`, com versões fixas, e são instaladas durante a construção da imagem. Para adicionar ou atualizar uma dependência:

1. Edite o `requirements.txt`, fixando a versão com `==`.
2. Execute `make up` para reconstruir a imagem e recriar o container `web`.

## Permissões de arquivos em hosts Linux

O container roda como root. Em hosts Linux, arquivos criados por comandos executados no container, como migrations geradas com `makemigrations`, ficam com o root como dono. Para criá-los com o seu usuário, execute o comando Docker Compose com `--user`:

```bash
docker compose run --rm --user "$(id -u):$(id -g)" web python manage.py makemigrations
```

No macOS e no Windows com Docker Desktop, isso não é necessário.

## Organização do repositório

```text
.
├── compose.yaml       # serviços web e db
├── Dockerfile         # imagem de desenvolvimento da aplicação
├── Makefile           # atalhos para os comandos do dia a dia
├── requirements.txt   # dependências Python com versões fixas
├── manage.py
├── config/            # configuração do projeto Django
├── accounts/          # usuários, perfis, permissões e autenticação
├── openspec/          # Constitution, convenções, specs e changes do OpenSpec
└── sources/           # texto do TCC
```

As funcionalidades do sistema e a estrutura de cada domínio são criadas pelas changes do OpenSpec, em `openspec/changes/`. As convenções de código que valem para todos os apps estão em `openspec/conventions.md`.
