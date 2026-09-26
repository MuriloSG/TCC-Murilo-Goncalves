# ensalamento Specification

## Purpose
Ocupação dos espaços pelo ensalamento: o semestre e o seu período, a importação da planilha institucional, as ocorrências calculadas das alocações e a Grade de consulta, semanal e mensal, por sala.
## Requirements
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

### Requirement: Semestre como recorte dos dados de ensalamento
O sistema DEVE (MUST) representar o semestre letivo como entidade própria, identificada por um código no formato `AAAA/1` ou `AAAA/2`, único e gravado como dado (por exemplo, `2026/1`). Um código fora desse formato DEVE (MUST) ser recusado. As faixas de horário e as alocações DEVEM (MUST) pertencer a um semestre, e uma operação sobre um semestre NÃO DEVE (MUST NOT) criar, alterar nem excluir faixa de horário ou alocação de outro semestre. O sistema DEVE (MUST) conseguir listar as alocações de um semestre informado, sem depender de nenhuma fonte externa.

#### Scenario: Semestres independentes
- **GIVEN** o semestre `2026/1` com as suas alocações
- **WHEN** o semestre `2026/2` é importado
- **THEN** as alocações de `2026/1` continuam as mesmas, em quantidade e em conteúdo

#### Scenario: Código fora do formato
- **WHEN** a criação de um semestre com o código `2026` ou `2026-1` é tentada
- **THEN** a criação é recusada e nenhum semestre é gravado

#### Scenario: Consulta por semestre
- **GIVEN** os semestres `2026/1` e `2026/2`, cada um com alocações
- **WHEN** as alocações de `2026/1` são consultadas
- **THEN** somente as alocações desse semestre são devolvidas

### Requirement: Entidades do ensalamento
O sistema DEVE (MUST) representar como entidades próprias o espaço, o curso, a disciplina, o docente, a turma, a faixa de horário e a alocação, e NÃO DEVE (MUST NOT) guardar nenhuma delas como texto dentro de outra. O espaço, o curso, a disciplina, o docente e a turma DEVEM (MUST) valer para todos os semestres, e a faixa de horário e a alocação DEVEM (MUST) pertencer a um semestre. Cada entidade DEVE (MUST) ser identificada assim, sempre sem diferenciar maiúsculas de minúsculas e sempre diferenciando letras acentuadas das não acentuadas:

- espaço: pelo nome;
- curso: pelo nome;
- disciplina: pelo nome, em todo o sistema, e não por curso;
- docente: pelo nome;
- turma: pelo curso e pelo rótulo;
- faixa de horário: pelo semestre, pela hora de início e pela hora de fim;
- alocação: pelo semestre, pela turma, pelo dia da semana, pela faixa de horário e pela disciplina.

O nome do espaço, do curso, da disciplina e do docente e o rótulo da turma DEVEM (MUST) ser gravados exatamente como informados, com os acentos e a caixa preservados, tendo apenas as bordas aparadas e os espaços internos repetidos reduzidos a um. O curso e a turma DEVEM (MUST) guardar a etapa de ensino, com o código gravado como dado, entre `GRADUACAO` e `ENSINO_MEDIO`. O dia da semana DEVE (MUST) ser gravado como código, entre `SEGUNDA`, `TERCA`, `QUARTA`, `QUINTA` e `SEXTA`. A hora de início DEVE (MUST) ser anterior à hora de fim.

#### Scenario: Nome gravado como informado
- **WHEN** o docente `Élcio José` e o espaço `Lab. Fenôm. de Transportes` são criados
- **THEN** os valores gravados são exatamente esses, com os acentos e a caixa preservados

#### Scenario: Nome equivalente não duplica
- **GIVEN** o espaço `Lab. Bromatologia`
- **WHEN** a criação do espaço ` lab.  bromatologia ` é tentada
- **THEN** nenhum espaço novo é criado e a operação devolve o espaço existente

#### Scenario: Acento distingue o registro
- **GIVEN** o docente `Érica`
- **WHEN** o docente `Erica` é criado
- **THEN** existem dois docentes, porque os acentos não são removidos na comparação

#### Scenario: Disciplina compartilhada entre cursos
- **GIVEN** a disciplina `Química Orgânica`, usada por uma turma de engenharia de alimentos
- **WHEN** uma turma de engenharia florestal passa a usar a disciplina `QUÍMICA ORGÂNICA`
- **THEN** existe uma única disciplina, referenciada pelas duas turmas

#### Scenario: Turmas homônimas de cursos diferentes
- **WHEN** as turmas com o rótulo `2º PERÍODO` são criadas para engenharia de alimentos e para engenharia florestal
- **THEN** existem duas turmas, uma em cada curso

#### Scenario: Faixa de horário inválida
- **WHEN** a criação de uma faixa de horário com início `10:00` e fim `09:00` é tentada
- **THEN** a criação é recusada

### Requirement: Alocação como agendamento recorrente do espaço
Uma alocação DEVE (MUST) registrar, para um semestre, a ocupação de um espaço por uma turma, numa disciplina, com um ou mais docentes, num dia da semana e numa faixa de horário. O espaço e os docentes PODEM (MAY) estar ausentes, porque a planilha institucional traz atividade sem sala e atividade sem docente reconhecido, e uma alocação sem espaço NÃO DEVE (MUST NOT) ocupar espaço nenhum. Cada alocação DEVE (MUST) cobrir exatamente uma faixa de horário, e o sistema NÃO DEVE (MUST NOT) unir faixas seguidas numa alocação única. Duas alocações do mesmo semestre PODEM (MAY) ter o mesmo espaço, o mesmo dia e a mesma faixa de horário, e o sistema NÃO DEVE (MUST NOT) recusar esse caso nem tratá-lo como conflito. O sistema NÃO DEVE (MUST NOT) implementar detecção de conflito de espaço ou de docente, nem reproduzir a marcação de choque da planilha institucional, nem gravar essa marcação como dado.

Cada alocação DEVE (MUST) registrar a origem, com o código gravado como dado, entre `IMPORTADA` e `MANUAL`. A alocação criada por importação DEVE (MUST) ter a origem `IMPORTADA`. A origem DEVE (MUST) existir para que uma funcionalidade futura distinga o que veio da planilha do que foi decidido no sistema, e NÃO DEVE (MUST NOT) ser usada nesta versão para excluir nem para desativar alocação.

#### Scenario: Espaço compartilhado por duas turmas
- **GIVEN** o semestre `2026/1`
- **WHEN** duas turmas de cursos diferentes recebem a mesma disciplina, no mesmo espaço, no mesmo dia e na mesma faixa de horário
- **THEN** as duas alocações são gravadas e nenhuma é recusada

#### Scenario: Faixas seguidas ficam separadas
- **WHEN** a mesma turma tem a mesma disciplina, no mesmo espaço e no mesmo dia, nas faixas `07:20 - 08:10` e `08:10 - 09:00`
- **THEN** existem duas alocações, uma por faixa, cada uma com o início e o fim da própria faixa

#### Scenario: Alocação sem espaço
- **WHEN** uma alocação é gravada sem espaço
- **THEN** ela existe, com a turma, a disciplina, o dia e a faixa, e não ocupa nenhum espaço

#### Scenario: Mesma disciplina duas vezes na mesma faixa
- **GIVEN** uma alocação da turma `2º PERÍODO` de engenharia florestal, na disciplina `Química Orgânica`, na segunda-feira, na faixa `13:20 - 14:10`
- **WHEN** outra alocação com a mesma turma, disciplina, dia e faixa é gravada
- **THEN** a gravação é recusada

#### Scenario: Ausência de detecção de conflito
- **WHEN** os módulos do ensalamento são inspecionados
- **THEN** nenhum deles implementa verificação de choque de espaço ou de docente, e nenhum campo guarda a marcação de choque da planilha

### Requirement: Importação do ensalamento por planilha
Um usuário ativo autenticado com a permissão `ENSALAMENTO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder carregar um semestre de ensalamento a partir da planilha institucional, conforme a spec `importacao-planilhas`, com o tipo `ENSALAMENTO`. O sistema NÃO DEVE (MUST NOT) exigir nenhuma alteração na planilha: NÃO DEVE (MUST NOT) exigir coluna, aba, identificador, código ou marcação criados para ele, e NÃO DEVE (MUST NOT) alterar o arquivo enviado.

O envio DEVE (MUST) receber o arquivo da planilha e o código do semestre, porque nenhuma aba da planilha traz o semestre. O código DEVE (MUST) ser obrigatório e validado no formato do semestre, e o semestre DEVE (MUST) ser criado quando ainda não existir. Um envio sem o código, ou com um código fora do formato, DEVE (MUST) ser recusado no formulário de envio, sem criar importação. A importação inteira DEVE (MUST) ficar vinculada ao semestre informado, e todas as alocações e faixas de horário dela DEVEM (MUST) pertencer a ele. O código DEVE (MUST) ser gravado nos valores de cada linha, e a confirmação DEVE (MUST) usar o código gravado, e não um informado de novo.

Depois da importação, os dados carregados DEVEM (MUST) ser dados do sistema. Nenhuma funcionalidade DEVE (MUST) consultar a planilha em tempo de execução para saber a ocupação de um espaço, e a ocupação DEVE (MUST) ser respondida a partir das alocações gravadas. O sistema NÃO DEVE (MUST NOT) guardar o arquivo enviado depois da leitura, e NÃO DEVE (MUST NOT) manter nenhuma sincronização automática com a planilha ou com serviço externo.

A importação NÃO DEVE (MUST NOT) criar, alterar nem desativar usuário, e a ausência de um usuário correspondente a um docente NÃO DEVE (MUST NOT) impedir a importação do docente nem da alocação.

#### Scenario: Carga de um semestre
- **GIVEN** um usuário com `ENSALAMENTO.IMPORTAR` e a planilha institucional
- **WHEN** ele envia o arquivo com o semestre `2026/1` e confirma a importação
- **THEN** o semestre, os espaços, os cursos, as disciplinas, os docentes, as turmas, as faixas de horário e as alocações da planilha existem no banco
- **AND** todas as faixas de horário e alocações criadas pertencem a `2026/1`

#### Scenario: Envio sem o semestre
- **WHEN** o arquivo é enviado sem o código do semestre
- **THEN** o formulário de envio mostra o erro, nenhuma importação é criada e nada é efetivado

#### Scenario: Código de semestre fora do formato
- **WHEN** o arquivo é enviado com o código `2026` no campo do semestre
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Semestre criado no envio
- **GIVEN** que não existe o semestre `2027/1`
- **WHEN** o arquivo é enviado com o código `2027/1`
- **THEN** o semestre passa a existir e a importação fica vinculada a ele

#### Scenario: Semestre da confirmação é o da prévia
- **GIVEN** uma importação `VALIDADA` enviada com o semestre `2026/1`
- **WHEN** ela é confirmada
- **THEN** os dados são aplicados a `2026/1`, a partir do código gravado nas linhas, e quem confirma não informa o semestre de novo

#### Scenario: Ocupação respondida pelo banco
- **GIVEN** uma importação concluída de `2026/1`
- **WHEN** a ocupação de um espaço no semestre é consultada
- **THEN** a resposta vem das alocações gravadas, sem nenhuma leitura do arquivo da planilha

#### Scenario: Arquivo não guardado
- **GIVEN** uma importação de ensalamento concluída
- **WHEN** os dados gravados da importação são consultados
- **THEN** o arquivo enviado não está guardado, e restam o nome do arquivo, os valores lidos de cada linha e o plano

#### Scenario: Nenhum usuário criado
- **GIVEN** a planilha com o docente `Aldo Gomes` e nenhum usuário com esse nome de usuário
- **WHEN** a importação é confirmada
- **THEN** o docente é criado, a alocação dele é criada e nenhum usuário é criado nem alterado

#### Scenario: Acesso sem a permissão
- **GIVEN** um usuário ativo autenticado sem `ENSALAMENTO.IMPORTAR`
- **WHEN** ele acessa qualquer rota da importação de ensalamento
- **THEN** o acesso é recusado com 403

#### Scenario: Visitante não autenticado
- **WHEN** um visitante não autenticado acessa qualquer rota da importação de ensalamento
- **THEN** ele é redirecionado para a página de login

### Requirement: Fontes dos dados na planilha institucional
A importação DEVE (MUST) extrair a ocupação exclusivamente das abas de horário da graduação e do ensino médio, e os catálogos de espaço e de docente exclusivamente da aba de validação de dados. Ela NÃO DEVE (MUST NOT) extrair dado de nenhuma aba cujo conteúdo seja calculado a partir de outra, o que inclui a aba de ensalamento por espaço, as abas de horário por docente e as abas por curso. A presença dessas abas NÃO DEVE (MUST NOT) recusar o arquivo, e a importação NÃO DEVE (MUST NOT) depender do valor em cache de nenhuma fórmula.

Em cada aba de horário, a importação DEVE (MUST) ler o dia da semana da coluna do dia, mesclada no bloco; a faixa de horário da coluna do horário, ignorando as linhas de intervalo e de almoço; a turma do cabeçalho da coluna; o curso do título sobre o grupo de colunas da turma; e a atividade do texto da célula. As colunas vazias que separam os cursos DEVEM (MUST) ser ignoradas.

O cabeçalho da turma DEVE (MUST) ser lido da primeira linha de cabeçalho da aba, e não do cabeçalho repetido em cada bloco de dia. O rótulo da turma DEVE (MUST) ser a primeira linha do cabeçalho quando houver mais de uma, e o cabeçalho inteiro quando houver só uma, sempre com as bordas aparadas, os espaços internos reduzidos e um separador ` - ` retirado, de modo que `1º ANO A Agroindústria` e `1º ANO A - Agroindústria` sejam a mesma turma.

Quando o título do curso não puder ser lido, o nome do curso DEVE (MUST) ser o nome curto que acompanha o rótulo no cabeçalho da turma, e a linha DEVE (MUST) receber um aviso. O arquivo NÃO DEVE (MUST NOT) ser recusado só porque o título não tem valor, desde que o nome curto exista. Quando não houver nem título nem nome curto, o curso não é identificável, e o arquivo DEVE (MUST) ser recusado informando as colunas envolvidas.

#### Scenario: Aba calculada ignorada
- **GIVEN** a planilha com a aba de ensalamento por espaço e as abas por curso, todas preenchidas por fórmula
- **WHEN** a prévia é gerada
- **THEN** nenhuma linha da importação vem dessas abas, e o arquivo não é recusado por causa delas

#### Scenario: Linhas de intervalo e de almoço
- **WHEN** a prévia é gerada
- **THEN** nenhuma alocação é planejada para as linhas de intervalo e de almoço

#### Scenario: Cabeçalho da turma com grafia diferente entre os blocos
- **GIVEN** uma coluna cujo cabeçalho é `1º ANO A Agroindústria` na primeira linha de cabeçalho e `1º ANO A - Agroindústria` nos blocos seguintes
- **WHEN** a prévia é gerada
- **THEN** todas as atividades da coluna pertencem à mesma turma

#### Scenario: Cabeçalho ausente num bloco
- **GIVEN** uma coluna com cabeçalho na primeira linha de cabeçalho e sem cabeçalho no bloco da sexta-feira
- **WHEN** a prévia é gerada
- **THEN** as atividades do bloco da sexta-feira pertencem à mesma turma das dos outros blocos

#### Scenario: Título do curso ilegível
- **GIVEN** um grupo de colunas cujo título do curso é uma fórmula sem valor
- **WHEN** a prévia é gerada
- **THEN** o arquivo é aceito, o curso recebe o nome curto do cabeçalho da turma e as linhas do grupo recebem o aviso correspondente

#### Scenario: Curso sem título e sem nome curto
- **GIVEN** um grupo de colunas cujo título do curso é uma fórmula sem valor e cujo cabeçalho da turma não traz nome curto
- **WHEN** o arquivo é enviado
- **THEN** o envio é recusado informando as colunas envolvidas, e nenhuma importação é criada

#### Scenario: Coluna com atividade e sem cabeçalho de turma
- **GIVEN** uma coluna com atividade cujo cabeçalho está vazio na primeira linha de cabeçalho
- **WHEN** o arquivo é enviado
- **THEN** o envio é recusado informando a coluna, e nenhuma importação é criada

### Requirement: Catálogo de espaços e de docentes da planilha
Os espaços e os docentes DEVEM (MUST) ser criados ou reconhecidos a partir das duas listas da aba de validação de dados, e NÃO DEVEM (MUST NOT) ser criados a partir do texto das células de atividade. Cada valor das duas listas DEVE (MUST) ser uma linha própria da importação, com a célula de origem dele, e essas linhas DEVEM (MUST) vir antes das linhas de atividade, porque é delas que sai o catálogo contra o qual as atividades são conferidas e são elas que criam os registros que as atividades referenciam. O catálogo usado na conferência das atividades DEVE (MUST) ser o das linhas da própria importação, e não o conjunto dos registros já existentes no sistema. Todos os valores das duas listas DEVEM (MUST) virar registro, inclusive os que nenhuma atividade referencia. Os parênteses que envolvem o nome do espaço na lista DEVEM (MUST) ser retirados, porque a lista mistura valores com e sem parênteses. Valores equivalentes na mesma lista DEVEM (MUST) gerar um único registro. Uma lista vazia DEVE (MUST) recusar o arquivo.

#### Scenario: Prévia mostra as salas que serão importadas
- **GIVEN** uma importação de ensalamento com a prévia gerada
- **WHEN** o recorte das salas é escolhido no detalhe
- **THEN** são listadas todas as linhas de sala, com a célula de origem, o valor lido e o nome que será cadastrado

#### Scenario: Espaço com e sem parênteses
- **GIVEN** a lista de espaços com os valores `(1/10)` e `Lab. de Madeira`
- **WHEN** a importação é confirmada
- **THEN** existem os espaços `1/10` e `Lab. de Madeira`

#### Scenario: Valor repetido na lista
- **GIVEN** a lista de espaços com `(Lab. Bromatologia)` em duas linhas
- **WHEN** a importação é confirmada
- **THEN** existe um único espaço `Lab. Bromatologia`
- **AND** a primeira linha tem a ação `create` e a segunda a ação `unchanged`

#### Scenario: Espaço de outro semestre que saiu da lista não vale para as atividades
- **GIVEN** o espaço `Zoo II`, criado por uma importação anterior
- **WHEN** a prévia de uma planilha cuja lista de espaços não traz `Zoo II` e cuja atividade cita `(Zoo II)` é gerada
- **THEN** a linha dessa atividade recebe erro, porque o catálogo da conferência é o da planilha enviada

#### Scenario: Docente sem atividade
- **GIVEN** a lista de docentes com um nome que nenhuma atividade referencia
- **WHEN** a importação é confirmada
- **THEN** o docente existe, sem nenhuma alocação

#### Scenario: Espaço já existente de outro semestre
- **GIVEN** o espaço `1/10`, criado pela importação de `2026/1`
- **WHEN** a importação de `2026/2` é confirmada com a mesma lista
- **THEN** nenhum espaço novo é criado e as alocações de `2026/2` apontam para o espaço existente

### Requirement: Leitura da atividade de uma célula
A importação DEVE (MUST) extrair de cada célula de atividade a disciplina, os docentes e o espaço, e DEVE (MUST) fazê-lo sem depender de posição fixa no texto, porque o nome da disciplina pode conter parênteses e o espaço pode estar ausente. Antes de qualquer leitura, o texto DEVE (MUST) ser normalizado, com a quebra de linha trocada por espaço, os espaços repetidos reduzidos a um e as bordas aparadas.

A leitura DEVE (MUST) acontecer do fim para o começo: o último grupo entre parênteses DEVE (MUST) ser o espaço quando corresponder a um espaço do catálogo; caso contrário, a atividade NÃO DEVE (MUST NOT) ter espaço e esse grupo DEVE (MUST) ser considerado a lista de docentes. O grupo imediatamente anterior ao do espaço DEVE (MUST) ser a lista de docentes, com os nomes separados por `/`, `,` ou ` e `. A disciplina DEVE (MUST) ser o texto anterior à lista de docentes, com os parênteses internos preservados e os separadores das bordas retirados. Uma célula DEVE (MUST) poder conter mais de uma atividade, separadas pelos ` / ` que estiverem fora de parênteses, e cada atividade DEVE (MUST) ser uma linha própria da importação, com o seu plano e a sua alocação. A separação DEVE (MUST) acontecer somente quando cada trecho tiver pelo menos um grupo entre parênteses; sem isso, a célula DEVE (MUST) ser uma atividade só. O erro de uma atividade NÃO DEVE (MUST NOT) impedir o plano das demais atividades da mesma célula, e a origem de cada linha DEVE (MUST) distinguir a atividade dentro da célula.

A correspondência de um nome de docente ou de espaço com o catálogo DEVE (MUST) ser exata, ignorando apenas a diferença entre maiúsculas e minúsculas e a normalização de espaços. Ela NÃO DEVE (MUST NOT) remover acentos, NÃO DEVE (MUST NOT) usar similaridade, NÃO DEVE (MUST NOT) comparar por prefixo e NÃO DEVE (MUST NOT) aceitar correspondência parcial.

#### Scenario: Atividade completa
- **WHEN** a célula `CÁLCULO III (Viviane) (2/6)` é lida
- **THEN** a disciplina é `CÁLCULO III`, o docente é `Viviane` e o espaço é `2/6`

#### Scenario: Disciplina com parênteses próprios
- **WHEN** a célula `Gestão Ambiental (optativa) (Élcio José) (3/10)` é lida
- **THEN** a disciplina é `Gestão Ambiental (optativa)`, o docente é `Élcio José` e o espaço é `3/10`

#### Scenario: Atividade sem espaço
- **WHEN** a célula `Educação Física (Jairo)` é lida
- **THEN** a disciplina é `Educação Física`, o docente é `Jairo` e a atividade não tem espaço

#### Scenario: Vários docentes
- **WHEN** a célula `UCE 2 (Eduardo Garrido/ Thaís/ Antônio )(HV 3)` é lida
- **THEN** a alocação tem os docentes `Eduardo Garrido`, `Thaís` e `Antônio` e o espaço `HV 3`

#### Scenario: Duas atividades na mesma célula
- **WHEN** a célula `Óleos e Gorduras (OPTATIVA I) (Bruna Porto) (Sl. Fenômenos) / Massas e Panificação (OPTATIVA II) (Márcia Antunes) (Sl. Oficina)` é lida
- **THEN** existem duas linhas, uma por atividade, cada uma planejando a sua alocação, em cada espaço, com a sua disciplina e o seu docente
- **AND** a origem das duas linhas cita a mesma célula, distinguida por um ordinal

#### Scenario: Barra dentro de parênteses não separa atividades
- **WHEN** a célula `UCE 2 (Eduardo Garrido/ Thaís/ Antônio )(HV 3)` é lida
- **THEN** existe uma única linha, com os três docentes

#### Scenario: Atividade com erro ao lado de atividades válidas
- **WHEN** a célula `Educação e Diversidade (Emille) (1/12)/ TCC I - Química (Gerson) / (1/9)` é lida
- **THEN** a linha do trecho `(1/9)`, que não tem disciplina, recebe erro
- **AND** as linhas das outras duas atividades têm o seu plano, sem erro

#### Scenario: Espaço fora do catálogo
- **GIVEN** a célula `Zootecnia Geral e Pequenas Criações (Paulo Eduardo) (Zoo I)` e o espaço `Zoo I` ausente do catálogo
- **WHEN** a prévia é gerada
- **THEN** a linha recebe erro na coluna da atividade, citando o valor não reconhecido, e a importação fica `COM_ERROS`

#### Scenario: Espaço com grafia diferente da do catálogo
- **GIVEN** o catálogo com o espaço `(HV 1)` e a célula `Fisiologia Animal I (Valéria) (HV1)`
- **WHEN** a prévia é gerada
- **THEN** a linha recebe erro, porque a correspondência é exata e não aproxima grafias

#### Scenario: Docente fora do catálogo
- **GIVEN** a célula `ESTATÍSTICA BÁSICA (EAD) (Agnaldo)` e o docente `Agnaldo` ausente do catálogo
- **WHEN** a prévia é gerada
- **THEN** a linha recebe erro na coluna da atividade e nenhum docente é criado

#### Scenario: Correspondência por prefixo recusada
- **GIVEN** o catálogo com os docentes `Gera Jr.` e `Gera Magela`
- **WHEN** a célula traz o docente `Gera`
- **THEN** a linha recebe erro, e nenhum dos dois docentes é escolhido

#### Scenario: Célula sem nenhum grupo entre parênteses
- **WHEN** a célula traz só um texto, sem parênteses
- **THEN** a linha recebe erro na coluna da atividade e a importação fica `COM_ERROS`

### Requirement: Reimportação de um semestre
A planilha DEVE (MUST) poder ser importada de novo para o mesmo semestre, e a nova importação NÃO DEVE (MUST NOT) duplicar espaço, docente, curso, disciplina, turma, faixa de horário nem alocação. A decisão de cada linha DEVE (MUST) ser `create` quando o registro não existir, `update` quando existir e algum dado diferir, e `unchanged` quando existir e nada diferir. Numa alocação, só o espaço e os docentes DEVEM (MUST) poder mudar sem criar registro novo.

A importação DEVE (MUST) acrescentar e atualizar, e NÃO DEVE (MUST NOT) excluir nada. Uma alocação do semestre que deixou de constar na planilha DEVE (MUST) ser preservada, em qualquer origem, e a ausência de um registro na planilha NÃO DEVE (MUST NOT) ser interpretada como ordem de exclusão, porque depois da importação o sistema é a fonte dos agendamentos. Espaço, docente, curso, disciplina, turma e faixa de horário ausentes da planilha nova DEVEM (MUST) ser preservados. A importação de um semestre NÃO DEVE (MUST NOT) excluir nem alterar alocação de outro semestre. Nenhuma linha de uma importação de ensalamento DEVE (MUST) ter ação de exclusão, e o sistema NÃO DEVE (MUST NOT) oferecer, nesta versão, nenhum caminho para excluir alocação.

Duas células da mesma aba que descrevam a mesma turma, o mesmo dia, a mesma faixa de horário e a mesma disciplina DEVEM (MUST) gerar erro de duplicidade, com as duas células citadas.

#### Scenario: Reimportação sem mudanças
- **GIVEN** uma importação de `2026/1` concluída
- **WHEN** a mesma planilha é enviada de novo para `2026/1`
- **THEN** todas as linhas têm a ação `unchanged` e nenhuma entidade é criada, alterada ou excluída

#### Scenario: Alocação que mudou de espaço
- **GIVEN** uma alocação da turma `6º PERÍODO` de engenharia florestal, na disciplina `Patologia Florestal`, na segunda-feira, na faixa `07:20 - 08:10`, no espaço `3/8`
- **WHEN** a prévia de uma planilha que põe a mesma aula no espaço `3/9` é gerada
- **THEN** a linha tem a ação `update`, com a mudança de espaço de `3/8` para `3/9`, e nenhuma alocação nova

#### Scenario: Alocação que deixou de constar é preservada
- **GIVEN** uma alocação `IMPORTADA` de `2026/1`
- **WHEN** uma planilha sem essa aula é importada e confirmada para `2026/1`
- **THEN** a alocação continua existindo, igual ao que era
- **AND** o plano da importação não tem nenhuma linha de exclusão

#### Scenario: Alocação nova acrescentada a um semestre já importado
- **GIVEN** uma importação de `2026/1` concluída
- **WHEN** uma planilha com uma aula a mais é importada e confirmada para `2026/1`
- **THEN** a alocação nova é criada e as anteriores continuam

#### Scenario: Alteração manual preservada
- **GIVEN** uma alocação de `2026/1` com a origem `MANUAL`
- **WHEN** a planilha é importada de novo para `2026/1`
- **THEN** essa alocação continua igual

#### Scenario: Catálogo preservado
- **GIVEN** o espaço `Zoo II`, usado por uma alocação de `2026/1`
- **WHEN** uma planilha cuja lista de espaços não traz `Zoo II` é importada para `2026/1`
- **THEN** o espaço continua existindo

#### Scenario: Ausência de exclusão
- **WHEN** os planos e as rotas da importação de ensalamento são inspecionados
- **THEN** nenhuma linha tem ação de exclusão e não existe rota que exclua alocação

#### Scenario: Outro semestre intocado
- **GIVEN** os semestres `2026/1` e `2026/2`, cada um com alocações
- **WHEN** uma planilha é importada de novo para `2026/2`
- **THEN** nenhuma alocação de `2026/1` é criada, alterada ou excluída

#### Scenario: Duplicidade dentro da planilha
- **GIVEN** duas células da mesma turma, dia e faixa de horário com a mesma disciplina
- **WHEN** a prévia é gerada
- **THEN** as duas linhas recebem erro de duplicidade citando as duas células, e a importação fica `COM_ERROS`

### Requirement: Registro de auditoria da importação de ensalamento
A importação de ensalamento DEVE (MUST) ser uma carga em lote, conforme a spec `auditoria`, e as operações de domínio executadas pelas suas linhas NÃO DEVEM (MUST NOT) gerar registro de auditoria por entidade. O registro da confirmação DEVE (MUST) ser o resumo da importação, e DEVE (MUST) conter quem executou, a data e a hora, o código do semestre importado, o nome do arquivo, a chave da importação, a quantidade de registros criados, a quantidade de registros atualizados, a quantidade de registros preservados, a quantidade de linhas com erro e o resultado final. O envio da prévia e o descarte DEVEM (MUST) continuar gerando registro, conforme a spec `importacao-planilhas`.

Os totais DEVEM (MUST) ser contados a partir das linhas da importação, e NÃO DEVEM (MUST NOT) ser gravados como campo da importação. O código do semestre DEVE (MUST) vir dos valores das linhas, e não de quem consulta.

#### Scenario: Resumo da confirmação
- **GIVEN** uma importação de ensalamento `VALIDADA` do semestre `2026/1`
- **WHEN** ela é confirmada
- **THEN** existe um registro de auditoria da importação com quem confirmou, a data e a hora, o semestre `2026/1`, o nome do arquivo, a chave da importação, os totais de criados, atualizados e preservados, o total de linhas com erro e o resultado final

#### Scenario: Sem registro por entidade
- **GIVEN** uma importação de ensalamento que cria centenas de alocações
- **WHEN** ela é confirmada
- **THEN** não existe registro de auditoria de nenhuma alocação, espaço, docente, curso, disciplina, turma ou faixa de horário criados

#### Scenario: Prévia registrada
- **WHEN** a prévia de uma planilha de ensalamento é gerada
- **THEN** existe um registro de auditoria da prévia da importação
- **AND** não existe registro de nenhuma entidade do ensalamento, porque nada foi mantido

### Requirement: Dados preparados para o calendário
As alocações DEVEM (MUST) poder ser consultadas por semestre, por espaço, por dia da semana, por faixa de horário, por turma e por docente, sem interpretar texto e sem recorrer à planilha. O semestre, o espaço, o dia da semana e a faixa de horário DEVEM (MUST) ser campos indexados, e o docente DEVE (MUST) ser relacionamento, e não texto. A modelagem NÃO DEVE (MUST NOT) impedir que, depois, existam alocação criada pela tela, reserva pontual, consulta de disponibilidade por data e horário, e visualização por espaço, por docente e por turma.

Esta Change NÃO DEVE (MUST NOT) implementar calendário, reserva, consulta de disponibilidade, notificação, edição manual de alocação nem visualização das alocações além da prévia e do detalhe da própria importação.

#### Scenario: Consulta da ocupação de um espaço
- **GIVEN** um semestre importado
- **WHEN** as alocações de um espaço num dia da semana são consultadas
- **THEN** a consulta usa os campos do semestre, do espaço, do dia e da faixa de horário, sem interpretar texto

#### Scenario: Consulta por docente
- **GIVEN** um semestre importado
- **WHEN** as alocações de um docente são consultadas
- **THEN** a consulta usa o relacionamento com o docente

#### Scenario: Ausência das telas futuras
- **WHEN** as rotas do sistema são inspecionadas
- **THEN** não existe rota de calendário, de reserva, de disponibilidade nem de criação ou edição de alocação

### Requirement: Cadastro manual sem vínculo acadêmico
O cadastro, a edição e a exclusão de disciplina ou turma pelas telas de Disciplinas e Turmas NÃO DEVEM (MUST NOT) criar, alterar nem excluir oferta de disciplina ou vínculo de docente: a relação entre docente, disciplina, turma e semestre continua estabelecida só pelo ensalamento. A importação do ensalamento DEVE (MUST) continuar identificando disciplina e turma pelo nome, sem diferenciar a caixa, e reaproveitar o registro cadastrado manualmente com o mesmo nome.

#### Scenario: Importação reaproveita o cadastro manual
- **GIVEN** a disciplina `Robótica Educacional` cadastrada pela tela de Disciplinas
- **WHEN** uma importação traz `robótica educacional` para o 1º ano com o docente `joao`
- **THEN** nenhuma disciplina nova é criada, e a oferta e o vínculo atual de `joao` nascem pela importação

#### Scenario: Cadastro manual fora da Agenda
- **GIVEN** a disciplina `Artes` e a turma `6º período` cadastradas pelas telas
- **WHEN** a Agenda consulta as combinações atuais do semestre para o docente `joao`
- **THEN** nenhuma combinação com elas é oferecida

