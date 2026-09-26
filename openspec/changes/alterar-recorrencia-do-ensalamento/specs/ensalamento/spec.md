## MODIFIED Requirements

### Requirement: Alocação como agendamento recorrente do espaço
Uma alocação DEVE (MUST) registrar, para um semestre, a ocupação de um espaço por uma turma, numa disciplina, com um ou mais docentes, num dia da semana e numa faixa de horário. O espaço e os docentes PODEM (MAY) estar ausentes, porque a planilha institucional traz atividade sem sala e atividade sem docente reconhecido, e uma alocação sem espaço NÃO DEVE (MUST NOT) ocupar espaço nenhum. Cada alocação DEVE (MUST) cobrir exatamente uma faixa de horário, e o sistema NÃO DEVE (MUST NOT) unir faixas seguidas numa alocação única. Duas alocações do mesmo semestre PODEM (MAY) ter o mesmo espaço, o mesmo dia e a mesma faixa de horário, e a importação NÃO DEVE (MUST NOT) recusar esse caso nem tratá-lo como conflito. A importação NÃO DEVE (MUST NOT) implementar detecção de conflito de espaço ou de docente, nem reproduzir a marcação de choque da planilha institucional, nem gravar essa marcação como dado. A detecção de conflito DEVE (MUST) existir só na alteração da recorrência feita no sistema.

Cada alocação DEVE (MUST) ter uma vigência, com início e fim opcionais: vazios, a alocação vale o período inteiro do semestre. A alocação criada pela importação DEVE (MUST) ter a vigência vazia. O fim da vigência NÃO DEVE (MUST NOT) ser anterior ao início. A identidade de uma alocação DEVE (MUST) ser o semestre, a turma, o dia, a faixa, a disciplina e o início da vigência.

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

#### Scenario: Importação sem detecção de conflito
- **WHEN** a importação grava duas aulas de disciplinas diferentes no mesmo espaço, dia e faixa
- **THEN** as duas alocações são gravadas, e nenhum campo guarda a marcação de choque da planilha

#### Scenario: Vigência vazia na importação
- **WHEN** uma alocação é criada pela importação
- **THEN** o início e o fim da vigência ficam vazios e ela vale o semestre inteiro

### Requirement: Ocorrências calculadas das alocações
Cada alocação DEVE (MUST) continuar sendo uma regra semanal do semestre, e o sistema NÃO DEVE (MUST NOT) gravar uma linha por data em que a aula ocorre. As ocorrências de um espaço num intervalo de datas DEVEM (MUST) ser calculadas na consulta: uma ocorrência por alocação do espaço, em cada data do intervalo que esteja no período do semestre da alocação e na vigência dela, cujo dia da semana seja o da alocação e que não tenha ocorrência cancelada, com a data, o início e o fim da faixa. Uma alocação sem espaço NÃO DEVE (MUST NOT) gerar ocorrência em espaço nenhum. O cálculo DEVE (MUST) aceitar qualquer intervalo, inclusive um que atravesse dois semestres, e DEVE (MUST) usar uma quantidade fixa de consultas ao banco, que não cresça com o tamanho do intervalo. O cálculo NÃO DEVE (MUST NOT) gravar dados. A mesma regra DEVE (MUST) valer para a Grade do Ensalamento, a Grade da Agenda, a disponibilidade do espaço na Agenda e o calendário público, sem cálculo paralelo. A reimportação PODE (MAY) mudar a representação das semanas anteriores de uma alocação sem vigência, e NÃO DEVE (MUST NOT) alterar uma alocação com vigência definida.

#### Scenario: Reimportação muda as semanas anteriores
- **GIVEN** uma alocação sem vigência na sala `3/8` e o semestre com período
- **WHEN** uma reimportação muda a sala dessa alocação para `3/9`
- **THEN** as ocorrências das semanas anteriores e das seguintes passam a ser da sala `3/9`

#### Scenario: Ocorrência fora da vigência
- **GIVEN** uma alocação às segundas-feiras com a vigência até 04/10/2026
- **WHEN** as ocorrências de 05/10/2026 a 09/10/2026 são calculadas
- **THEN** nenhuma ocorrência dessa alocação é devolvida

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

### Requirement: Reimportação de um semestre
A planilha DEVE (MUST) poder ser importada de novo para o mesmo semestre, e a nova importação NÃO DEVE (MUST NOT) duplicar espaço, docente, curso, disciplina, turma, faixa de horário nem alocação. A decisão de cada linha DEVE (MUST) ser `create` quando o registro não existir, `update` quando existir e algum dado diferir, e `unchanged` quando existir e nada diferir. Numa alocação, só o espaço e os docentes DEVEM (MUST) poder mudar sem criar registro novo. Quando a identidade da linha corresponde a uma alocação com vigência definida, alterada no sistema, a linha DEVE (MUST) ter a ação `unchanged` e o aviso "Esta aula teve a recorrência alterada no sistema e não foi atualizada pela planilha.", e a importação NÃO DEVE (MUST NOT) alterar essa alocação nem criar outra com a mesma identidade.

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
- **GIVEN** uma aula de `2026/2` cuja recorrência foi alterada no sistema a partir de 05/10/2026, da sala `HV 1` para a `HV 2`
- **WHEN** a planilha, que ainda traz a aula na `HV 1`, é importada de novo para `2026/2`
- **THEN** a alocação encerrada e a versão nova continuam iguais, e a linha tem a ação `unchanged` com o aviso de recorrência alterada

#### Scenario: Regra antiga não é recriada
- **GIVEN** uma aula de segunda-feira cuja recorrência passou para quarta-feira a partir de 05/10/2026
- **WHEN** a planilha, que ainda traz a aula na segunda-feira, é importada de novo
- **THEN** nenhuma alocação é criada e a aula continua sem ocorrência na segunda-feira a partir de 05/10/2026

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

## ADDED Requirements

### Requirement: Cancelamento de ocorrência
O sistema DEVE (MUST) permitir cancelar uma ocorrência de uma aula numa data sem alterar a regra semanal, gravando uma exceção do tipo `CANCELADA` por alocação do bloco da Grade. Podem cancelar o docente da aula, reconhecido pelo nome igual ao `username`, e quem tem `ENSALAMENTO.CANCELAR_OCORRENCIA`. A data DEVE (MUST) ser uma ocorrência da alocação, e a mesma ocorrência NÃO DEVE (MUST NOT) ser cancelada duas vezes. A ocorrência cancelada NÃO DEVE (MUST NOT) aparecer na Grade do Ensalamento, na Grade da Agenda nem no calendário público, e o espaço DEVE (MUST) ficar disponível na Agenda nessa data.

#### Scenario: Docente cancela a própria aula
- **GIVEN** a aula de Cálculo III da docente Viviane às segundas
- **WHEN** Viviane cancela a ocorrência de 28/09/2026
- **THEN** a aula some da Grade de 28/09/2026 e continua em 05/10/2026

### Requirement: Alteração da recorrência a partir de uma data
Um usuário ativo com `ENSALAMENTO.ALTERAR_RECORRENCIA`, ou superadmin ativo, DEVE (MUST) poder alterar a recorrência de uma aula a partir de uma data, informando o dia da semana, o horário, o espaço e os docentes. Cada alocação da aula DEVE (MUST) ser encerrada na véspera da data, sem outra mudança, e uma alocação nova DEVE (MUST) começar na data, com a origem `MANUAL`, os dados informados, a mesma turma, disciplina e semestre, e o fim da vigência da anterior. As ocorrências anteriores à data NÃO DEVEM (MUST NOT) mudar. Uma aula de várias faixas seguidas DEVE (MUST) mudar inteira, para um intervalo com a mesma quantidade de faixas seguidas do semestre, e o sistema NÃO DEVE (MUST NOT) criar faixa de horário.

A data DEVE (MUST) ser de hoje em diante, estar no período do semestre, ser uma ocorrência da regra atual e ser posterior ao início da vigência. O espaço escolhido DEVE (MUST) estar ativo, salvo quando é o atual. A alteração DEVE (MUST) mudar ao menos um dado. A alteração DEVE (MUST) ser recusada, com a explicação, quando o espaço estiver ocupado em alguma ocorrência não cancelada da regra nova por agendamento aprovado ou por aula de outra alocação com disciplina ou docentes diferentes; aula com a mesma disciplina e os mesmos docentes é turma junta e NÃO DEVE (MUST NOT) impedir a alteração. A alteração também DEVE (MUST) ser recusada quando a turma já tem a mesma disciplina no mesmo dia e faixa na vigência nova.

A alteração DEVE (MUST) ser atômica: a recusa ou a falha de qualquer etapa NÃO DEVE (MUST NOT) deixar a alocação encerrada sem a nova. A interface DEVE (MUST) oferecer a ação "Alterar recorrência" no card da Grade datada, de hoje em diante, só a quem pode executá-la, deixar claro que a alteração vale para todas as aulas a partir da data e mostrar o resumo de antes, da data e de depois antes da confirmação. A permissão DEVE (MUST) ser conferida na execução, e não só pela ação escondida.

#### Scenario: Troca de sala a partir de uma data
- **GIVEN** a aula de segunda-feira das 08:00 às 10:00 na `HV 1`, desde 01/09/2026
- **WHEN** um usuário com a permissão altera a recorrência a partir de 05/10/2026 para a `HV 2`
- **THEN** a alocação original vale até 04/10/2026 na `HV 1`
- **AND** uma alocação nova vale de 05/10/2026 até o fim do semestre na `HV 2`, com a mesma turma, disciplina, dia, horário e docentes
- **AND** a Grade, a Agenda e o calendário público mostram a `HV 1` até 28/09/2026 e a `HV 2` a partir de 05/10/2026

#### Scenario: Usuário sem a permissão
- **GIVEN** um docente da aula sem `ENSALAMENTO.ALTERAR_RECORRENCIA`
- **WHEN** ele tenta abrir ou enviar a alteração
- **THEN** a resposta é 403, a ação não aparece na Grade e nenhuma alocação muda

#### Scenario: Data que não é ocorrência
- **WHEN** a alteração de uma aula de segunda-feira é pedida a partir de uma terça-feira
- **THEN** a alteração é recusada com "A aula não acontece em 06/10/2026. Escolha uma data da aula."

#### Scenario: Choque com outra aula
- **GIVEN** a aula de Química na `HV 2` às segundas das 08:00 às 10:00
- **WHEN** outra aula tenta passar para a `HV 2` nesse horário a partir de 05/10/2026
- **THEN** a alteração é recusada com a aula, a data e o horário ocupados

#### Scenario: Agendamento aprovado
- **GIVEN** um agendamento aprovado na `HV 2` em 12/10/2026 das 10:30 às 11:00
- **WHEN** uma aula de segunda-feira das 10:00 às 12:00 tenta passar para a `HV 2` a partir de 05/10/2026
- **THEN** a alteração é recusada citando o agendamento

#### Scenario: Falha no meio da alteração
- **WHEN** a gravação da auditoria falha depois de a alocação ter sido encerrada
- **THEN** a alocação original continua sem fim de vigência e nenhuma alocação nova existe

### Requirement: Exceções na alteração da recorrência
As exceções anteriores à data da alteração DEVEM (MUST) continuar na alocação encerrada. As exceções da data em diante DEVEM (MUST) passar para a alocação nova quando a data delas é ocorrência da regra nova. Se alguma não for, a alteração DEVE (MUST) ser recusada citando as datas, e nenhuma exceção DEVE (MUST) ser removida.

#### Scenario: Cancelamento anterior preservado
- **GIVEN** a ocorrência de 28/09/2026 cancelada e a de 12/10/2026 cancelada
- **WHEN** a sala muda a partir de 05/10/2026
- **THEN** o cancelamento de 28/09/2026 continua na alocação original e o de 12/10/2026 passa para a nova, e as duas datas continuam sem aula

#### Scenario: Cancelamento que não cabe na regra nova
- **GIVEN** a ocorrência de segunda-feira 12/10/2026 cancelada
- **WHEN** a aula passa para quarta-feira a partir de 05/10/2026
- **THEN** a alteração é recusada citando 12/10/2026
