## MODIFIED Requirements

### Requirement: Prévia por executar e desfazer
A prévia DEVE (MUST) executar o mesmo fluxo da confirmação, com as operações reais do domínio, numa transação cujas alterações de domínio sofrem rollback. A prévia NÃO DEVE (MUST NOT) deixar nenhuma alteração de domínio nem nenhum registro no outbox. Cada linha DEVE (MUST) ser executada de forma que a recusa de uma linha, inclusive por erro do banco, não impeça a execução das seguintes, e a prévia DEVE (MUST) apresentar os erros e as pendências de todas as linhas de uma vez. Depois de todas as linhas, DEVEM (MUST) ser executadas as verificações do arquivo declaradas pela importação específica. A prévia DEVE (MUST) gravar a importação e o plano de cada linha, com a situação `COM_ERROS` quando há algum erro de linha ou de arquivo, `PENDENTE` quando não há erro e há alguma pendência, e `VALIDADA` quando não há erro nem pendência.

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

#### Scenario: Pendência sem erro
- **GIVEN** um arquivo sem erros em que a linha 5 tem uma pendência
- **WHEN** a prévia é gerada
- **THEN** a importação fica `PENDENTE` e a linha 5 mostra a pendência

#### Scenario: Erro prevalece sobre pendência
- **GIVEN** um arquivo em que a linha 5 tem uma pendência e a linha 9 tem um erro
- **WHEN** a prévia é gerada
- **THEN** a importação fica `COM_ERROS`

### Requirement: Plano da importação
O plano de cada linha DEVE (MUST) conter a ação (`create`, `update`, `unchanged`, ou nenhuma quando a linha não pôde ser identificada ou não resulta em registro), o alvo (a chave do registro existente nas ações `update` e `unchanged`), as mudanças (só os campos alterados, com o valor anterior e o novo, nulo como anterior em `create`), os avisos (lista de códigos), as pendências (lista de código e chave, em que a chave é o valor canônico que a pendência agrupa) e os erros (lista de coluna ou nenhuma, código e mensagem). Uma pendência é um ponto que precisa de uma decisão de usuário prevista pela importação específica, e não um erro do arquivo. Uma linha com pendência NÃO DEVE (MUST NOT) ter as suas operações de domínio aplicadas. O plano da importação DEVE (MUST) conter também os erros do arquivo, com código e mensagem. Os valores do plano DEVEM (MUST) ser canônicos, como códigos e valores normalizados, e nunca rótulos exibidos. O plano DEVE (MUST) ser determinístico e serializável em JSON. O texto exibido nas telas DEVE (MUST) ser gerado a partir do plano. Dois planos DEVEM (MUST) ser considerados idênticos somente quando forem iguais, em todas as linhas, a ação, o alvo, as mudanças, os avisos, as pendências e os pares de coluna e código dos erros, e, no arquivo, os códigos dos erros. As mensagens, os valores lidos e o registro criado NÃO DEVEM (MUST NOT) entrar na comparação.

Uma linha cujo registro existente foi criado por uma linha anterior da mesma execução NÃO DEVE (MUST NOT) ter alvo, porque a chave gerada na prévia desaparece no rollback e a da confirmação é outra, e o plano divergiria sempre. A ação dessa linha DEVE (MUST) continuar sendo registrada, e a decisão DEVE (MUST) ser a mesma na prévia e na confirmação. Uma linha cujo registro existia antes da importação DEVE (MUST) continuar com o alvo. O mesmo vale para um registro criado pela execução antes das linhas, na etapa de travamento declarada pela importação específica.

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

#### Scenario: Pendência entra na comparação
- **GIVEN** uma importação `VALIDADA` sem pendência
- **WHEN** os dados mudam de forma que uma linha passa a ter uma pendência e a importação é confirmada
- **THEN** o plano é considerado diferente e nada é aplicado

### Requirement: Confirmação condicionada ao plano idêntico
A confirmação DEVE (MUST) ser aceita somente para uma importação com a situação `VALIDADA`. Ela DEVE (MUST) travar a importação e aplicar a verificação própria da confirmação declarada pela importação específica, quando houver. Uma recusa dessa verificação DEVE (MUST) mostrar a mensagem da recusa e NÃO DEVE (MUST NOT) alterar a importação nem nenhum dado. Aceita a verificação, a confirmação DEVE (MUST) travar os registros que a importação específica declara, reexecutar todas as linhas a partir dos valores lidos gravados, com o executor da confirmação e com a importação em curso, e comparar o plano obtido com o plano gravado, tudo numa única transação. Quando os planos forem idênticos, as alterações de domínio, os registros no outbox e a situação `CONCLUIDA` DEVEM (MUST) ser efetivados juntos, e quem confirmou e quando DEVEM (MUST) ser gravados. Quando os planos forem diferentes, nenhuma alteração de domínio nem registro no outbox DEVE (MUST) ser efetivado. Nesse caso, o novo plano DEVE (MUST) substituir o anterior, a quantidade de prévias refeitas DEVE (MUST) aumentar em um, a situação DEVE (MUST) ficar `VALIDADA`, `PENDENTE` ou `COM_ERROS` conforme o novo plano, e o executor DEVE (MUST) ver a mensagem "Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo." A falha de uma operação durante a confirmação NÃO DEVE (MUST NOT) deixar nenhuma linha aplicada.

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

#### Scenario: Novo plano com pendência
- **GIVEN** uma importação `VALIDADA` cujo novo plano, por mudança dos dados, tem uma pendência
- **WHEN** a importação é confirmada
- **THEN** nada é aplicado e a importação fica `PENDENTE`

#### Scenario: Verificação própria recusa a confirmação
- **GIVEN** uma importação específica cuja verificação da confirmação recusa o executor com uma mensagem
- **WHEN** ele confirma uma importação `VALIDADA` dela
- **THEN** a mensagem é exibida, nenhuma linha é reexecutada, a importação continua `VALIDADA` e a quantidade de prévias refeitas não muda

#### Scenario: Falha no meio da aplicação
- **GIVEN** uma importação `VALIDADA` com dez linhas
- **WHEN** uma operação falha na confirmação depois de executadas cinco linhas
- **THEN** nenhuma das linhas fica aplicada

### Requirement: Descarte da importação
Uma importação `VALIDADA` ou `PENDENTE` DEVE (MUST) poder ser descartada. O descarte DEVE (MUST) mudar a situação para `DESCARTADA` e gravar quem descartou e quando, sem alterar dados de domínio.

#### Scenario: Descarte de importação validada
- **GIVEN** uma importação `VALIDADA`
- **WHEN** ela é descartada
- **THEN** a situação passa a `DESCARTADA`, com quem descartou e quando, e nenhum dado de domínio muda

#### Scenario: Descarte de importação que precisa de decisão
- **GIVEN** uma importação `PENDENTE`
- **WHEN** ela é descartada
- **THEN** a situação passa a `DESCARTADA` e nenhum dado de domínio muda

### Requirement: Situações finais
As situações `COM_ERROS`, `CONCLUIDA` e `DESCARTADA` DEVEM (MUST) ser finais. As situações `VALIDADA` e `PENDENTE` NÃO DEVEM (MUST NOT) ser finais. Confirmar, descartar ou atualizar a prévia de uma importação numa situação final DEVE (MUST) ser recusado com mensagem, sem alterar dados. Confirmar uma importação `PENDENTE` DEVE (MUST) ser recusado com mensagem, sem alterar dados. Duas confirmações simultâneas da mesma importação NÃO DEVEM (MUST NOT) aplicá-la duas vezes. Uma importação `VALIDADA` ou `PENDENTE` NÃO DEVE (MUST NOT) expirar.

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

#### Scenario: Confirmação de importação que precisa de decisão
- **GIVEN** uma importação `PENDENTE`
- **WHEN** a confirmação é enviada por POST
- **THEN** a tentativa é recusada com mensagem e nenhum dado muda

#### Scenario: Descarte de importação concluída
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** alguém tenta descartá-la
- **THEN** a tentativa é recusada e a situação continua `CONCLUIDA`

### Requirement: Contrato das importações específicas
Cada importação específica DEVE (MUST) declarar o tipo, a fonte do arquivo, as colunas, a coluna identificadora com a sua normalização, os registros a travar, a execução de uma linha, as verificações do arquivo e os rótulos das ações, dos campos, dos avisos, das pendências e dos erros. Ela PODE (MAY) declarar os limites de tamanho e de quantidade de linhas, PODE (MAY) declarar campos próprios do envio, além do arquivo, PODE (MAY) declarar metadados próprios para o registro de auditoria das suas importações, PODE (MAY) declarar que não oferece modelo para baixar e PODE (MAY) declarar uma verificação própria da confirmação, que recebe a importação e o executor e recusa a confirmação com mensagem. A execução DEVE (MUST) receber a importação em curso quando ela já existe, na atualização da prévia e na confirmação, e nenhuma na primeira prévia, para que a importação específica possa ler os dados que guarda junto da importação. A execução de uma linha DEVE (MUST) aplicar as operações reais do domínio e devolver o plano da linha, transformando as recusas das regras de negócio em erros do plano e os pontos que dependem de decisão de usuário em pendências do plano. A regra de negócio DEVE (MUST) continuar nas operações do model, e a importação específica NÃO DEVE (MUST NOT) repeti-la. Uma importação específica NÃO DEVE (MUST NOT) produzir efeitos fora da transação do banco, como envio de e-mail, gravação de arquivo, uso de cache ou chamada externa. O que deve acontecer depois da confirmação DEVE (MUST) ser registrado no outbox. O motor NÃO DEVE (MUST NOT) interpretar o conteúdo do plano, resolver referências entre objetos nem conhecer as regras de uma importação específica.

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

#### Scenario: Execução recebe a importação em curso
- **GIVEN** uma importação específica que guarda dados próprios junto da importação
- **WHEN** a importação é confirmada
- **THEN** a execução recebe a importação e lê esses dados, e na primeira prévia recebe nenhuma

## ADDED Requirements

### Requirement: Importação que precisa de decisão
A situação `PENDENTE` DEVE (MUST) existir para a importação sem erro de linha nem de arquivo que tem pelo menos uma pendência, e DEVE (MUST) ser exibida como "Precisa de decisão", no histórico e no detalhe, com ícone e texto. Uma importação `PENDENTE` NÃO DEVE (MUST NOT) oferecer o controle de confirmar, DEVE (MUST) poder ser descartada e NÃO DEVE (MUST NOT) poder ser excluída, conforme a exclusão de importações, que continua limitada às situações `DESCARTADA` e `COM_ERROS`. A situação `COM_ERROS` DEVE (MUST) continuar reservada aos erros de linha e de arquivo, e uma pendência NÃO DEVE (MUST NOT) ser tratada como erro. Cada pendência DEVE (MUST) ser exibida na linha, com o rótulo declarado pela importação específica. Uma importação específica que não declara pendências NÃO DEVE (MUST NOT) ter o comportamento alterado.

#### Scenario: Rótulo da situação
- **GIVEN** uma importação `PENDENTE`
- **WHEN** o histórico de importações é exibido
- **THEN** a importação aparece com "Precisa de decisão"

#### Scenario: Importação que precisa de decisão não é excluída
- **GIVEN** uma importação `PENDENTE` e um usuário com a permissão de exclusão
- **WHEN** a exclusão é enviada por POST
- **THEN** a exclusão é recusada com mensagem e a importação continua existindo

#### Scenario: Importação de usuários sem mudança
- **GIVEN** a importação de usuários, que não declara pendências
- **WHEN** uma prévia sem erros é gerada
- **THEN** a importação fica `VALIDADA`, como antes

### Requirement: Atualização da prévia
Uma importação `PENDENTE` ou `VALIDADA` DEVE (MUST) poder ter a prévia atualizada, por uma operação do motor acionada pela importação específica. A atualização DEVE (MUST) travar a importação, reexecutar todas as linhas a partir dos valores lidos gravados, com o executor que a aciona e com a importação em curso, desfazer todas as alterações de domínio e registros no outbox, substituir o plano pelo novo e definir a situação pelo novo plano: `COM_ERROS`, `PENDENTE` ou `VALIDADA`. A atualização NÃO DEVE (MUST NOT) aplicar nenhuma alteração de domínio, NÃO DEVE (MUST NOT) aumentar a quantidade de prévias refeitas, que continua contando só as divergências da confirmação, NÃO DEVE (MUST NOT) mudar quem enviou nem quando e NÃO DEVE (MUST NOT) gerar registro de auditoria, como a substituição do plano numa divergência. Um erro inesperado durante a atualização DEVE (MUST) desfazer tudo e deixar a importação como estava. A atualização de uma importação numa situação final DEVE (MUST) ser recusada com mensagem, sem alterar dados.

#### Scenario: Atualização deixa a importação pronta
- **GIVEN** uma importação `PENDENTE` cujo motivo da pendência deixou de existir
- **WHEN** a prévia é atualizada
- **THEN** o plano é substituído, a importação fica `VALIDADA` e nenhum dado de domínio muda

#### Scenario: Atualização sem contar divergência
- **GIVEN** uma importação `PENDENTE` com 0 prévias refeitas
- **WHEN** a prévia é atualizada duas vezes
- **THEN** a importação continua com 0 prévias refeitas

#### Scenario: Erro inesperado na atualização
- **GIVEN** uma importação `PENDENTE`
- **WHEN** um erro inesperado interrompe a atualização da prévia
- **THEN** o plano, a situação e os dados de domínio continuam como estavam

#### Scenario: Atualização de importação concluída
- **GIVEN** uma importação `CONCLUIDA`
- **WHEN** a atualização da prévia é acionada
- **THEN** a tentativa é recusada com mensagem e nada muda
