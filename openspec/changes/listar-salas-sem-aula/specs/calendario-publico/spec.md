## MODIFIED Requirements

### Requirement: Filtros do calendário público
O calendário público DEVE (MUST) aceitar pela URL os filtros `semestre` (código do semestre letivo), `sala` (nome atual do espaço), `docente` (nome do docente), `curso` (nome do curso), `nivel` (`graduacao` ou `ensino-medio`, exibidos como "Graduação" e "Ensino médio"), `inicio` e `fim` (datas `aaaa-mm-dd`). Os filtros DEVEM (MUST) ser combinados por "e" e aplicados na consulta ao banco. O nome informado DEVE (MUST) ser comparado sem diferenciar maiúsculas de minúsculas com as opções carregadas, e só o registro encontrado DEVE (MUST) entrar na consulta. Um valor fora das opções, com mais de 200 caracteres ou fora do formato DEVE (MUST) ser descartado sem mensagem. As opções DEVEM (MUST) ser: todos os espaços ativos, com ou sem alocação no semestre, e os inativos com alocação no semestre, na ordem natural do nome; os docentes com alocação no semestre; os cursos com turma alocada no semestre; os dois níveis que o sistema já tem. As opções NÃO DEVEM (MUST NOT) depender dos demais filtros. O sistema NÃO DEVE (MUST NOT) oferecer filtro pelo período ou ano da turma, nem outros níveis.

#### Scenario: Docente e sala combinados
- **GIVEN** o docente Aldo Gomes com aulas nas salas 10 e 12
- **WHEN** o calendário é aberto com `docente=Aldo Gomes&sala=10`
- **THEN** só as aulas dele na sala 10 aparecem

#### Scenario: Curso e nível incompatíveis
- **GIVEN** o curso Informática, de Ensino médio
- **WHEN** o calendário é aberto com `curso=Informática&nivel=graduacao`
- **THEN** a Grade aparece com as células vazias, sem erro e sem mensagem

#### Scenario: Valor desconhecido descartado
- **WHEN** o calendário é aberto com `sala=Inexistente&docente=Aldo Gomes`
- **THEN** o filtro de sala volta para todas as salas e o calendário mostra as aulas de Aldo Gomes

#### Scenario: Sala inativa com aula
- **GIVEN** a sala 7, inativa, com alocação no semestre `2026/2`
- **WHEN** as opções de sala de `2026/2` são montadas
- **THEN** a sala 7 está entre elas

#### Scenario: Sala ativa sem aula
- **GIVEN** a sala 1/3, ativa, sem alocação no semestre `2026/2`
- **WHEN** o calendário é aberto com `sala=1/3` e uma semana do semestre
- **THEN** a sala 1/3 está entre as opções
- **AND** a Grade aparece com as faixas do semestre e as células vazias

#### Scenario: Sala inativa sem aula
- **GIVEN** a sala 8, inativa, sem alocação no semestre `2026/2`
- **WHEN** as opções de sala de `2026/2` são montadas
- **THEN** a sala 8 não está entre elas

#### Scenario: Curso sem aula fora das opções
- **GIVEN** um curso sem turma alocada no semestre `2026/2`
- **WHEN** as opções de curso de `2026/2` são montadas
- **THEN** esse curso não está entre elas
