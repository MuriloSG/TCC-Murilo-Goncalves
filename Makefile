COMPOSE = docker compose
MANAGE = $(COMPOSE) run --rm web python manage.py

.DEFAULT_GOAL := help
.PHONY: help up down logs migrate makemigrations test shell manage css npm psql reset-db clear-data

help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Sobe o ambiente em segundo plano, reconstruindo as imagens e reinstalando as dependências de Node.js se necessário
	$(COMPOSE) up -d --build --renew-anon-volumes

down: ## Para e remove os containers (os dados do banco são mantidos)
	$(COMPOSE) down

logs: ## Acompanha os logs dos containers
	$(COMPOSE) logs -f

migrate: ## Aplica as migrations pendentes
	$(MANAGE) migrate

makemigrations: ## Gera migrations a partir das alterações nos models
	$(MANAGE) makemigrations

test: ## Executa a suíte de testes
	$(MANAGE) test

shell: ## Abre o shell do Django
	$(MANAGE) shell

manage: ## Executa um comando do manage.py (ex.: make manage cmd="showmigrations")
	$(MANAGE) $(cmd)

css: ## Gera o CSS minificado da interface em ui/static/ui/css/app.css
	$(COMPOSE) run --rm tailwind npx @tailwindcss/cli -i ui/styles/app.css -o ui/static/ui/css/app.css --minify

npm: ## Executa um comando do npm no container tailwind (ex.: make npm cmd="install --save-exact pacote@1.0.0")
	$(COMPOSE) run --rm tailwind npm $(cmd)

psql: ## Abre o psql no banco de dados do container db
	$(COMPOSE) up -d --wait db
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

reset-db: ## ATENÇÃO: para os containers e apaga todos os dados do banco
	$(COMPOSE) down -v

clear-data: ## ATENÇÃO: apaga todos os dados do banco, mantendo apenas os usuários, perfis e permissões
	$(MANAGE) clear_data
