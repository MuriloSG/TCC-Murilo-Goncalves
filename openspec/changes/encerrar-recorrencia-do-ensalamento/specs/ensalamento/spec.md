## ADDED Requirements

### Requirement: Encerramento da recorrência
O sistema DEVE (MUST) permitir encerrar uma aula do ensalamento a partir de uma data, a quem tem `ENSALAMENTO.ENCERRAR_RECORRENCIA`. Cada alocação do bloco da aula DEVE (MUST) receber o fim da vigência na véspera da data, e a aula NÃO DEVE (MUST NOT) gerar ocorrência dessa data em diante, na Grade do Ensalamento, na Grade da Agenda, na disponibilidade do espaço e no calendário público. As ocorrências anteriores DEVEM (MUST) continuar existindo, e nenhuma alocação DEVE (MUST) ser excluída.

A data DEVE (MUST) ser igual ou posterior ao dia de hoje, estar no período do semestre e ser uma data em que a aula acontece. Quando a data é a primeira da vigência ou anterior a ela, a aula DEVE (MUST) ficar sem nenhuma ocorrência, e o encerramento NÃO DEVE (MUST NOT) ser recusado por isso. As ocorrências canceladas da aula NÃO DEVEM (MUST NOT) ser excluídas nem transferidas.

O encerramento DEVE (MUST) acontecer numa transação: uma recusa ou uma falha NÃO DEVE (MUST NOT) deixar vigência nem registro de auditoria gravados. Depois do encerramento, a reimportação da planilha NÃO DEVE (MUST NOT) alterar a aula nem criar outra com a mesma identidade, pela regra já válida para toda alocação com vigência definida.

#### Scenario: Aula encerrada a partir de uma data
- **GIVEN** uma aula às segundas-feiras, das 10:00 às 12:00, no semestre de 03/08/2026 a 18/12/2026
- **WHEN** ela é encerrada a partir de 05/10/2026
- **THEN** cada alocação do bloco passa a ter o fim da vigência em 04/10/2026

#### Scenario: Ocorrências seguintes somem
- **GIVEN** a mesma aula encerrada a partir de 05/10/2026
- **WHEN** as ocorrências de 05/10/2026 a 09/10/2026 são calculadas
- **THEN** nenhuma ocorrência dessa aula é devolvida

#### Scenario: Ocorrências anteriores continuam
- **GIVEN** a mesma aula encerrada a partir de 05/10/2026
- **WHEN** as ocorrências de 28/09/2026 a 02/10/2026 são calculadas
- **THEN** a ocorrência de 28/09/2026 continua sendo devolvida

#### Scenario: Aula que ainda não começou
- **GIVEN** uma aula cadastrada no sistema com a vigência a partir de 20/10/2026
- **WHEN** ela é encerrada a partir de 20/10/2026
- **THEN** o encerramento é aceito e a aula não gera ocorrência em data nenhuma

#### Scenario: Data que não é da aula
- **WHEN** o encerramento é pedido para uma data em que a aula não acontece
- **THEN** ele é recusado e nenhuma vigência muda

#### Scenario: Data no passado
- **WHEN** o encerramento é pedido para uma data anterior ao dia de hoje
- **THEN** ele é recusado e nenhuma vigência muda

#### Scenario: Nada é excluído
- **GIVEN** uma aula encerrada
- **THEN** as alocações dela continuam no banco, com as ocorrências canceladas que tinham

#### Scenario: Reimportação não recria a aula encerrada
- **GIVEN** uma aula de `2026/2` encerrada a partir de 05/10/2026
- **WHEN** a planilha, que ainda traz a aula, é importada de novo para `2026/2`
- **THEN** nenhuma alocação é criada nem alterada, e a linha tem a ação `unchanged` com o aviso da aula definida no sistema

### Requirement: Encerramento na Grade do ensalamento
A Grade datada DEVE (MUST) oferecer o encerramento da aula a quem tem `ENSALAMENTO.ENCERRAR_RECORRENCIA`, em cada aula de hoje em diante, junto das demais ações do card. A ação DEVE (MUST) abrir uma confirmação em modal, com a pergunta que identifica a aula, a quantidade de aulas que deixam de existir, a data a partir da qual isso vale e a informação de que as anteriores continuam. O GET DEVE (MUST) mostrar a confirmação e só o POST DEVE (MUST) executar.

Uma recusa DEVE (MUST) virar mensagem, sem alterar dados. No sucesso, a Grade DEVE (MUST) abrir na semana da data, com a mensagem do fato. A Grade sem data NÃO DEVE (MUST NOT) oferecer a ação, e esconder a ação NÃO DEVE (MUST NOT) ser a proteção: a rota DEVE (MUST) declarar a permissão e a operação do model DEVE (MUST) conferi-la de novo.

#### Scenario: Confirmação antes de encerrar
- **GIVEN** uma aula com 11 ocorrências de 05/10/2026 até o fim do semestre
- **WHEN** um usuário com a permissão aciona o encerramento a partir de 05/10/2026
- **THEN** a confirmação diz que 11 aulas deixam de existir a partir de 05/10/2026 e que as anteriores continuam, e nada foi alterado

#### Scenario: Sem a permissão não há ação
- **GIVEN** um usuário sem `ENSALAMENTO.ENCERRAR_RECORRENCIA`
- **WHEN** ele abre a Grade datada
- **THEN** nenhuma ação de encerrar é exibida

#### Scenario: Aula passada sem ação
- **WHEN** a Grade datada mostra uma semana já encerrada
- **THEN** as aulas dessas datas não oferecem o encerramento

## MODIFIED Requirements

### Requirement: Alocação como agendamento recorrente do espaço
Uma alocação DEVE (MUST) registrar, para um semestre, a ocupação de um espaço por uma turma, numa disciplina, com um ou mais docentes, num dia da semana e numa faixa de horário. O espaço e os docentes PODEM (MAY) estar ausentes, porque a planilha institucional traz atividade sem sala e atividade sem docente reconhecido, e uma alocação sem espaço NÃO DEVE (MUST NOT) ocupar espaço nenhum. Cada alocação DEVE (MUST) cobrir exatamente uma faixa de horário, e o sistema NÃO DEVE (MUST NOT) unir faixas seguidas numa alocação única. Duas alocações do mesmo semestre PODEM (MAY) ter o mesmo espaço, o mesmo dia e a mesma faixa de horário, e a importação NÃO DEVE (MUST NOT) recusar esse caso nem tratá-lo como conflito. A importação NÃO DEVE (MUST NOT) implementar detecção de conflito de espaço ou de docente, nem reproduzir a marcação de choque da planilha institucional, nem gravar essa marcação como dado. A detecção de conflito DEVE (MUST) existir só nas operações feitas no sistema: a alteração da recorrência e a criação da recorrência.

Cada alocação DEVE (MUST) ter uma vigência, com início e fim opcionais: vazios, a alocação vale o período inteiro do semestre. A alocação criada pela importação DEVE (MUST) ter a vigência vazia, e a criada pela interface DEVE (MUST) ter o início preenchido. O fim da vigência PODE (MAY) ser anterior ao início, e esse par DEVE (MUST) significar uma recorrência encerrada sem nenhuma ocorrência. Nenhum par de datas da vigência DEVE (MUST) ser recusado pelo banco. A identidade de uma alocação DEVE (MUST) ser o semestre, a turma, o dia, a faixa, a disciplina e o início da vigência.

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

#### Scenario: Recorrência sem nenhuma ocorrência
- **GIVEN** uma alocação com o início da vigência em 06/10/2026
- **WHEN** o fim da vigência passa a ser 05/10/2026
- **THEN** a alocação existe e não gera ocorrência em data nenhuma
