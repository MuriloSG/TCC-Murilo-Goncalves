## ADDED Requirements

### Requirement: Área Agenda própria
O sistema DEVE (MUST) ter uma área autenticada chamada Agenda, na rota `agenda/`, com view, templates e regras próprias, e com o item "Agenda" no menu, visível só para quem tem `AGENDA.VISUALIZAR`. A Agenda NÃO DEVE (MUST NOT) reaproveitar a view autenticada do Ensalamento, e a tela do Ensalamento NÃO DEVE (MUST NOT) ganhar ação de solicitação nem de agendamento. A Agenda DEVE (MUST) mostrar a mesma Grade do Ensalamento (semana e mês, dias, faixas, espaço, ocupação, navegação e o mesmo comportamento abaixo de 640 px), montada com as estruturas compartilhadas da Grade, sem uma representação própria para o celular.

#### Scenario: Visualizar a Agenda
- **GIVEN** um usuário autenticado com `AGENDA.VISUALIZAR`
- **WHEN** ele abre `agenda/` e escolhe a sala `Laboratório de Informática 2` e a semana de 12/10/2026
- **THEN** a resposta é 200 e mostra a Grade da semana com as aulas do ensalamento e os agendamentos aprovados da sala
- **AND** o menu mostra o item "Agenda" separado do item "Ensalamento"

#### Scenario: Visão mensal
- **WHEN** o mesmo usuário escolhe a visão por mês
- **THEN** a Agenda mostra o mês na mesma estrutura da visão mensal do Ensalamento, mantendo a sala escolhida

#### Scenario: Ensalamento sem ação de agendamento
- **GIVEN** um usuário com `ENSALAMENTO.VISUALIZAR` e `AGENDA.SOLICITAR`
- **WHEN** ele abre a Grade do Ensalamento
- **THEN** a Grade não tem botão, link nem formulário de solicitação de agendamento

### Requirement: Permissões da Agenda
O catálogo DEVE (MUST) ganhar as permissões `AGENDA.VISUALIZAR` (ver a Grade da Agenda), `AGENDA.SOLICITAR` (enviar solicitação, ver as próprias e responder à alternativa sugerida nelas) e `AGENDA.ANALISAR` (ver as solicitações de todos, aprovar, rejeitar e sugerir alternativa), por migration de dados. O catálogo NÃO DEVE (MUST NOT) ter `AGENDA.GERENCIAR` nem outra permissão genérica da Agenda. A migration DEVE (MUST) conceder as três ao perfil `ADMINISTRADOR` e `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR` ao perfil `DOCENTE`, sem alterar as demais concessões, e nenhuma delas DEVE (MUST) ser reservada ao superadmin. Cada rota da Agenda DEVE (MUST) exigir autenticação e a sua permissão, e toda mudança de estado DEVE (MUST) verificar de novo a permissão, a posse quando exigida e o estado atual, no momento da operação.

#### Scenario: Catálogo da Agenda
- **WHEN** as migrations são aplicadas
- **THEN** existem `AGENDA.VISUALIZAR`, `AGENDA.SOLICITAR` e `AGENDA.ANALISAR` e não existe `AGENDA.GERENCIAR`

#### Scenario: Anônimo
- **WHEN** um visitante não autenticado abre `agenda/`, `agenda/solicitar/` ou `agenda/solicitacoes/`
- **THEN** ele é levado à página de login com `next`

#### Scenario: Sem permissão de visualizar
- **GIVEN** um usuário autenticado sem `AGENDA.VISUALIZAR`
- **WHEN** ele abre `agenda/`
- **THEN** a resposta é 403 e o menu não mostra "Agenda"

#### Scenario: Sem permissão de solicitar
- **GIVEN** um usuário com `AGENDA.VISUALIZAR` e sem `AGENDA.SOLICITAR`
- **WHEN** ele envia um POST para `agenda/solicitar/`
- **THEN** a resposta é 403 e nenhuma solicitação é criada
- **AND** a faixa disponível da Grade não oferece "Solicitar agendamento"

#### Scenario: Sem permissão de analisar
- **GIVEN** um usuário com `AGENDA.SOLICITAR` e sem `AGENDA.ANALISAR`
- **WHEN** ele envia um POST para aprovar, rejeitar ou sugerir alternativa numa solicitação pendente
- **THEN** a resposta é 403 e a solicitação continua `PENDENTE`

#### Scenario: POST sem CSRF
- **WHEN** um usuário com a permissão envia uma ação da Agenda sem token CSRF
- **THEN** a resposta é 403 e nada muda

### Requirement: Solicitação de agendamento
Um usuário com `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR` DEVE (MUST) poder escolher uma faixa disponível da Grade da Agenda e a ação "Solicitar agendamento", que abre um modal com o espaço, a data, o início e o fim preenchidos pela faixa. O início e o fim PODEM (MAY) ser ajustados, e o espaço e a data NÃO DEVEM (MUST NOT) ser editáveis no modal. A descrição breve do uso DEVE (MUST) ser obrigatória, com até 500 caracteres, e uma descrição só com espaços DEVE (MUST) ser tratada como vazia. O envio DEVE (MUST) criar uma solicitação `PENDENTE` do usuário e NÃO DEVE (MUST NOT) criar agendamento. A solicitação DEVE (MUST) ser recusada, sem gravar nada, quando o espaço estiver inativo, o fim não for posterior ao início, o início já tiver passado ou o intervalo estiver ocupado no momento do envio. Espaço, data e horário forjados na requisição DEVEM (MUST) passar pelas mesmas regras.

#### Scenario: Criar solicitação
- **GIVEN** um usuário com `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR` e a sala `Laboratório de Informática 2` disponível em 15/10/2026 das 14:00 às 16:00
- **WHEN** ele escolhe a faixa, abre "Solicitar agendamento", informa a descrição "Reunião do projeto de extensão com os alunos." e envia
- **THEN** existe uma solicitação `PENDENTE` dele para essa sala, data e horário, com essa descrição
- **AND** não existe agendamento para esse horário
- **AND** a faixa continua disponível na Grade

#### Scenario: Modal preenchido pela faixa
- **WHEN** o usuário escolhe a faixa de 15/10/2026 das 14:00 às 16:00 da sala `Laboratório de Informática 2`
- **THEN** o modal mostra essa sala, 15/10/2026, 14:00 e 16:00 preenchidos e o campo da descrição vazio

#### Scenario: Descrição obrigatória
- **WHEN** o usuário envia a solicitação com a descrição vazia ou só com espaços
- **THEN** o modal mostra o erro no campo da descrição e nenhuma solicitação é criada

#### Scenario: Fim antes do início
- **WHEN** o usuário envia a solicitação com início 16:00 e fim 14:00
- **THEN** a solicitação é recusada com o erro do horário e nada é gravado

#### Scenario: Horário no passado
- **GIVEN** hoje é 15/10/2026 às 15:00
- **WHEN** o usuário envia uma solicitação para 15/10/2026 das 14:00 às 16:00
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Horário ocupado
- **GIVEN** um agendamento aprovado na sala em 15/10/2026 das 14:00 às 15:00
- **WHEN** o usuário envia uma solicitação para a mesma sala e data das 14:30 às 16:00
- **THEN** a solicitação é recusada com "Este espaço está ocupado das 14:00 às 15:00. Escolha outro horário." e nada é gravado

#### Scenario: Espaço forjado
- **WHEN** o usuário altera na requisição o espaço para um espaço inativo
- **THEN** a solicitação é recusada e nada é gravado

### Requirement: Solicitação pendente não ocupa o horário
Uma solicitação `PENDENTE` ou `ALTERNATIVA_SUGERIDA` DEVE (MUST) representar só a intenção de uso e NÃO DEVE (MUST NOT) ocupar o horário: ela NÃO DEVE (MUST NOT) aparecer como ocupação na Grade, NÃO DEVE (MUST NOT) impedir outra solicitação para o mesmo horário e NÃO DEVE (MUST NOT) travar o espaço. Só o agendamento aprovado ocupa o horário.

#### Scenario: Duas solicitações para o mesmo horário
- **GIVEN** uma solicitação `PENDENTE` de Ana para a sala em 15/10/2026 das 14:00 às 16:00
- **WHEN** Bruno envia uma solicitação para o mesmo espaço e horário
- **THEN** a solicitação de Bruno é criada como `PENDENTE`

### Requirement: Conflito de horário
O sistema DEVE (MUST) tratar cada horário como o intervalo semiaberto `[início, fim)`, e dois intervalos do mesmo espaço e da mesma data DEVEM (MUST) conflitar quando `início < outro_fim` e `fim > outro_início`. Um agendamento aprovado NÃO DEVE (MUST NOT) conflitar com uma aula do ensalamento do mesmo espaço naquela data (alocação do semestre com período que contém a data, no dia da semana da data) nem com outro agendamento aprovado do mesmo espaço. A verificação DEVE (MUST) acontecer no model, e não só na interface, e a ausência de sobreposição entre agendamentos aprovados DEVE (MUST) ser garantida por restrição do banco.

#### Scenario: Horários encostados
- **GIVEN** um agendamento aprovado na sala em 15/10/2026 das 14:00 às 15:00
- **WHEN** uma solicitação da mesma sala e data das 15:00 às 16:00 é aprovada
- **THEN** o agendamento das 15:00 às 16:00 é criado

#### Scenario: Conflito com o ensalamento
- **GIVEN** uma alocação da sala às quintas-feiras, na faixa `14:10 - 15:00`, no semestre `2026/2` com período de 03/08/2026 a 18/12/2026
- **WHEN** uma solicitação da sala em 15/10/2026, quinta-feira, das 14:00 às 16:00 é enviada
- **THEN** ela é recusada por conflito com o ensalamento

#### Scenario: Ensalamento fora do período
- **GIVEN** a mesma alocação
- **WHEN** uma solicitação da sala em 07/01/2027, quinta-feira, das 14:00 às 16:00 é enviada
- **THEN** ela é criada, porque a data está fora do período do semestre

#### Scenario: Conflito com agendamento
- **GIVEN** um agendamento aprovado na sala em 15/10/2026 das 14:00 às 16:00
- **WHEN** outra solicitação da sala das 15:30 às 17:00 é aprovada
- **THEN** a aprovação é recusada por conflito e nenhum agendamento é criado

#### Scenario: Restrição do banco
- **WHEN** dois agendamentos sobrepostos do mesmo espaço são gravados diretamente, sem passar pelas operações do model
- **THEN** o banco recusa o segundo

### Requirement: Estados da solicitação
A solicitação DEVE (MUST) ter um dos estados `PENDENTE`, `APROVADA`, `REJEITADA`, `ALTERNATIVA_SUGERIDA` e `ALTERNATIVA_RECUSADA`, exibidos como "Pendente", "Aprovada", "Rejeitada", "Alternativa sugerida" e "Alternativa recusada". As únicas transições DEVEM (MUST) ser:

| De | Para | Quem |
|---|---|---|
| criação | `PENDENTE` | o solicitante, com `AGENDA.SOLICITAR` |
| `PENDENTE` | `APROVADA` | quem tem `AGENDA.ANALISAR` |
| `PENDENTE` | `REJEITADA` | quem tem `AGENDA.ANALISAR` |
| `PENDENTE` | `ALTERNATIVA_SUGERIDA` | quem tem `AGENDA.ANALISAR` |
| `ALTERNATIVA_SUGERIDA` | `ALTERNATIVA_SUGERIDA` (nova alternativa) | quem tem `AGENDA.ANALISAR` |
| `ALTERNATIVA_SUGERIDA` | `REJEITADA` | quem tem `AGENDA.ANALISAR` |
| `ALTERNATIVA_SUGERIDA` | `APROVADA` (aceite) | só o solicitante, com `AGENDA.SOLICITAR` |
| `ALTERNATIVA_SUGERIDA` | `ALTERNATIVA_RECUSADA` (recusa) | só o solicitante, com `AGENDA.SOLICITAR` |

`APROVADA`, `REJEITADA` e `ALTERNATIVA_RECUSADA` DEVEM (MUST) ser finais nesta versão. Qualquer outra transição DEVE (MUST) ser recusada pelo model, sem alterar a solicitação e sem registro de auditoria, e a leitura do estado DEVE (MUST) acontecer com a solicitação travada na transação da operação. Os dados originais da solicitação NÃO DEVEM (MUST NOT) mudar depois da criação.

#### Scenario: Aprovar solicitação rejeitada
- **GIVEN** uma solicitação `REJEITADA`
- **WHEN** um usuário com `AGENDA.ANALISAR` tenta aprová-la
- **THEN** a operação é recusada, a solicitação continua `REJEITADA` e nenhum agendamento é criado

#### Scenario: Aceitar sem alternativa
- **GIVEN** uma solicitação `PENDENTE` de Ana
- **WHEN** Ana envia o aceite de alternativa
- **THEN** a operação é recusada e a solicitação continua `PENDENTE`

#### Scenario: Decisão dupla
- **GIVEN** uma solicitação `PENDENTE` aberta por dois usuários com `AGENDA.ANALISAR`
- **WHEN** o primeiro a rejeita e depois o segundo envia a aprovação
- **THEN** a aprovação é recusada e a solicitação continua `REJEITADA`

### Requirement: Aprovação
Um usuário com `AGENDA.ANALISAR` DEVE (MUST) poder aprovar uma solicitação `PENDENTE`. A aprovação DEVE (MUST) verificar de novo, no momento da aprovação, com o espaço travado na transação, que o espaço está ativo, que o início não passou e que não há conflito com o ensalamento nem com agendamento aprovado. Aprovada, a solicitação DEVE (MUST) passar a `APROVADA`, com quem decidiu e quando, e DEVE (MUST) ser criado na mesma transação um agendamento avulso, não recorrente, com o espaço, a data, o início, o fim e a descrição da solicitação. Recusada a aprovação, a solicitação DEVE (MUST) continuar `PENDENTE`, disponível para rejeição ou sugestão de alternativa. A aprovação NÃO DEVE (MUST NOT) criar nem alterar `Allocation`.

#### Scenario: Aprovar
- **GIVEN** uma solicitação `PENDENTE` da sala em 15/10/2026 das 14:00 às 16:00, com o horário disponível
- **WHEN** um usuário com `AGENDA.ANALISAR` a aprova
- **THEN** a solicitação passa a `APROVADA`
- **AND** existe um agendamento da sala em 15/10/2026 das 14:00 às 16:00, ligado a ela
- **AND** a quantidade de alocações não muda

#### Scenario: Horário ocupado depois da solicitação
- **GIVEN** duas solicitações `PENDENTE` da mesma sala em 15/10/2026 das 14:00 às 16:00
- **WHEN** a primeira é aprovada e depois a aprovação da segunda é enviada
- **THEN** a segunda aprovação é recusada com a mensagem do horário ocupado
- **AND** a segunda solicitação continua `PENDENTE`

#### Scenario: Aprovações simultâneas
- **GIVEN** duas solicitações `PENDENTE` sobrepostas da mesma sala
- **WHEN** as duas são aprovadas ao mesmo tempo, em transações diferentes
- **THEN** só um agendamento é criado e a outra solicitação continua `PENDENTE`

### Requirement: Rejeição
Um usuário com `AGENDA.ANALISAR` DEVE (MUST) poder rejeitar uma solicitação `PENDENTE` ou `ALTERNATIVA_SUGERIDA`, informando o motivo, que DEVE (MUST) ser obrigatório. A rejeição DEVE (MUST) registrar o motivo, quem decidiu e quando, e NÃO DEVE (MUST NOT) criar agendamento.

#### Scenario: Rejeitar
- **WHEN** um usuário com `AGENDA.ANALISAR` rejeita uma solicitação `PENDENTE` com o motivo "Laboratório em manutenção nessa data."
- **THEN** a solicitação passa a `REJEITADA`, com esse motivo, e nenhum agendamento é criado

#### Scenario: Rejeitar sem motivo
- **WHEN** a rejeição é enviada com o motivo vazio
- **THEN** o modal mostra o erro no motivo e a solicitação continua no estado anterior

### Requirement: Sugestão de alternativa
Um usuário com `AGENDA.ANALISAR` DEVE (MUST) poder devolver uma solicitação `PENDENTE` ou `ALTERNATIVA_SUGERIDA` sugerindo outro espaço, outra data, outro horário ou uma combinação deles, com uma mensagem opcional. A alternativa DEVE (MUST) ser diferente do original, DEVE (MUST) seguir as mesmas regras de validade da solicitação e DEVE (MUST) estar disponível no momento da sugestão. A solicitação DEVE (MUST) passar a `ALTERNATIVA_SUGERIDA`, com a alternativa, a mensagem, quem decidiu e quando, mantendo os dados originais. Uma nova sugestão DEVE (MUST) substituir a anterior. A sugestão NÃO DEVE (MUST NOT) criar agendamento nem ocupar o horário sugerido.

#### Scenario: Sugerir alternativa
- **GIVEN** uma solicitação `PENDENTE` de Ana para o `Laboratório de Informática 2` em 15/10/2026 das 14:00 às 16:00
- **WHEN** um usuário com `AGENDA.ANALISAR` sugere o `Laboratório de Informática 3` em 16/10/2026 das 14:00 às 16:00, com a mensagem "O laboratório 2 recebe manutenção no dia 15."
- **THEN** a solicitação passa a `ALTERNATIVA_SUGERIDA`, com a sala, a data e o horário originais e os sugeridos, e a mensagem
- **AND** nenhum agendamento é criado

#### Scenario: Alternativa igual ao original
- **WHEN** a sugestão é enviada com o mesmo espaço, data e horário da solicitação
- **THEN** ela é recusada e a solicitação continua no estado anterior

#### Scenario: Alternativa ocupada
- **WHEN** a sugestão é enviada com um horário que conflita com um agendamento aprovado
- **THEN** ela é recusada com a mensagem do horário ocupado

### Requirement: Resposta do solicitante à alternativa
Só o próprio solicitante, com `AGENDA.SOLICITAR`, DEVE (MUST) poder aceitar ou recusar a alternativa de uma solicitação `ALTERNATIVA_SUGERIDA`. O aceite DEVE (MUST) verificar de novo, com o espaço sugerido travado na transação, que a alternativa continua válida e disponível e, nesse caso, passar a solicitação a `APROVADA` e criar o agendamento com o espaço, a data e o horário sugeridos. Recusado o aceite por conflito, a solicitação DEVE (MUST) continuar `ALTERNATIVA_SUGERIDA`. A recusa DEVE (MUST) passar a solicitação a `ALTERNATIVA_RECUSADA`, sem criar agendamento. As duas respostas DEVEM (MUST) registrar quando o solicitante respondeu.

#### Scenario: Aceitar sugestão
- **GIVEN** a solicitação de Ana com a alternativa `Laboratório de Informática 3`, 16/10/2026, das 14:00 às 16:00, disponível
- **WHEN** Ana escolhe "Aceitar alternativa"
- **THEN** a solicitação passa a `APROVADA`
- **AND** existe um agendamento do `Laboratório de Informática 3` em 16/10/2026 das 14:00 às 16:00

#### Scenario: Aceitar alternativa já ocupada
- **GIVEN** a mesma alternativa, ocupada por outro agendamento aprovado depois da sugestão
- **WHEN** Ana escolhe "Aceitar alternativa"
- **THEN** o aceite é recusado com a mensagem do horário ocupado e a solicitação continua `ALTERNATIVA_SUGERIDA`

#### Scenario: Recusar sugestão
- **WHEN** Ana escolhe "Recusar alternativa"
- **THEN** a solicitação passa a `ALTERNATIVA_RECUSADA` e nenhum agendamento é criado

#### Scenario: Resposta por outro usuário
- **GIVEN** Bruno, com `AGENDA.SOLICITAR` e `AGENDA.ANALISAR`
- **WHEN** Bruno envia o aceite ou a recusa da alternativa da solicitação de Ana
- **THEN** a resposta é 404 e a solicitação continua `ALTERNATIVA_SUGERIDA`

### Requirement: Minhas solicitações
Um usuário com `AGENDA.SOLICITAR` DEVE (MUST) ver, em "Minhas solicitações", só as solicitações que ele criou, da mais recente para a mais antiga, com o espaço, a data, o horário, a descrição e o estado. A solicitação com alternativa DEVE (MUST) mostrar o selo "Resposta pendente" e, no detalhe, a sala, a data e o horário originais, a sala, a data e o horário sugeridos, a mensagem de quem analisou e as ações "Aceitar alternativa" e "Recusar alternativa". A rejeitada DEVE (MUST) mostrar o motivo. Uma solicitação de outro usuário acessada pelo ID na URL DEVE (MUST) responder 404.

#### Scenario: Só as próprias
- **GIVEN** solicitações de Ana e de Bruno
- **WHEN** Ana abre "Minhas solicitações"
- **THEN** a lista mostra só as solicitações de Ana, cada uma com o estado

#### Scenario: Acesso indevido pelo ID
- **WHEN** Ana abre `agenda/minhas-solicitacoes/<id>/` com o ID de uma solicitação de Bruno
- **THEN** a resposta é 404

### Requirement: Análise das solicitações
Um usuário com `AGENDA.ANALISAR` DEVE (MUST) ver, em "Solicitações para análise", as solicitações `PENDENTE` e `ALTERNATIVA_SUGERIDA`, das mais antigas para as mais recentes, com a opção de ver também as encerradas. O detalhe DEVE (MUST) mostrar o nome e o e-mail do solicitante, o espaço, a data, o horário, a descrição, o estado e o histórico da solicitação (criação, decisão, alternativa, resposta e motivo, com quem e quando), e as ações "Aprovar", "Rejeitar" e "Sugerir alternativa" permitidas no estado atual. A tela NÃO DEVE (MUST NOT) mostrar perfil, permissões nem outros dados pessoais do solicitante.

#### Scenario: Lista de análise
- **GIVEN** uma solicitação `PENDENTE`, uma `ALTERNATIVA_SUGERIDA` e uma `APROVADA`
- **WHEN** um usuário com `AGENDA.ANALISAR` abre "Solicitações para análise"
- **THEN** a lista mostra a pendente e a com alternativa sugerida, e não a aprovada

#### Scenario: Detalhe sem dados desnecessários
- **WHEN** ele abre o detalhe de uma solicitação
- **THEN** a tela mostra o nome e o e-mail do solicitante e não mostra o perfil nem as permissões dele

### Requirement: Agendamentos aprovados nas Grades e no calendário público
A Grade da Agenda e a Grade do Ensalamento DEVEM (MUST) mostrar, na célula do espaço, da data e da faixa, as aulas do ensalamento e os agendamentos aprovados, em todas as faixas que o agendamento cruza, cada um com o seu tipo indicado por texto e ícone, e não só por cor. O card do agendamento DEVE (MUST) mostrar o selo "Agendamento", o horário e a descrição, e o nome do solicitante só para quem tem `AGENDA.ANALISAR`. Um agendamento que não cruza nenhuma faixa do semestre DEVE (MUST) ganhar uma linha própria com o seu intervalo. A faixa com agendamento aprovado DEVE (MUST) deixar de contar como disponível. A Grade do Ensalamento DEVE (MUST) continuar só de consulta, sem ação de solicitar. O calendário público DEVE (MUST) mostrar o agendamento aprovado só na consulta em que o único filtro principal é a sala, com o selo "Agendamento", o horário e a descrição, e NÃO DEVE (MUST NOT) mostrar o nome, o e-mail nem outro dado de quem solicitou ou de quem aprovou. Solicitações pendentes ou com alternativa sugerida NÃO DEVEM (MUST NOT) aparecer em nenhuma dessas telas.

#### Scenario: Agendamento na Grade da Agenda
- **GIVEN** um agendamento aprovado da sala em 15/10/2026 das 14:00 às 16:00 e uma aula da mesma sala na segunda-feira da mesma semana
- **WHEN** a Grade da Agenda da semana é aberta para a sala
- **THEN** a quinta-feira mostra o card com o selo "Agendamento" e a descrição, e a segunda-feira mostra a aula com o selo "Ensalamento"
- **AND** a faixa do agendamento não oferece "Solicitar agendamento"

#### Scenario: Agendamento na Grade do Ensalamento
- **GIVEN** o mesmo agendamento
- **WHEN** um usuário com `ENSALAMENTO.VISUALIZAR` e sem `AGENDA.ANALISAR` abre a Grade do Ensalamento da sala e da semana
- **THEN** a Grade mostra o card do agendamento com o horário e a descrição, sem o nome de quem solicitou
- **AND** a Grade não tem ação de solicitar agendamento

#### Scenario: Agendamento no calendário público
- **GIVEN** o mesmo agendamento
- **WHEN** um visitante abre o calendário público da sala nessa semana
- **THEN** o calendário mostra o selo "Agendamento", o horário e a descrição
- **AND** a página não contém o nome nem o e-mail de quem solicitou ou aprovou

#### Scenario: Calendário público por docente
- **GIVEN** o mesmo agendamento
- **WHEN** o calendário público é aberto com o filtro de um docente
- **THEN** o agendamento não aparece

#### Scenario: Solicitação pendente fora das telas
- **GIVEN** uma solicitação pendente da sala
- **WHEN** a Grade da Agenda, a Grade do Ensalamento e o calendário público da sala são abertos
- **THEN** a solicitação não aparece em nenhum deles

### Requirement: Auditoria da Agenda
As mudanças de estado da Agenda DEVEM (MUST) gerar registros de auditoria no padrão existente: a criação da solicitação (`CRIAR`), a aprovação (`APROVAR`), a rejeição com o motivo (`REJEITAR`), a sugestão de alternativa (`SUGERIR`), o aceite (`ACEITAR`) e a recusa (`RECUSAR`), com o recurso `SOLICITACAO_AGENDAMENTO`, e a criação do agendamento (`CRIAR`), com o recurso `AGENDAMENTO`. Operação recusada, por permissão, posse, estado, validação ou conflito, NÃO DEVE (MUST NOT) gerar registro.

#### Scenario: Aprovação auditada
- **WHEN** uma solicitação `PENDENTE` é aprovada
- **THEN** existe um registro `APROVAR` do recurso `SOLICITACAO_AGENDAMENTO` com o estado anterior e o posterior
- **AND** existe um registro `CRIAR` do recurso `AGENDAMENTO` com o espaço, a data e o horário

#### Scenario: Recusa não auditada
- **WHEN** uma aprovação é recusada por conflito
- **THEN** nenhum registro de auditoria é criado

### Requirement: Desempenho da Agenda
A Grade da Agenda DEVE (MUST) usar uma quantidade fixa de consultas por requisição, que não cresça com o intervalo, com o número de faixas nem com o número de agendamentos, e NÃO DEVE (MUST NOT) consultar o banco por célula nem por agendamento. As listas de solicitações DEVEM (MUST) ser paginadas e usar uma quantidade fixa de consultas por página. A verificação de conflito DEVE (MUST) usar no máximo duas consultas.

#### Scenario: Consultas fixas
- **WHEN** a Grade da Agenda é aberta para uma semana com um agendamento e depois para um mês com trinta agendamentos
- **THEN** as duas requisições usam a mesma quantidade de consultas

### Requirement: Escopo da primeira versão da Agenda
O agendamento DEVE (MUST) ser avulso, numa única data, e NÃO DEVE (MUST NOT) ser recorrente. Esta versão NÃO DEVE (MUST NOT) enviar notificações, NÃO DEVE (MUST NOT) permitir editar uma solicitação enviada e NÃO DEVE (MUST NOT) oferecer cancelamento de agendamento aprovado; o cancelamento fica para uma Change futura.

#### Scenario: Sem notificação
- **WHEN** uma solicitação é criada, aprovada, rejeitada ou recebe alternativa
- **THEN** nenhuma notificação nem e-mail é gerado
