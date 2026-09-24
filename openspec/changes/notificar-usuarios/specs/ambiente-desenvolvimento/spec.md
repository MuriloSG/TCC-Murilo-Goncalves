## MODIFIED Requirements

### Requirement: Execução do ambiente via Docker Compose
O ambiente de desenvolvimento DEVE (MUST) ser iniciado integralmente pelo Docker Compose, com a aplicação Django, o worker do outbox de e-mails, o PostgreSQL e a compilação do CSS da interface em containers separados, sem exigir Python, Node.js, PostgreSQL ou dependências da aplicação instalados na máquina do desenvolvedor. O container de compilação do CSS DEVE (MUST) gerar o CSS ao iniciar e gerá-lo de novo sempre que um template ou o arquivo-fonte de CSS for alterado. O container `worker` DEVE (MUST) usar a mesma imagem e o mesmo código da aplicação e executar continuamente o processamento do outbox. A aplicação DEVE (MUST) atender também ao canal de tempo real das notificações, e todo serviço que esse canal exigir DEVE (MUST) subir pelo mesmo `docker compose up`, com as mesmas variáveis de ambiente do projeto, sem instalação nem configuração manual na máquina do desenvolvedor. A escolha da tecnologia do canal fica no design da implementação, e o ambiente NÃO DEVE (MUST NOT) exigir um passo próprio para as notificações funcionarem em tempo real.

#### Scenario: Primeira execução após clonar o repositório
- **WHEN** um desenvolvedor que tem apenas Docker e Docker Compose instalados clona o repositório e executa `docker compose up --build`
- **THEN** os containers do projeto são iniciados, o CSS da interface é gerado e `http://localhost:8000/` responde com a interface estilizada
- **AND** o canal de tempo real das notificações está disponível, sem nenhum comando adicional

#### Scenario: Notificação em tempo real no ambiente de desenvolvimento
- **GIVEN** o ambiente em execução, com um usuário autenticado numa janela do navegador
- **WHEN** um comunicado é publicado para ele em outra sessão
- **THEN** o sino da janela aberta passa a mostrar a notificação sem recarregar a página

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
