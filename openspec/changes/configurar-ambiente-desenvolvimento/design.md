## Context

O repositório contém apenas o TCC (`sources/TCC_REVISADO (1).pdf`), a Constitution, a configuração do OpenSpec e os arquivos do Cline. Não há código de aplicação.

O que o TCC já define e esta Change deve respeitar:

- **Tecnologias:** Python com Django, PostgreSQL, acesso a dados exclusivamente pelo ORM e evolução do esquema por migrations (3.3.1; Constitution P1 e P3).
- **Justificativa do PostgreSQL:** o SQLite é descartado por não ser adequado a múltiplos acessos simultâneos (3.3.1). Por isso o desenvolvimento também usa PostgreSQL.
- **Poucas dependências externas:** o Django foi escolhido por reunir nativamente os componentes necessários e reduzir a dependência de bibliotecas externas (3.3.1).
- **Testes unitários e de integração** verificam a conformidade com os requisitos (3.3.1; P9).
- **Cronograma (Tabela 4):** "Configuração do ambiente e estrutura do projeto" precede Models, Views, Templates, autenticação, importação de planilhas, e-mail e relatórios.
- **Decisões adiadas pelo TCC:** a hospedagem ainda depende de articulação institucional (Render, Railway ou PythonAnywhere como alternativas). django-allauth, Tailwind CSS e SMTP com Gmail têm etapas próprias no cronograma.

Restrições definidas para esta Change: o ambiente roda inteiramente em Docker, o resultado é propositalmente mínimo, e nenhuma estrutura de domínio ou diretório "para o futuro" é criado.

Interessados: o autor do TCC, que desenvolve o sistema, os orientadores e qualquer desenvolvedor que venha a clonar o repositório (por exemplo, na implantação institucional).

## Goals / Non-Goals

**Goals:**

- Projeto Django mínimo que sobe com `docker compose up --build` logo após o clone.
- Aplicação conectada ao PostgreSQL em container, com dados persistidos em volume.
- Comandos padronizados por um `Makefile`, executados nos containers, para subir e parar o ambiente, aplicar migrations, executar testes e rodar comandos do `manage.py`.
- Dependências declaradas e instaladas de forma reproduzível.
- Base neutra, sem apps, para que cada Change seguinte crie a estrutura de que precisar.

**Non-Goals:**

- Apps, models, views, templates, rotas, formulários ou testes de domínio.
- django-allauth, modelo de usuário customizado, papéis e permissões (RBAC).
- Tailwind CSS e arquivos estáticos próprios.
- Envio de e-mail e configuração SMTP.
- Configuração de produção e hospedagem: servidor WSGI de produção, `ALLOWED_HOSTS` públicos, `STATIC_ROOT`, HTTPS e segredos reais.
- Divisão do `settings.py` por ambiente, lint/formatação, CI e hooks de pre-commit.

## Decisions

### D1. Docker Compose com dois serviços: `web` e `db`

A aplicação Django (`web`) e o PostgreSQL (`db`) rodam em containers separados, definidos em `compose.yaml` (nome canônico do Compose v2, sem a chave obsoleta `version`). Eles se comunicam pela rede padrão que o Compose cria, na qual o nome do serviço `db` funciona como hostname. Com apenas dois serviços, uma rede customizada não acrescenta nada.

Alternativas consideradas:
- **Django e PostgreSQL no mesmo container:** mistura ciclos de vida e dificulta reiniciar ou atualizar cada parte.
- **PostgreSQL instalado localmente:** viola a exigência de não depender de instalações locais.
- **SQLite no desenvolvimento:** o TCC descarta o SQLite (3.3.1), e usar outro banco no desenvolvimento esconderia comportamentos específicos do PostgreSQL até a implantação.

### D2. Imagens e versões

- **`python:3.13-slim`:** imagem oficial e menor que a completa. Com `psycopg[binary]` não é preciso instalar compilador nem `libpq-dev`.
- **Django 5.2 (LTS):** recebe correções de segurança até abril de 2028, o que cobre o TCC 2 e a implantação posterior pela instituição. O Django 6.x não é LTS e tem janela de suporte menor.
- **psycopg 3 (`psycopg[binary]`):** geração atual do driver do PostgreSQL suportada pelo Django 5.2; o psycopg2 está em modo de manutenção. A variante binária é adequada ao desenvolvimento, e a Change de hospedagem pode reavaliá-la.
- **`postgres:17` (Debian):** suportado pelo Django 5.2 e montado no caminho de dados documentado `/var/lib/postgresql/data`. A partir da versão 18 a imagem oficial passou a usar um diretório de dados por versão, o que muda o ponto de montagem do volume. A variante Alpine foi descartada pelas diferenças de locale e ordenação da musl.
- **Fixação:** as imagens usam tags de versão principal para receber correções menores; as bibliotecas Python são fixadas na versão exata (D3).

### D3. Dependências com pip e `requirements.txt`

Um único `requirements.txt` com versões exatas (`==`), instalado pelo `Dockerfile` durante a construção da imagem. Ele contém apenas `Django` e `psycopg[binary]`. Para adicionar uma dependência, o desenvolvedor edita o arquivo e reconstrói a imagem (`docker compose build web`).

As variáveis de ambiente são lidas com `os.environ`, sem django-environ, python-decouple ou dj-database-url, em linha com a redução de bibliotecas externas prevista no TCC.

Alternativas consideradas:
- **Poetry, uv ou Pipenv:** acrescentam uma ferramenta e um lockfile, sem benefício proporcional para duas dependências.
- **Arquivo separado para dependências de desenvolvimento:** ainda não há nenhuma.

### D4. Imagem apenas com dependências; código via bind mount

O `Dockerfile` define `WORKDIR /app`, as variáveis `PYTHONDONTWRITEBYTECODE=1` e `PYTHONUNBUFFERED=1` e instala o `requirements.txt`. Ele não copia o código. O código chega ao container por bind mount do diretório do projeto em `/app` (declarado no `compose.yaml`), e o comando do servidor é `python manage.py runserver 0.0.0.0:8000`, também no `compose.yaml`, com a porta 8000 publicada.

Com isso:
- o autoreload do `runserver` reflete as alterações sem reconstruir a imagem;
- arquivos gerados no container (migrations, o próprio `startproject`) aparecem no repositório;
- `PYTHONDONTWRITEBYTECODE` evita que `__pycache__` seja criado no diretório do host, e `PYTHONUNBUFFERED` faz os logs aparecerem imediatamente em `docker compose logs`;
- a imagem continua pequena e não guarda uma cópia desatualizada do código, de modo que o `.dockerignore` também é dispensável.

A imagem serve apenas ao desenvolvimento. Uma imagem autocontida, com código copiado, `.dockerignore` e servidor WSGI de produção, será definida na Change de hospedagem.

Alternativas consideradas:
- **`COPY . .` na imagem:** exige reconstrução a cada alteração se não houver bind mount, e, com bind mount, a cópia é inútil no desenvolvimento.
- **`develop.watch` do Compose:** sincroniza só do host para o container, então as migrations geradas não voltariam ao repositório.

### D5. Estrutura do projeto: `startproject config .`

O projeto é gerado com `django-admin startproject config .`, executado no container para não depender de Python local. O resultado é `manage.py` na raiz e o pacote `config/` com `settings.py`, `urls.py`, `wsgi.py` e `asgi.py`. O nome `config` separa a configuração do projeto das apps de domínio, que serão criadas pelas Changes seguintes.

Não são criados `apps/`, `templates/`, `static/`, app `core` ou `common` nem settings divididos (`base`/`dev`/`prod`). Onde e como as apps de domínio serão organizadas é decisão da primeira Change que criar uma.

Alternativas consideradas:
- **Pacote com o nome do projeto (`agendamento/`):** confunde o pacote de configuração com o domínio.
- **Código em `src/`:** acrescenta um nível sem benefício neste momento.

### D6. Padrões do `startproject` mantidos

`INSTALLED_APPS`, `MIDDLEWARE`, `ALLOWED_HOSTS` e `urls.py` permanecem como gerados, incluindo `django.contrib.admin`, `django.contrib.auth` e `CsrfViewMiddleware` (proteção CSRF citada no RNF02). Esses itens são padrões do framework, não estrutura de domínio. Removê-los agora também seria antecipar decisões da Change de autenticação e autorização. Nenhum superusuário, registro no admin ou customização é criado.

Consequência: o `migrate` desta Change aplica apenas as migrations das apps padrão do Django (`admin`, `auth`, `contenttypes` e `sessions`).

### D7. Configuração por variáveis de ambiente

O `settings.py` lê do ambiente:

| Variável | Uso | Leitura |
|---|---|---|
| `DJANGO_SECRET_KEY` | `SECRET_KEY` | obrigatória |
| `DJANGO_DEBUG` | `DEBUG`, ativo somente com o valor `1` | opcional, desativado por padrão |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | nome, usuário e senha do banco | obrigatórias |
| `POSTGRES_HOST`, `POSTGRES_PORT` | endereço do banco | obrigatórias |

- As variáveis obrigatórias são lidas diretamente de `os.environ`. Se uma faltar, a inicialização falha com um erro que traz o nome da variável, em vez de seguir com um valor silencioso.
- Os nomes `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` são os mesmos que a imagem oficial do PostgreSQL usa para criar o banco, então uma única definição alimenta os dois containers.
- Os valores de desenvolvimento ficam no `compose.yaml`, no formato `${VAR:-padrão}`, dentro de um bloco compartilhado por âncora YAML entre `web` e `db` (DRY). O Compose lê automaticamente um `.env` na raiz para sobrescrever qualquer valor; o `.env` fica no `.gitignore`.
- A `SECRET_KEY` gerada pelo `startproject` é removida do código.
- `ALLOWED_HOSTS` continua vazio: com `DEBUG` ativo, o Django aceita `localhost`, `127.0.0.1` e `[::1]`, o que basta para o desenvolvimento.
- `LANGUAGE_CODE = "pt-br"` e `TIME_ZONE = "America/Sao_Paulo"`, com `USE_TZ = True`. O sistema atende ao campus de Salinas (MG), e o fuso define como os horários de reserva serão exibidos e interpretados. Definir isso na fundação evita que Changes futuras precisem revisar datas e mensagens já implementadas.

Alternativas consideradas:
- **`.env.example` com cópia obrigatória para `.env`:** acrescenta um passo manual depois do clone e duplica os valores.
- **`env_file` obrigatório no Compose:** mesmo problema, pois o arquivo precisaria existir.
- **Valores fixos no `settings.py`:** versionariam o segredo no código da aplicação e impediriam a sobrescrita.
- **django-environ:** dependência extra para algo que `os.environ` resolve.

### D8. Ordem de inicialização com healthcheck

O serviço `db` tem um healthcheck com `pg_isready`, e o `web` declara `depends_on` com `condition: service_healthy`. Isso evita erro de conexão na primeira subida, quando o PostgreSQL ainda está inicializando o cluster.

O `pg_isready` testa a conexão por TCP (`-h 127.0.0.1`), e não pelo socket Unix. Na primeira inicialização de um volume vazio, o entrypoint da imagem oficial sobe um servidor temporário que escuta apenas no socket. Um teste pelo socket poderia declarar o banco pronto antes do servidor definitivo aceitar as conexões TCP que o `web` usa.

Alternativas consideradas:
- **Script `wait-for-it` ou entrypoint próprio:** arquivo extra para algo que o Compose já oferece.
- **`depends_on` simples:** garante apenas a ordem de início, não que o banco esteja pronto.

### D9. Persistência e exposição do PostgreSQL

Os dados ficam no volume nomeado `postgres_data`, montado em `/var/lib/postgresql/data`. O volume sobrevive a `docker compose down` e só é removido com `docker compose down -v`.

A porta 5432 não é publicada no host: só o `web` precisa acessar o banco, e isso evita conflito com um PostgreSQL local. O acesso manual é feito com `docker compose exec db psql`.

Alternativa considerada: **bind mount de um diretório local para os dados**, que traz problemas de permissão entre sistemas operacionais e deixaria arquivos do banco dentro do repositório.

### D10. Migrations e testes como comandos explícitos

A subida do ambiente não aplica migrations automaticamente. Todo comando do Django é executado com `docker compose run --rm web python manage.py <comando>`, encapsulado pelos alvos do `Makefile` (D11), como `make migrate` e `make test`. O `run --rm` funciona com ou sem o ambiente em execução e descarta o container ao terminar.

Motivos:
- aplicar migrations continua sendo um passo visível e controlado pelo desenvolvedor, de forma incremental e rastreável (P3);
- uma migration com erro não derruba o servidor em loop de reinício.

Para os testes é usado o executor nativo do Django (`manage.py test`, baseado em `unittest`), que atende a testes unitários e de integração (P9) sem dependência extra. O banco de testes é criado no próprio PostgreSQL; o usuário definido em `POSTGRES_USER` é superusuário na imagem oficial e pode criá-lo.

Um único teste de verificação do ambiente fica em `config/tests.py` e confirma que a conexão usa o PostgreSQL e executa uma consulta. Ele fica no pacote de configuração porque verifica a configuração, não o domínio, o que dispensa criar um diretório de testes ou uma app só para ele.

Alternativas consideradas:
- **`migrate` no entrypoint:** esconde falhas e roda a cada reinício.
- **pytest com pytest-django:** dependência extra sem ganho neste momento.

### D11. `Makefile` como interface dos comandos do dia a dia

Um `Makefile` na raiz reúne os comandos do ambiente em alvos curtos. Cada alvo apenas chama o Docker Compose, então nada é executado com o Python ou o PostgreSQL da máquina do desenvolvedor.

| Alvo | Comando executado |
|---|---|
| `help` (padrão) | lista os alvos e suas descrições |
| `up` | `docker compose up -d --build` |
| `down` | `docker compose down` |
| `logs` | `docker compose logs -f` |
| `migrate` | `docker compose run --rm web python manage.py migrate` |
| `makemigrations` | `docker compose run --rm web python manage.py makemigrations` |
| `test` | `docker compose run --rm web python manage.py test` |
| `shell` | `docker compose run --rm web python manage.py shell` |
| `manage cmd="..."` | `docker compose run --rm web python manage.py <cmd>` |
| `psql` | `psql` no container `db`, com o usuário e o banco definidos nas variáveis do próprio container |
| `reset-db` | `docker compose down -v` (apaga os dados do banco) |

- **`up` com `--build`:** a reconstrução usa o cache do Docker e é rápida quando nada mudou. Assim, uma dependência adicionada ao `requirements.txt` é instalada no próximo `make up`, sem um alvo `build` separado.
- **`up` em segundo plano:** o terminal fica livre, e `make logs` acompanha a saída dos containers.
- **`manage` genérico:** cobre qualquer comando do `manage.py` sem alvo próprio, então o `Makefile` não precisa crescer a cada comando novo. Só os comandos de uso frequente ganham alvo específico.
- **Descrições junto dos alvos:** cada alvo tem um comentário `##` que o `help` lê, de modo que alvo e documentação ficam no mesmo lugar (DRY).
- **`.PHONY`:** todos os alvos são declarados assim, pois nenhum gera arquivo.
- **Nome `reset-db`:** deixa explícito que os dados do banco são apagados, o que um nome genérico como `clean` esconderia.

Alternativas consideradas:
- **Apenas os comandos do Compose documentados no README:** funcionam em qualquer sistema, mas os comandos longos seriam redigitados a cada uso.
- **Scripts shell em um diretório `scripts/`:** um arquivo por comando e nenhuma listagem central.
- **`docker compose exec` nos alvos:** exigiria o ambiente em execução; `run --rm` funciona nos dois casos (D10).

### D12. Documentação e arquivos auxiliares

- **`README.md`:** pré-requisitos (Docker, Docker Compose v2 e `make`), primeira execução, alvos do `Makefile` com o comando Docker Compose equivalente a cada um, variáveis de ambiente com seus valores padrão, inclusão de dependências e remoção dos dados do banco.
- **`.gitignore`:** `.env`, `__pycache__/` e `*.pyc`.

## Risks / Trade-offs

- **[Risco] Troca do modelo de usuário depois das migrations padrão.** O `migrate` desta Change cria as tabelas de `django.contrib.auth` com o `User` padrão. Se a Change de autenticação adotar um modelo de usuário customizado (`AUTH_USER_MODEL`), o Django não suporta essa troca sobre um banco já migrado. → Mitigação: não há dados reais nesta fase. A Change de autenticação deve incluir em suas tasks a recriação do banco de desenvolvimento com `docker compose down -v` antes de aplicar as próprias migrations.
- **[Risco] Chave secreta e senha do banco inseguras versionadas no `compose.yaml`.** → Mitigação: os valores servem só ao ambiente local, o banco não tem porta publicada e o README avisa que eles não podem ser reutilizados. A Change de hospedagem definirá segredos próprios.
- **[Risco] Arquivos criados pelo container pertencem ao root em hosts Linux.** O container roda como root, então migrations geradas ficam com esse dono no host. → Mitigação: o README orienta usar `docker compose run --rm --user "$(id -u):$(id -g)" web ...` nesses casos. No macOS e no Windows, o Docker Desktop mapeia as permissões e o problema não ocorre.
- **[Trade-off] A imagem é só de desenvolvimento.** Ela não serve para produção como está. → A Change de hospedagem definirá imagem e servidor de produção, ainda dependentes da escolha da plataforma (TCC 3.3.1).
- **[Trade-off] O Tailwind CSS fica fora.** → A primeira Change com templates precisará decidir como compilar o CSS dentro do Docker, possivelmente acrescentando um serviço ao Compose.
- **[Trade-off] O `make` não vem instalado por padrão no Windows.** No macOS ele vem com as Command Line Tools do Xcode, e nas distribuições Linux costuma estar disponível. → Mitigação: no Windows, usar o `make` pelo WSL. Como os alvos só encapsulam o Docker Compose, o README lista o comando equivalente de cada um, que pode ser executado diretamente.
- **[Trade-off] `run --rm` cria um container novo a cada comando.** Leva alguns segundos a mais que `exec`, o que é aceitável; com o ambiente em execução, `docker compose exec web ...` também funciona.

## Migration Plan

Não há sistema em produção nem dados a migrar. A implementação segue a ordem do `tasks.md`. Para reverter, basta executar `docker compose down -v` e remover os arquivos criados por esta Change.

## Open Questions

- **`django.contrib.admin`:** fica ativo nesta Change por ser padrão do framework (D6). A Change de autenticação e autorização deve decidir se o admin permanece, já que ele expõe uma tela de login própria, fora do fluxo do django-allauth e do RBAC.
- **Build do Tailwind CSS no Docker:** a definir na primeira Change que criar templates.
