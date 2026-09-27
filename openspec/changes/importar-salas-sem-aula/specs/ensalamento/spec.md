## MODIFIED Requirements

### Requirement: Catálogo de espaços e de docentes da planilha
Os docentes DEVEM (MUST) ser criados ou reconhecidos a partir da lista de docentes da aba de validação de dados, e NÃO DEVEM (MUST NOT) ser criados a partir do texto das células de atividade. Todos os valores da lista de docentes DEVEM (MUST) virar registro, inclusive os que nenhuma atividade referencia.

A lista de salas da aba de validação de dados DEVE (MUST) ser a fonte dos nomes que a importação pode propor como espaço novo, conforme "Classificação dos espaços da importação". Todo nome da lista, usado ou não por uma aula, DEVE (MUST) passar pela classificação, e vira espaço quando não identifica nenhum espaço e é proposto como novo ou decidido como novo, somente na confirmação. O espaço cadastrado a partir de um nome sem aula DEVE (MUST) ficar ativo e sem alocação, para aparecer com a grade vazia nos calendários. Um nome da lista sem aula que identifica um espaço inativo NÃO DEVE (MUST NOT) ser nome encontrado: o espaço continua inativo e a linha dele fica sem ação, sem aviso e sem pendência.

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

#### Scenario: Sala da lista sem aula é cadastrada
- **GIVEN** a lista de salas com `Lab. Carnes`, que nenhuma aula usa e que não identifica nenhum espaço nem tem parecido
- **WHEN** a importação é confirmada
- **THEN** o espaço `Lab. Carnes` existe, ativo e sem alocação
- **AND** a linha dele tem a ação `create`

#### Scenario: Sala inativa da lista sem aula
- **GIVEN** o espaço inativo `Lab. Carnes` e a lista de salas com `Lab. Carnes`, que nenhuma aula usa
- **WHEN** a importação é confirmada
- **THEN** o espaço continua inativo, e a linha dele não tem ação, aviso nem pendência

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

