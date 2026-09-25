## ADDED Requirements

### Requirement: Período do semestre
O semestre DEVE (MUST) poder ter um período, com uma data de início e uma data de fim, gravadas juntas ou nenhuma das duas, e o semestre DEVE (MUST) ser o único lugar em que o período é guardado. A data de início DEVE (MUST) ser anterior ou igual à de fim, e um período maior que 366 dias DEVE (MUST) ser recusado. A regra DEVE (MUST) ser uma operação do model, e a recusa NÃO DEVE (MUST NOT) alterar o semestre. Um semestre sem período DEVE (MUST) continuar válido.

#### Scenario: Período definido
- **GIVEN** o semestre `2026/2` sem período
- **WHEN** o período de 03/08/2026 a 18/12/2026 é definido
- **THEN** o semestre passa a ter esse início e esse fim

#### Scenario: Início depois do fim
- **WHEN** o período de 18/12/2026 a 03/08/2026 é definido para `2026/2`
- **THEN** a operação é recusada e o semestre continua como estava

### Requirement: Período do semestre informado na importação
O envio da importação de ensalamento DEVE (MUST) oferecer, além do arquivo e do semestre, os campos "Início do semestre" e "Fim do semestre", e as datas informadas DEVEM (MUST) ser gravadas nos valores de todas as linhas, como os demais campos próprios do envio, e aplicadas ao semestre da importação a partir desses valores. As duas datas DEVEM (MUST) ser informadas juntas: uma data preenchida com a outra vazia DEVE (MUST) ser erro do formulário de envio, sem criar importação. Quando o semestre informado ainda não existe ou não tem período, o início e o fim DEVEM (MUST) ser obrigatórios. O sistema NÃO DEVE (MUST NOT) inferir o fim a partir do código do semestre. Datas que o model recusa DEVEM (MUST) ser erro do formulário de envio, sem criar importação. O período DEVE (MUST) ser aplicado na mesma transação da execução: a prévia NÃO DEVE (MUST NOT) alterar o semestre, a confirmação DEVE (MUST) gravar o período junto com as alocações, e o descarte, a divergência do plano e a importação com erros NÃO DEVEM (MUST NOT) alterar o semestre. Numa reimportação de um semestre com período, as duas datas preenchidas DEVEM (MUST) substituir o período, e as duas em branco DEVEM (MUST) preservar o período existente; a importação NÃO DEVE (MUST NOT) apagar o período. Como as ocorrências são calculadas do período atual, a mudança do período PODE (MAY) mudar a visualização de semanas e meses anteriores. O resumo da importação DEVE (MUST) mostrar o período informado uma vez, em dd/mm/aaaa, e o registro de auditoria da confirmação DEVE (MUST) conter o período informado e, quando ele mudou, o anterior, sem registro de auditoria separado do semestre.

A Grade NÃO DEVE (MUST NOT) oferecer ação, botão, modal ou rota para definir ou alterar o período, e DEVE (MUST) apenas consumir o período do semestre. Quando o semestre escolhido não tem período, a Grade DEVE (MUST) mostrar a semana típica sem datas, sem o campo "Visualização", com o aviso "Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre.", e um pedido da visão mensal DEVE (MUST) mostrar essa mesma semana típica com o aviso.

#### Scenario: Período na primeira importação
- **GIVEN** o semestre `2026/2` ainda não importado
- **WHEN** a planilha é enviada para `2026/2` com o início 03/08/2026 e o fim 18/12/2026, e a importação é confirmada
- **THEN** o semestre `2026/2` tem o período de 03/08/2026 a 18/12/2026
- **AND** o resumo auditado da confirmação contém o semestre, o início e o fim

#### Scenario: Prévia não altera o período
- **GIVEN** o semestre `2026/2` com o período de 03/08/2026 a 18/12/2026
- **WHEN** a prévia de uma importação de `2026/2` com o início 10/08/2026 é gerada e depois descartada
- **THEN** o semestre continua com o período de 03/08/2026 a 18/12/2026

#### Scenario: Reimportação com datas novas
- **GIVEN** o semestre `2026/2` com o período de 03/08/2026 a 18/12/2026
- **WHEN** a planilha é importada e confirmada de novo com o início 10/08/2026 e o fim 18/12/2026
- **THEN** o período passa a ser de 10/08/2026 a 18/12/2026
- **AND** o resumo auditado contém o período anterior e o novo

#### Scenario: Reimportação sem datas
- **GIVEN** o semestre `2026/2` com o período de 03/08/2026 a 18/12/2026
- **WHEN** a planilha é importada e confirmada de novo com as datas em branco
- **THEN** o semestre continua com o período de 03/08/2026 a 18/12/2026

#### Scenario: Datas recusadas no envio
- **WHEN** a planilha é enviada com o início 18/12/2026 e o fim 03/08/2026, só com o início ou só com o fim
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Primeira importação sem datas
- **GIVEN** o semestre `2026/2` ainda não importado, ou existente sem período
- **WHEN** a planilha é enviada para `2026/2` com as duas datas em branco
- **THEN** o formulário de envio mostra que o início e o fim são obrigatórios, e nenhuma importação é criada

#### Scenario: Grade sem definição de período
- **WHEN** a Grade é aberta por um usuário com `ENSALAMENTO.VISUALIZAR` e `ENSALAMENTO.IMPORTAR`
- **THEN** não há botão, modal nem rota para definir o período

#### Scenario: Semestre sem período na Grade
- **GIVEN** o semestre `2026/2` importado sem período
- **WHEN** a Grade de `2026/2` é aberta, com ou sem `visao=mes`
- **THEN** ela mostra a semana típica sem datas, sem o campo "Visualização", e o aviso "Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre."

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
A Grade DEVE (MUST) oferecer, quando o semestre tem período, um campo de seleção "Visualização" junto dos filtros, com as opções "Semana" e "Mês", e NÃO DEVE (MUST NOT) fazer essa troca por abas. Trocar a opção DEVE (MUST) abrir a visualização escolhida mantendo o semestre e a sala: da semana, abre o mês da segunda-feira dela; do mês, abre a semana de hoje, quando hoje está no mês, ou a do primeiro dia do mês no período. A troca DEVE (MUST) funcionar com e sem JavaScript. A visão mensal DEVE (MUST) ser a mesma Grade da visão semanal, com as mesmas faixas do semestre nas linhas e uma coluna por dia útil do mês, de segunda a sexta, com o número do dia e o dia da semana abreviado (`01 TER`). Ela DEVE (MUST) ser montada pelas mesmas ocorrências e pela mesma estrutura da visão semanal, mudando só o intervalo consultado, sem estrutura de dados própria do mês e sem gravar dados. As células DEVEM (MUST) seguir as regras da visão semanal: o card com a disciplina, a turma com o curso e os docentes, a cor da etapa, as faixas seguidas num bloco, as turmas juntas e o choque agrupados, a faixa disponível visualmente vazia e o dia fora do período com "Fora do semestre". A visão mensal NÃO DEVE (MUST NOT) resumir o dia em marcas, contagens ou lista de eventos no lugar da Grade. Quando os dias não couberem na largura, a Grade DEVE (MUST) rolar na horizontal dentro da própria área, com a coluna de horários e a linha dos dias sempre à vista, e a página NÃO DEVE (MUST NOT) rolar na horizontal. Abaixo de 640 px, a visão mensal DEVE (MUST) continuar sendo a Grade. O mês DEVE (MUST) vir do parâmetro `mes`, no formato `AAAA-MM`, com o padrão no mês de hoje quando hoje estiver no período, no primeiro mês do período antes dele e no último depois dele, e um valor inválido DEVE (MUST) cair no padrão com 200. A visão DEVE (MUST) ter os links "Mês anterior", "Hoje" e "Próximo mês", e NÃO DEVE (MUST NOT) navegar para mês que não toque o período do semestre. "Hoje" DEVE (MUST) abrir o mês atual e levar a Grade até a coluna do dia atual. A visão mensal NÃO DEVE (MUST NOT) criar, editar nem cancelar ocupação.

#### Scenario: Mês com aula semanal
- **GIVEN** o semestre `2026/2` de 03/08/2026 a 18/12/2026 e uma alocação na sala `1/13`, às segundas-feiras, das 19:00 às 19:50
- **WHEN** a visão mensal de outubro de 2026 da sala `1/13` é exibida
- **THEN** as colunas vão de `01 QUI` a `30 SEX`, só com dias úteis
- **AND** as colunas `05 SEG`, `12 SEG`, `19 SEG` e `26 SEG` mostram o card da aula na faixa `19:00 - 19:50`, e as demais colunas deixam essa faixa vazia

#### Scenario: Mesmo cálculo nas duas visões
- **GIVEN** uma sala com ocorrências em 05/10/2026
- **WHEN** a visão semanal de 05/10/2026 e a visão mensal de outubro são exibidas
- **THEN** a coluna de 05/10/2026 tem as mesmas células nas duas visões

#### Scenario: Turmas juntas no mês
- **GIVEN** duas turmas com a mesma disciplina e a mesma docente na sala, no mesmo dia e faixa
- **WHEN** a visão mensal é exibida
- **THEN** a célula desse dia mostra os dois cards sob "2 turmas juntas"

#### Scenario: Limite do semestre
- **GIVEN** o semestre `2026/2` de 05/08/2026 a 18/12/2026
- **WHEN** a visão mensal de agosto de 2026 é exibida
- **THEN** o link "Mês anterior" está desabilitado, e as colunas de 03/08 e 04/08 mostram "Fora do semestre"

#### Scenario: Troca pelo campo Visualização
- **GIVEN** a visão semanal da sala `HV 3` na semana de 12/10/2026
- **WHEN** a opção "Mês" é escolhida no campo "Visualização"
- **THEN** a visão mensal de outubro de 2026 da sala `HV 3` é aberta, e o campo mostra "Mês"
- **AND** escolher "Semana" de novo abre a semana de 28/09/2026 a 02/10/2026, a do primeiro dia de outubro, na mesma sala

#### Scenario: Semestre sem período
- **GIVEN** o semestre escolhido sem período
- **WHEN** a Grade é exibida
- **THEN** o campo "Visualização" não aparece, e a Grade mostra a semana típica

#### Scenario: Mês inválido
- **WHEN** a Grade é aberta com `visao=mes&mes=2026-13`
- **THEN** o mês padrão é mostrado e a resposta é 200

#### Scenario: Rolagem só na Grade
- **WHEN** a visão mensal é exibida em 360 px e em 1.280 px de largura
- **THEN** a página não tem rolagem horizontal, e a área da Grade rola com a coluna de horários à vista

### Requirement: Faixas disponíveis sem poluição visual
Toda faixa do semestre sem ocorrência numa data do período DEVE (MUST) aparecer nas visões semanal e mensal como célula visualmente vazia, e NÃO DEVE (MUST NOT) mostrar texto visível em cada célula disponível. A célula DEVE (MUST) informar à tecnologia assistiva que a faixa está disponível, com o dia, a data e o horário. A faixa disponível NÃO DEVE (MUST NOT) ser apresentada como erro nem confundida com ausência de dados: o dia fora do período DEVE (MUST) mostrar "Fora do semestre", e o semestre sem período ou sem ensalamento DEVE (MUST) mostrar o aviso próprio, e não uma grade vazia. "Disponível" DEVE (MUST) ser um estado calculado, e o sistema NÃO DEVE (MUST NOT) gravar registro de faixa disponível. As faixas disponíveis DEVEM (MUST) entrar na contagem da faixa de situação. O texto exibido DEVE (MUST) usar "disponível" e "ocupado", e NÃO DEVE (MUST NOT) usar "livre" nem "vago".

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

### Requirement: Turmas juntas e choque agrupados na Grade
Quando mais de uma turma ocupa a sala na mesma faixa do mesmo dia, a Grade DEVE (MUST) mostrar os cards delas agrupados numa só célula, com a indicação "N turmas juntas" quando todas têm a mesma disciplina e os mesmos docentes, sem diferenciar maiúsculas de minúsculas, e "Choque: N turmas neste horário" nos demais casos, sempre com ícone e texto, e não só com cor. O agrupamento DEVE (MUST) valer na semana típica, na semana datada e abaixo de 640 px, e NÃO DEVE (MUST NOT) dar a impressão de que um card pertence à faixa seguinte. A classificação DEVE (MUST) ser calculada das ocorrências da célula, e NÃO DEVE (MUST NOT) ser gravada nem recusar a importação ou a confirmação.

#### Scenario: Turmas juntas
- **GIVEN** duas turmas de cursos diferentes com a disciplina `Química orgânica`, a docente `Elza`, na sala `1/13`, às segundas-feiras, na faixa `13:20 - 14:10`
- **WHEN** a semana de 05/10/2026 da sala é exibida
- **THEN** a faixa de segunda-feira mostra os dois cards numa só célula, sob "2 turmas juntas"

#### Scenario: Choque
- **GIVEN** duas turmas com disciplinas diferentes na mesma sala, dia e faixa
- **WHEN** a semana é exibida
- **THEN** a faixa mostra os dois cards numa só célula, sob "Choque: 2 turmas neste horário"
