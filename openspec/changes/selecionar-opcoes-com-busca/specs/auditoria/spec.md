## MODIFIED Requirements

### Requirement: Consulta dos registros de auditoria
Usuários autorizados DEVEM (MUST) poder consultar os registros de auditoria numa tela própria. A consulta DEVE (MUST) permitir filtrar por usuário responsável, ação, recurso, identificador do recurso, período e origem da operação, com os filtros combináveis entre si e recebidos como parâmetros da URL, de modo que o mesmo endereço reproduza o mesmo resultado. Um valor de filtro fora das opções DEVE (MUST) ser tratado como ausência do filtro. Os registros DEVEM (MUST) ser apresentados em ordem cronológica, do mais recente para o mais antigo, paginados conforme a spec `interface`, com a página combinada aos filtros. A lista DEVE (MUST) exibir, de cada registro, a data e a hora, o responsável, a ação, o recurso e a origem, com os rótulos em português, e "Sistema" como responsável quando não houver usuário. Cada registro DEVE (MUST) ter uma ação que exiba os detalhes dele, incluindo o identificador do recurso, os valores anteriores e posteriores campo a campo, as informações adicionais, o endereço IP e o cliente. Quando nenhum registro atender aos filtros, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar os filtros. O filtro por usuário DEVE (MUST) usar o componente de seleção da spec `interface`, com as opções vindas de uma rota de opções paginada no servidor, de modo que a tela não carregue todos os usuários cadastrados. Sem JavaScript, esse filtro DEVE (MUST) oferecer a primeira página das opções, e os demais filtros DEVEM (MUST) continuar completos. A consulta NÃO DEVE (MUST NOT) alterar dados.

#### Scenario: Lista em ordem cronológica
- **GIVEN** registros de auditoria de datas diferentes
- **WHEN** a tela de auditoria é acessada sem filtros
- **THEN** os registros aparecem do mais recente para o mais antigo, com a data e a hora no formato dd/mm/aaaa e 24 horas

#### Scenario: Filtro por usuário e por ação
- **GIVEN** registros de Ana e de Bruno, de ações diferentes
- **WHEN** a consulta é feita com o filtro de usuário igual a Ana e o filtro de ação igual a `LOGIN`
- **THEN** só os registros de login de Ana são exibidos

#### Scenario: Filtro por recurso e identificador
- **GIVEN** registros de vários usuários alterados
- **WHEN** a consulta é feita pelo recurso `USUARIO` e pelo identificador `25`
- **THEN** só os registros do usuário de identificador 25 são exibidos

#### Scenario: Filtro por período
- **GIVEN** registros de 20/09/2026 e de 24/09/2026
- **WHEN** a consulta é feita com o período de 24/09/2026 até 24/09/2026
- **THEN** só os registros de 24/09/2026 são exibidos

#### Scenario: Filtro por origem
- **GIVEN** registros com as origens `INTERFACE`, `SISTEMA` e `IMPORTACAO`
- **WHEN** a consulta é feita com a origem `SISTEMA`
- **THEN** só os registros das ações automáticas são exibidos

#### Scenario: Filtro inválido
- **WHEN** a consulta é feita com uma ação que não existe no catálogo ou com uma data fora do formato
- **THEN** o filtro correspondente é ignorado e a lista é exibida sem erro

#### Scenario: Detalhe de um registro
- **GIVEN** um registro de alteração de usuário
- **WHEN** os detalhes dele são exibidos
- **THEN** aparecem o responsável, a ação, o recurso, o identificador, a data e a hora, o endereço IP, o cliente, a origem e cada campo alterado com o valor anterior e o posterior

#### Scenario: Consulta sem resultado
- **WHEN** a consulta é feita com filtros que não correspondem a nenhum registro
- **THEN** a lista informa que nenhum registro foi encontrado e oferece um link para limpar os filtros

#### Scenario: Opções do filtro por usuário
- **GIVEN** 300 usuários cadastrados
- **WHEN** a tela de auditoria é renderizada
- **THEN** o HTML do filtro por usuário contém no máximo 10 opções, mais a opção escolhida quando houver

#### Scenario: Busca de usuário no filtro
- **GIVEN** 300 usuários cadastrados, dos quais 3 têm "silva" no nome
- **WHEN** a busca "silva" é feita no filtro por usuário
- **THEN** as 3 opções correspondentes são oferecidas, buscadas no servidor
