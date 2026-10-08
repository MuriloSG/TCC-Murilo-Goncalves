## MODIFIED Requirements

### Requirement: Execução do ambiente via Docker Compose
O ambiente de desenvolvimento DEVE (MUST) ser iniciado integralmente pelo Docker Compose, com a aplicação Django, o worker do outbox de e-mails, o worker das importações, o PostgreSQL e a compilação do CSS da interface em containers separados, sem exigir Python, Node.js, PostgreSQL ou dependências da aplicação instalados na máquina do desenvolvedor. O container de compilação do CSS DEVE (MUST) gerar o CSS ao iniciar e gerá-lo de novo sempre que um template ou o arquivo-fonte de CSS for alterado. Os containers `worker` e `import_worker` DEVEM (MUST) usar a mesma imagem e o mesmo código da aplicação; o `worker` DEVE (MUST) executar continuamente o processamento do outbox, e o `import_worker`, o das importações, com reinício automático.

#### Scenario: Primeira execução após clonar o repositório
- **WHEN** um desenvolvedor que tem apenas Docker e Docker Compose instalados clona o repositório e executa `docker compose up --build`
- **THEN** os containers `web`, `worker`, `import_worker`, `db` e `tailwind` são iniciados, o CSS da interface é gerado e `http://localhost:8000/` responde com a interface estilizada

#### Scenario: Aplicação aguarda o banco de dados
- **WHEN** os containers são iniciados
- **THEN** os containers `web`, `worker` e `import_worker` só iniciam depois que o PostgreSQL do container `db` estiver pronto para aceitar conexões

#### Scenario: E-mails do outbox no ambiente de desenvolvimento
- **GIVEN** o ambiente em execução com o backend de e-mail de console
- **WHEN** um usuário é cadastrado pela interface
- **THEN** o e-mail com o link de definição de senha aparece nos logs do container `worker`

#### Scenario: Importação no ambiente de desenvolvimento
- **GIVEN** o ambiente em execução
- **WHEN** uma planilha é enviada pela interface
- **THEN** a prévia é executada pelo container `import_worker` e a execução aparece nos logs dele

#### Scenario: Alteração de template com o ambiente em execução
- **GIVEN** o ambiente em execução
- **WHEN** o desenvolvedor adiciona a um template uma classe de token ainda não usada em nenhum template
- **THEN** o CSS gerado passa a conter essa classe, sem reiniciar containers

#### Scenario: Encerramento do ambiente
- **WHEN** o desenvolvedor executa `docker compose down`
- **THEN** os containers do projeto são encerrados e removidos
