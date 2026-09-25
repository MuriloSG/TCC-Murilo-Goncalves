## ADDED Requirements

### Requirement: Abas do detalhe da importação
A importação específica DEVE (MUST) poder declarar abas para o detalhe de uma importação, cada uma com a sua rota e o seu rótulo. Com abas declaradas, cada aba DEVE (MUST) ter URL própria, mostrar a navegação entre as abas com a atual marcada, e repetir o mesmo cabeçalho do detalhe: título, controles de confirmar, descartar e enviar arquivo corrigido conforme a situação, alertas da situação, erros do arquivo e resumo. A importação que não declara abas DEVE (MUST) continuar com o detalhe sem navegação entre abas. Os redirecionamentos depois do envio, da confirmação e do descarte DEVEM (MUST) continuar levando à rota do detalhe.

#### Scenario: Importação sem abas
- **GIVEN** a importação de usuários, que não declara abas
- **WHEN** o detalhe de uma importação de usuários é aberto
- **THEN** a tela é a tabela de linhas, sem navegação entre abas

#### Scenario: Troca de aba
- **GIVEN** uma importação `VALIDADA` com as abas Grade e Conferência
- **WHEN** a aba Conferência é aberta
- **THEN** o controle de confirmar continua presente
- **AND** a aba Conferência aparece como atual

#### Scenario: Acesso às abas
- **WHEN** qualquer aba é aberta por um usuário autenticado sem a permissão da importação
- **THEN** a resposta é 403

### Requirement: Filtro pelo número da linha
A tabela de linhas da importação DEVE (MUST) aceitar um ou mais números de linha na URL e, com eles, mostrar só as linhas com esses números, combinados com o recorte escolhido, quando houver. Um número que não é inteiro DEVE (MUST) ser descartado sem erro. Com o filtro ativo, a tabela DEVE (MUST) oferecer o controle para voltar a todas as linhas.

#### Scenario: Duas linhas pedidas
- **WHEN** a tabela de linhas é aberta com `numero=12&numero=13`
- **THEN** só as linhas 12 e 13 são listadas

#### Scenario: Número inválido
- **WHEN** a tabela de linhas é aberta com `numero=abc`
- **THEN** todas as linhas são listadas, e a resposta é 200
