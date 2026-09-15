## 1. Arquivos base do repositório

- [x] 1.1 Criar `.gitignore` na raiz ignorando `.env`, `__pycache__/` e `*.pyc`
- [x] 1.2 Criar `requirements.txt` com `Django` 5.2 (LTS) e `psycopg[binary]` 3, ambos fixados com `==` na última versão de correção disponível

## 2. Imagem e orquestração Docker

- [x] 2.1 Criar `Dockerfile` baseado em `python:3.13-slim` com `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `WORKDIR /app` e instalação do `requirements.txt` com `pip install --no-cache-dir`, sem copiar o código do projeto
- [x] 2.2 Criar `compose.yaml` com um bloco de variáveis `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` compartilhado por âncora YAML, com valores padrão de desenvolvimento no formato `${VAR:-padrão}`
- [x] 2.3 Adicionar ao `compose.yaml` o serviço `db` com a imagem `postgres:17`, o volume nomeado `postgres_data` montado em `/var/lib/postgresql/data`, healthcheck com `pg_isready` e nenhuma porta publicada
- [x] 2.4 Adicionar ao `compose.yaml` o serviço `web` com build do `Dockerfile`, bind mount `.:/app`, porta `8000:8000`, comando `python manage.py runserver 0.0.0.0:8000` e `depends_on` do `db` com `condition: service_healthy`
- [x] 2.5 Definir no serviço `web` o bloco compartilhado e as variáveis `DJANGO_SECRET_KEY` (chave insegura de desenvolvimento) e `DJANGO_DEBUG=1` no formato `${VAR:-padrão}`, além de `POSTGRES_HOST=db` e `POSTGRES_PORT=5432`
- [x] 2.6 Executar `docker compose build` e confirmar que a imagem é construída sem erros

## 3. Makefile

- [x] 3.1 Criar `Makefile` na raiz com todos os alvos declarados em `.PHONY` e o alvo padrão `help`, que lista os alvos com as descrições escritas em comentários `##`
- [x] 3.2 Adicionar os alvos `up` (`docker compose up -d --build`), `down` (`docker compose down`) e `logs` (`docker compose logs -f`)
- [x] 3.3 Adicionar os alvos `migrate`, `makemigrations`, `test` e `shell`, cada um executando `docker compose run --rm web python manage.py <comando>`
- [x] 3.4 Adicionar o alvo `manage`, que executa `docker compose run --rm web python manage.py $(cmd)` com o comando recebido na variável `cmd`
- [x] 3.5 Adicionar o alvo `psql`, que abre o `psql` no container `db` usando `POSTGRES_USER` e `POSTGRES_DB` do próprio container
- [x] 3.6 Adicionar o alvo `reset-db`, que executa `docker compose down -v`, com uma descrição avisando que os dados do banco serão apagados
- [x] 3.7 Executar `make help` e confirmar que todos os alvos aparecem com suas descrições

## 4. Projeto Django mínimo

- [x] 4.1 Gerar o projeto com `docker compose run --rm --no-deps web django-admin startproject config .` e confirmar que apenas `manage.py` e o pacote `config/` foram criados na raiz
- [x] 4.2 Em `config/settings.py`, remover a `SECRET_KEY` gerada e lê-la de `DJANGO_SECRET_KEY` com acesso obrigatório a `os.environ`
- [x] 4.3 Em `config/settings.py`, definir `DEBUG` a partir de `DJANGO_DEBUG`, ativo somente quando o valor for `1`
- [x] 4.4 Em `config/settings.py`, substituir a configuração SQLite pelo backend `django.db.backends.postgresql`, lendo `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT` com acesso obrigatório a `os.environ`
- [x] 4.5 Em `config/settings.py`, definir `LANGUAGE_CODE = "pt-br"` e `TIME_ZONE = "America/Sao_Paulo"`, mantendo `USE_TZ = True`
- [x] 4.6 Conferir que `INSTALLED_APPS`, `MIDDLEWARE`, `ALLOWED_HOSTS` e `config/urls.py` continuam como gerados pelo `startproject`
- [x] 4.7 Executar `make manage cmd=check` e confirmar que nenhum problema é reportado

## 5. Teste de verificação do ambiente

- [x] 5.1 Criar `config/tests.py` com um `TestCase` que verifica que `connection.vendor` é `"postgresql"` e que `SELECT 1` retorna `1`
- [x] 5.2 Executar `make test` e confirmar que um teste é encontrado, que o banco de testes é criado no PostgreSQL e que a execução termina com sucesso

## 6. Documentação

- [x] 6.1 Criar `README.md` com os pré-requisitos (Docker, Docker Compose v2 e `make`, com a indicação do WSL no Windows) e o passo a passo da primeira execução com `make up`
- [x] 6.2 Documentar no `README.md` todos os alvos do `Makefile`, cada um com o comando Docker Compose equivalente para quem não tiver `make`
- [x] 6.3 Documentar no `README.md` as variáveis de ambiente, seus valores padrão e a sobrescrita por `.env`, com o aviso de que os valores padrão servem apenas ao desenvolvimento local
- [x] 6.4 Documentar no `README.md` como adicionar uma dependência (editar `requirements.txt` e executar `make up`), o efeito destrutivo de `make reset-db` e o uso de `--user "$(id -u):$(id -g)"` em hosts Linux

## 7. Verificação dos cenários da spec

- [x] 7.1 Executar `make up` e confirmar pela saída do comando que o `web` só é iniciado depois que o `db` fica `healthy`
- [x] 7.2 Acessar `http://localhost:8000/` e confirmar que a página padrão de boas-vindas do Django é exibida
- [x] 7.3 Executar `make migrate` e confirmar que as migrations das apps padrão do Django são aplicadas sem erros
- [x] 7.4 Alterar temporariamente um arquivo Python do projeto, confirmar com `make logs` que o `runserver` recarregou sem reconstrução da imagem e desfazer a alteração
- [x] 7.5 Executar `make down` e `make up` e confirmar com `make manage cmd=showmigrations` que as migrations continuam aplicadas
- [x] 7.6 Executar `make psql`, confirmar a conexão ao banco definido em `POSTGRES_DB` e sair
- [x] 7.7 Executar `make reset-db` e `make up` e confirmar com `make manage cmd=showmigrations` que nenhuma migration está aplicada
- [x] 7.8 Criar um `.env` temporário com outro valor de `POSTGRES_DB`, confirmar com `docker compose config` que ele substitui o padrão e que `git status` não lista o `.env`, e depois remover o arquivo
- [x] 7.9 Executar `docker compose run --rm --no-deps web env -u DJANGO_SECRET_KEY python manage.py check` e confirmar que o erro identifica `DJANGO_SECRET_KEY`
- [x] 7.10 Confirmar com `git status` que, fora de `openspec/`, os únicos arquivos novos são `.gitignore`, `requirements.txt`, `Dockerfile`, `compose.yaml`, `Makefile`, `README.md`, `manage.py` e `config/`, sem banco SQLite, caches ou diretórios extras
