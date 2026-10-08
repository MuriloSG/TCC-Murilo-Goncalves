COMPOSE = docker compose
MANAGE = $(COMPOSE) run --rm web python manage.py

.DEFAULT_GOAL := help

LOCAL_IP = $(shell ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $$1}')

.PHONY: help up dev-network down logs migrate makemigrations test shell manage css npm psql reset-db mark-local-db clear-data delete-users set-passwords

help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Sobe o ambiente em segundo plano, reconstruindo as imagens e reinstalando as dependências de Node.js se necessário
	$(COMPOSE) up -d --build --renew-anon-volumes

dev-network: ## Sobe o ambiente aceitando acessos de outros aparelhos da rede local (ex.: o celular no mesmo Wi-Fi)
	@test -n "$(LOCAL_IP)" || { echo "Não foi possível descobrir o IPv4 da rede local. Informe-o: make dev-network LOCAL_IP=192.168.0.10"; exit 1; }
	DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,$(LOCAL_IP)" DJANGO_SITE_URL="http://$(LOCAL_IP):8000" $(COMPOSE) up -d --build --renew-anon-volumes
	@echo
	@echo "Aplicação disponível na rede local na porta 8000:"
	@echo "  neste computador: http://localhost:8000/"
	@echo "  no celular:       http://$(LOCAL_IP):8000/"
	@echo
	@echo "Acompanhe os logs com make logs e pare o ambiente com make down."

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

mark-local-db: ## Marca o banco do container db como banco local, condição dos comandos destrutivos
	$(COMPOSE) up -d --wait db
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "ALTER DATABASE \"$$POSTGRES_DB\" SET ifagenda.environment = '"'"'local'"'"'"'

clear-data: ## ATENÇÃO: apaga todos os dados do banco, mantendo apenas os usuários, perfis e permissões
	$(MANAGE) clear_data

delete-users: ## ATENÇÃO: exclui os usuários que não são superadmin e os vínculos deles, mantendo perfis e superadmins
	$(MANAGE) delete_users

set-passwords: ## Define a senha padrão de desenvolvimento para todos os usuários
	$(MANAGE) set_passwords
