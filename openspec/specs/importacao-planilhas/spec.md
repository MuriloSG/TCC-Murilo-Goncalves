# importacao-planilhas Specification

## Purpose
TBD - created by archiving change importar-usuarios-por-planilha. Update Purpose after archive.
## Requirements
### Requirement: Importação como registro da prévia
Uma importação DEVE (MUST) ser o registro persistido de um arquivo que chegou à etapa de prévia. Ela DEVE (MUST) ter um tipo, gravado como código em português (por exemplo, `USUARIO`), e uma situação entre `VALIDADA`, `COM_ERROS`, `CONCLUIDA` e `DESCARTADA`, exibidas como "Validada", "Com erros", "Concluída" e "Descartada". Um arquivo recusado na leitura ou na conferência da estrutura NÃO DEVE (MUST NOT) criar importação. Cada envio que chega à prévia DEVE (MUST) criar uma importação nova, e o reenvio de um arquivo corrigido NÃO DEVE (MUST NOT) alterar importações anteriores. O arquivo enviado NÃO DEVE (MUST NOT) ser guardado depois da leitura. A situação DEVE (MUST) valer para a importação inteira, e as linhas NÃO DEVEM (MUST NOT) ter situação própria.

#### Scenario: Arquivo que chega à prévia
- **GIVEN** um arquivo com estrutura válida
- **WHEN** ele é enviado
- **THEN** uma importação é criada com a situação `VALIDADA` ou `COM_ERROS`

#### Scenario: Arquivo recusado antes da prévia
- **GIVEN** um arquivo com uma coluna desconhecida
- **WHEN** ele é enviado
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Reenvio após correção
- **GIVEN** uma importação com a situação `COM_ERROS`
- **WHEN** o arquivo corrigido é enviado
- **THEN** uma nova importação é criada e a anterior continua com a situação `COM_ERROS`

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

### Requirement: Conferência do cabeçalho
A primeira linha do arquivo DEVE (MUST) ser o cabeçalho. Cada cabeçalho DEVE (MUST) ser reconhecido pelo rótulo da coluna declarada pela importação específica, sem diferenciar maiúsculas de minúsculas nem letras acentuadas das não acentuadas e ignorando espaços nas bordas. A ordem das colunas NÃO DEVE (MUST NOT) importar. O motor DEVE (MUST) recusar o arquivo quando houver coluna desconhecida, coluna obrigatória ausente ou cabeçalho repetido, informando as colunas envolvidas e as colunas esperadas. Nesta versão, toda coluna declarada DEVE (MUST) ser obrigatória.

#### Scenario: Colunas em outra ordem e com outra grafia
- **GIVEN** uma importação que declara as colunas `E-mail`, `Nome` e `Perfil`
- **WHEN** é enviado um arquivo com o cabeçalho `perfil;NOME; e-mail `
- **THEN** as três colunas são reconhecidas

#### Scenario: Coluna desconhecida
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome;Perfl`
- **THEN** o envio é recusado com a mensagem "Coluna "Perfl" não reconhecida. Use as colunas do modelo: E-mail, Nome, Perfil."

#### Scenario: Coluna obrigatória ausente
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome`
- **THEN** o envio é recusado informando que a coluna `Perfil` está ausente

#### Scenario: Cabeçalho repetido
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome;Perfil;E-mail`
- **THEN** o envio é recusado informando que a coluna `E-mail` está repetida

### Requirement: Linhas do arquivo
Cada linha DEVE (MUST) ser identificada pelo número da linha física em que o registro começa no arquivo, com o cabeçalho sendo a linha 1. Linhas em que todas as células estão vazias DEVEM (MUST) ser ignoradas, sem alterar a numeração das demais. Células entre aspas com `;` ou quebra de linha DEVEM (MUST) ser aceitas conforme o formato CSV. Uma linha com mais células que o cabeçalho DEVE (MUST) receber um erro. Uma linha com menos células DEVE (MUST) ter as células faltantes tratadas como vazias. Uma célula obrigatória vazia ou só com espaços DEVE (MUST) gerar erro na linha e na coluna. Quando o mesmo valor da coluna identificadora, depois da normalização declarada pela importação específica, aparece em mais de uma linha, todas essas linhas DEVEM (MUST) receber um erro que cite as linhas repetidas. O motor DEVE (MUST) entregar à importação específica os valores das células como texto, sem converter tipos.

#### Scenario: Linhas vazias no meio e no fim
- **GIVEN** um arquivo com dados nas linhas 2, 3 e 5, a linha 4 vazia e duas linhas vazias no fim
- **WHEN** a prévia é gerada
- **THEN** são processadas as linhas 2, 3 e 5, com esses números

#### Scenario: Célula obrigatória só com espaços
- **GIVEN** a linha 4 com a coluna `Nome` preenchida só com espaços
- **WHEN** a prévia é gerada
- **THEN** a linha 4 recebe erro na coluna `Nome`

#### Scenario: Linha com células a mais
- **GIVEN** a linha 6 com quatro células num arquivo de três colunas
- **WHEN** a prévia é gerada
- **THEN** a linha 6 recebe erro informando que tem mais colunas que o cabeçalho

#### Scenario: Identificador repetido com grafias diferentes
- **GIVEN** a linha 3 com `ana@ifnmg.edu.br` e a linha 9 com ` ANA@ifnmg.edu.br`
- **WHEN** a prévia é gerada
- **THEN** as linhas 3 e 9 recebem o erro "E-mail repetido nas linhas 3 e 9."

### Requirement: Prévia por executar e desfazer
A prévia DEVE (MUST) executar o mesmo fluxo da confirmação, com as operações reais do domínio, numa transação cujas alterações de domínio sofrem rollback. A prévia NÃO DEVE (MUST NOT) deixar nenhuma alteração de domínio nem nenhum registro no outbox. Cada linha DEVE (MUST) ser executada de forma que a recusa de uma linha, inclusive por erro do banco, não impeça a execução das seguintes, e a prévia DEVE (MUST) apresentar os erros de todas as linhas de uma vez. Depois de todas as linhas, DEVEM (MUST) ser executadas as verificações do arquivo declaradas pela importação específica. A prévia DEVE (MUST) gravar a importação e o plano de cada linha, com a situação `VALIDADA` quando não há nenhum erro de linha nem de arquivo e `COM_ERROS` caso contrário.

#### Scenario: Prévia sem alterar dados
- **GIVEN** um arquivo que cadastra dois usuários
- **WHEN** a prévia é gerada
- **THEN** nenhum usuário é criado, nenhum registro é criado no outbox e a importação fica `VALIDADA` com duas linhas de cadastro

#### Scenario: Todos os erros de uma vez
- **GIVEN** um arquivo com erros nas linhas 3, 7 e 12
- **WHEN** a prévia é gerada
- **THEN** a importação fica `COM_ERROS` e as três linhas mostram os seus erros

#### Scenario: Erro de banco numa linha
- **GIVEN** um arquivo em que a linha 3 é recusada por uma restrição do banco
- **WHEN** a prévia é gerada
- **THEN** a linha 3 recebe o erro e as linhas seguintes são executadas e têm o seu plano

#### Scenario: Erro de verificação do arquivo
- **GIVEN** um arquivo cujas linhas são válidas, mas que falha numa verificação do arquivo
- **WHEN** a prévia é gerada
- **THEN** a importação fica `COM_ERROS`, com o erro registrado no arquivo e não numa linha

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

### Requirement: Confirmação condicionada ao plano idêntico
A confirmação DEVE (MUST) ser aceita somente para uma importação com a situação `VALIDADA`. Ela DEVE (MUST) travar a importação, travar os registros que a importação específica declara, reexecutar todas as linhas a partir dos valores lidos gravados, com o executor da confirmação, e comparar o plano obtido com o plano gravado, tudo numa única transação. Quando os planos forem idênticos, as alterações de domínio, os registros no outbox e a situação `CONCLUIDA` DEVEM (MUST) ser efetivados juntos, e quem confirmou e quando DEVEM (MUST) ser gravados. Quando os planos forem diferentes, nenhuma alteração de domínio nem registro no outbox DEVE (MUST) ser efetivado. Nesse caso, o novo plano DEVE (MUST) substituir o anterior, a quantidade de prévias refeitas DEVE (MUST) aumentar em um, a situação DEVE (MUST) ficar `VALIDADA` ou `COM_ERROS` conforme o novo plano, e o executor DEVE (MUST) ver a mensagem "Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo." A falha de uma operação durante a confirmação NÃO DEVE (MUST NOT) deixar nenhuma linha aplicada.

#### Scenario: Confirmação com plano idêntico
- **GIVEN** uma importação `VALIDADA` que cadastra dois usuários
- **WHEN** ela é confirmada sem mudança nos dados
- **THEN** os dois usuários são criados, a importação fica `CONCLUIDA` e registra quem confirmou e quando

#### Scenario: Dados alterados entre a prévia e a confirmação
- **GIVEN** uma importação `VALIDADA` cuja linha 2 troca o perfil de Ana de `DOCENTE` para `ADMINISTRADOR`
- **AND** que outro administrador fez essa troca pela tela depois da prévia
- **WHEN** a importação é confirmada
- **THEN** nada é aplicado, a linha 2 passa a `unchanged` no novo plano, a importação continua `VALIDADA` e a quantidade de prévias refeitas passa a 1

#### Scenario: Novo plano com erros
- **GIVEN** uma importação `VALIDADA` que cadastra `bruno@ifnmg.edu.br`
- **AND** que o perfil citado na linha foi excluído depois da prévia
- **WHEN** a importação é confirmada
- **THEN** nada é aplicado e a importação fica `COM_ERROS`

#### Scenario: Falha no meio da aplicação
- **GIVEN** uma importação `VALIDADA` com dez linhas
- **WHEN** uma operação falha na confirmação depois de executadas cinco linhas
- **THEN** nenhuma das linhas fica aplicada

### Requirement: Descarte da importação
Uma importação `VALIDADA` DEVE (MUST) poder ser descartada. O descarte DEVE (MUST) mudar a situação para `DESCARTADA` e gravar quem descartou e quando, sem alterar dados de domínio.

#### Scenario: Descarte de importação validada
- **GIVEN** uma importação `VALIDADA`
- **WHEN** ela é descartada
- **THEN** a situação passa a `DESCARTADA`, com quem descartou e quando, e nenhum dado de domínio muda

### Requirement: Situações finais
As situações `COM_ERROS`, `CONCLUIDA` e `DESCARTADA` DEVEM (MUST) ser finais. Confirmar ou descartar uma importação numa situação final DEVE (MUST) ser recusado com mensagem, sem alterar dados. Duas confirmações simultâneas da mesma importação NÃO DEVEM (MUST NOT) aplicá-la duas vezes. Uma importação `VALIDADA` NÃO DEVE (MUST NOT) expirar.

#### Scenario: Confirmação repetida
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** alguém tenta confirmá-la de novo
- **THEN** a tentativa é recusada e nenhum dado muda

#### Scenario: Confirmações simultâneas
- **GIVEN** uma importação `VALIDADA` que cadastra um usuário
- **WHEN** duas confirmações dela são enviadas ao mesmo tempo
- **THEN** exatamente uma é aplicada, o usuário é criado uma vez e a outra é recusada

#### Scenario: Confirmação de importação com erros
- **GIVEN** uma importação `COM_ERROS`
- **WHEN** alguém tenta confirmá-la
- **THEN** a tentativa é recusada e nenhum dado muda

#### Scenario: Descarte de importação concluída
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** alguém tenta descartá-la
- **THEN** a tentativa é recusada e a situação continua `CONCLUIDA`

### Requirement: Erros inesperados
Um erro que não seja uma recusa de regra, como a indisponibilidade do banco ou um defeito, DEVE (MUST) seguir o tratamento normal da aplicação, com rollback e registro no log. Na prévia, a importação NÃO DEVE (MUST NOT) ser criada. Na confirmação, a importação DEVE (MUST) continuar `VALIDADA` e poder ser confirmada de novo. NÃO DEVE (MUST NOT) existir situação de falha nesta versão.

#### Scenario: Erro inesperado na confirmação
- **GIVEN** uma importação `VALIDADA`
- **WHEN** um erro inesperado interrompe a confirmação
- **THEN** nenhum dado de domínio muda e a importação continua `VALIDADA`

#### Scenario: Erro inesperado na prévia
- **WHEN** um erro inesperado interrompe a prévia de um arquivo
- **THEN** nenhuma importação é criada

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

### Requirement: Motor desacoplado dos apps de domínio
O motor NÃO DEVE (MUST NOT) importar código de nenhum app de domínio nem manter um registro central das importações específicas. Cada app DEVE (MUST) definir a sua importação, as suas rotas e o seu histórico, usando o model e as views base do motor, e o histórico de cada app DEVE (MUST) listar só as importações do seu tipo. Acrescentar uma importação específica NÃO DEVE (MUST NOT) exigir alteração no motor, exceto para implementar uma capacidade ainda não implementada que ela use.

#### Scenario: Motor sem dependência de domínio
- **WHEN** os módulos do motor são inspecionados
- **THEN** nenhum deles importa módulos de `accounts` ou de outro app de domínio

#### Scenario: Histórico filtrado pelo tipo
- **GIVEN** importações de dois tipos diferentes
- **WHEN** o histórico de um app é acessado
- **THEN** só as importações do tipo desse app são listadas

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

### Requirement: Validação conjunta e exibição dos campos próprios do envio
Uma importação específica PODE (MAY) declarar uma validação que recebe os valores de todos os seus campos próprios do envio, já limpos, para regras que envolvem mais de um campo. O motor DEVE (MUST) chamá-la antes de ler o arquivo, e uma recusa DEVE (MUST) ser erro do formulário de envio, sem criar importação. A regra DEVE (MUST) continuar na operação do model, e o motor NÃO DEVE (MUST NOT) conhecê-la. Uma importação específica PODE (MAY) também declarar como exibir o valor de um campo próprio, e o resumo da importação DEVE (MUST) mostrar o valor exibido quando ele existir, mantendo o valor gravado nas linhas como dado. Uma importação que não declara nenhuma das duas DEVE (MUST) continuar funcionando como antes.

#### Scenario: Campos próprios recusados juntos
- **GIVEN** uma importação específica que declara dois campos próprios de data e a validação conjunta deles
- **WHEN** o envio tem a data final anterior à inicial
- **THEN** o formulário de envio mostra o erro da validação e nenhuma importação é criada

#### Scenario: Data exibida formatada
- **GIVEN** uma importação cujo campo próprio de data foi gravado nas linhas como `2026-08-03`
- **WHEN** o resumo da importação é exibido
- **THEN** o valor aparece como `03/08/2026`, e as linhas continuam com `2026-08-03`

#### Scenario: Importação sem os ganchos
- **WHEN** uma importação de usuários é enviada e exibida
- **THEN** o envio, a prévia e o resumo se comportam como antes

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

