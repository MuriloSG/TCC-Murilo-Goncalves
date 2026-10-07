## MODIFIED Requirements

### Requirement: Alteração da recorrência a partir de uma data
Um usuário ativo com `ENSALAMENTO.ALTERAR_RECORRENCIA`, ou superadmin ativo, DEVE (MUST) poder alterar a recorrência de uma aula a partir de uma data, informando o dia da semana, o horário de início, a duração em faixas seguidas, o espaço e os docentes. Cada alocação da aula DEVE (MUST) ser encerrada na véspera da data, sem outra mudança, e uma alocação nova DEVE (MUST) começar na data para cada faixa da duração escolhida, com a origem `MANUAL`, os dados informados, a mesma turma, disciplina e semestre, e o fim da vigência da anterior. As ocorrências anteriores à data NÃO DEVEM (MUST NOT) mudar. Uma aula de várias faixas seguidas DEVE (MUST) mudar inteira, para um intervalo de faixas seguidas do semestre com a quantidade escolhida, que PODE (MAY) ser maior ou menor que a atual, e o sistema NÃO DEVE (MUST NOT) criar faixa de horário. Quando a duração aumenta, cada faixa a mais DEVE (MUST) receber as ocorrências canceladas da aula da data em diante.

A data DEVE (MUST) ser de hoje em diante, estar no período do semestre, ser uma ocorrência da regra atual e ser posterior ao início da vigência. O espaço escolhido DEVE (MUST) estar ativo, salvo quando é o atual. A alteração DEVE (MUST) mudar ao menos um dado, e a duração conta como dado. A alteração DEVE (MUST) ser recusada, com a explicação, quando o espaço estiver ocupado em alguma ocorrência não cancelada da regra nova por agendamento aprovado ou por aula de outra alocação com disciplina ou docentes diferentes; aula com a mesma disciplina e os mesmos docentes é turma junta e NÃO DEVE (MUST NOT) impedir a alteração. A alteração também DEVE (MUST) ser recusada quando a turma já tem a mesma disciplina no mesmo dia e faixa na vigência nova, e quando o semestre não tem a quantidade de faixas seguidas escolhida a partir do horário de início.

A alteração DEVE (MUST) ser atômica: a recusa ou a falha de qualquer etapa NÃO DEVE (MUST NOT) deixar a alocação encerrada sem a nova. A interface DEVE (MUST) oferecer a ação "Alterar recorrência" no card da Grade datada, de hoje em diante, só a quem pode executá-la, deixar claro que a alteração vale para todas as aulas a partir da data e mostrar o resumo de antes, da data e de depois antes da confirmação. O formulário DEVE (MUST) trazer "Horário de início" e "Duração" como o cadastro da aula, com a duração atual escolhida. A permissão DEVE (MUST) ser conferida na execução, e não só pela ação escondida.

#### Scenario: Troca de sala a partir de uma data
- **GIVEN** a aula de segunda-feira das 08:00 às 10:00 na `HV 1`, desde 01/09/2026
- **WHEN** um usuário com a permissão altera a recorrência a partir de 05/10/2026 para a `HV 2`
- **THEN** a alocação original vale até 04/10/2026 na `HV 1`
- **AND** uma alocação nova vale de 05/10/2026 até o fim do semestre na `HV 2`, com a mesma turma, disciplina, dia, horário e docentes
- **AND** a Grade, a Agenda e o calendário público mostram a `HV 1` até 28/09/2026 e a `HV 2` a partir de 05/10/2026

#### Scenario: Aula estendida
- **GIVEN** a aula de segunda-feira das 10:00 às 12:00, em duas faixas
- **WHEN** a recorrência é alterada a partir de 05/10/2026 para começar às 09:00 com 3 faixas seguidas
- **THEN** a partir de 05/10/2026 a aula ocupa das 09:00 às 12:00, e as ocorrências anteriores continuam das 10:00 às 12:00

#### Scenario: Aula encurtada
- **WHEN** a mesma aula é alterada a partir de 05/10/2026 para 1 faixa
- **THEN** a partir de 05/10/2026 a aula ocupa das 10:00 às 11:00, e a alocação das 11:00 vale até 04/10/2026

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
