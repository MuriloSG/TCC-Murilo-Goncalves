## MODIFIED Requirements

### Requirement: Desempenho do calendário público
Uma requisição do calendário público DEVE (MUST) usar no máximo 8 consultas ao banco: semestres, salas, docentes e cursos das opções, faixas do semestre, aulas filtradas, docentes das aulas e e-mails desses docentes. A quantidade NÃO DEVE (MUST NOT) crescer com o número de dias do intervalo, de aulas, de docentes ou de células, e NÃO DEVE (MUST NOT) haver consulta por dia, por célula ou por aula. Os filtros DEVEM (MUST) ser aplicados no banco, e as aulas NÃO DEVEM (MUST NOT) ser carregadas sem filtro para serem filtradas em Python. A consulta dos e-mails DEVE (MUST) receber só os nomes dos docentes das aulas encontradas. Quando as opções do semestre estiverem no cache público, a requisição NÃO DEVE (MUST NOT) consultar semestres, salas, docentes nem cursos no banco. A página NÃO DEVE (MUST NOT) gravar sessão, cookie, auditoria ou qualquer registro no banco; a gravação no cache público não é registro. O conteúdo da página DEVE (MUST) ser o mesmo com e sem o cache público.

#### Scenario: Consultas iguais numa semana e em 31 dias
- **GIVEN** o docente Aldo Gomes com aulas em várias salas
- **WHEN** o calendário dele é aberto numa semana e depois em 31 dias
- **THEN** as duas requisições usam a mesma quantidade de consultas, no máximo 8

#### Scenario: Sem filtro principal
- **WHEN** o calendário é aberto sem sala, docente ou curso
- **THEN** a requisição usa no máximo 4 consultas, nenhuma delas de alocação

#### Scenario: Sem filtro principal com as opções em cache
- **GIVEN** as opções do semestre já estão no cache público
- **WHEN** o calendário é aberto sem sala, docente ou curso
- **THEN** a requisição não faz nenhuma consulta ao banco

#### Scenario: Mesmo conteúdo com e sem cache
- **WHEN** o calendário da sala 10 é aberto com o cache público desligado, com o cache vazio e com o cache preenchido
- **THEN** as três respostas mostram os mesmos filtros e a mesma Grade

#### Scenario: Página sem gravação
- **WHEN** um visitante abre o calendário da sala 10
- **THEN** nenhum registro de auditoria é criado e a resposta não define cookie
