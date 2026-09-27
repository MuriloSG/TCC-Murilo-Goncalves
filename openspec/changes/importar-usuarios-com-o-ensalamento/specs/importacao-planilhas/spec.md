## MODIFIED Requirements

### Requirement: Leitura de planilha em grade
A fonte de planilha em grade DEVE (MUST) ler um arquivo XLSX e entregar ao motor uma linha por registro que a importação específica extrair das células das abas que ela declarar, com os valores como texto, exatamente como estão na planilha, identificados pelos rótulos das colunas lógicas declaradas. Uma célula PODE (MAY) produzir mais de uma linha, e cada linha DEVE (MUST) ter o seu plano, de modo que o erro de uma não impeça as demais linhas da mesma célula. Ela NÃO DEVE (MUST NOT) recalcular fórmulas e NÃO DEVE (MUST NOT) alterar o arquivo enviado.

A numeração das linhas DEVE (MUST) ser sequencial, na ordem de leitura, porque a linha física da planilha não identifica um registro. Cada linha DEVE (MUST) registrar a aba e a célula de origem entre os seus valores, e a coluna identificadora DEVE (MUST) ser a que traz essa origem. Quando uma célula produz mais de uma linha, a origem DEVE (MUST) distinguir cada uma por um ordinal, de modo a continuar única. Uma aba presente na planilha e não declarada pela importação NÃO DEVE (MUST NOT) recusar o arquivo e NÃO DEVE (MUST NOT) gerar linha, e uma coluna a mais numa aba declarada NÃO DEVE (MUST NOT) recusar o arquivo. A conferência de cabeçalho da fonte de CSV NÃO DEVE (MUST NOT) ser aplicada a esta fonte.

A importação PODE (MAY) declarar abas opcionais, além das obrigatórias. Uma aba opcional ausente NÃO DEVE (MUST NOT) recusar o arquivo nem gerar erro, e a importação específica DEVE (MUST) seguir sem as linhas dela; presente, ela DEVE (MUST) ser lida como as demais abas declaradas. O texto de ajuda do envio DEVE (MUST) citar a aba opcional como opcional.

O arquivo DEVE (MUST) ser recusado inteiro, sem criar importação, quando não puder ser aberto como XLSX, quando faltar uma aba obrigatória declarada pela importação, ou quando a estrutura da grade descrita pela importação não for encontrada. A recusa DEVE (MUST) informar o que falta e aparecer como erro do formulário de envio. Problemas do conteúdo de uma célula DEVEM (MUST) virar erro da linha correspondente, e o arquivo DEVE (MUST) seguir para a prévia.

#### Scenario: Arquivo que não é planilha
- **WHEN** um arquivo que não pode ser aberto como XLSX é enviado
- **THEN** o envio é recusado e nenhuma importação é criada

#### Scenario: Aba declarada ausente
- **GIVEN** uma importação que declara duas abas
- **WHEN** é enviada uma planilha sem uma delas
- **THEN** o envio é recusado informando a aba que falta, e nenhuma importação é criada

#### Scenario: Aba a mais ignorada
- **GIVEN** uma planilha com abas calculadas além das declaradas
- **WHEN** ela é enviada
- **THEN** o arquivo é aceito e nenhuma linha vem das abas não declaradas

#### Scenario: Valores como texto
- **GIVEN** uma célula com quebra de linha e espaços nas bordas
- **WHEN** a prévia é gerada
- **THEN** a linha registra o valor lido exatamente como está na planilha

#### Scenario: Numeração e origem das linhas
- **WHEN** a prévia de uma planilha em grade é gerada
- **THEN** as linhas são numeradas em sequência na ordem de leitura, e cada uma registra a aba e a célula de origem

#### Scenario: Célula que produz mais de uma linha
- **GIVEN** uma importação cuja leitura extrai dois registros de uma mesma célula
- **WHEN** a prévia é gerada
- **THEN** existem duas linhas, cada uma com o seu plano, e a origem de cada uma distingue a célula por um ordinal
- **AND** nenhuma das duas recebe erro de identificador repetido

#### Scenario: Erro de uma linha não esconde as outras da mesma célula
- **GIVEN** uma célula que produz três linhas, e a segunda é recusada
- **WHEN** a prévia é gerada
- **THEN** a segunda linha tem o erro, e a primeira e a terceira têm o seu plano

#### Scenario: Fórmula não recalculada
- **GIVEN** uma aba declarada cuja célula é uma fórmula
- **WHEN** a prévia é gerada
- **THEN** o motor não recalcula a fórmula

#### Scenario: Aba opcional ausente
- **GIVEN** uma importação que declara uma aba opcional
- **WHEN** é enviada uma planilha sem ela
- **THEN** o arquivo é aceito, sem erro, e nenhuma linha vem dessa aba

#### Scenario: Aba opcional presente
- **GIVEN** uma importação que declara uma aba opcional
- **WHEN** é enviada uma planilha com ela
- **THEN** as linhas dessa aba entram na importação como as das demais abas declaradas
