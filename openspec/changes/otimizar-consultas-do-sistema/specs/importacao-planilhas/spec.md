## MODIFIED Requirements

### Requirement: Contrato das importações específicas
Cada importação específica DEVE (MUST) declarar o tipo, a fonte do arquivo, as colunas, a coluna identificadora com a sua normalização, os registros a travar, a execução de uma linha, as verificações do arquivo e os rótulos das ações, dos campos, dos avisos, das pendências e dos erros. Ela PODE (MAY) declarar os limites de tamanho e de quantidade de linhas, PODE (MAY) declarar campos próprios do envio, além do arquivo, PODE (MAY) declarar metadados próprios para o registro de auditoria das suas importações, PODE (MAY) declarar que não oferece modelo para baixar e PODE (MAY) declarar uma verificação própria da confirmação, que recebe a importação e o executor e recusa a confirmação com mensagem. A execução DEVE (MUST) receber a importação em curso quando ela já existe, na atualização da prévia e na confirmação, e nenhuma na primeira prévia, para que a importação específica possa ler os dados que guarda junto da importação. Ela PODE (MAY) declarar uma etapa final, executada uma vez depois de todas as linhas e antes das verificações do arquivo, na mesma transação e com a mesma importação em curso, que só considera o que as linhas mantidas fizeram: a prévia DEVE (MUST) desfazê-la junto com as linhas, e a confirmação DEVE (MUST) gravá-la junto com elas. A execução de uma linha DEVE (MUST) aplicar as operações reais do domínio e devolver o plano da linha, transformando as recusas das regras de negócio em erros do plano e os pontos que dependem de decisão de usuário em pendências do plano. A regra de negócio DEVE (MUST) continuar nas operações do model, e a importação específica NÃO DEVE (MUST NOT) repeti-la. Uma importação específica NÃO DEVE (MUST NOT) produzir efeitos fora da transação do banco, como envio de e-mail, gravação de arquivo, uso de cache ou chamada externa. Guardar em memória, durante uma execução, os registros que ela já leu ou criou não é efeito externo, desde que essa memória seja descartada no fim da execução e que um registro criado por uma linha desfeita deixe de valer para as linhas seguintes. O que deve acontecer depois da confirmação DEVE (MUST) ser registrado no outbox. O motor NÃO DEVE (MUST NOT) interpretar o conteúdo do plano, resolver referências entre objetos nem conhecer as regras de uma importação específica.

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

#### Scenario: Etapa final desfeita na prévia
- **GIVEN** uma importação específica cuja etapa final grava registros a partir das linhas mantidas
- **WHEN** a prévia é gerada
- **THEN** a etapa final roda depois da última linha e é desfeita junto com as linhas, sem deixar registro

#### Scenario: Etapa final ignora a linha desfeita
- **GIVEN** uma importação em que a linha 7 é recusada com erro
- **WHEN** a confirmação executa a etapa final
- **THEN** a etapa final não considera o que a linha 7 tentou fazer

#### Scenario: Registro de uma linha desfeita não é reaproveitado
- **GIVEN** uma importação em que a linha 5 cria uma disciplina e depois é recusada
- **AND** que a linha 6 cita a mesma disciplina
- **WHEN** a prévia é gerada
- **THEN** a linha 6 cria a disciplina de novo, como se a linha 5 não tivesse existido
