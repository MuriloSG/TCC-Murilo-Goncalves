## MODIFIED Requirements

### Requirement: Entidades do ensalamento
O sistema DEVE (MUST) representar como entidades próprias o espaço, o curso, a disciplina, o docente, a turma, a faixa de horário e a alocação, e NÃO DEVE (MUST NOT) guardar nenhuma delas como texto dentro de outra. O espaço, o curso, a disciplina, o docente e a turma DEVEM (MUST) valer para todos os semestres, e a faixa de horário e a alocação DEVEM (MUST) pertencer a um semestre. Cada entidade DEVE (MUST) ser identificada assim, sempre sem diferenciar maiúsculas de minúsculas e sempre diferenciando letras acentuadas das não acentuadas:

- espaço: pelo nome atual ou por um dos outros nomes, conforme a spec `gestao-espacos`;
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
- **GIVEN** o docente `Aldo Gomes`
- **WHEN** a criação do docente ` aldo  gomes ` é tentada
- **THEN** nenhum docente novo é criado e a operação devolve o docente existente

#### Scenario: Espaço identificado pelo outro nome
- **GIVEN** o espaço `HV 5` com o outro nome `HV5`
- **WHEN** uma alocação é gravada para o espaço identificado por `hv5`
- **THEN** a alocação aponta para o espaço `HV 5`

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

### Requirement: Importação do ensalamento por planilha
Um usuário ativo autenticado com a permissão `ENSALAMENTO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder carregar um semestre de ensalamento a partir da planilha institucional, conforme a spec `importacao-planilhas`, com o tipo `ENSALAMENTO`. Quando a importação altera o cadastro de espaços, a confirmação DEVE (MUST) exigir também as permissões de espaço descritas em "Permissões de espaço na importação". O sistema NÃO DEVE (MUST NOT) exigir nenhuma alteração na planilha: NÃO DEVE (MUST NOT) exigir coluna, aba, identificador, código ou marcação criados para ele, e NÃO DEVE (MUST NOT) alterar o arquivo enviado.

O envio DEVE (MUST) receber o arquivo da planilha e o código do semestre, porque nenhuma aba da planilha traz o semestre. O código DEVE (MUST) ser obrigatório e validado no formato do semestre, e o semestre DEVE (MUST) ser criado quando ainda não existir. Um envio sem o código, ou com um código fora do formato, DEVE (MUST) ser recusado no formulário de envio, sem criar importação. A importação inteira DEVE (MUST) ficar vinculada ao semestre informado, e todas as alocações e faixas de horário dela DEVEM (MUST) pertencer a ele. O código DEVE (MUST) ser gravado nos valores de cada linha, e a confirmação DEVE (MUST) usar o código gravado, e não um informado de novo.

Depois da importação, os dados carregados DEVEM (MUST) ser dados do sistema. Nenhuma funcionalidade DEVE (MUST) consultar a planilha em tempo de execução para saber a ocupação de um espaço, e a ocupação DEVE (MUST) ser respondida a partir das alocações gravadas. O sistema NÃO DEVE (MUST NOT) guardar o arquivo enviado depois da leitura, e NÃO DEVE (MUST NOT) manter nenhuma sincronização automática com a planilha ou com serviço externo.

A importação NÃO DEVE (MUST NOT) criar, alterar nem desativar usuário, e a ausência de um usuário correspondente a um docente NÃO DEVE (MUST NOT) impedir a importação do docente nem da alocação.

#### Scenario: Carga de um semestre
- **GIVEN** um usuário com `ENSALAMENTO.IMPORTAR` e `ESPACO.CRIAR` e a planilha institucional, com o cadastro de espaços vazio
- **WHEN** ele envia o arquivo com o semestre `2026/1` e confirma a importação
- **THEN** o semestre, os espaços usados pelas aulas, os cursos, as disciplinas, os docentes, as turmas, as faixas de horário e as alocações da planilha existem no banco
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

#### Scenario: Reimportação sem mudança de espaços com a permissão de importar
- **GIVEN** um usuário cujo perfil concede somente `ENSALAMENTO.IMPORTAR`
- **AND** uma planilha em que todos os espaços usados já são reconhecidos
- **WHEN** ele envia e confirma a importação
- **THEN** a importação é concluída sem exigir permissão de espaço

#### Scenario: Acesso sem a permissão
- **GIVEN** um usuário ativo autenticado sem `ENSALAMENTO.IMPORTAR`
- **WHEN** ele acessa qualquer rota da importação de ensalamento
- **THEN** o acesso é recusado com 403

#### Scenario: Visitante não autenticado
- **WHEN** um visitante não autenticado acessa qualquer rota da importação de ensalamento
- **THEN** ele é redirecionado para a página de login

### Requirement: Catálogo de espaços e de docentes da planilha
Os docentes DEVEM (MUST) ser criados ou reconhecidos a partir da lista de docentes da aba de validação de dados, e NÃO DEVEM (MUST NOT) ser criados a partir do texto das células de atividade. Todos os valores da lista de docentes DEVEM (MUST) virar registro, inclusive os que nenhuma atividade referencia.

A lista de salas da aba de validação de dados DEVE (MUST) ser a fonte dos nomes que a importação pode propor como espaço novo, conforme "Classificação dos espaços da importação", e NÃO DEVE (MUST NOT) criar espaço por si só: um nome da lista vira espaço somente quando é usado por uma aula, não identifica nenhum espaço e é proposto como novo ou decidido como novo, e somente na confirmação. Um nome da lista que nenhuma aula usa NÃO DEVE (MUST NOT) ser cadastrado, e a linha dele DEVE (MUST) ficar sem ação, com um aviso que diga isso, quando ele não identificar um espaço existente.

Cada valor das duas listas DEVE (MUST) ser uma linha própria da importação, com a célula de origem dele, e essas linhas DEVEM (MUST) vir antes das linhas de atividade. Os parênteses que envolvem o nome do espaço na lista DEVEM (MUST) ser retirados, porque a lista mistura valores com e sem parênteses. Valores equivalentes na mesma lista DEVEM (MUST) ser tratados como um só nome. Uma lista vazia DEVE (MUST) recusar o arquivo.

A linha de sala DEVE (MUST) ter a ação `create` quando o espaço será criado com aquele nome, `update` quando um espaço existente receberá aquele nome como outro nome ou será reativado, `unchanged` quando o nome identifica um espaço ativo e nada muda nele, e nenhuma ação quando o nome não é cadastrado nem precisa de decisão. A linha de sala cujo nome precisa de decisão DEVE (MUST) ter a pendência do espaço, conforme a spec `importacao-planilhas`.

#### Scenario: Prévia mostra as salas da planilha
- **GIVEN** uma importação de ensalamento com a prévia gerada
- **WHEN** o recorte das salas é escolhido no detalhe
- **THEN** são listadas todas as linhas de sala, com a célula de origem, o valor lido, a ação e a pendência de cada uma

#### Scenario: Espaço com e sem parênteses
- **GIVEN** o cadastro de espaços vazio e a lista de espaços com os valores `(1/10)` e `Lab. de Madeira`, ambos usados por aulas
- **WHEN** a importação é confirmada
- **THEN** existem os espaços `1/10` e `Lab. de Madeira`

#### Scenario: Valor repetido na lista
- **GIVEN** o cadastro de espaços vazio e a lista de espaços com `(Lab. Bromatologia)` em duas linhas, usado por uma aula
- **WHEN** a importação é confirmada
- **THEN** existe um único espaço `Lab. Bromatologia`
- **AND** a primeira linha tem a ação `create` e a segunda a ação `unchanged`

#### Scenario: Sala da lista sem aula não é cadastrada
- **GIVEN** a lista de salas com `Lab. Carnes`, que nenhuma aula usa e que não identifica nenhum espaço
- **WHEN** a importação é confirmada
- **THEN** o espaço `Lab. Carnes` não existe
- **AND** a linha dele não tem ação e tem o aviso de sala sem aula

#### Scenario: Espaço existente citado só nas células
- **GIVEN** o espaço ativo `Zoo II`, criado por uma importação anterior
- **WHEN** a prévia de uma planilha cuja lista de salas não traz `Zoo II` e cuja atividade cita `(Zoo II)` é gerada
- **THEN** a atividade é lida com o espaço `Zoo II`, sem erro e sem pendência

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

Os nomes de espaço conhecidos na leitura DEVEM (MUST) ser os da lista de salas da planilha somados aos nomes atuais e aos outros nomes de todos os espaços do cadastro, ativos e inativos. Os nomes de docente conhecidos DEVEM (MUST) ser os da lista de docentes da planilha.

A leitura DEVE (MUST) acontecer do fim para o começo: o último grupo entre parênteses DEVE (MUST) ser o espaço quando corresponder a um nome de espaço conhecido. Quando não corresponder e o grupo anterior for uma lista de docentes conhecidos, o último grupo DEVE (MUST) ser lido como um nome de espaço citado só nas células, e DEVE (MUST) ser tratado conforme "Classificação dos espaços da importação", e não como erro da linha. Nos demais casos, a atividade NÃO DEVE (MUST NOT) ter espaço e o último grupo DEVE (MUST) ser considerado a lista de docentes. O grupo imediatamente anterior ao do espaço DEVE (MUST) ser a lista de docentes, com os nomes separados por `/`, `,` ou ` e `. A disciplina DEVE (MUST) ser o texto anterior à lista de docentes, com os parênteses internos preservados e os separadores das bordas retirados. Uma célula DEVE (MUST) poder conter mais de uma atividade, separadas pelos ` / ` que estiverem fora de parênteses, e cada atividade DEVE (MUST) ser uma linha própria da importação, com o seu plano e a sua alocação. A separação DEVE (MUST) acontecer somente quando cada trecho tiver pelo menos um grupo entre parênteses; sem isso, a célula DEVE (MUST) ser uma atividade só. O erro ou a pendência de uma atividade NÃO DEVE (MUST NOT) impedir o plano das demais atividades da mesma célula, e a origem de cada linha DEVE (MUST) distinguir a atividade dentro da célula.

A correspondência de um nome de docente ou de espaço com os nomes conhecidos DEVE (MUST) ser exata, ignorando apenas a diferença entre maiúsculas e minúsculas e a normalização de espaços. Ela NÃO DEVE (MUST NOT) remover acentos, NÃO DEVE (MUST NOT) usar similaridade, NÃO DEVE (MUST NOT) comparar por prefixo e NÃO DEVE (MUST NOT) aceitar correspondência parcial. A sugestão de espaços parecidos da spec `gestao-espacos` só DEVE (MUST) ser usada para montar as perguntas da classificação.

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

#### Scenario: Espaço citado só nas células
- **GIVEN** a célula `Zootecnia Geral e Pequenas Criações (Paulo Eduardo) (Zoo I)`, o docente `Paulo Eduardo` na lista e o nome `Zoo I` fora da lista de salas e do cadastro
- **WHEN** a prévia é gerada
- **THEN** a linha não recebe erro e tem a pendência do espaço `Zoo I`

#### Scenario: Grafia aprendida reconhecida nas células
- **GIVEN** o espaço `HV 1` com o outro nome `HV1`
- **AND** a célula `Fisiologia Animal I (Valéria) (HV1)`, com `HV1` fora da lista de salas
- **WHEN** a prévia é gerada
- **THEN** a atividade é lida com o espaço `HV 1`, sem erro e sem pendência

#### Scenario: Grafia diferente sem outro nome gravado
- **GIVEN** a lista de salas com `(HV 1)`, o cadastro sem o nome `HV1` e a célula `Fisiologia Animal I (Valéria) (HV1)`
- **WHEN** a prévia é gerada
- **THEN** a linha tem a pendência do espaço `HV1`, que não é associado a `HV 1` sem decisão

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

### Requirement: Registro de auditoria da importação de ensalamento
A importação de ensalamento DEVE (MUST) ser uma carga em lote, conforme a spec `auditoria`, e as operações de domínio executadas pelas suas linhas NÃO DEVEM (MUST NOT) gerar registro de auditoria por entidade, com exceção das alterações do cadastro de espaços, que DEVEM (MUST) ser registradas conforme o requisito "Auditoria do cadastro de espaços" da spec `auditoria`. O registro da confirmação DEVE (MUST) ser o resumo da importação, e DEVE (MUST) conter quem executou, a data e a hora, o código do semestre importado, o nome do arquivo, a chave da importação, a quantidade de registros criados, a quantidade de registros atualizados, a quantidade de registros preservados, a quantidade de linhas com erro, a quantidade de espaços cadastrados, a quantidade de outros nomes associados a espaços existentes, a quantidade de espaços reativados e o resultado final. O envio da prévia e o descarte DEVEM (MUST) continuar gerando registro, conforme a spec `importacao-planilhas`.

Os totais de registros e de linhas DEVEM (MUST) ser contados a partir das linhas da importação, e os totais de espaços DEVEM (MUST) ser contados a partir das alterações do cadastro aplicadas pela confirmação. Nenhum desses totais DEVE (MUST) ser gravado como campo da importação. O código do semestre DEVE (MUST) vir dos valores das linhas, e não de quem consulta.

#### Scenario: Resumo da confirmação
- **GIVEN** uma importação de ensalamento `VALIDADA` do semestre `2026/1` que cadastra 3 espaços e associa 1 outro nome
- **WHEN** ela é confirmada
- **THEN** existe um registro de auditoria da importação com quem confirmou, a data e a hora, o semestre `2026/1`, o nome do arquivo, a chave da importação, os totais de criados, atualizados e preservados, o total de linhas com erro, 3 espaços cadastrados, 1 outro nome associado, 0 espaço reativado e o resultado final

#### Scenario: Sem registro por entidade fora do cadastro de espaços
- **GIVEN** uma importação de ensalamento que cria centenas de alocações e cadastra 3 espaços
- **WHEN** ela é confirmada
- **THEN** existem 3 registros de cadastro de espaço
- **AND** não existe registro de auditoria de nenhuma alocação, docente, curso, disciplina, turma ou faixa de horário criados

#### Scenario: Prévia registrada
- **WHEN** a prévia de uma planilha de ensalamento é gerada
- **THEN** existe um registro de auditoria da prévia da importação
- **AND** não existe registro de nenhuma entidade do ensalamento nem de espaço, porque nada foi mantido

## ADDED Requirements

### Requirement: Classificação dos espaços da importação
A importação de ensalamento DEVE (MUST) reunir os nomes de espaço encontrados na planilha, agrupados pela comparação sem diferenciar maiúsculas de minúsculas e com os espaços normalizados, de modo que um nome citado em várias aulas seja um único nome encontrado. Os nomes encontrados DEVEM (MUST) ser os da lista de salas usados por pelo menos uma aula e os nomes citados só nas células, conforme "Leitura da atividade de uma célula". Os nomes da lista de salas que nenhuma aula usa NÃO DEVEM (MUST NOT) ser nomes encontrados.

Cada nome encontrado DEVE (MUST) receber exatamente uma destas classificações, nesta ordem de precedência:

1. **Reconhecido**: o nome identifica um espaço ativo, pelo nome atual ou por um outro nome. A aula usa esse espaço, sem pergunta e sem alteração do cadastro. O reconhecimento DEVE (MUST) prevalecer sobre qualquer decisão gravada para o nome.
2. **Decidido**: existe uma decisão válida para o nome, conforme "Decisões de espaço da importação", e o nome segue a decisão.
3. **Novo proposto**: o nome vem da lista de salas, não identifica nenhum espaço e não tem nenhum nome parecido, segundo a sugestão de espaços parecidos da spec `gestao-espacos`, entre os nomes de todos os espaços do cadastro, ativos e inativos, e entre os demais nomes encontrados da lista de salas. O espaço será cadastrado na confirmação, com esse nome, sem decisão individual. Um nome citado só nas células não torna ambíguo o nome da lista de salas, porque a lista é a referência que o campus mantém.
4. **Precisa de decisão**: todos os demais casos, isto é, o nome identifica um espaço inativo, tem um ou mais nomes parecidos, ou é citado só nas células. O nome citado só nas células NUNCA DEVE (MUST NOT) ser proposto como novo, mesmo sem nenhum parecido, e os parecidos dele DEVEM (MUST) ser procurados entre os nomes do cadastro e entre todos os demais nomes encontrados.

A classificação DEVE (MUST) ser calculada a partir das linhas gravadas da importação, do cadastro de espaços e das decisões gravadas, sem executar as linhas nem abrir o arquivo, e DEVE (MUST) ser a mesma usada pela execução. Cada nome que precisa de decisão DEVE (MUST) virar uma pendência, conforme a spec `importacao-planilhas`, na linha de sala dele, quando houver, e em cada linha de atividade que o usa, e essas linhas de atividade NÃO DEVEM (MUST NOT) ser executadas enquanto houver a pendência. Para cada nome encontrado, a classificação DEVE (MUST) oferecer o uso agregado: a quantidade de aulas, a quantidade de turmas e os dias da semana em que ele aparece.

#### Scenario: Primeira importação da planilha corrigida
- **GIVEN** o cadastro de espaços vazio e a planilha `planilha_example_corrigida.xlsx`
- **WHEN** a prévia é gerada
- **THEN** os 62 nomes da lista de salas usados por aulas são novos propostos, nenhum nome precisa de decisão e a importação fica `VALIDADA`
- **AND** os 24 nomes da lista sem aula não são nomes encontrados

#### Scenario: Primeira importação da planilha original
- **GIVEN** o cadastro de espaços vazio e a planilha `planilha_example.xlsx`
- **WHEN** a prévia é gerada
- **THEN** `HV 1`, `HV 3` e `HV 4`, da lista, são novos propostos
- **AND** precisam de decisão `HV1`, `HV3` e `HV4`, citados só nas células e parecidos com `HV 1`, `HV 3` e `HV 4`, e `HV5`, `Zoo I`, `EaD` e `2/41`, citados só nas células e sem parecido
- **AND** a importação fica `COM_ERROS`, porque a planilha também tem docentes fora do catálogo, e o quadro mostra esses nomes sem controles de decisão

#### Scenario: Nome citado em várias aulas
- **GIVEN** o nome `HV5`, citado só nas células, em 12 aulas de 3 turmas, na segunda e na quarta-feira
- **WHEN** a classificação é calculada
- **THEN** existe um único nome encontrado `HV5`, com 12 aulas, 3 turmas e os dias segunda e quarta-feira

#### Scenario: Nome reconhecido pelo outro nome
- **GIVEN** o espaço ativo `HV 5` com o outro nome `HV5`
- **WHEN** a planilha cita `HV5`
- **THEN** o nome é reconhecido e as aulas usam o espaço `HV 5`, sem pergunta

#### Scenario: Vários parecidos
- **GIVEN** os espaços `Lab. Química I` e `Lab. Química II`
- **WHEN** a lista de salas traz `Lab. Química`, usado por uma aula
- **THEN** o nome precisa de decisão, com os dois espaços como parecidos, e não é associado a nenhum deles

#### Scenario: Espaço inativo citado
- **GIVEN** o espaço inativo `Lab. Redes`
- **WHEN** uma aula da planilha cita `Lab. Redes`
- **THEN** o nome precisa de decisão, e o espaço não é reativado

### Requirement: Decisões de espaço da importação
Numa importação de ensalamento `PENDENTE` ou `VALIDADA`, um usuário com `ENSALAMENTO.IMPORTAR` DEVE (MUST) poder gravar, para cada nome encontrado que não é reconhecido, uma decisão entre:

- **"É um espaço novo"**: o espaço será cadastrado com o nome encontrado;
- **"É o mesmo que"** um espaço do cadastro, ativo ou inativo, ou outro nome encontrado da mesma importação que será cadastrado: o nome encontrado será guardado como outro nome desse espaço;
- **"Reativar"**, somente para o nome que identifica um espaço inativo: o espaço será reativado.

Para o nome que é o nome atual de um espaço inativo, somente a reativação DEVE (MUST) ser oferecida. Para o nome que é um outro nome de um espaço inativo, "É um espaço novo" e "É o mesmo que" DEVEM (MUST) retirar esse outro nome do espaço inativo. "É o mesmo que" um espaço inativo DEVE (MUST) reativá-lo. Um novo proposto DEVE (MUST) aceitar a decisão "É o mesmo que", para o caso raro de ele ser um espaço já cadastrado com outro nome.

A decisão DEVE (MUST) ser gravada na própria importação, com a importação, o nome encontrado, o tipo, o espaço ou o nome encontrado escolhido quando houver, quem decidiu e quando. Cada nome encontrado DEVE (MUST) ter no máximo uma decisão por importação, e uma decisão nova DEVE (MUST) substituir a anterior. Uma decisão DEVE (MUST) poder ser desfeita enquanto a importação estiver `PENDENTE` ou `VALIDADA`. Gravar ou desfazer uma decisão NÃO DEVE (MUST NOT) criar, alterar, desativar, reativar nem excluir espaço ou outro nome, e NÃO DEVE (MUST NOT) ser possível numa importação `COM_ERROS`, `CONCLUIDA` ou `DESCARTADA`. A decisão DEVE (MUST) ser registrada na auditoria da importação, e não na do espaço.

Uma decisão que perdeu o sentido DEVE (MUST) ser desconsiderada, e o nome volta a ser classificado sem ela: quando o nome passou a identificar um espaço ativo, quando o espaço escolhido foi excluído, ou quando o nome encontrado escolhido não será mais cadastrado. Excluir ou descartar a importação NÃO DEVE (MUST NOT) deixar nenhuma alteração no cadastro de espaços, e excluir a importação DEVE (MUST) excluir as decisões dela.

#### Scenario: Associação decidida
- **GIVEN** uma importação `PENDENTE` em que `HV1` precisa de decisão, parecido com o espaço `HV 1`
- **WHEN** um usuário com `ESPACO.EDITAR` escolhe "É o mesmo que HV 1"
- **THEN** a decisão é gravada com ele e a data e a hora
- **AND** o espaço `HV 1` continua sem o outro nome `HV1` até a confirmação

#### Scenario: Espaço novo decidido para nome só nas células
- **GIVEN** uma importação `PENDENTE` em que `Zoo I` é citado só nas células
- **WHEN** um usuário com `ESPACO.CRIAR` escolhe "É um espaço novo"
- **THEN** a decisão é gravada e nenhum espaço é criado antes da confirmação

#### Scenario: Associação a outro nome desta importação
- **GIVEN** o cadastro de espaços vazio, `HV 1` novo proposto pela lista e `HV1` citado só nas células
- **WHEN** um usuário com `ESPACO.CRIAR` escolhe "É o mesmo que HV 1" para `HV1` e a importação é confirmada
- **THEN** existe o espaço `HV 1` com o outro nome `HV1`, e as aulas que citam `HV1` usam esse espaço

#### Scenario: Decisão desfeita
- **GIVEN** uma importação `VALIDADA` com a decisão "É um espaço novo" para `Zoo I`
- **WHEN** a decisão é desfeita
- **THEN** `Zoo I` volta a precisar de decisão e a importação volta a `PENDENTE`

#### Scenario: Reconhecimento prevalece sobre decisão antiga
- **GIVEN** uma importação `VALIDADA` com a decisão "É um espaço novo" para `Sala 101`
- **AND** que outro usuário cadastrou o espaço `Sala 101` pela tela depois da decisão
- **WHEN** a importação é confirmada
- **THEN** nada é aplicado, a prévia é refeita com `Sala 101` reconhecido e nenhum espaço duplicado é criado

#### Scenario: Descarte sem alteração do cadastro
- **GIVEN** uma importação `PENDENTE` com decisões gravadas
- **WHEN** ela é descartada
- **THEN** nenhum espaço, outro nome ou situação de espaço foi alterado

### Requirement: Permissões de espaço na importação
Gravar ou desfazer uma decisão DEVE (MUST) exigir, além de `ENSALAMENTO.IMPORTAR`, a permissão de espaço da alteração que a decisão fará: `ESPACO.CRIAR` para "É um espaço novo" e para "É o mesmo que" um nome encontrado que será cadastrado; `ESPACO.EDITAR` para "É o mesmo que" um espaço do cadastro e para retirar um outro nome de um espaço inativo; e `ESPACO.ALTERAR_SITUACAO` para reativar, inclusive pela associação a um espaço inativo. A falta da permissão DEVE (MUST) recusar a decisão com mensagem, sem gravar nada, e os controles de decisão DEVEM (MUST) aparecer somente para as decisões que o usuário pode tomar.

Confirmar uma importação de ensalamento que altera o cadastro de espaços DEVE (MUST) exigir, além de `ENSALAMENTO.IMPORTAR`, `ESPACO.CRIAR` quando ela cadastra algum espaço, `ESPACO.EDITAR` quando ela acrescenta ou retira outro nome de um espaço existente e `ESPACO.ALTERAR_SITUACAO` quando ela reativa algum espaço. As permissões DEVEM (MUST) ser conferidas contra quem confirma, pelo que a importação vai alterar no momento da confirmação, antes de reexecutar as linhas. A falta de uma delas DEVE (MUST) recusar a confirmação com a mensagem "A importação encontrou espaços que precisam ser cadastrados ou associados. O seu perfil não tem permissão para essa configuração.", sem alterar a importação nem nenhum dado. A importação que não altera o cadastro de espaços NÃO DEVE (MUST NOT) exigir permissão de espaço. A falta de permissão de espaço NÃO DEVE (MUST NOT) virar erro de linha nem mudar o plano, para que outro usuário com a permissão possa concluir a mesma importação.

#### Scenario: Usuário só com a permissão de importar
- **GIVEN** um usuário cujo perfil concede somente `ENSALAMENTO.IMPORTAR`
- **AND** uma importação `VALIDADA` que cadastra 3 espaços
- **WHEN** ele abre a prévia
- **THEN** o controle de confirmar não aparece, e a prévia mostra "A importação encontrou espaços que precisam ser cadastrados ou associados. O seu perfil não tem permissão para essa configuração."
- **WHEN** ele envia a confirmação por POST
- **THEN** a confirmação é recusada com essa mensagem e a importação continua `VALIDADA`

#### Scenario: Outro usuário conclui a importação
- **GIVEN** a importação do cenário anterior, enviada pelo usuário só com `ENSALAMENTO.IMPORTAR`
- **WHEN** um usuário com `ENSALAMENTO.IMPORTAR` e `ESPACO.CRIAR` a confirma
- **THEN** os 3 espaços são cadastrados e a importação fica `CONCLUIDA`

#### Scenario: Permissão parcial nas decisões
- **GIVEN** um usuário com `ENSALAMENTO.IMPORTAR` e `ESPACO.CRIAR`, sem `ESPACO.EDITAR`
- **AND** o nome `HV5` que precisa de decisão, parecido com o espaço `HV 5`
- **WHEN** ele abre a prévia
- **THEN** a pendência oferece "É um espaço novo" e não oferece "É o mesmo que HV 5"
- **WHEN** ele envia por POST a decisão "É o mesmo que HV 5"
- **THEN** a decisão é recusada com mensagem e nada é gravado

#### Scenario: Reativação exige a permissão de situação
- **GIVEN** uma importação `VALIDADA` com a decisão de reativar `Lab. Redes`
- **AND** um usuário com `ENSALAMENTO.IMPORTAR` e `ESPACO.CRIAR`, sem `ESPACO.ALTERAR_SITUACAO`
- **WHEN** ele confirma a importação
- **THEN** a confirmação é recusada com a mensagem de permissão e nada muda

### Requirement: Aplicação dos espaços na confirmação
A execução da importação de ensalamento DEVE (MUST) aplicar ao cadastro de espaços o resultado da classificação antes das linhas de atividade: cadastrar cada novo proposto e cada nome decidido como novo, com o nome encontrado como nome atual, a origem `PLANILHA` e a importação como importação de origem, junto com os outros nomes associados a ele pela mesma importação; acrescentar cada nome associado a um espaço existente como outro nome dele; retirar os outros nomes movidos de espaços inativos; e reativar os espaços decididos. As aulas DEVEM (MUST) usar o espaço resultante. Essas alterações DEVEM (MUST) usar as operações do cadastro de espaços da spec `gestao-espacos`, e DEVEM (MUST) acontecer na mesma transação das alocações: na prévia e na atualização da prévia elas DEVEM (MUST) ser desfeitas com o resto, e na confirmação DEVEM (MUST) ser efetivadas junto com as alocações, a situação `CONCLUIDA` e os registros de auditoria, ou nenhuma delas DEVE (MUST) ser efetivada. A importação NÃO DEVE (MUST NOT) excluir espaço, desativar espaço nem mudar a origem de espaço existente.

Quando o cadastro de espaços mudar entre a prévia e a confirmação, o plano da confirmação DEVE (MUST) divergir conforme a spec `importacao-planilhas`, e nada DEVE (MUST) ser aplicado. A importação concluída DEVE (MUST) permitir consultar os espaços que ela cadastrou.

#### Scenario: Espaços criados só na confirmação
- **GIVEN** o cadastro de espaços vazio e uma importação `VALIDADA` com 62 novos propostos
- **WHEN** a prévia é exibida
- **THEN** nenhum espaço existe
- **WHEN** a importação é confirmada por quem tem `ESPACO.CRIAR`
- **THEN** existem 62 espaços com a origem `PLANILHA` e essa importação como importação de origem

#### Scenario: Falha na confirmação não deixa espaço
- **GIVEN** uma importação `VALIDADA` que cadastra 3 espaços
- **WHEN** uma operação falha na confirmação depois de cadastrados os espaços e antes do fim das alocações
- **THEN** nenhum dos 3 espaços existe e nenhuma alocação foi aplicada

#### Scenario: Outro nome acrescentado na confirmação
- **GIVEN** uma importação `VALIDADA` com a decisão "É o mesmo que HV 5" para `HV5`
- **WHEN** ela é confirmada
- **THEN** o espaço `HV 5` tem o outro nome `HV5`, mantém a origem, e as aulas que citam `HV5` usam `HV 5`
- **AND** uma importação seguinte que cita `HV5` o reconhece sem pergunta

#### Scenario: Espaço novo cadastrado por outra importação no meio do caminho
- **GIVEN** duas importações `VALIDADA`, de semestres diferentes, que propõem o novo espaço `Sala 101`
- **WHEN** a primeira é confirmada e depois a segunda é confirmada
- **THEN** a segunda não aplica nada, a prévia dela é refeita com `Sala 101` reconhecido e existe um único espaço `Sala 101`

### Requirement: Quadro de espaços da prévia
O detalhe de uma importação de ensalamento DEVE (MUST) mostrar, antes das linhas, o quadro "Espaços desta importação", calculado pela classificação, dentro da experiência de importar o ensalamento e sem etapa separada de cadastro. Enquanto a importação estiver `PENDENTE` ou `VALIDADA`, o quadro DEVE (MUST) mostrar a frase "Nenhuma alteração foi feita no cadastro de espaços." e as quantidades, cada uma com a lista dos nomes que ela conta, recolhida:

- "<n> espaços já cadastrados foram reconhecidos.";
- "<n> espaços novos serão cadastrados ao confirmar esta importação.", com os novos propostos e os decididos como novos;
- "<n> nomes serão associados como outros nomes de espaços cadastrados.";
- "<n> espaços serão reativados.";
- "<n> espaços precisam de decisão antes de concluir.";
- e a informação de quantos nomes da lista de salas não têm aula e não serão cadastrados.

Uma quantidade zero DEVE (MUST) ser omitida. Cada nome que precisa de decisão DEVE (MUST) aparecer como um item próprio, com o nome como veio da planilha, a origem do nome ("Lista de salas" ou "Só nas aulas"), o uso agregado e as decisões possíveis: "É o mesmo que <espaço>" para cada parecido, com a indicação de que um espaço inativo será reativado; "É o mesmo que…" com a escolha entre os espaços do cadastro, quando não houver parecido ou quando o usuário quiser outro; "É um espaço novo", quando aplicável; e "Reativar <espaço>" para o espaço inativo. O nome citado só nas células DEVE (MUST) trazer também a orientação "Se for erro de digitação, corrija a planilha e envie de novo.". Cada novo proposto DEVE (MUST) oferecer, na lista dele, "Não é um espaço novo", que leva à escolha de um espaço do cadastro. As decisões DEVEM (MUST) ser feitas com um clique por nome, sem formulário de cadastro, e cada decisão gravada DEVE (MUST) mostrar o que acontecerá e oferecer "Alterar decisão".

Até a confirmação, os textos DEVEM (MUST) usar o futuro ("será cadastrado", "será associado", "será reativado") e NÃO DEVEM (MUST NOT) apresentar nenhuma alteração do cadastro como já feita. Quando a importação estiver `VALIDADA`, o quadro DEVE (MUST) informar "Pronta para confirmar." e, junto ao controle de confirmar, o resumo do que a confirmação gravará. Para quem não tem as permissões de espaço de uma decisão ou da confirmação, o quadro DEVE (MUST) mostrar as mesmas informações sem os controles correspondentes, com a mensagem "A importação encontrou espaços que precisam ser cadastrados ou associados. O seu perfil não tem permissão para essa configuração.". Numa importação `COM_ERROS`, o quadro DEVE (MUST) mostrar os nomes que precisarão de decisão sem nenhum controle, com a orientação "Depois de corrigir a planilha, estes espaços também vão precisar de decisão.". Numa importação `CONCLUIDA`, o quadro DEVE (MUST) informar os espaços cadastrados por ela, no passado, e a mensagem de conclusão DEVE (MUST) incluir as quantidades de espaços cadastrados, de outros nomes associados e de espaços reativados, omitindo as quantidades zero.

#### Scenario: Prévia com propostas e pendências
- **GIVEN** uma importação `PENDENTE` com 57 nomes reconhecidos, 3 novos propostos, 1 nome decidido como associação e 2 que precisam de decisão
- **WHEN** a prévia é exibida
- **THEN** o quadro mostra "Nenhuma alteração foi feita no cadastro de espaços.", "57 espaços já cadastrados foram reconhecidos.", "3 espaços novos serão cadastrados ao confirmar esta importação.", "1 nome será associado como outro nome de um espaço cadastrado." e "2 espaços precisam de decisão antes de concluir."
- **AND** nenhum texto diz que um espaço foi cadastrado

#### Scenario: Pendência de nome parecido
- **GIVEN** o nome `HV5` que precisa de decisão, parecido com o espaço `HV 5`, e um usuário com `ESPACO.CRIAR` e `ESPACO.EDITAR`
- **WHEN** a prévia é exibida
- **THEN** o item de `HV5` mostra a pergunta se é o mesmo espaço que `HV 5`, com "É o mesmo que HV 5" e "É um espaço novo"

#### Scenario: Pendência de nome só nas células
- **GIVEN** o nome `2/41` citado só nas células, sem parecido
- **WHEN** a prévia é exibida
- **THEN** o item de `2/41` mostra "Só nas aulas", "É o mesmo que…", "É um espaço novo" e a orientação de corrigir a planilha

#### Scenario: Importação com erro da planilha
- **GIVEN** uma importação `COM_ERROS` que também tem o nome `Zoo I` citado só nas células
- **WHEN** a prévia é exibida
- **THEN** o quadro mostra `Zoo I` com a orientação de decidir depois de corrigir a planilha, sem nenhum controle de decisão

#### Scenario: Conclusão
- **GIVEN** uma importação `VALIDADA` que cadastra 4 espaços e associa 2 outros nomes
- **WHEN** ela é confirmada
- **THEN** a mensagem de conclusão informa 4 espaços cadastrados e 2 outros nomes associados, sem citar reativação
- **AND** o quadro da importação concluída lista os 4 espaços cadastrados por ela

### Requirement: Atualização automática da prévia após as decisões
Depois de gravar ou desfazer uma decisão, o sistema DEVE (MUST) recalcular o quadro de espaços pela classificação, sem executar as linhas, e mostrá-lo atualizado na mesma resposta, com e sem JavaScript. Quando, depois da decisão, nenhum nome precisar de decisão, ou quando a importação estava `VALIDADA`, a mesma requisição DEVE (MUST) atualizar a prévia completa, conforme a spec `importacao-planilhas`, e a importação DEVE (MUST) ficar `VALIDADA`, "Pronta para confirmar", ou `PENDENTE`, quando surgir nova pendência, ou `COM_ERROS`, conforme o novo plano. O fluxo normal NÃO DEVE (MUST NOT) ter um controle "Conferir de novo". Quando a atualização da prévia falhar por erro inesperado, as decisões gravadas DEVEM (MUST) ser mantidas, a importação DEVE (MUST) continuar como estava, e o quadro DEVE (MUST) mostrar "Não foi possível atualizar a prévia." com o controle "Tentar novamente", que refaz a atualização; esse controle DEVE (MUST) aparecer somente numa importação `PENDENTE` cuja classificação não tem mais nenhum nome que precise de decisão.

#### Scenario: Última decisão deixa a importação pronta
- **GIVEN** uma importação `PENDENTE` em que só `HV5` precisa de decisão
- **WHEN** um usuário com `ESPACO.EDITAR` escolhe "É o mesmo que HV 5"
- **THEN** na mesma resposta a prévia é refeita, a importação fica `VALIDADA` e o quadro mostra "Pronta para confirmar."

#### Scenario: Decisão intermediária não refaz a prévia
- **GIVEN** uma importação `PENDENTE` com 3 nomes que precisam de decisão
- **WHEN** um deles é decidido
- **THEN** o quadro mostra 2 nomes que precisam de decisão, as linhas não são executadas e a importação continua `PENDENTE`

#### Scenario: Falha ao atualizar a prévia
- **GIVEN** uma importação `PENDENTE` com uma única pendência
- **WHEN** ela é decidida e a atualização da prévia é interrompida por erro inesperado
- **THEN** a decisão continua gravada, a importação continua `PENDENTE` e o quadro mostra "Não foi possível atualizar a prévia." com "Tentar novamente"
- **WHEN** "Tentar novamente" é acionado e a atualização termina
- **THEN** a importação fica `VALIDADA`
