## ADDED Requirements

### Requirement: Permissão de criar solicitação para outro usuário
O catálogo DEVE (MUST) ganhar a permissão `AGENDA.CRIAR`, por migration de dados, que permite criar uma solicitação de agendamento em nome de outro usuário. A migration DEVE (MUST) concedê-la ao perfil `ADMINISTRADOR`, sem alterar as demais concessões, e NÃO DEVE (MUST NOT) concedê-la ao perfil `DOCENTE`. Ela NÃO DEVE (MUST NOT) ser reservada ao superadmin, e o superadmin ativo DEVE (MUST) tê-la sem concessão por perfil. A rota `agenda/criar/` DEVE (MUST) exigir autenticação e `AGENDA.CRIAR`, e a operação do model DEVE (MUST) conferir a permissão de novo a cada envio. `AGENDA.SOLICITAR` NÃO DEVE (MUST NOT) dar acesso a essa rota.

#### Scenario: Catálogo com a permissão
- **WHEN** as migrations são aplicadas
- **THEN** existe `AGENDA.CRIAR`, concedida a `ADMINISTRADOR` e não a `DOCENTE`

#### Scenario: Superadmin sem a permissão no perfil
- **GIVEN** um superadmin ativo cujo perfil não concede `AGENDA.CRIAR`
- **WHEN** ele abre `agenda/criar/` e envia uma solicitação válida em nome de Ana
- **THEN** a solicitação é criada

#### Scenario: Sem a permissão
- **GIVEN** um usuário ativo, sem superadmin, com `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR` e sem `AGENDA.CRIAR`
- **WHEN** ele abre `agenda/criar/` ou envia um POST para ela com IDs válidos
- **THEN** as duas respostas são 403 e nenhuma solicitação é criada

#### Scenario: Anônimo
- **WHEN** um visitante não autenticado abre `agenda/criar/`
- **THEN** ele é levado à página de login com `next`

#### Scenario: Operação chamada sem a permissão
- **WHEN** a operação do model é chamada com um solicitante diferente do usuário e o usuário não tem `AGENDA.CRIAR`
- **THEN** ela é recusada e nada é gravado

### Requirement: Cadeia usuário, curso, disciplina e turma
O modal "Criar solicitação para outro usuário" DEVE (MUST) pedir, nesta ordem, usuário, curso, disciplina, turma, espaço, data, início, fim e descrição. A cadeia DEVE (MUST) vir dos vínculos atuais do ensalamento no semestre da data: o docente que corresponde ao usuário pelo `username`, os vínculos atuais dele no semestre, e as ofertas desses vínculos, com a disciplina, a turma e o curso da turma. O sistema NÃO DEVE (MUST NOT) criar relacionamento novo para isso. O usuário DEVE (MUST) listar só os usuários ativos que correspondem a um docente com vínculo atual no semestre. O curso DEVE (MUST) listar só os cursos das turmas dos vínculos do usuário escolhido; a disciplina, só as disciplinas desses vínculos no curso escolhido; e a turma, só as turmas dos vínculos na disciplina e no curso escolhidos.

A troca do usuário DEVE (MUST) limpar e recarregar curso, disciplina e turma; a troca do curso DEVE (MUST) limpar e recarregar disciplina e turma; e a troca da disciplina DEVE (MUST) limpar e recarregar a turma, sem fechar o modal.

#### Scenario: Cursos do usuário escolhido
- **GIVEN** em `2026/2`, Ana com Redes do `2º ANO A (INFORMÁTICA)` e Bruno com Física do `1º ANO A (AGROPECUÁRIA)`
- **WHEN** o usuário com `AGENDA.CRIAR` escolhe Ana
- **THEN** o curso oferece `INFORMÁTICA` e não `AGROPECUÁRIA`

#### Scenario: Disciplinas do usuário no curso
- **GIVEN** Ana com Redes no `2º ANO A (INFORMÁTICA)` e Química no `1º ANO A (AGROPECUÁRIA)`, e Érica com Física no `2º ANO A (INFORMÁTICA)`
- **WHEN** o usuário escolhe Ana e `INFORMÁTICA`
- **THEN** a disciplina oferece só Redes

#### Scenario: Turmas do usuário na disciplina e no curso
- **GIVEN** Ana com Redes no `2º ANO A` e no `3º ANO A` de `INFORMÁTICA`, e Érica com Redes no `1º ANO A` de `INFORMÁTICA`
- **WHEN** o usuário escolhe Ana, `INFORMÁTICA` e Redes
- **THEN** a turma oferece o `2º ANO A` e o `3º ANO A`, e não o `1º ANO A`

#### Scenario: Troca do usuário
- **GIVEN** Ana e Bruno com Redes no `2º ANO A (INFORMÁTICA)`, e o modal com Ana, `INFORMÁTICA`, Redes e `2º ANO A` escolhidos
- **WHEN** o usuário troca Ana por Bruno
- **THEN** curso, disciplina e turma aparecem sem escolha, com as opções de Bruno

#### Scenario: Troca do curso
- **WHEN** o usuário troca o curso escolhido
- **THEN** disciplina e turma aparecem sem escolha, com as opções do novo curso

#### Scenario: Troca da disciplina
- **WHEN** o usuário troca a disciplina escolhida
- **THEN** a turma aparece sem escolha, com as opções da nova disciplina

### Requirement: Conferência da cadeia no backend
A criação em nome de outro usuário DEVE (MUST) conferir no backend, a cada envio e de novo na confirmação, que o usuário escolhido está ativo e corresponde a um docente, que o curso é o curso da turma do vínculo, que a disciplina é a da oferta do vínculo e que o vínculo é atual, do docente do usuário escolhido e do semestre da data. A conferência DEVE (MUST) ficar numa única operação do model, usada também pelo fluxo "Solicitar agendamento". IDs incompatíveis enviados na requisição DEVEM (MUST) ser recusados, sem gravar nada.

#### Scenario: Curso de outro usuário
- **WHEN** a requisição traz Ana com o curso `AGROPECUÁRIA`, em que ela não tem vínculo
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Disciplina fora do curso
- **WHEN** a requisição traz Ana, `INFORMÁTICA` e Química, que Ana só tem em `AGROPECUÁRIA`
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Turma fora da cadeia
- **WHEN** a requisição traz Ana, `INFORMÁTICA`, Redes e o vínculo de Érica com Redes no `1º ANO A`
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Usuário que não é docente
- **WHEN** a requisição traz um usuário sem docente correspondente
- **THEN** a solicitação é recusada e nada é gravado

### Requirement: Solicitação criada em nome de outro usuário
Depois da cadeia, a criação DEVE (MUST) seguir o fluxo da solicitação de agendamento: a revisão antes do envio, as regras de semestre, período, espaço, data, horário, disponibilidade e conflito, e a criação da solicitação `PENDENTE`, sem agendamento. A solicitação DEVE (MUST) ter como solicitante o usuário escolhido e DEVE (MUST) guardar quem a criou. Ela DEVE (MUST) aparecer em "Minhas solicitações" do usuário escolhido e na análise, com "Criada por", e a auditoria da criação DEVE (MUST) registrar o solicitante e quem criou.

#### Scenario: Criação válida
- **GIVEN** um administrador com `AGENDA.CRIAR` e Ana com Redes no `2º ANO A (INFORMÁTICA)` em `2026/2`
- **WHEN** ele cria, para Ana, a solicitação do `Laboratório de Informática 2` em 15/10/2026 das 16:00 às 18:00, revisa e envia
- **THEN** existe uma solicitação `PENDENTE` com Ana como solicitante, esse vínculo e o administrador como quem criou
- **AND** não existe agendamento para esse horário
- **AND** a solicitação aparece em "Minhas solicitações" de Ana

#### Scenario: Conflito com o ensalamento
- **GIVEN** uma aula no `Laboratório de Informática 2` em 15/10/2026 das 14:10 às 15:00
- **WHEN** o administrador cria para Ana a solicitação desse espaço das 14:00 às 16:00
- **THEN** a solicitação é recusada com a mensagem do conflito e nada é gravado

#### Scenario: Data fora do período
- **WHEN** o administrador cria para Ana uma solicitação em 07/01/2027, fora do período de `2026/2`
- **THEN** a solicitação é recusada no campo da data e nada é gravado
