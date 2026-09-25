## ADDED Requirements

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
