## ADDED Requirements

### Requirement: Período do semestre
O semestre DEVE (MUST) poder ter um período, com uma data de início e uma data de fim, gravadas juntas ou nenhuma das duas. A data de início DEVE (MUST) ser anterior ou igual à de fim, e um período maior que 366 dias DEVE (MUST) ser recusado. A regra DEVE (MUST) ser uma operação do model, numa transação, e a recusa NÃO DEVE (MUST NOT) alterar o semestre. Um semestre sem período DEVE (MUST) continuar válido, e a importação NÃO DEVE (MUST NOT) exigir nem alterar o período.

#### Scenario: Período definido
- **GIVEN** o semestre `2026/2` sem período
- **WHEN** o período de 03/08/2026 a 18/12/2026 é definido
- **THEN** o semestre passa a ter esse início e esse fim

#### Scenario: Início depois do fim
- **WHEN** o período de 18/12/2026 a 03/08/2026 é definido para `2026/2`
- **THEN** a operação é recusada e o semestre continua como estava

#### Scenario: Importação sem período
- **GIVEN** o semestre `2026/2` sem período
- **WHEN** uma planilha é importada e confirmada para `2026/2`
- **THEN** a importação conclui e o semestre continua sem período

### Requirement: Definição do período pela Grade
Um usuário com `ENSALAMENTO.IMPORTAR` DEVE (MUST) poder definir o período do semestre por um modal "Definir período", aberto pela Grade, conforme as convenções de ações em modal. A definição DEVE (MUST) gerar um registro de auditoria `ALTERAR` do recurso `SEMESTRE`, com o código, o período anterior e o novo. O botão "Definir período" NÃO DEVE (MUST NOT) aparecer para quem não tem a permissão, e a rota DEVE (MUST) responder 403 a esse usuário. Quando o semestre escolhido não tem período, a Grade DEVE (MUST) mostrar a semana típica sem datas, como antes desta Change, com o aviso "Período do semestre 2026/2 não definido.", e a visão mensal DEVE (MUST) mostrar o mesmo aviso no lugar do mês.

#### Scenario: Definição pelo modal
- **GIVEN** um usuário com `ENSALAMENTO.VISUALIZAR` e `ENSALAMENTO.IMPORTAR`, e o semestre `2026/2` sem período
- **WHEN** ele abre "Definir período" na Grade e informa 03/08/2026 e 18/12/2026
- **THEN** o período é gravado, a Grade de `2026/2` é aberta com datas e existe um registro de auditoria da alteração do semestre

#### Scenario: Consulta sem permissão de definir
- **GIVEN** um usuário cujo perfil concede somente `ENSALAMENTO.VISUALIZAR`
- **WHEN** ele abre a Grade de um semestre sem período
- **THEN** a Grade mostra a semana típica e o aviso, sem o botão "Definir período"
- **AND** a rota do modal responde 403

#### Scenario: Acesso à rota do período
- **WHEN** a rota do período é acessada por um anônimo, por um usuário sem `ENSALAMENTO.IMPORTAR`, por um usuário com a permissão e por um POST sem CSRF
- **THEN** as respostas são, na ordem, o redirecionamento ao login com `next`, 403, o modal e 403

### Requirement: Ocorrências calculadas das alocações
Cada alocação DEVE (MUST) continuar sendo uma regra semanal do semestre, e o sistema NÃO DEVE (MUST NOT) gravar uma linha por data em que a aula ocorre. As ocorrências de um espaço num intervalo de datas DEVEM (MUST) ser calculadas na consulta: uma ocorrência por alocação do espaço, em cada data do intervalo que esteja no período do semestre da alocação e cujo dia da semana seja o da alocação, com a data, o início e o fim da faixa. Uma alocação sem espaço NÃO DEVE (MUST NOT) gerar ocorrência em espaço nenhum. O cálculo DEVE (MUST) aceitar qualquer intervalo, inclusive um que atravesse dois semestres, e DEVE (MUST) usar uma quantidade fixa de consultas ao banco, que não cresça com o tamanho do intervalo. O cálculo NÃO DEVE (MUST NOT) gravar dados. Nesta versão a alocação DEVE (MUST) representar só a regra vigente, e o sistema NÃO DEVE (MUST NOT) ter vigência própria da alocação, versão de regra nem registro de histórico dela; por isso a atualização de uma alocação pela reimportação PODE (MAY) mudar a representação das semanas anteriores.

#### Scenario: Reimportação muda as semanas anteriores
- **GIVEN** uma alocação na sala `3/8` e o semestre com período
- **WHEN** uma reimportação muda a sala dessa alocação para `3/9`
- **THEN** as ocorrências das semanas anteriores e das seguintes passam a ser da sala `3/9`

#### Scenario: Aula semanal numa semana
- **GIVEN** o semestre `2026/2` de 03/08/2026 a 18/12/2026 e uma alocação na sala `1/13`, às segundas-feiras, na faixa `19:00 - 19:50`
- **WHEN** as ocorrências da sala `1/13` de 05/10/2026 a 09/10/2026 são calculadas
- **THEN** existe uma ocorrência dessa alocação, em 05/10/2026, das 19:00 às 19:50

#### Scenario: Data fora do período
- **GIVEN** o mesmo semestre e a mesma alocação
- **WHEN** as ocorrências da sala de 27/07/2026 a 31/07/2026 são calculadas
- **THEN** nenhuma ocorrência é devolvida

#### Scenario: Nenhuma linha por data
- **GIVEN** um semestre importado com período definido
- **WHEN** as ocorrências de um mês e depois de todo o semestre são calculadas
- **THEN** a quantidade de registros do banco não muda
- **AND** as duas consultas usam a mesma quantidade de consultas ao banco

#### Scenario: Semestre sem período
- **GIVEN** o semestre `2026/1` sem período, com alocações
- **WHEN** as ocorrências de um intervalo de 2026 são calculadas
- **THEN** nenhuma ocorrência de `2026/1` é devolvida

### Requirement: Fontes de ocupação separadas
O cálculo das ocorrências DEVE (MUST) reunir uma lista explícita de fontes de ocupação, e cada ocorrência DEVE (MUST) informar o seu tipo. Nesta versão a única fonte DEVE (MUST) ser o ensalamento, com o tipo `ENSALAMENTO`. A Grade DEVE (MUST) ser montada só a partir das ocorrências, sem ler `Allocation` diretamente, para que outra fonte, como a reserva de uma funcionalidade futura, apareça na Grade sem mudança na estrutura da Grade. A Grade NÃO DEVE (MUST NOT) criar, alterar nem excluir ocupação de nenhuma fonte, e NÃO DEVE (MUST NOT) oferecer formulário, botão ou clique que o faça. Em particular, a Grade NÃO DEVE (MUST NOT) criar reserva, NÃO DEVE (MUST NOT) editar reserva, NÃO DEVE (MUST NOT) cancelar reserva e NÃO DEVE (MUST NOT) ter formulário de reserva. As reservas DEVEM (MUST) ser criadas e mantidas por uma tela própria, de uma funcionalidade posterior, e a Grade DEVE (MUST) apenas recebê-las como uma fonte adicional de ocupação. Esta Change NÃO DEVE (MUST NOT) implementar reserva, edição de alocação, versão de alocação nem exceção por data.

#### Scenario: Fonte a mais
- **GIVEN** uma fonte de teste que devolve uma ocorrência de outro tipo na sala `1/13`, em 06/10/2026, na faixa `21:00 - 21:50`
- **WHEN** a Grade da semana é montada com o ensalamento e essa fonte
- **THEN** a faixa mostra a ocorrência da fonte de teste e deixa de contar como disponível

#### Scenario: Grade só consulta
- **WHEN** as rotas e os templates da Grade são inspecionados
- **THEN** nenhum deles cria, altera ou exclui alocação
- **AND** não existe rota, formulário nem botão que crie, edite ou cancele reserva

### Requirement: Visão semanal com datas
Quando o semestre tem período, a visão semanal DEVE (MUST) mostrar uma semana de segunda a sexta com a data de cada dia, as faixas com aula no semestre nas linhas e as ocorrências da sala em cada faixa, com o card atual. A semana DEVE (MUST) vir do parâmetro `semana`, que é qualquer data dela, e o padrão DEVE (MUST) ser a semana de hoje quando hoje estiver no período, a primeira semana do período antes dele e a última depois dele. Um valor de `semana` inválido DEVE (MUST) cair no padrão, com a resposta 200. A visão DEVE (MUST) ter os links "Semana anterior", "Próxima semana" e "Hoje", funcionando com e sem JavaScript, e DEVE (MUST) marcar como "Hoje" a coluna da data de hoje. O dia fora do período DEVE (MUST) mostrar "Fora do semestre" e NÃO DEVE (MUST NOT) entrar na contagem de faixas ocupadas e disponíveis. Faixas seguidas com as mesmas ocorrências, sem intervalo entre elas, DEVEM (MUST) continuar aparecendo como um bloco.

#### Scenario: Semana padrão dentro do período
- **GIVEN** hoje é 07/10/2026 e o semestre `2026/2` vai de 03/08/2026 a 18/12/2026
- **WHEN** a Grade é aberta sem `semana`
- **THEN** a semana mostrada vai de 05/10/2026 a 09/10/2026, com a quarta-feira marcada como "Hoje"

#### Scenario: Navegação para a próxima semana
- **WHEN** "Próxima semana" é acionado na semana de 05/10/2026
- **THEN** a Grade mostra a semana de 12/10/2026 a 16/10/2026, e a URL tem `semana` com uma data dessa semana

#### Scenario: Semana que começa antes do período
- **GIVEN** o semestre começa na quarta-feira, 05/08/2026
- **WHEN** a semana de 03/08/2026 é mostrada
- **THEN** segunda e terça mostram "Fora do semestre" e a contagem considera só quarta, quinta e sexta

#### Scenario: Semana inválida
- **WHEN** a Grade é aberta com `semana=abc`
- **THEN** a semana padrão é mostrada e a resposta é 200

### Requirement: Visão mensal
A Grade DEVE (MUST) permitir alternar entre as visões "Semana" e "Mês", preservando o semestre, a sala e a data de referência. A visão mensal DEVE (MUST) ser um mapa da ocupação do ensalamento no mês, calculado pelas mesmas ocorrências e pelas mesmas faixas do semestre da visão semanal, sem estrutura de dados gravada própria, e NÃO DEVE (MUST NOT) ser uma tela de criação de reserva. Ela DEVE (MUST) mostrar as semanas do mês de segunda a sexta, e cada dia do mês dentro do período DEVE (MUST) indicar visualmente se tem ocupação e quantas faixas estão ocupadas, com texto e não só com cor, e com a data e as contagens no nome acessível do dia. O dia fora do período DEVE (MUST) mostrar "Fora do semestre", sem contagem. O mês DEVE (MUST) vir do parâmetro `mes`, no formato `AAAA-MM`, com o padrão no mês de hoje quando hoje estiver no período, no primeiro mês do período antes dele e no último depois dele, e um valor inválido DEVE (MUST) cair no padrão com 200. A visão DEVE (MUST) ter os links "Mês anterior", "Próximo mês" e "Hoje", e NÃO DEVE (MUST NOT) navegar para mês que não toque o período do semestre. Cada dia DEVE (MUST) ser um link para a visão semanal da semana dele, e NÃO DEVE (MUST NOT) abrir formulário nem modal.

#### Scenario: Mês com aula semanal
- **GIVEN** o semestre `2026/2` de 03/08/2026 a 18/12/2026 e uma alocação na sala `1/13`, às segundas-feiras, das 19:00 às 19:50
- **WHEN** a visão mensal de outubro de 2026 da sala `1/13` é exibida
- **THEN** as segundas-feiras 05/10, 12/10, 19/10 e 26/10 aparecem com uma faixa ocupada, e os demais dias com nenhuma

#### Scenario: Mesmo cálculo nas duas visões
- **GIVEN** uma sala com ocorrências em 05/10/2026
- **WHEN** a visão semanal de 05/10/2026 e a visão mensal de outubro são exibidas
- **THEN** a quantidade de faixas ocupadas e disponíveis de 05/10/2026 é a mesma nas duas

#### Scenario: Dia abre a semana
- **WHEN** o dia 14/10/2026 é acionado na visão mensal
- **THEN** a visão semanal de 12/10/2026 a 16/10/2026 é aberta, na mesma sala e no mesmo semestre

#### Scenario: Limite do semestre
- **GIVEN** o semestre `2026/2` de 03/08/2026 a 18/12/2026
- **WHEN** a visão mensal de agosto de 2026 é exibida
- **THEN** o link "Mês anterior" está desabilitado, e 03/08/2026 é o primeiro dia com contagem

#### Scenario: Mês inválido
- **WHEN** a Grade é aberta com `visao=mes&mes=2026-13`
- **THEN** o mês padrão é mostrado e a resposta é 200

### Requirement: Faixas disponíveis sem poluição visual
Toda faixa do semestre sem ocorrência numa data do período DEVE (MUST) aparecer na visão semanal como célula visualmente vazia, e NÃO DEVE (MUST NOT) mostrar texto visível em cada célula disponível. A célula DEVE (MUST) informar à tecnologia assistiva que a faixa está disponível, com o dia, a data e o horário. A faixa disponível NÃO DEVE (MUST NOT) ser apresentada como erro nem confundida com ausência de dados: o dia fora do período DEVE (MUST) mostrar "Fora do semestre", e o semestre sem período ou sem ensalamento DEVE (MUST) mostrar o aviso próprio, e não uma grade vazia. "Disponível" DEVE (MUST) ser um estado calculado, e o sistema NÃO DEVE (MUST NOT) gravar registro de faixa disponível. As faixas disponíveis DEVEM (MUST) entrar na contagem da faixa de situação. O texto exibido DEVE (MUST) usar "disponível" e "ocupado", e NÃO DEVE (MUST NOT) usar "livre" nem "vago".

#### Scenario: Faixa sem aula
- **GIVEN** a sala `1/13` com aula às segundas-feiras das 19:00 às 20:40 e nenhuma na faixa `21:00 - 21:50`
- **WHEN** a semana de 05/10/2026 é exibida
- **THEN** a célula da faixa `21:00 - 21:50` da segunda-feira não tem texto visível
- **AND** o nome acessível dela informa segunda-feira, 05/10/2026, das 21:00 às 21:50, disponível

#### Scenario: Disponível não é fora do semestre
- **GIVEN** o semestre começa na quarta-feira, 05/08/2026
- **WHEN** a semana de 03/08/2026 é exibida
- **THEN** segunda e terça mostram "Fora do semestre", e as faixas sem aula de quarta a sexta ficam vazias e disponíveis

#### Scenario: Dia sem ocupação no celular
- **GIVEN** uma sala sem nenhuma ocorrência em 09/10/2026
- **WHEN** a semana é exibida abaixo de 640 px
- **THEN** a sexta-feira mostra "Sala disponível o dia todo."
