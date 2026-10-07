## ADDED Requirements

### Requirement: Horário original
O sistema DEVE (MUST) oferecer, sem autenticação, em `/horario-original/`, a semana típica do semestre só com as alocações importadas, sem as versões das alterações de recorrência, sem as ocorrências canceladas e sem os agendamentos, com os mesmos filtros do calendário público, exceto as datas.

#### Scenario: Ocorrência cancelada continua no horário original
- **WHEN** a aula de Matemática de segunda tem uma ocorrência cancelada e o visitante abre o horário original da sala
- **THEN** a aula aparece na segunda-feira da semana típica

#### Scenario: Alteração de recorrência não muda o horário original
- **WHEN** uma aula importada é alterada de segunda para terça
- **THEN** o horário original mostra a aula na segunda e não mostra a versão de terça

#### Scenario: Alternar entre as telas mantém os filtros
- **WHEN** o visitante escolhe uma sala no calendário público e clica em "Ver horário original"
- **THEN** o horário original abre com a mesma sala, sem as datas
