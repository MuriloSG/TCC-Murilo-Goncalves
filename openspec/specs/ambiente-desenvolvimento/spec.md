# ambiente-desenvolvimento Specification

## Purpose
TBD - created by archiving change configurar-ambiente-desenvolvimento. Update Purpose after archive.
## Requirements
### Requirement: Execução do ambiente via Docker Compose
O ambiente de desenvolvimento DEVE (MUST) ser iniciado integralmente pelo Docker Compose, com a aplicação Django, o worker do outbox de e-mails, o PostgreSQL e a compilação do CSS da interface em containers separados, sem exigir Python, Node.js, PostgreSQL ou dependências da aplicação instalados na máquina do desenvolvedor. O container de compilação do CSS DEVE (MUST) gerar o CSS ao iniciar e gerá-lo de novo sempre que um template ou o arquivo-fonte de CSS for alterado. O container `worker` DEVE (MUST) usar a mesma imagem e o mesmo código da aplicação e executar continuamente o processamento do outbox.

#### Scenario: Primeira execução após clonar o repositório
- **WHEN** um desenvolvedor que tem apenas Docker e Docker Compose instalados clona o repositório e executa `docker compose up --build`
- **THEN** os containers `web`, `worker`, `db` e `tailwind` são iniciados, o CSS da interface é gerado e `http://localhost:8000/` responde com a interface estilizada

#### Scenario: Aplicação aguarda o banco de dados
- **WHEN** os containers são iniciados
- **THEN** os containers `web` e `worker` só iniciam depois que o PostgreSQL do container `db` estiver pronto para aceitar conexões

#### Scenario: E-mails do outbox no ambiente de desenvolvimento
- **GIVEN** o ambiente em execução com o backend de e-mail de console
- **WHEN** um usuário é cadastrado pela interface
- **THEN** o e-mail com o link de definição de senha aparece nos logs do container `worker`

#### Scenario: Alteração de template com o ambiente em execução
- **GIVEN** o ambiente em execução
- **WHEN** o desenvolvedor adiciona a um template uma classe de token ainda não usada em nenhum template
- **THEN** o CSS gerado passa a conter essa classe, sem reiniciar containers

#### Scenario: Encerramento do ambiente
- **WHEN** o desenvolvedor executa `docker compose down`
- **THEN** os containers do projeto são encerrados e removidos

### Requirement: Conexão com o PostgreSQL
A aplicação DEVE (MUST) usar como banco de dados o PostgreSQL do container `db`, acessado pela rede interna do Docker Compose.

#### Scenario: Aplicação conectada ao PostgreSQL
- **WHEN** um comando do Django que acessa o banco é executado no container `web`
- **THEN** a conexão usa o backend PostgreSQL e as consultas são executadas no container `db`

### Requirement: Persistência dos dados do PostgreSQL
Os dados do PostgreSQL DEVEM (MUST) ficar em um volume nomeado do Docker, preservado quando os containers são encerrados e removido apenas por solicitação explícita.

#### Scenario: Dados preservados após reinício
- **WHEN** o desenvolvedor aplica as migrations, executa `docker compose down` e depois `docker compose up`
- **THEN** as migrations aplicadas anteriormente continuam registradas no banco

#### Scenario: Remoção explícita dos dados
- **WHEN** o desenvolvedor executa `docker compose down -v`
- **THEN** o volume de dados é removido e a próxima inicialização cria um banco vazio

### Requirement: Configuração por variáveis de ambiente
A chave secreta do Django, o modo de depuração, as credenciais e o endereço do banco de dados e a URL base usada nos links enviados por e-mail fora de uma requisição DEVEM (MUST) ser lidos de variáveis de ambiente, sem valores fixados no código da aplicação. O ambiente de desenvolvimento DEVE (MUST) fornecer valores padrão para essas variáveis e permitir sobrescrevê-los localmente sem versioná-los.

#### Scenario: Execução com os valores padrão
- **WHEN** o desenvolvedor inicia o ambiente sem criar nenhum arquivo de configuração local
- **THEN** a aplicação e o PostgreSQL usam os valores de desenvolvimento definidos no `compose.yaml`
- **AND** os links enviados pelo worker usam a URL base `http://localhost:8000`

#### Scenario: Sobrescrita local de variável
- **WHEN** o desenvolvedor define uma dessas variáveis em um arquivo `.env` na raiz do projeto
- **THEN** o valor do `.env` substitui o valor padrão e o arquivo `.env` é ignorado pelo Git

#### Scenario: Variável obrigatória ausente
- **WHEN** a aplicação é iniciada sem uma variável obrigatória, como `DJANGO_SECRET_KEY`
- **THEN** a inicialização falha com um erro que identifica a variável ausente

### Requirement: Código-fonte sincronizado com o container
O diretório do projeto DEVE (MUST) ser montado no container `web`, de modo que alterações feitas na máquina do desenvolvedor valham sem reconstruir a imagem e que arquivos gerados no container fiquem no repositório.

#### Scenario: Alteração de código com o servidor em execução
- **WHEN** o desenvolvedor altera um arquivo Python do projeto com o ambiente em execução
- **THEN** o servidor de desenvolvimento recarrega a aplicação automaticamente, sem reconstrução da imagem

#### Scenario: Arquivo gerado dentro do container
- **WHEN** um comando executado no container `web` cria um arquivo no diretório do projeto, como uma migration
- **THEN** o arquivo aparece no diretório do repositório na máquina do desenvolvedor

### Requirement: Execução de migrations pelo container
O ambiente DEVE (MUST) permitir gerar e aplicar migrations do Django com comandos executados no container `web`.

#### Scenario: Aplicação das migrations
- **WHEN** o desenvolvedor executa `docker compose run --rm web python manage.py migrate`
- **THEN** as migrations pendentes são aplicadas no PostgreSQL e o comando termina sem erros

### Requirement: Execução de testes pelo container
O ambiente DEVE (MUST) permitir executar a suíte de testes do Django no container `web`, usando um banco de testes criado no PostgreSQL.

#### Scenario: Execução da suíte de testes
- **WHEN** o desenvolvedor executa `docker compose run --rm web python manage.py test`
- **THEN** o Django cria um banco de testes no PostgreSQL, executa os testes e o comando termina com sucesso

#### Scenario: Verificação do banco usado nos testes
- **WHEN** a suíte de testes é executada
- **THEN** um teste confirma que a conexão de banco de dados usa o PostgreSQL

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

### Requirement: Documentação do ambiente
O repositório DEVE (MUST) documentar os pré-requisitos e os comandos necessários para operar o ambiente de desenvolvimento.

#### Scenario: Consulta à documentação
- **WHEN** um desenvolvedor abre o `README.md` do repositório
- **THEN** encontra os pré-requisitos, os passos da primeira execução, os alvos do `Makefile` com o comando Docker Compose equivalente a cada um, as variáveis de ambiente com seus valores padrão e o procedimento para adicionar dependências

