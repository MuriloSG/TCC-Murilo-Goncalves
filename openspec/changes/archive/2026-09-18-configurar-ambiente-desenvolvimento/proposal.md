## Why

O repositório ainda não possui nenhum projeto executável: contém apenas o TCC, a Constitution e a configuração do OpenSpec. O cronograma do TCC (Tabela 4) coloca a configuração do ambiente e da estrutura do projeto antes dos Models, das Views e das demais funcionalidades, e nenhuma Change funcional pode começar sem uma base Django reproduzível, conectada ao PostgreSQL e executável da mesma forma por qualquer desenvolvedor.

## What Changes

- Projeto Django mínimo gerado com `django-admin startproject`, com o pacote de configuração `config` e nenhuma app própria.
- Imagem Docker de desenvolvimento com Python e as dependências do projeto.
- `compose.yaml` com dois serviços, a aplicação Django (`web`) e o PostgreSQL (`db`), que se comunicam pela rede padrão do Docker Compose.
- Volume nomeado para persistir os dados do PostgreSQL.
- Chave secreta, modo de depuração e credenciais do banco lidos de variáveis de ambiente, com valores de desenvolvimento no `compose.yaml` e sobrescrita opcional por um `.env` não versionado.
- `requirements.txt` com versões fixas do Django e do driver do PostgreSQL.
- Um teste de verificação do ambiente que confirma a conexão com o PostgreSQL.
- `Makefile` com atalhos para os comandos do dia a dia (`up`, `down`, `logs`, `migrate`, `makemigrations`, `test`, `shell`, `manage`, `psql` e `reset-db`), todos executados pelo Docker Compose.
- `README.md` com os pré-requisitos, os alvos do `Makefile` e o comando Docker Compose equivalente a cada um, as variáveis de ambiente e o procedimento para gerenciar dependências, e `.gitignore`.

Não fazem parte desta Change: apps, models, views, templates, rotas ou testes de domínio; autenticação (django-allauth), papéis e permissões (RBAC); Tailwind CSS; envio de e-mail; configuração de hospedagem ou de produção. Cada um desses itens, e a estrutura de diretórios que ele exigir, será criado na Change correspondente.

## Capabilities

### New Capabilities

- `ambiente-desenvolvimento`: execução do projeto via Docker Compose, conexão com o PostgreSQL, persistência dos dados, configuração por variáveis de ambiente, execução de migrations e testes, atalhos de comandos via `Makefile` e gerenciamento de dependências.

### Modified Capabilities

Nenhuma. Não há specs existentes em `openspec/specs/`.

## Impact

- **Arquivos novos na raiz:** `Dockerfile`, `compose.yaml`, `Makefile`, `requirements.txt`, `.gitignore`, `README.md`, `manage.py` e o pacote `config/`.
- **Dependências:** Django 5.2 (LTS) e psycopg 3; imagens oficiais `python:3.13-slim` e `postgres:17`.
- **Pré-requisitos para desenvolvedores:** Docker com Docker Compose v2 e `make`. Python e PostgreSQL instalados localmente não são necessários. No Windows, o `make` está disponível pelo WSL; sem ele, os comandos Docker Compose equivalentes documentados no README funcionam diretamente.
- **Constitution:** concretiza P1 (Python, Django e PostgreSQL) e prepara P3 (ORM e migrations) e P9 (testes). P5 (RBAC), P8 (Tailwind CSS) e a hospedagem ficam para as Changes correspondentes.
- **Código existente:** nenhum; o repositório ainda não tem código de aplicação.
