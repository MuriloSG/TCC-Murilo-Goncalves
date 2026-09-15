COMPOSE = docker compose
MANAGE = $(COMPOSE) run --rm web python manage.py

.DEFAULT_GOAL := help
.PHONY: help up down logs migrate makemigrations test shell manage psql reset-db

help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Sobe o ambiente em segundo plano, reconstruindo a imagem se necessário
	$(COMPOSE) up -d --build

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

psql: ## Abre o psql no banco de dados do container db
	$(COMPOSE) up -d --wait db
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

reset-db: ## ATENÇÃO: para os containers e apaga todos os dados do banco
	$(COMPOSE) down -v
