## ADDED Requirements

### Requirement: Grade por sala da importação de ensalamento
O detalhe de uma importação de ensalamento DEVE (MUST) abrir na Grade, também numa importação `COM_ERROS`. A Grade DEVE (MUST) ter um único filtro, a sala, com as salas da lista de salas da planilha, na ordem da planilha, e a primeira sala da lista como padrão. Uma sala que não está na lista DEVE (MUST) cair no padrão, sem erro. A Grade DEVE (MUST) mostrar a semana inteira da sala escolhida: as faixas de horário com atividade na importação nas linhas, na ordem do início, e os dias de segunda a sexta nas colunas, com o dia atual marcado como "Hoje". Cada faixa ocupada DEVE (MUST) mostrar a disciplina, a turma com o curso e os docentes, e indicar a etapa da turma por texto e cor. A mesma atividade em faixas seguidas sem intervalo entre elas DEVE (MUST) aparecer uma vez, ocupando as faixas. A Grade NÃO DEVE (MUST NOT) mostrar linhas de intervalo. A Grade DEVE (MUST) informar quantas faixas da semana estão ocupadas e quantas estão disponíveis na sala. A Grade DEVE (MUST) ser montada a partir das linhas gravadas da importação, com as mesmas funções de leitura que a execução usa, e NÃO DEVE (MUST NOT) gravar dados, executar linhas, alterar o plano nem abrir o arquivo. A Grade exige a permissão `ENSALAMENTO.IMPORTAR`, como as demais telas da importação.

#### Scenario: Grade aberta por padrão
- **GIVEN** uma importação de ensalamento `VALIDADA` da planilha corrigida
- **WHEN** o detalhe da importação é aberto sem filtro
- **THEN** a Grade mostra a semana da primeira sala da lista de salas da planilha
- **AND** o select de sala lista as salas na ordem da planilha

#### Scenario: Sala na URL
- **WHEN** a Grade é aberta com `sala=1/13`
- **THEN** ela mostra a semana da sala `1/13`, com ou sem JavaScript

#### Scenario: Sala fora da lista
- **WHEN** a Grade é aberta com uma sala que não está na lista de salas da importação
- **THEN** ela mostra a primeira sala da lista, e a resposta é 200

#### Scenario: Card da atividade
- **GIVEN** a atividade `CÁLCULO III (Viviane) (2/6)` na turma `4º PERÍODO` de um curso de graduação
- **WHEN** a Grade da sala `2/6` é exibida
- **THEN** a faixa da atividade mostra a disciplina `CÁLCULO III`, a turma com o curso, o docente `Viviane` e a indicação de graduação

#### Scenario: Faixas seguidas com a mesma atividade
- **GIVEN** a mesma atividade na mesma sala, turma e dia nas faixas `07:20 - 08:10` e `08:10 - 09:00`
- **WHEN** a Grade da sala é exibida
- **THEN** a atividade aparece uma vez, ocupando as duas faixas

#### Scenario: Atividade não atravessa intervalo
- **GIVEN** a mesma atividade na mesma sala, turma e dia nas faixas `08:10 - 09:00` e `09:20 - 10:10`
- **WHEN** a Grade da sala é exibida
- **THEN** a atividade aparece duas vezes, uma em cada faixa, e nenhuma linha de intervalo é mostrada

#### Scenario: Dia atual
- **GIVEN** o dia atual é uma sexta-feira
- **WHEN** a Grade é exibida
- **THEN** a coluna da sexta-feira é marcada como "Hoje"

#### Scenario: Sala sem atividade
- **GIVEN** uma sala da lista sem nenhuma atividade na importação
- **WHEN** a Grade dessa sala é exibida
- **THEN** todas as faixas aparecem disponíveis e a quantidade de faixas ocupadas é zero

#### Scenario: Importação recusada
- **GIVEN** uma importação com erro do arquivo e sem linhas
- **WHEN** a Grade é aberta
- **THEN** a tela mostra os erros do arquivo e o fato "Nenhuma atividade lida do arquivo.", sem grade

#### Scenario: Grade sem gravação
- **GIVEN** uma importação `VALIDADA`
- **WHEN** a Grade é exibida para qualquer sala
- **THEN** a quantidade de semestres, cursos, turmas, disciplinas, docentes, espaços, faixas e alocações não muda
- **AND** as linhas e a situação da importação não mudam

### Requirement: Turmas juntas e choque na Grade
Quando mais de uma turma ocupa a sala na mesma faixa do mesmo dia, a Grade DEVE (MUST) agrupar as turmas na célula e classificar o grupo: "turmas juntas" quando todas têm a mesma disciplina, sem diferenciar maiúsculas de minúsculas, e os mesmos docentes; "choque" nos demais casos. O choque DEVE (MUST) ser indicado com ícone e texto, e não só com cor. A Grade DEVE (MUST) informar quantas faixas da semana da sala têm choque, e o select de sala DEVE (MUST) marcar as salas com choque. O choque NÃO DEVE (MUST NOT) virar erro da linha, impedir a confirmação nem alterar o plano.

#### Scenario: Turmas juntas
- **GIVEN** a disciplina `Cálculo Diferencial e integral III` com o docente `Eilson Santiago` para duas turmas na mesma sala, dia e faixa
- **WHEN** a Grade da sala é exibida
- **THEN** a célula mostra as duas turmas agrupadas como "2 turmas juntas"

#### Scenario: Choque
- **GIVEN** duas disciplinas diferentes, de turmas diferentes, na mesma sala, dia e faixa
- **WHEN** a Grade da sala é exibida
- **THEN** a célula mostra as duas turmas agrupadas sob "Choque: 2 turmas neste horário", com o ícone de aviso
- **AND** a sala aparece marcada com choque no select de sala

#### Scenario: Choque não bloqueia
- **GIVEN** uma importação `VALIDADA` com choque numa sala
- **WHEN** a importação é confirmada
- **THEN** a confirmação acontece como numa importação sem choque

### Requirement: Erros da importação na Grade
Uma atividade com erro que tem sala reconhecida DEVE (MUST) aparecer na Grade da sala com o estado de erro, indicado com ícone e texto, mostrando o texto da planilha no lugar da leitura, e DEVE (MUST) levar à Conferência filtrada nas linhas dela. A mensagem do erro NÃO DEVE (MUST NOT) ser repetida no conteúdo do card. A Grade DEVE (MUST) informar quantas atividades da sala têm erro e quantas linhas com erro não têm lugar em nenhuma sala, cada contagem com o link para a Conferência.

#### Scenario: Atividade com docente fora do catálogo
- **GIVEN** a atividade `Deontologia Veterinária ( Fernanda ) (HV 2)`, com erro `docente_desconhecido`, na linha 812
- **WHEN** a Grade da sala `HV 2` é exibida
- **THEN** o card da atividade tem o ícone de erro, o texto "Com erro" e o texto da planilha
- **AND** o link do card leva à Conferência com `numero=812`

#### Scenario: Erro sem sala
- **GIVEN** uma atividade cuja sala não está na lista de salas
- **WHEN** a Grade de qualquer sala é exibida
- **THEN** a Grade informa a quantidade de linhas com erro fora da Grade, com o link para a Conferência
