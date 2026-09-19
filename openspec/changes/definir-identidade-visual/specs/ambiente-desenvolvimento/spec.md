## MODIFIED Requirements

### Requirement: Execução do ambiente via Docker Compose
O ambiente de desenvolvimento DEVE (MUST) ser iniciado integralmente pelo Docker Compose, com a aplicação Django, o PostgreSQL e a compilação do CSS da interface em containers separados, sem exigir Python, Node.js, PostgreSQL ou dependências da aplicação instalados na máquina do desenvolvedor. O container de compilação do CSS DEVE (MUST) gerar o CSS ao iniciar e gerá-lo de novo sempre que um template ou o arquivo-fonte de CSS for alterado.

#### Scenario: Primeira execução após clonar o repositório
- **WHEN** um desenvolvedor que tem apenas Docker e Docker Compose instalados clona o repositório e executa `docker compose up --build`
- **THEN** os containers `web`, `db` e `tailwind` são iniciados, o CSS da interface é gerado e `http://localhost:8000/` responde com a interface estilizada

#### Scenario: Aplicação aguarda o banco de dados
- **WHEN** os containers são iniciados
- **THEN** o container `web` só inicia depois que o PostgreSQL do container `db` estiver pronto para aceitar conexões

#### Scenario: Alteração de template com o ambiente em execução
- **GIVEN** o ambiente em execução
- **WHEN** o desenvolvedor adiciona a um template uma classe de token ainda não usada em nenhum template
- **THEN** o CSS gerado passa a conter essa classe, sem reiniciar containers

#### Scenario: Encerramento do ambiente
- **WHEN** o desenvolvedor executa `docker compose down`
- **THEN** os containers do projeto são encerrados e removidos

### Requirement: Gerenciamento de dependências
As dependências Python DEVEM (MUST) ser declaradas com versão exata em um único arquivo versionado (`requirements.txt`) e instaladas durante a construção da imagem da aplicação. As dependências de Node.js, usadas só para compilar o CSS, DEVEM (MUST) ser declaradas com versão exata no `package.json`, travadas no `package-lock.json` versionado e instaladas durante a construção da imagem de compilação do CSS. Nenhuma dependência de Node.js DEVE (MUST) ser necessária para executar a aplicação Django.

#### Scenario: Instalação na construção da imagem
- **WHEN** as imagens do ambiente são construídas
- **THEN** todas as dependências declaradas são instaladas nos containers nas versões fixadas, sem instalação na máquina do desenvolvedor

#### Scenario: Inclusão de nova dependência Python
- **WHEN** o desenvolvedor adiciona uma dependência ao `requirements.txt` e reconstrói a imagem
- **THEN** a dependência fica disponível no container `web`

#### Scenario: Inclusão de nova dependência de Node.js
- **WHEN** o desenvolvedor adiciona uma dependência com `make npm cmd="install --save-exact <pacote>@<versão>"` e executa `make up`
- **THEN** o `package.json` e o `package-lock.json` são atualizados no repositório e a dependência fica disponível no container `tailwind`

### Requirement: Atalhos de comandos via Makefile
O repositório DEVE (MUST) oferecer um `Makefile` cujos alvos executam, por meio do Docker Compose, os comandos de uso diário do ambiente, sem executar Python, Node.js ou PostgreSQL na máquina do desenvolvedor.

#### Scenario: Listagem dos alvos
- **WHEN** o desenvolvedor executa `make` ou `make help`
- **THEN** são listados os alvos disponíveis, cada um com sua descrição

#### Scenario: Subir e parar o ambiente
- **WHEN** o desenvolvedor executa `make up` e, depois, `make down`
- **THEN** o ambiente é iniciado em segundo plano, com as imagens reconstruídas e as dependências de Node.js reinstaladas se necessário, e depois encerrado

#### Scenario: Migrations e testes pelo Makefile
- **WHEN** o desenvolvedor executa `make migrate`, `make makemigrations` ou `make test`
- **THEN** o comando correspondente do `manage.py` é executado no container `web`

#### Scenario: Comando arbitrário do manage.py
- **WHEN** o desenvolvedor executa `make manage cmd="<comando>"`
- **THEN** `python manage.py <comando>` é executado no container `web`

#### Scenario: Geração do CSS minificado
- **WHEN** o desenvolvedor executa `make css`
- **THEN** o CSS da interface é gerado minificado no container `tailwind`, no caminho servido como arquivo estático

#### Scenario: Comando do npm
- **WHEN** o desenvolvedor executa `make npm cmd="<comando>"`
- **THEN** `npm <comando>` é executado no container `tailwind`, no diretório do projeto

#### Scenario: Acesso ao banco pelo psql
- **WHEN** o desenvolvedor executa `make psql`
- **THEN** o `psql` é aberto no container `db`, conectado ao banco definido em `POSTGRES_DB`

#### Scenario: Remoção dos dados do banco
- **WHEN** o desenvolvedor executa `make reset-db`
- **THEN** os containers são encerrados e o volume de dados do PostgreSQL é removido
