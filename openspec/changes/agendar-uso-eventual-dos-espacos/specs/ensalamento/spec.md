## MODIFIED Requirements

### Requirement: Fontes de ocupação separadas
O cálculo das ocorrências DEVE (MUST) reunir uma lista explícita de fontes de ocupação, e cada ocorrência DEVE (MUST) informar o seu tipo. A Grade do Ensalamento DEVE (MUST) usar só a fonte do ensalamento, com o tipo `ENSALAMENTO`. A Grade DEVE (MUST) ser montada só a partir das ocorrências, sem ler `Allocation` diretamente, para que outra área, como a Agenda, monte a sua própria lista de fontes sobre a mesma estrutura da Grade sem mudar a Grade do Ensalamento. A Grade do Ensalamento NÃO DEVE (MUST NOT) criar, alterar nem excluir ocupação de nenhuma fonte, e NÃO DEVE (MUST NOT) oferecer formulário, botão ou clique que o faça. Em particular, a Grade do Ensalamento NÃO DEVE (MUST NOT) criar, editar nem cancelar agendamento e NÃO DEVE (MUST NOT) ter formulário de solicitação de agendamento. Solicitações e agendamentos DEVEM (MUST) ser criados e mantidos pela Agenda, conforme a spec `agenda`. O ensalamento NÃO DEVE (MUST NOT) implementar edição de alocação, versão de alocação nem exceção por data.

#### Scenario: Fonte a mais
- **GIVEN** uma fonte de teste que devolve uma ocorrência de outro tipo na sala `1/13`, em 06/10/2026, na faixa `21:00 - 21:50`
- **WHEN** a Grade da semana é montada com o ensalamento e essa fonte
- **THEN** a faixa mostra a ocorrência da fonte de teste e deixa de contar como disponível

#### Scenario: Grade só consulta
- **WHEN** as rotas e os templates da Grade do Ensalamento são inspecionados
- **THEN** nenhum deles cria, altera ou exclui alocação
- **AND** não existe rota, formulário nem botão que crie, edite ou cancele agendamento

#### Scenario: Grade do Ensalamento sem agendamentos
- **GIVEN** um agendamento aprovado na sala `1/13`
- **WHEN** a Grade do Ensalamento da semana do agendamento é aberta para a sala
- **THEN** o agendamento não aparece e a faixa continua como no ensalamento
