## MODIFIED Requirements

### Requirement: Leitura do arquivo
O motor DEVE (MUST) ler o arquivo enviado pela fonte declarada pela importação específica, e DEVE (MUST) oferecer a fonte de CSV e a fonte de planilha em grade. Uma importação que não declara fonte DEVE (MUST) usar a de CSV.

Na fonte de CSV, o motor DEVE (MUST) aceitar somente arquivos codificados em UTF-8, com ou sem BOM, e o BOM NÃO DEVE (MUST NOT) fazer parte do primeiro cabeçalho. O separador DEVE (MUST) ser `;`. DEVE (MUST) recusar um arquivo que não esteja em UTF-8, com a instrução de salvá-lo como "CSV UTF-8", e um arquivo sem linhas de dados. Quando o cabeçalho, dividido por vírgula, seria reconhecido, a recusa DEVE (MUST) informar que o separador deve ser `;`.

Em qualquer fonte, o motor DEVE (MUST) recusar, antes de processar qualquer linha, um arquivo acima do tamanho máximo ou com mais linhas de dados que o máximo. Os dois limites DEVEM (MUST) vir da configuração e PODEM (MAY) ser substituídos pela importação específica, que DEVE (MUST) declará-los quando os seus arquivos legítimos passarem dos limites da configuração. Toda recusa da leitura DEVE (MUST) aparecer como erro do formulário de envio, sem criar importação.

#### Scenario: Arquivo com BOM
- **GIVEN** um arquivo em UTF-8 com BOM e o cabeçalho esperado
- **WHEN** ele é enviado
- **THEN** o cabeçalho é reconhecido e a prévia é gerada

#### Scenario: Arquivo fora de UTF-8
- **GIVEN** um arquivo salvo em Windows-1252 com a palavra "João"
- **WHEN** ele é enviado
- **THEN** o envio é recusado com a instrução de salvar o arquivo como "CSV UTF-8" e nenhuma importação é criada

#### Scenario: Arquivo acima do limite de linhas
- **GIVEN** um limite de linhas configurado
- **WHEN** é enviado um arquivo com mais linhas de dados que o limite
- **THEN** o envio é recusado informando a quantidade de linhas e o limite, e nenhuma linha é processada

#### Scenario: Limite declarado pela importação
- **GIVEN** uma importação que declara um limite de linhas maior que o da configuração
- **WHEN** é enviado um arquivo com mais linhas que o da configuração e menos que o declarado
- **THEN** o arquivo é lido e a prévia é gerada

#### Scenario: Arquivo acima do tamanho máximo
- **GIVEN** um tamanho máximo configurado
- **WHEN** é enviado um arquivo maior que ele
- **THEN** o envio é recusado e nenhuma importação é criada

#### Scenario: Arquivo só com cabeçalho
- **WHEN** é enviado um arquivo com o cabeçalho e nenhuma linha de dados
- **THEN** o envio é recusado com a mensagem "O arquivo não tem linhas de dados."

#### Scenario: Separador vírgula
- **GIVEN** um arquivo com o cabeçalho esperado separado por vírgulas
- **WHEN** ele é enviado
- **THEN** o envio é recusado informando que o separador deve ser ";"

### Requirement: Contrato das importações específicas
Cada importação específica DEVE (MUST) declarar o tipo, a fonte do arquivo, as colunas, a coluna identificadora com a sua normalização, os registros a travar, a execução de uma linha, as verificações do arquivo e os rótulos das ações, dos campos, dos avisos e dos erros. Ela PODE (MAY) declarar os limites de tamanho e de quantidade de linhas, PODE (MAY) declarar campos próprios do envio, além do arquivo, PODE (MAY) declarar metadados próprios para o registro de auditoria das suas importações e PODE (MAY) declarar que não oferece modelo para baixar. A execução de uma linha DEVE (MUST) aplicar as operações reais do domínio e devolver o plano da linha, transformando as recusas das regras de negócio em erros do plano. A regra de negócio DEVE (MUST) continuar nas operações do model, e a importação específica NÃO DEVE (MUST NOT) repeti-la. Uma importação específica NÃO DEVE (MUST NOT) produzir efeitos fora da transação do banco, como envio de e-mail, gravação de arquivo, uso de cache ou chamada externa. O que deve acontecer depois da confirmação DEVE (MUST) ser registrado no outbox. O motor NÃO DEVE (MUST NOT) interpretar o conteúdo do plano, resolver referências entre objetos nem conhecer as regras de uma importação específica.

O valor de um campo próprio do envio DEVE (MUST) ser gravado nos valores de cada linha, como uma coluna lógica, porque a confirmação reexecuta as linhas a partir dos valores gravados e NÃO DEVE (MUST NOT) receber esse valor de novo de quem confirma. Um campo próprio obrigatório vazio ou inválido DEVE (MUST) ser erro do formulário de envio, sem criar importação.

Os metadados próprios DEVEM (MUST) ser acrescentados às informações adicionais dos registros de auditoria da importação, sem substituir os que o motor já grava, e DEVEM (MUST) ser valores canônicos, e não texto exibido.

#### Scenario: Recusa do model vira erro da linha
- **GIVEN** uma importação específica cuja operação do model recusa a linha 5 com uma mensagem
- **WHEN** a prévia é gerada
- **THEN** a linha 5 recebe o erro com a coluna, o código e a mensagem da recusa

#### Scenario: Prévia sem efeitos externos
- **GIVEN** uma importação que cadastra usuários
- **WHEN** a prévia é gerada
- **THEN** nenhum e-mail é enviado e nenhum registro fica no outbox

#### Scenario: Campo próprio do envio gravado nas linhas
- **GIVEN** uma importação específica que declara um campo próprio no envio
- **WHEN** a prévia é gerada
- **THEN** cada linha registra o valor desse campo entre os seus valores

#### Scenario: Confirmação usa o campo próprio gravado
- **GIVEN** uma importação `VALIDADA` gerada com um campo próprio do envio
- **WHEN** ela é confirmada
- **THEN** a reexecução usa o valor gravado nas linhas, e quem confirma não informa esse valor de novo

#### Scenario: Campo próprio obrigatório vazio
- **GIVEN** uma importação específica que declara um campo próprio obrigatório
- **WHEN** o envio é feito sem esse campo
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Metadados próprios na auditoria
- **GIVEN** uma importação específica que declara metadados próprios
- **WHEN** uma importação dela é confirmada
- **THEN** o registro de auditoria da confirmação contém esses metadados junto dos que o motor já grava

### Requirement: Plano da importação
O plano de cada linha DEVE (MUST) conter a ação (`create`, `update`, `unchanged`, ou nenhuma quando a linha não pôde ser identificada), o alvo (a chave do registro existente nas ações `update` e `unchanged`), as mudanças (só os campos alterados, com o valor anterior e o novo, nulo como anterior em `create`), os avisos (lista de códigos) e os erros (lista de coluna ou nenhuma, código e mensagem). O plano da importação DEVE (MUST) conter também os erros do arquivo, com código e mensagem. Os valores do plano DEVEM (MUST) ser canônicos, como códigos e valores normalizados, e nunca rótulos exibidos. O plano DEVE (MUST) ser determinístico e serializável em JSON. O texto exibido nas telas DEVE (MUST) ser gerado a partir do plano. Dois planos DEVEM (MUST) ser considerados idênticos somente quando forem iguais, em todas as linhas, a ação, o alvo, as mudanças, os avisos e os pares de coluna e código dos erros, e, no arquivo, os códigos dos erros. As mensagens, os valores lidos e o registro criado NÃO DEVEM (MUST NOT) entrar na comparação.

Uma linha cujo registro existente foi criado por uma linha anterior da mesma execução NÃO DEVE (MUST NOT) ter alvo, porque a chave gerada na prévia desaparece no rollback e a da confirmação é outra, e o plano divergiria sempre. A ação dessa linha DEVE (MUST) continuar sendo registrada, e a decisão DEVE (MUST) ser a mesma na prévia e na confirmação. Uma linha cujo registro existia antes da importação DEVE (MUST) continuar com o alvo.

#### Scenario: Mudança com valor anterior e novo
- **GIVEN** uma linha que troca o perfil de um usuário de `DOCENTE` para `ADMINISTRADOR`
- **WHEN** a prévia é gerada
- **THEN** o plano da linha tem a ação `update`, o alvo com a chave do usuário e a mudança `role` de `DOCENTE` para `ADMINISTRADOR`

#### Scenario: Rótulo alterado sem mudar o plano
- **GIVEN** uma importação `VALIDADA` cujo plano cita o perfil pelo código `DOCENTE`
- **WHEN** o nome do perfil é alterado de "Docente" para "Docentes" e a importação é confirmada
- **THEN** o plano é considerado idêntico

#### Scenario: Duas linhas do arquivo para o mesmo registro novo
- **GIVEN** um arquivo cujas linhas 2 e 3 descrevem o mesmo registro, que ainda não existe
- **WHEN** a prévia é gerada
- **THEN** a linha 2 tem a ação `create` e a linha 3 tem a ação `unchanged` sem alvo
- **WHEN** a importação é confirmada
- **THEN** o plano é considerado idêntico, existe um único registro e a importação fica `CONCLUIDA`

### Requirement: Dados registrados da importação
A importação DEVE (MUST) registrar o tipo, a situação, o nome do arquivo enviado, quem enviou e quando, quem confirmou ou descartou e quando, a quantidade de prévias refeitas por divergência e os erros do arquivo. Cada linha DEVE (MUST) registrar o número, os valores lidos exatamente como vieram no arquivo, identificados pelo rótulo da coluna, e o plano da linha. Os valores de uma linha DEVEM (MUST) conter também os valores dos campos próprios do envio, identificados pelo rótulo da sua coluna lógica, ainda que não venham do arquivo. Nas linhas com a ação `create`, a chave do registro criado DEVE (MUST) ser gravada somente na conclusão. Os totais por ação NÃO DEVEM (MUST NOT) ser gravados e DEVEM (MUST) ser contados a partir das linhas. NÃO DEVEM (MUST NOT) ser gravados o arquivo, as chaves geradas na prévia, os planos anteriores a uma divergência, o texto exibido nem as permissões do executor. O histórico DEVE (MUST) ser mantido por tempo indeterminado.

#### Scenario: Registro criado só na conclusão
- **GIVEN** uma importação que cadastra `carla@ifnmg.edu.br`
- **WHEN** a prévia é gerada
- **THEN** a linha não tem registro criado
- **WHEN** a importação é confirmada
- **THEN** a linha passa a ter a chave do usuário criado

#### Scenario: Valores lidos preservados
- **GIVEN** uma linha com ` Ana@IFNMG.edu.br ` na coluna `E-mail`
- **WHEN** a prévia é gerada
- **THEN** a linha registra o valor ` Ana@IFNMG.edu.br `, com os espaços e as maiúsculas

#### Scenario: Valor do envio entre os valores da linha
- **GIVEN** uma importação cujo envio tem um campo próprio com o valor `2026/1`
- **WHEN** a prévia é gerada
- **THEN** cada linha registra `2026/1` na coluna lógica desse campo

### Requirement: Telas da importação
As views base do motor DEVEM (MUST) oferecer o envio do arquivo, a prévia, a confirmação, o descarte, o histórico e o detalhe de uma importação, e DEVEM (MUST) oferecer o download do modelo quando a importação específica tiver modelo. O envio DEVE (MUST) abrir em modal, conforme o padrão de ações de gestão, e o campo de arquivo e a sua ajuda DEVEM (MUST) descrever o formato aceito pela fonte declarada. O envio DEVE (MUST) apresentar os campos próprios declarados pela importação específica, além do arquivo. A prévia e o detalhe DEVEM (MUST) ser páginas completas, com os totais por ação, os erros do arquivo e, em cada linha, o número, a ação, as mudanças, os avisos e os erros com a coluna. Numa linha de atualização as mudanças DEVEM (MUST) mostrar o valor anterior e o novo, e numa linha de cadastro DEVEM (MUST) mostrar o valor que será gravado. Os valores dos campos próprios do envio DEVEM (MUST) aparecer uma vez no resumo da importação, e não repetidos em cada linha.

A importação específica PODE (MAY) declarar recortes das linhas, e o detalhe DEVE (MUST) oferecer cada recorte declarado que tenha linhas, com a quantidade delas, ao lado do recorte das linhas com erro. Um recorte PODE (MAY) limitar as colunas exibidas enquanto está escolhido, para que a tabela mostre só o que importa nele. Um recorte que a importação não declara DEVE (MUST) responder 404. O controle de confirmar DEVE (MUST) aparecer somente numa importação `VALIDADA`, e confirmar e descartar DEVEM (MUST) ser feitos por POST com CSRF. O histórico DEVE (MUST) listar as importações da mais recente para a mais antiga, com situação, arquivo, quem enviou e quando.

Quando houver modelo, ele DEVE (MUST) ser um CSV em UTF-8 com BOM, separado por `;`, contendo só o cabeçalho com as colunas declaradas. Numa importação sem modelo, a rota do modelo NÃO DEVE (MUST NOT) existir e as telas NÃO DEVEM (MUST NOT) oferecer o download.

#### Scenario: Confirmar ausente numa importação com erros
- **GIVEN** uma importação `COM_ERROS`
- **WHEN** a prévia dela é exibida
- **THEN** não há controle para confirmar e os erros aparecem com a linha e a coluna

#### Scenario: Confirmação sem CSRF
- **WHEN** uma confirmação é enviada por POST sem o token CSRF
- **THEN** a requisição é recusada com 403 e a importação não muda

#### Scenario: Modelo para baixar
- **WHEN** o modelo de uma importação que tem modelo é baixado
- **THEN** o arquivo está em UTF-8 com BOM, usa ";" e contém só a linha de cabeçalho

#### Scenario: Importação sem modelo
- **GIVEN** uma importação específica que declara não ter modelo
- **WHEN** as telas dela são exibidas
- **THEN** não há link para baixar o modelo, e a rota do modelo não existe

#### Scenario: Campo próprio no envio
- **GIVEN** uma importação específica que declara um campo próprio no envio
- **WHEN** o modal de envio é exibido
- **THEN** o campo aparece ao lado do campo de arquivo, com o rótulo e a ajuda dele

#### Scenario: Valor do envio no resumo
- **GIVEN** uma importação gerada com um campo próprio do envio com o valor `2026/1`
- **WHEN** o detalhe é exibido
- **THEN** o resumo mostra esse valor uma vez, com o rótulo do campo

#### Scenario: Recorte das linhas
- **GIVEN** uma importação específica que declara um recorte das linhas
- **WHEN** o detalhe é exibido
- **THEN** o recorte aparece com a quantidade de linhas dele
- **WHEN** o recorte é escolhido
- **THEN** só as linhas dele são listadas, com as colunas que ele declara

#### Scenario: Recorte desconhecido
- **WHEN** o detalhe é acessado com um recorte que a importação não declara
- **THEN** a resposta é 404

#### Scenario: Valor gravado numa linha de cadastro
- **GIVEN** uma linha que cadastra um registro
- **WHEN** a prévia é exibida
- **THEN** a linha mostra o valor que será gravado, e não uma mudança com valor anterior

## ADDED Requirements

### Requirement: Leitura de planilha em grade
A fonte de planilha em grade DEVE (MUST) ler um arquivo XLSX e entregar ao motor uma linha por registro que a importação específica extrair das células das abas que ela declarar, com os valores como texto, exatamente como estão na planilha, identificados pelos rótulos das colunas lógicas declaradas. Uma célula PODE (MAY) produzir mais de uma linha, e cada linha DEVE (MUST) ter o seu plano, de modo que o erro de uma não impeça as demais linhas da mesma célula. Ela NÃO DEVE (MUST NOT) recalcular fórmulas e NÃO DEVE (MUST NOT) alterar o arquivo enviado.

A numeração das linhas DEVE (MUST) ser sequencial, na ordem de leitura, porque a linha física da planilha não identifica um registro. Cada linha DEVE (MUST) registrar a aba e a célula de origem entre os seus valores, e a coluna identificadora DEVE (MUST) ser a que traz essa origem. Quando uma célula produz mais de uma linha, a origem DEVE (MUST) distinguir cada uma por um ordinal, de modo a continuar única. Uma aba presente na planilha e não declarada pela importação NÃO DEVE (MUST NOT) recusar o arquivo e NÃO DEVE (MUST NOT) gerar linha, e uma coluna a mais numa aba declarada NÃO DEVE (MUST NOT) recusar o arquivo. A conferência de cabeçalho da fonte de CSV NÃO DEVE (MUST NOT) ser aplicada a esta fonte.

O arquivo DEVE (MUST) ser recusado inteiro, sem criar importação, quando não puder ser aberto como XLSX, quando faltar uma aba declarada pela importação, ou quando a estrutura da grade descrita pela importação não for encontrada. A recusa DEVE (MUST) informar o que falta e aparecer como erro do formulário de envio. Problemas do conteúdo de uma célula DEVEM (MUST) virar erro da linha correspondente, e o arquivo DEVE (MUST) seguir para a prévia.

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
