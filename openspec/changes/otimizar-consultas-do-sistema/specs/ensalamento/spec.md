## ADDED Requirements

### Requirement: Consultas da execução da importação do ensalamento
A execução das linhas da importação do ensalamento, na prévia, na atualização da prévia e na confirmação, DEVE (MUST) ter uma quantidade de consultas ao banco limitada pelos registros distintos da planilha, e não pela quantidade de linhas. Um curso, uma turma, uma disciplina, uma faixa de horário ou um docente já resolvido numa execução NÃO DEVE (MUST NOT) ser procurado de novo no banco com a mesma grafia na mesma execução. As alocações do semestre, com o espaço e os docentes delas, DEVEM (MUST) ser lidas uma vez por execução, junto da trava que a execução já faz, e a trava NÃO DEVE (MUST NOT) alcançar outras tabelas além das alocações. A oferta de cada disciplina para cada turma e os vínculos de docente DEVEM (MUST) ser sincronizados uma vez por execução, depois das linhas, só para as linhas mantidas.

A otimização NÃO DEVE (MUST NOT) mudar o resultado. Para os mesmos dados, o plano de cada linha (ação, alvo, mudanças, avisos, pendências e erros), a situação da importação, as alocações com o espaço e os docentes, as ofertas, os vínculos de docente com a indicação de atual, o cadastro de espaços e os registros de auditoria DEVEM (MUST) ser os mesmos que antes da otimização. A comparação de duas grafias sem diferenciar a caixa DEVE (MUST) continuar sendo decidida pelo banco, como antes, e não por uma regra própria da memória da execução.

#### Scenario: Mais linhas com os mesmos catálogos
- **GIVEN** duas planilhas do mesmo semestre com os mesmos cursos, turmas, disciplinas, faixas, docentes e espaços, a segunda com o dobro de linhas de atividade
- **WHEN** a prévia de cada uma é gerada
- **THEN** a quantidade de consultas da segunda prévia é menor que o dobro da quantidade da primeira

#### Scenario: Plano igual ao de antes da otimização
- **GIVEN** a planilha `planilha_example_sugerida_corrigida.xlsx` e o plano gerado para ela antes da otimização
- **WHEN** a prévia, a atualização depois das decisões, a confirmação e a reimportação são executadas
- **THEN** o plano de cada linha e o estado das alocações, ofertas, vínculos de docente e espaços são iguais aos de antes

#### Scenario: Grafias que diferem só na caixa
- **GIVEN** uma planilha em que uma linha cita a disciplina `Química Geral` e outra cita `QUÍMICA GERAL`
- **WHEN** a prévia é gerada
- **THEN** as duas linhas usam a mesma disciplina, e só uma é criada

#### Scenario: Oferta só das linhas mantidas
- **GIVEN** uma planilha em que a única linha da disciplina `Patologia Florestal` para o `6º PERÍODO` é recusada com erro
- **WHEN** a importação é confirmada
- **THEN** nenhuma oferta dessa disciplina para essa turma é criada

#### Scenario: Trava restrita às alocações
- **GIVEN** uma importação de `2026/1`
- **WHEN** a execução trava as alocações do semestre
- **THEN** a trava alcança só as alocações de `2026/1`, e os espaços e os docentes delas continuam livres para outras transações
