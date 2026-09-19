## MODIFIED Requirements

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
