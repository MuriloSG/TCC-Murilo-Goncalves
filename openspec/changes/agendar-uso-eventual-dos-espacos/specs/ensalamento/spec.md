## MODIFIED Requirements

### Requirement: Fontes de ocupação separadas
O cálculo das ocorrências DEVE (MUST) reunir uma lista explícita de fontes de ocupação, e cada ocorrência DEVE (MUST) informar o seu tipo. As fontes DEVEM (MUST) ser o ensalamento, com o tipo `ENSALAMENTO`, e as registradas por outros apps por `register_source`, como os agendamentos aprovados da Agenda, com o tipo `AGENDAMENTO`, sem que o ensalamento dependa desses apps. A Grade DEVE (MUST) ser montada só a partir das ocorrências, sem ler `Allocation` diretamente, e uma ocorrência que não coincide com as faixas do semestre DEVE (MUST) aparecer em todas as faixas que cruza. A Grade do Ensalamento NÃO DEVE (MUST NOT) criar, alterar nem excluir ocupação de nenhuma fonte, e NÃO DEVE (MUST NOT) oferecer formulário, botão ou clique que o faça. Em particular, a Grade do Ensalamento NÃO DEVE (MUST NOT) criar, editar nem cancelar agendamento e NÃO DEVE (MUST NOT) ter formulário de solicitação de agendamento. Solicitações e agendamentos DEVEM (MUST) ser criados e mantidos pela Agenda, conforme a spec `agenda`. A marca de choque e a de turmas juntas DEVEM (MUST) considerar só as aulas. O ensalamento NÃO DEVE (MUST NOT) implementar edição de alocação, versão de alocação nem exceção por data.

#### Scenario: Fonte a mais
- **GIVEN** uma fonte de teste que devolve uma ocorrência de outro tipo na sala `1/13`, em 06/10/2026, na faixa `21:00 - 21:50`
- **WHEN** a Grade da semana é montada com o ensalamento e essa fonte
- **THEN** a faixa mostra a ocorrência da fonte de teste e deixa de contar como disponível

#### Scenario: Grade só consulta
- **WHEN** as rotas e os templates da Grade do Ensalamento são inspecionados
- **THEN** nenhum deles cria, altera ou exclui alocação
- **AND** não existe rota, formulário nem botão que crie, edite ou cancele agendamento

#### Scenario: Agendamento aprovado na Grade do Ensalamento
- **GIVEN** um agendamento aprovado na sala `1/13`, das 14:30 às 15:30
- **WHEN** a Grade do Ensalamento da semana do agendamento é aberta para a sala
- **THEN** o agendamento aparece com o selo "Agendamento" em todas as faixas que cruza, sem ação de solicitar
