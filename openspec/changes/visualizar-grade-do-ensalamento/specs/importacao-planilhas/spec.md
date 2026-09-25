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

### Requirement: Exclusão da importação
A importação específica DEVE (MUST) poder declarar a permissão de exclusão das suas importações. Com ela declarada, uma importação `DESCARTADA` ou `COM_ERROS` DEVE (MUST) poder ser excluída por quem tem a permissão, junto com todas as suas linhas. A exclusão DEVE (MUST) abrir a confirmação em modal pelo GET e excluir pelo POST com CSRF, e DEVE (MUST) voltar à lista de importações com mensagem. Uma importação `VALIDADA` ou `CONCLUIDA` NÃO DEVE (MUST NOT) ser excluída, e a tentativa DEVE (MUST) ser recusada com mensagem, sem alterar dados. A exclusão NÃO DEVE (MUST NOT) alterar dados de domínio e DEVE (MUST) ser auditada com a ação `EXCLUIR`, o arquivo, a situação e as informações próprias da importação. O controle de excluir DEVE (MUST) aparecer somente numa importação que pode ser excluída e para quem tem a permissão.

#### Scenario: Exclusão de importação descartada
- **GIVEN** uma importação `DESCARTADA` e um usuário com a permissão de exclusão
- **WHEN** ele confirma a exclusão
- **THEN** a importação e as linhas deixam de existir, e a tela volta à lista com "Importação do arquivo planilha.xlsx excluída."
- **AND** um registro de auditoria `EXCLUIR` guarda o arquivo e a situação

#### Scenario: Importação pendente não é excluída
- **GIVEN** uma importação `VALIDADA`
- **WHEN** a exclusão é enviada por POST
- **THEN** a exclusão é recusada com mensagem e a importação continua existindo

#### Scenario: Exclusão sem a permissão
- **GIVEN** um usuário com a permissão da importação, sem a de exclusão
- **WHEN** ele abre o detalhe de uma importação descartada
- **THEN** não há controle de excluir
- **AND** o POST na rota de exclusão responde 403

### Requirement: Resumo recolhido do detalhe da importação
O resumo do detalhe de uma importação DEVE (MUST) abrir recolhido, mostrando a situação e o resultado, e DEVE (MUST) expandir ao ser acionado, com animação, mostrando quem enviou, quem confirmou ou descartou, os campos próprios do envio, as prévias refeitas e o arquivo. No caminho de navegação das telas da importação, a seção DEVE (MUST) ser link somente para quem pode abrir a tela dela.

#### Scenario: Seção sem acesso
- **GIVEN** um usuário que tem a permissão da importação de ensalamento, mas não `ENSALAMENTO.VISUALIZAR`
- **WHEN** ele abre a lista de importações
- **THEN** "Ensalamento" aparece no caminho de navegação sem link
