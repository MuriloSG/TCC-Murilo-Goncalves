## MODIFIED Requirements

### Requirement: Isolamento da área autenticada
O calendário público DEVE (MUST) ter view, formulário, consulta, templates e layout próprios. Ele NÃO DEVE (MUST NOT) herdar nem chamar a view da Grade autenticada, NÃO DEVE (MUST NOT) usar o formulário da Grade, NÃO DEVE (MUST NOT) chamar `occupancy()` nem `grid_sources()` e NÃO DEVE (MUST NOT) ler `request.user`. Além das aulas, só DEVEM (MUST) entrar as fontes registradas como públicas, hoje os agendamentos aprovados da Agenda, conforme a spec `agenda`. Nenhuma rota existente DEVE (MUST) perder `login_required` ou `permission_required`. O layout público NÃO DEVE (MUST NOT) conter menu, sidebar, usuário, notificações, modal, token CSRF, nem link, ação ou formulário da área autenticada, exceto o link "Entrar" para a página de login.

#### Scenario: Visitante acessa só a rota pública
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa a raiz (`/`) e depois `ensalamento/`
- **THEN** a raiz (`/`) responde 200
- **AND** `ensalamento/` redireciona para a página de login com a indicação da página solicitada

#### Scenario: Grade autenticada protegida como antes
- **GIVEN** um usuário autenticado sem `ENSALAMENTO.VISUALIZAR`
- **WHEN** ele acessa `ensalamento/`
- **THEN** a resposta é 403

#### Scenario: Fonte futura de ocupação não aparece
- **GIVEN** uma fonte de ocupação de teste acrescentada a `grid_sources()` sem ser registrada como pública, com uma ocorrência na sala 10 numa data do intervalo
- **WHEN** o calendário público da sala 10 é aberto nesse intervalo
- **THEN** a ocorrência dessa fonte não aparece

#### Scenario: Layout sem elementos da área autenticada
- **WHEN** um usuário autenticado abre o calendário público
- **THEN** a página não mostra o menu, o nome do usuário, o perfil, as notificações nem o controle de sair
- **AND** a página não contém token CSRF

### Requirement: Dados expostos no calendário público
Cada aula do calendário público DEVE (MUST) mostrar só a data e o horário (pela posição na Grade), a disciplina, o curso e a turma, a sala pelo nome atual ou "Sem sala definida", os docentes pelo nome e, quando houver, o e-mail de cada docente, e o nível pela cor com o texto para tecnologia assistiva. A página NÃO DEVE (MUST NOT) expor IDs de registro, outros nomes do espaço, origem ou situação do espaço, dados da importação, dados de auditoria, nome civil, perfil, permissões, situação ou qualquer outro dado de usuário além do e-mail do docente, solicitações de agendamento, quem aprovou um agendamento, a descrição do agendamento, exceções, nem a marca "Choque". O agendamento aprovado DEVE (MUST) mostrar só o selo "Agendamento", o horário, a sala, o nome e o e-mail de quem solicitou, sem a descrição. Os valores dos filtros na URL e nos campos DEVEM (MUST) ser nomes e códigos, e nunca IDs. A consulta das aulas DEVE (MUST) carregar só as colunas usadas no card.

#### Scenario: Card da aula
- **GIVEN** a alocação de Banco de Dados, Informática 2º ano A, sala 10, docente Aldo Gomes, segunda-feira das 07:00 às 07:50
- **WHEN** o calendário da sala 10 é aberto numa semana do período que contém uma segunda-feira
- **THEN** a célula de segunda-feira das 07:00 às 07:50 mostra "Banco de Dados", "Informática, 2º ano A", "10" e "Aldo Gomes"

#### Scenario: Aula sem sala
- **GIVEN** uma alocação sem espaço do docente Aldo Gomes
- **WHEN** o calendário do docente é aberto numa data dessa aula
- **THEN** o card mostra "Sem sala definida"

#### Scenario: Dados administrativos ausentes
- **GIVEN** a sala 10 criada por uma importação, com o outro nome "Sala Dez", e um registro de auditoria dessa importação
- **WHEN** o calendário da sala 10 é aberto
- **THEN** o HTML não contém "Sala Dez", a origem, a importação, a auditoria, "Choque" nem o ID da sala, do docente, do curso, da turma ou da alocação

### Requirement: Montagem do calendário público
O calendário DEVE (MUST) ser montado com a estrutura da Grade: nas linhas, sempre todas as faixas do semestre, com ou sem aula no resultado, como na Grade autenticada, dias nas colunas, faixas seguidas com as mesmas aulas unidas num bloco e "Hoje" marcado. As aulas da mesma faixa e do mesmo dia DEVEM (MUST) ficar na mesma célula, ordenadas pela sala, pelo curso e pela turma, cada uma com a sua sala. "N turmas juntas" DEVE (MUST) ser indicado só quando as aulas têm a mesma sala, a mesma disciplina e os mesmos docentes. A marca "Choque" NÃO DEVE (MUST NOT) aparecer. Na consulta por sala, por docente ou pelos dois, sem curso e sem nível, os agendamentos aprovados que atendem aos filtros DEVEM (MUST) entrar em todas as faixas que cruzam, e o que não cruza nenhuma faixa DEVE (MUST) ganhar uma linha própria; o do docente é o solicitado pelo usuário cujo `username` é igual ao nome do docente. Na consulta por curso ou por nível, eles NÃO DEVEM (MUST NOT) aparecer. A faixa sem aula DEVE (MUST) ser anunciada à tecnologia assistiva como "disponível" só quando o único filtro principal é a sala; nos demais casos, como "sem aula".

#### Scenario: Turmas em salas diferentes no mesmo horário
- **GIVEN** a turma A na sala 1 e a turma B na sala 2 do curso Informática, com disciplinas diferentes, na mesma faixa
- **WHEN** o calendário do curso Informática é aberto
- **THEN** as duas aulas aparecem na mesma célula, cada uma com a sua sala, sem marca de choque nem de turmas juntas

#### Scenario: Turmas juntas na mesma sala
- **GIVEN** duas turmas de Licenciatura em Física com a mesma disciplina, os mesmos docentes e a mesma sala, na mesma faixa
- **WHEN** o calendário do curso é aberto
- **THEN** a célula mostra "2 turmas juntas"

#### Scenario: Grade completa mesmo sem aula na faixa
- **GIVEN** o curso Informática com aulas até 17:00 e outros cursos com aulas até 22:40
- **WHEN** o calendário do curso Informática é aberto
- **THEN** a Grade mostra todas as faixas do semestre, até a que termina às 22:40, com as células sem aula vazias

#### Scenario: Faixa vazia na consulta por docente
- **WHEN** o calendário do docente Aldo Gomes é aberto e uma faixa de segunda-feira não tem aula dele
- **THEN** o texto para tecnologia assistiva da faixa diz "sem aula", e não "disponível"

### Requirement: Desempenho do calendário público
Uma requisição do calendário público DEVE (MUST) usar no máximo 8 consultas ao banco: semestres, salas, docentes e cursos das opções, faixas do semestre, aulas filtradas, docentes das aulas e e-mails desses docentes; na consulta por sala ou por docente, sem curso e sem nível, DEVE (MUST) usar no máximo 9, com a dos agendamentos aprovados do intervalo. A quantidade NÃO DEVE (MUST NOT) crescer com o número de dias do intervalo, de aulas, de docentes ou de células, e NÃO DEVE (MUST NOT) haver consulta por dia, por célula ou por aula. Os filtros DEVEM (MUST) ser aplicados no banco, e as aulas NÃO DEVEM (MUST NOT) ser carregadas sem filtro para serem filtradas em Python. A consulta dos e-mails DEVE (MUST) receber só os nomes dos docentes das aulas encontradas. A página NÃO DEVE (MUST NOT) gravar sessão, cookie, auditoria ou qualquer registro.

#### Scenario: Consultas iguais numa semana e em 31 dias
- **GIVEN** o docente Aldo Gomes com aulas em várias salas
- **WHEN** o calendário dele é aberto numa semana e depois em 31 dias
- **THEN** as duas requisições usam a mesma quantidade de consultas, no máximo 8

#### Scenario: Sem filtro principal
- **WHEN** o calendário é aberto sem sala, docente ou curso
- **THEN** a requisição usa no máximo 4 consultas, nenhuma delas de alocação

#### Scenario: Página sem gravação
- **WHEN** um visitante abre o calendário da sala 10
- **THEN** nenhum registro de auditoria é criado e a resposta não define cookie
