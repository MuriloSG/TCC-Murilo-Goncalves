## ADDED Requirements

### Requirement: Criação da recorrência pela interface
O sistema DEVE (MUST) permitir cadastrar uma aula recorrente direto na interface, sem passar pela planilha, a quem tem `ENSALAMENTO.CRIAR_RECORRENCIA`. O cadastro DEVE (MUST) receber o semestre, a turma, a disciplina, os docentes, o espaço, o horário de início, a duração em faixas seguidas, a data da primeira aula e, opcionalmente, a data da última. A turma, a disciplina, os docentes, o espaço, o semestre e as faixas de horário DEVEM (MUST) ser escolhidos entre os já cadastrados, e o cadastro NÃO DEVE (MUST NOT) criar nenhum deles.

Cada faixa da duração DEVE (MUST) virar uma alocação própria, com a mesma turma, disciplina, dia, vigência, espaço e docentes, e com origem `MANUAL`. O dia da semana DEVE (MUST) ser o da data da primeira aula, e não um campo separado. O início da vigência DEVE (MUST) ser a data da primeira aula, igual ou posterior ao dia de hoje e dentro do período do semestre. O fim da vigência, quando informado, NÃO DEVE (MUST NOT) ser anterior ao início nem posterior ao fim do semestre; vazio, a aula vale até o fim do semestre. O espaço PODE (MAY) ficar vazio, e nesse caso a aula não ocupa espaço nenhum. Os docentes PODEM (MAY) ficar vazios.

Toda a criação DEVE (MUST) acontecer numa transação: uma recusa ou uma falha NÃO DEVE (MUST NOT) deixar alocação, oferta nem registro de auditoria gravados. Depois de gravar, a oferta da disciplina para a turma no semestre DEVE (MUST) ser registrada e os docentes dela sincronizados, como na importação e na alteração da recorrência.

#### Scenario: Aula de uma faixa cadastrada
- **GIVEN** o semestre `2026/2` de 03/08/2026 a 18/12/2026 e a sala `HV 2` ativa
- **WHEN** um usuário com a permissão cadastra `Química Orgânica` para a turma `2º PERÍODO`, na `HV 2`, das 13:20 às 14:10, a partir de 06/10/2026, sem data final
- **THEN** existe uma alocação de origem `MANUAL`, às terças-feiras, com o início da vigência em 06/10/2026 e o fim vazio

#### Scenario: Aula de duas faixas seguidas
- **WHEN** a mesma aula é cadastrada com a duração de duas faixas seguidas a partir das 13:20
- **THEN** existem duas alocações, uma por faixa, com a mesma turma, disciplina, dia e vigência

#### Scenario: Duração maior que o semestre oferece
- **WHEN** a duração pedida não tem faixas seguidas no semestre a partir do horário escolhido
- **THEN** o cadastro é recusado com a mensagem de escolher um horário do semestre e nenhuma faixa de horário é criada

#### Scenario: Data de início no passado
- **WHEN** a data da primeira aula é anterior ao dia de hoje
- **THEN** o cadastro é recusado e nenhuma alocação é gravada

#### Scenario: Data de início fora do semestre
- **WHEN** a data da primeira aula está fora do período do semestre escolhido
- **THEN** o cadastro é recusado e nenhuma alocação é gravada

#### Scenario: Data final anterior ao início
- **WHEN** a data da última aula é anterior à data da primeira
- **THEN** o cadastro é recusado e nenhuma alocação é gravada

#### Scenario: Aula sem espaço
- **WHEN** a aula é cadastrada sem espaço
- **THEN** as alocações existem, não ocupam espaço nenhum e nenhuma conferência de conflito de espaço é feita

#### Scenario: Oferta registrada
- **WHEN** a aula é cadastrada para uma turma que ainda não tinha a disciplina no semestre
- **THEN** a oferta da disciplina para a turma no semestre existe, com os docentes da aula

### Requirement: Conflito na criação da recorrência
A criação DEVE (MUST) ser recusada quando o espaço escolhido estiver ocupado em alguma ocorrência da vigência da aula nova, por outra aula do ensalamento que forme choque ou por um agendamento aprovado da Agenda, considerando a sobreposição de horário e já descontadas as ocorrências canceladas. Outra aula no mesmo espaço, dia e horário com a mesma disciplina e os mesmos docentes DEVE (MUST) ser aceita, porque é turma junta. A criação também DEVE (MUST) ser recusada quando a turma já tiver a mesma disciplina no mesmo dia e na mesma faixa, numa alocação cuja vigência se sobreponha à da aula nova. A conferência DEVE (MUST) ser a mesma usada pela alteração da recorrência, sem regra paralela, e a mensagem de recusa DEVE (MUST) dizer a data, o horário e a ocupação encontrada.

#### Scenario: Espaço ocupado por outra aula
- **GIVEN** a sala `HV 2` com a aula de `Cálculo I` às terças-feiras das 13:20 às 14:10
- **WHEN** um usuário cadastra `Química Orgânica` na `HV 2`, às terças-feiras, no mesmo horário, numa vigência que alcança essas ocorrências
- **THEN** o cadastro é recusado com a data, o horário e a aula que ocupa a sala, e nada é gravado

#### Scenario: Espaço com agendamento aprovado
- **GIVEN** um agendamento aprovado da sala `HV 2` em 06/10/2026 das 13:00 às 14:00
- **WHEN** uma aula na `HV 2` é cadastrada às terças-feiras das 13:20 às 14:10 a partir de 06/10/2026
- **THEN** o cadastro é recusado com a data e o horário do agendamento

#### Scenario: Turma junta aceita
- **GIVEN** a sala `HV 2` com `Química Orgânica` dos mesmos docentes às terças-feiras das 13:20 às 14:10, de outra turma
- **WHEN** a mesma disciplina, com os mesmos docentes, é cadastrada para outra turma no mesmo espaço e horário
- **THEN** o cadastro é aceito e as duas aulas existem

#### Scenario: Conflito fora da vigência
- **GIVEN** a sala `HV 2` ocupada por outra aula só até 30/09/2026
- **WHEN** a aula nova é cadastrada na `HV 2` a partir de 06/10/2026
- **THEN** o cadastro é aceito

#### Scenario: Turma com a mesma disciplina no horário
- **GIVEN** a turma `2º PERÍODO` com `Química Orgânica` às terças-feiras das 13:20 às 14:10 até o fim do semestre
- **WHEN** a mesma turma recebe a mesma disciplina no mesmo dia e faixa a partir de 06/10/2026
- **THEN** o cadastro é recusado com a orientação de escolher outro horário

### Requirement: Cadastro de aula na Grade do ensalamento
A Grade datada DEVE (MUST) oferecer o cadastro de aula a quem tem `ENSALAMENTO.CRIAR_RECORRENCIA`, por um controle no cabeçalho da tela e por um gatilho em cada faixa disponível de hoje em diante. O gatilho da faixa DEVE (MUST) abrir o cadastro com o semestre, o espaço, a data e o horário daquela célula preenchidos; o controle do cabeçalho DEVE (MUST) abrir o cadastro sem preenchimento. A faixa disponível DEVE (MUST) continuar visualmente vazia, com o dia, a data, o horário e a situação apenas para a tecnologia assistiva, e o gatilho DEVE (MUST) ser alcançável pelo teclado, com nome acessível que traga a ação, o dia, a data e o horário. A Grade sem data NÃO DEVE (MUST NOT) mostrar o gatilho da faixa.

O cadastro DEVE (MUST) abrir em modal sobre a Grade e acontecer em duas etapas na mesma tela: o primeiro envio confere tudo e mostra o resumo da aula, de quando ela acontece, de onde acontece e de quantas ocorrências serão geradas, sem gravar nada; o envio seguinte, com a confirmação, grava. Uma recusa DEVE (MUST) voltar como erro do formulário, com os dados informados preservados. No sucesso, a Grade DEVE (MUST) abrir na semana da primeira aula e no espaço escolhido, com a mensagem do fato.

Esconder o controle NÃO DEVE (MUST NOT) ser a proteção: a rota DEVE (MUST) declarar a permissão e a operação do model DEVE (MUST) conferi-la de novo.

#### Scenario: Gatilho na faixa disponível
- **GIVEN** um usuário com a permissão na Grade datada da sala `HV 2`
- **WHEN** ele aciona uma faixa disponível de uma data futura
- **THEN** o cadastro abre em modal com o semestre, a sala `HV 2`, aquela data e aquele horário preenchidos

#### Scenario: Faixa disponível continua vazia
- **WHEN** a Grade datada é exibida com a permissão de cadastro
- **THEN** a faixa disponível não mostra texto nem marcador visível, e o dia, a data, o horário e a situação continuam disponíveis para a tecnologia assistiva

#### Scenario: Faixa passada sem gatilho
- **WHEN** a Grade datada mostra uma semana já encerrada
- **THEN** as faixas disponíveis dessas datas não oferecem o cadastro

#### Scenario: Sem a permissão não há controle
- **GIVEN** um usuário sem `ENSALAMENTO.CRIAR_RECORRENCIA`
- **WHEN** ele abre a Grade datada
- **THEN** nenhum controle de cadastro de aula é exibido

#### Scenario: Resumo antes de gravar
- **WHEN** o usuário envia o cadastro pela primeira vez, com dados válidos
- **THEN** a tela mostra a turma, a disciplina, os docentes, o dia, o horário, a vigência, o espaço e a quantidade de ocorrências, e nenhuma alocação foi gravada

#### Scenario: Recusa preserva o formulário
- **WHEN** a confirmação é recusada por conflito
- **THEN** o erro aparece no formulário, com os dados informados preservados, e nada é gravado

## MODIFIED Requirements

### Requirement: Reimportação de um semestre
A planilha DEVE (MUST) poder ser importada de novo para o mesmo semestre, e a nova importação NÃO DEVE (MUST NOT) duplicar espaço, docente, curso, disciplina, turma, faixa de horário nem alocação. A decisão de cada linha DEVE (MUST) ser `create` quando o registro não existir, `update` quando existir e algum dado diferir, e `unchanged` quando existir e nada diferir. Numa alocação, só o espaço e os docentes DEVEM (MUST) poder mudar sem criar registro novo. Quando a identidade da linha corresponde a uma alocação com vigência definida, cadastrada ou alterada no sistema, a linha DEVE (MUST) ter a ação `unchanged` e o aviso "Esta aula foi definida no sistema e não foi atualizada pela planilha.", e a importação NÃO DEVE (MUST NOT) alterar essa alocação nem criar outra com a mesma identidade.

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
- **THEN** a alocação encerrada e a versão nova continuam iguais, e a linha tem a ação `unchanged` com o aviso da aula definida no sistema

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

#### Scenario: Aula cadastrada no sistema preservada
- **GIVEN** uma aula de `2026/2` cadastrada pela interface, com a vigência a partir de 06/10/2026
- **WHEN** uma planilha com a mesma turma, disciplina, dia e faixa é importada de novo para `2026/2`
- **THEN** a alocação continua igual, nenhuma outra é criada e a linha tem a ação `unchanged` com o aviso da aula definida no sistema

### Requirement: Alocação como agendamento recorrente do espaço
Uma alocação DEVE (MUST) registrar, para um semestre, a ocupação de um espaço por uma turma, numa disciplina, com um ou mais docentes, num dia da semana e numa faixa de horário. O espaço e os docentes PODEM (MAY) estar ausentes, porque a planilha institucional traz atividade sem sala e atividade sem docente reconhecido, e uma alocação sem espaço NÃO DEVE (MUST NOT) ocupar espaço nenhum. Cada alocação DEVE (MUST) cobrir exatamente uma faixa de horário, e o sistema NÃO DEVE (MUST NOT) unir faixas seguidas numa alocação única. Duas alocações do mesmo semestre PODEM (MAY) ter o mesmo espaço, o mesmo dia e a mesma faixa de horário, e a importação NÃO DEVE (MUST NOT) recusar esse caso nem tratá-lo como conflito. A importação NÃO DEVE (MUST NOT) implementar detecção de conflito de espaço ou de docente, nem reproduzir a marcação de choque da planilha institucional, nem gravar essa marcação como dado. A detecção de conflito DEVE (MUST) existir só nas operações feitas no sistema: a alteração da recorrência e a criação da recorrência.

Cada alocação DEVE (MUST) ter uma vigência, com início e fim opcionais: vazios, a alocação vale o período inteiro do semestre. A alocação criada pela importação DEVE (MUST) ter a vigência vazia, e a criada pela interface DEVE (MUST) ter o início preenchido. O fim da vigência NÃO DEVE (MUST NOT) ser anterior ao início. A identidade de uma alocação DEVE (MUST) ser o semestre, a turma, o dia, a faixa, a disciplina e o início da vigência.

Cada alocação DEVE (MUST) registrar a origem, com o código gravado como dado, entre `IMPORTADA` e `MANUAL`. A alocação criada por importação DEVE (MUST) ter a origem `IMPORTADA`, e a criada pela interface DEVE (MUST) ter a origem `MANUAL`. A origem NÃO DEVE (MUST NOT) ser usada nesta versão para excluir nem para desativar alocação.

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

#### Scenario: Origem da alocação criada na interface
- **WHEN** uma aula é cadastrada pela interface
- **THEN** cada alocação dela tem a origem `MANUAL` e o início da vigência preenchido
