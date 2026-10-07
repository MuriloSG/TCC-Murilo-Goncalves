## Context

Uma aula de várias faixas é um bloco de alocações, uma por faixa. A alteração casava cada alocação atual com uma faixa nova (`zip`), por isso a quantidade não podia mudar. As exceções de cancelamento existem por alocação e por data.

## Decisions

### D1. Duração como no cadastro
O formulário usa o mesmo par do cadastro: "Horário de início", com as faixas do semestre, e "Duração", de 1 faixa até a maior sequência de faixas seguidas (`duration_choices`). O model confere se a sequência existe a partir do início escolhido e recusa com "Escolha um horário do semestre." no campo do horário.

### D2. Faixas casadas pela ordem
As alocações atuais e as faixas novas são casadas na ordem do horário. As casadas seguem a regra existente: versão nova, exceções transferidas e auditoria da alteração.

### D3. Faixa a mais
Cada faixa sem alocação atual vira uma `RecurrenceAddition`, com a turma, a disciplina e o fim da vigência da aula. Ela recebe uma exceção de cancelamento para cada ocorrência cancelada da aula da data em diante, para que o cancelamento continue valendo no bloco inteiro, e registra a criação na auditoria como o cadastro.

### D4. Faixa que sobra
Cada alocação atual sem faixa nova vira uma `RecurrenceRemoval`: só é encerrada na véspera da data, como no encerramento da recorrência, e as exceções dela continuam onde estão.

### D5. Parâmetro opcional
`slot_count` é opcional em `plan_recurrence` e `change_recurrence`; sem ele, a aula mantém a quantidade de faixas, como antes.
