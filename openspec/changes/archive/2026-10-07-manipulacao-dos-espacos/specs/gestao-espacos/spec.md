## ADDED Requirements

### Requirement: Nomes do espaço
Cada espaço DEVE (MUST) ter um nome atual e PODE (MAY) ter outros nomes, que são as grafias pelas quais a planilha institucional o cita. O nome atual e os outros nomes DEVEM (MUST) ser gravados como informados, com os acentos e a caixa preservados, tendo apenas as bordas aparadas e os espaços internos repetidos reduzidos a um, pela mesma normalização do nome do espaço já usada pelo ensalamento. O conjunto formado pelos nomes atuais e pelos outros nomes de todos os espaços DEVE (MUST) ser único sem diferenciar maiúsculas de minúsculas, de modo que uma grafia identifique no máximo um espaço, e essa unicidade DEVE (MUST) ser garantida pelo banco de dados. Os acentos NÃO DEVEM (MUST NOT) ser removidos na comparação. Um nome vazio depois da normalização DEVE (MUST) ser recusado. Encontrar um espaço por um nome DEVE (MUST) considerar o nome atual e os outros nomes, sem diferenciar maiúsculas de minúsculas.

#### Scenario: Espaço encontrado pelo outro nome
- **GIVEN** o espaço `HV 5` com o outro nome `HV5`
- **WHEN** o espaço de nome `hv5` é procurado
- **THEN** o espaço encontrado é `HV 5`

#### Scenario: Outro nome igual ao nome de outro espaço
- **GIVEN** os espaços `HV 4` e `HV 5`
- **WHEN** a gravação de `hv 4` como outro nome de `HV 5` é tentada
- **THEN** a gravação é recusada com "Já existe um espaço com este nome." e nenhum dado muda

#### Scenario: Nome gravado como informado
- **WHEN** o espaço `  Lab.   Fenôm. de Transportes ` é cadastrado
- **THEN** o nome gravado é `Lab. Fenôm. de Transportes`

#### Scenario: Acento distingue o nome
- **GIVEN** o espaço `Sala Música`
- **WHEN** o espaço `Sala Musica` é cadastrado
- **THEN** existem dois espaços

### Requirement: Origem do espaço
Cada espaço DEVE (MUST) registrar a origem, com o código gravado como dado, entre `MANUAL` e `PLANILHA`. O espaço cadastrado pela tela de Espaços DEVE (MUST) ter a origem `MANUAL`. O espaço criado pela confirmação de uma importação de ensalamento DEVE (MUST) ter a origem `PLANILHA` e DEVE (MUST) guardar a referência à importação que o criou. A origem e a importação de origem DEVEM (MUST) ser definidas na criação e NÃO DEVEM (MUST NOT) mudar depois, em nenhuma operação: editar, renomear, acrescentar ou retirar outro nome, desativar, reativar e ser reconhecido por outra importação preservam as duas. A origem DEVE (MUST) ser só informativa, e nenhuma regra do sistema DEVE (MUST) mudar de comportamento por causa dela. A interface DEVE (MUST) exibir a origem `MANUAL` como "Manual" e a origem `PLANILHA` como "Planilha", com o arquivo e a data da importação de origem quando houver.

#### Scenario: Espaço manual reconhecido pela planilha
- **GIVEN** o espaço `Sala 101`, com a origem `MANUAL`
- **WHEN** uma importação cuja planilha cita `Sala 101` é confirmada
- **THEN** o espaço continua com a origem `MANUAL` e sem importação de origem

#### Scenario: Espaço da planilha editado pela tela
- **GIVEN** o espaço `Laboratório 01`, criado pela importação 12 com a origem `PLANILHA`
- **WHEN** um usuário o renomeia para `Lab. 01` pela tela
- **THEN** o espaço continua com a origem `PLANILHA` e com a importação 12 como importação de origem

#### Scenario: Origem fora das operações de edição
- **WHEN** o formulário de edição de um espaço é enviado com um valor de origem
- **THEN** o valor é ignorado, porque a origem não é campo do formulário

### Requirement: Situação do espaço
Cada espaço DEVE (MUST) estar ativo ou inativo, e o espaço criado DEVE (MUST) estar ativo. Desativar um espaço NÃO DEVE (MUST NOT) alterar nem excluir nenhuma alocação, e as alocações do espaço inativo DEVEM (MUST) continuar na Grade do ensalamento dos semestres em que existem. A importação NÃO DEVE (MUST NOT) desativar um espaço, nem mesmo quando a planilha deixa de citá-lo, e NÃO DEVE (MUST NOT) reativar um espaço sem uma decisão de reativação, conforme a spec `ensalamento`. A interface DEVE (MUST) exibir a situação como "Ativo" ou "Inativo".

#### Scenario: Espaço inativo continua na Grade
- **GIVEN** o espaço `3/8`, com alocações em `2026/1`
- **WHEN** o espaço é desativado
- **THEN** as alocações continuam existindo e a Grade de `2026/1` continua mostrando a sala `3/8`

#### Scenario: Espaço ausente da planilha continua ativo
- **GIVEN** o espaço ativo `Zoo II`
- **WHEN** uma importação cuja planilha não cita `Zoo II` é confirmada
- **THEN** o espaço continua ativo

### Requirement: Lista de espaços
Um usuário com `ESPACO.VISUALIZAR` DEVE (MUST) poder consultar a lista de espaços, com o nome atual, os outros nomes, a origem e a situação de cada um. A lista DEVE (MUST) aceitar uma busca por trecho do nome atual ou de um outro nome, sem diferenciar maiúsculas de minúsculas; um filtro por situação com as opções todas, ativos e inativos; e um filtro por origem com as opções todas, manual e planilha. Busca e filtros DEVEM (MUST) valer juntos e ser recebidos como parâmetros da URL da lista (`busca`, `situacao` e `origem`), e um valor de filtro fora das opções DEVE (MUST) ser tratado como todas. A lista DEVE (MUST) ser ordenada pelo nome, na ordem natural dos números (`1/4` antes de `1/10`), e paginada conforme a spec `interface`, voltando à primeira página quando a busca ou um filtro mudar. Quando nenhum espaço atender à busca, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar a busca, e sem nenhum espaço cadastrado DEVE (MUST) mostrar "Nenhum espaço cadastrado.". Os controles de cadastrar, editar, desativar, reativar e excluir DEVEM (MUST) aparecer somente para quem tem a permissão da operação, e o de excluir somente para o espaço que pode ser excluído. Quem tem `AUDITORIA.VISUALIZAR` DEVE (MUST) ver, em cada espaço, um link para os registros de auditoria dele. A busca, os filtros e a paginação NÃO DEVEM (MUST NOT) alterar dados.

#### Scenario: Busca pelo outro nome
- **GIVEN** o espaço `HV 5` com o outro nome `HV5` e o espaço `HV 4`
- **WHEN** a lista é acessada com `busca=hv5`
- **THEN** só `HV 5` é exibido

#### Scenario: Filtro por origem
- **GIVEN** um espaço de origem `MANUAL` e dois de origem `PLANILHA`
- **WHEN** a lista é acessada com `origem=MANUAL`
- **THEN** só o espaço manual é exibido

#### Scenario: Filtro desconhecido
- **WHEN** a lista é acessada com `situacao=qualquer`
- **THEN** todos os espaços são exibidos e a resposta é 200

#### Scenario: Consulta sem permissão de alterar
- **GIVEN** um usuário cujo perfil concede somente `ESPACO.VISUALIZAR`
- **WHEN** ele abre a lista de espaços
- **THEN** a lista é exibida sem os controles de cadastrar, editar, desativar, reativar e excluir

### Requirement: Item "Espaços" no menu
O menu principal DEVE (MUST) ter o item "Espaços", que leva à lista de espaços, e o item DEVE (MUST) aparecer somente para quem tem `ESPACO.VISUALIZAR`.

#### Scenario: Menu com a permissão
- **GIVEN** um usuário cujo perfil concede `ESPACO.VISUALIZAR`
- **WHEN** ele abre qualquer página autenticada
- **THEN** o menu mostra o item "Espaços"

#### Scenario: Menu sem a permissão
- **GIVEN** um usuário cujo perfil não concede `ESPACO.VISUALIZAR`
- **WHEN** ele abre qualquer página autenticada
- **THEN** o menu não mostra o item "Espaços"

### Requirement: Cadastro manual de espaço
Um usuário com `ESPACO.CRIAR` DEVE (MUST) poder cadastrar um espaço informando o nome, obrigatório, e os outros nomes, opcionais, um por linha. O cadastro DEVE (MUST) abrir em modal, conforme o padrão de ações de gestão da spec `interface`. O espaço cadastrado DEVE (MUST) ter a origem `MANUAL`, nenhuma importação de origem e a situação ativo. Um nome ou outro nome que já identifique um espaço, ou que se repita no próprio formulário, DEVE (MUST) ser erro do formulário, citando o nome, sem gravar nada. No sucesso, a tela DEVE (MUST) voltar à lista com a mensagem "Espaço <nome> cadastrado.".

#### Scenario: Cadastro com outro nome
- **GIVEN** um usuário com `ESPACO.CRIAR`
- **WHEN** ele cadastra o espaço `Sala 101` com o outro nome `S101`
- **THEN** o espaço existe com a origem `MANUAL`, ativo, com o outro nome `S101`
- **AND** a lista mostra "Espaço Sala 101 cadastrado."

#### Scenario: Nome já usado como outro nome
- **GIVEN** o espaço `HV 5` com o outro nome `HV5`
- **WHEN** o cadastro do espaço `hv5` é enviado
- **THEN** o formulário mostra o erro no campo do nome e nenhum espaço é criado

### Requirement: Edição e renomeação de espaço
Um usuário com `ESPACO.EDITAR` DEVE (MUST) poder alterar o nome atual e os outros nomes de um espaço, ativo ou inativo, em modal. Ao renomear, o nome anterior DEVE (MUST) passar a ser outro nome do espaço, para que as importações seguintes continuem reconhecendo a grafia antiga. Quando o nome novo já for um outro nome do próprio espaço, ele DEVE (MUST) deixar de ser outro nome e passar a ser o nome atual, e o nome anterior DEVE (MUST) passar a ser outro nome. Retirar um outro nome DEVE (MUST) ser permitido, e a grafia retirada volta a ser desconhecida para as importações seguintes. Um nome ou outro nome que identifique outro espaço DEVE (MUST) ser erro do formulário, sem gravar nada. A alteração NÃO DEVE (MUST NOT) mudar a origem, a importação de origem, a situação nem as alocações do espaço. As alocações DEVEM (MUST) passar a exibir o nome novo, em todos os semestres, porque continuam apontando para o mesmo espaço. A edição DEVE (MUST) mostrar a origem, sem permitir alterá-la.

#### Scenario: Renomear guarda o nome anterior
- **GIVEN** o espaço `HV 5` com o outro nome `HV5`
- **WHEN** ele é renomeado para `Sala HV 05`
- **THEN** o nome atual é `Sala HV 05` e os outros nomes são `HV5` e `HV 5`
- **AND** uma importação seguinte que cita `HV 5` reconhece o espaço `Sala HV 05`

#### Scenario: Outro nome promovido a nome atual
- **GIVEN** o espaço `HV 5` com o outro nome `HV5`
- **WHEN** ele é renomeado para `HV5`
- **THEN** o nome atual é `HV5` e o outro nome é `HV 5`

#### Scenario: Grade exibe o nome novo
- **GIVEN** o espaço `3/8`, com alocações em `2026/1`
- **WHEN** ele é renomeado para `Sala 3/8`
- **THEN** a Grade de `2026/1` mostra as mesmas alocações na sala `Sala 3/8`

### Requirement: Desativação e reativação de espaço
Um usuário com `ESPACO.ALTERAR_SITUACAO` DEVE (MUST) poder desativar um espaço ativo e reativar um espaço inativo, com a confirmação aberta em modal pelo GET e a ação executada pelo POST com CSRF. A confirmação DEVE (MUST) ter como título a pergunta com o nome do espaço ("Desativar 1/10?", "Reativar 1/10?") e dizer a consequência: um espaço inativo continua no histórico e na Grade, e uma aula da planilha num espaço inativo vai precisar de decisão na importação. No sucesso, a tela DEVE (MUST) voltar à lista com "Espaço <nome> desativado." ou "Espaço <nome> reativado.". Desativar um espaço inativo ou reativar um ativo NÃO DEVE (MUST NOT) alterar nada nem gerar registro de auditoria.

#### Scenario: Desativação
- **GIVEN** o espaço ativo `1/10` e um usuário com `ESPACO.ALTERAR_SITUACAO`
- **WHEN** ele confirma a desativação
- **THEN** o espaço fica inativo, as alocações dele continuam e a lista mostra "Espaço 1/10 desativado."

#### Scenario: Reativação
- **GIVEN** o espaço inativo `1/10`
- **WHEN** a reativação é confirmada
- **THEN** o espaço fica ativo e a lista mostra "Espaço 1/10 reativado."

### Requirement: Exclusão de espaço sem uso
Um usuário com `ESPACO.EXCLUIR` DEVE (MUST) poder excluir um espaço somente quando nenhuma alocação, de nenhum semestre, apontar para ele, com a confirmação em modal pelo GET e a exclusão pelo POST com CSRF. A exclusão DEVE (MUST) apagar também os outros nomes do espaço e as decisões de importação que o citam, que voltam a ser pendências na atualização seguinte da importação. A exclusão de um espaço com alocação DEVE (MUST) ser recusada com a mensagem "O espaço <nome> tem aulas no ensalamento e não pode ser excluído. Desative o espaço.", sem alterar dados. A importação NÃO DEVE (MUST NOT) excluir espaço em nenhuma situação. No sucesso, a tela DEVE (MUST) voltar à lista com "Espaço <nome> excluído.".

#### Scenario: Exclusão de espaço cadastrado por engano
- **GIVEN** o espaço `Sala Teste`, cadastrado pela tela e sem nenhuma alocação
- **WHEN** um usuário com `ESPACO.EXCLUIR` confirma a exclusão
- **THEN** o espaço e os outros nomes dele deixam de existir e a lista mostra "Espaço Sala Teste excluído."

#### Scenario: Espaço com aulas não é excluído
- **GIVEN** o espaço `1/10`, com alocações em `2026/2`
- **WHEN** a exclusão é enviada por POST
- **THEN** a exclusão é recusada com a mensagem que manda desativar o espaço, e nada muda

#### Scenario: Controle de excluir oculto
- **GIVEN** o espaço `1/10`, com alocações
- **WHEN** um usuário com `ESPACO.EXCLUIR` abre a lista
- **THEN** o espaço `1/10` não mostra o controle de excluir

### Requirement: Sugestão de espaços parecidos
O sistema DEVE (MUST) oferecer uma única operação que, dado um nome e um conjunto de nomes conhecidos, devolve os nomes parecidos, e ela DEVE (MUST) servir somente para gerar perguntas ao usuário. Nenhuma operação DEVE (MUST) associar, criar, renomear ou unir espaços a partir de uma semelhança. A semelhança DEVE (MUST) considerar parecidos, no mínimo, os nomes que ficam iguais quando se ignoram espaços, pontos, hífens, acentos, maiúsculas e zeros à esquerda dos números, e os nomes em que um é o outro acrescido, no fim, de um número ou de um algarismo romano. A regra de semelhança é heurística: ela PODE (MAY) ser ajustada sem mudar esta spec, desde que os cenários abaixo continuem valendo e que ela continue sem efeito automático.

#### Scenario: Diferença de espaço
- **WHEN** os parecidos de `HV5` são procurados entre `HV 5` e `HV 4`
- **THEN** o resultado é `HV 5`

#### Scenario: Diferença de ponto e espaço
- **WHEN** os parecidos de `Lab.3 - Info` são procurados entre `Lab. 3 - Info` e `Lab. 4 - Info`
- **THEN** o resultado é `Lab. 3 - Info`

#### Scenario: Zero à esquerda
- **WHEN** os parecidos de `Sala 01` são procurados entre `Sala 1` e `Sala 10`
- **THEN** o resultado é `Sala 1`

#### Scenario: Numeral acrescido
- **WHEN** os parecidos de `Lab. Química` são procurados entre `Lab. Química I`, `Lab. Química II` e `Lab. Redes`
- **THEN** o resultado é `Lab. Química I` e `Lab. Química II`

#### Scenario: Nomes que não são parecidos
- **WHEN** os parecidos de `1/1` são procurados entre `1/10` e `11`, e os de `Lab. Análise Alim.` entre `Sl. Análise Alim.`, e os de `1/10` entre `Sala 10 do Bloco 1`
- **THEN** nenhum resultado é devolvido

### Requirement: Espaços existentes antes do cadastro
A adoção do cadastro NÃO DEVE (MUST NOT) excluir, renomear nem unir nenhum espaço existente, e NÃO DEVE (MUST NOT) alterar nenhuma alocação. Todo espaço existente antes desta mudança DEVE (MUST) passar a ter a origem `PLANILHA`, porque a importação era o único caminho de criação, a situação ativo e o próprio nome como nome atual, sem outros nomes. A importação de origem DEVE (MUST) ser a importação de ensalamento concluída cuja linha de sala registra a criação do espaço, e DEVE (MUST) ficar vazia quando essa linha não existir. Os espaços existentes que nenhuma alocação usa DEVEM (MUST) ser preservados. A adoção NÃO DEVE (MUST NOT) gerar registros de auditoria retroativos.

#### Scenario: Espaço atual rastreado até a importação
- **GIVEN** o espaço `1/10`, criado pela importação concluída 46
- **WHEN** a migração é aplicada
- **THEN** o espaço tem a origem `PLANILHA`, a importação 46 como importação de origem, a situação ativo e o nome `1/10` como nome atual

#### Scenario: Espaço sem aulas preservado
- **GIVEN** o espaço `Lab. Carnes`, criado pela lista de salas e sem nenhuma alocação
- **WHEN** a migração é aplicada
- **THEN** o espaço continua existindo, ativo

#### Scenario: Reimportação da mesma planilha depois da adoção
- **GIVEN** os espaços da importação concluída de `planilha_example_corrigida.xlsx`, adotados pelo cadastro
- **WHEN** a mesma planilha é enviada de novo
- **THEN** todos os espaços usados são reconhecidos e nenhum é proposto como novo nem vira pendência
