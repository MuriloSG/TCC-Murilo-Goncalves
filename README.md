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
make up        # constrói a imagem e sobe os containers
make migrate   # aplica as migrations no PostgreSQL
```

A aplicação fica disponível em <http://localhost:8000/>. Enquanto nenhuma funcionalidade estiver implementada, essa página exibe a tela padrão de boas-vindas do Django.

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

`POSTGRES_HOST` (`db`) e `POSTGRES_PORT` (`5432`) são fixadas no `compose.yaml`, pois apontam para o serviço de banco.

Os valores padrão estão no `compose.yaml` e permitem subir o ambiente sem nenhuma configuração. Para sobrescrever um valor, crie um arquivo `.env` na raiz do projeto, que é ignorado pelo Git:

```dotenv
DJANGO_SECRET_KEY=outra-chave-local
```

- O PostgreSQL só lê `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` ao criar o banco. Se alterá-las depois da primeira execução, rode `make reset-db` para recriar o banco com os novos valores.
- Se uma variável obrigatória estiver ausente, a aplicação não inicia e o erro indica o nome da variável.

> **Atenção:** os valores padrão são inseguros e servem apenas ao desenvolvimento local. Não os reutilize em nenhum ambiente acessível externamente.

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
├── openspec/          # Constitution, specs e changes do OpenSpec
└── sources/           # texto do TCC
```

As funcionalidades do sistema e a estrutura de cada domínio são criadas pelas changes do OpenSpec, em `openspec/changes/`.
