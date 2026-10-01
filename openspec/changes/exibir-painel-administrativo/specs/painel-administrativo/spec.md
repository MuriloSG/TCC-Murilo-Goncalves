## ADDED Requirements

### Requirement: Rota e composição do painel
O sistema DEVE (MUST) oferecer o painel na rota autenticada `painel/`, com `login_required` na URL e `permission_required = PAINEL.VISUALIZAR` na view. O painel DEVE (MUST) mostrar somente os blocos cujas permissões de módulo o usuário tem, conforme o requisito "Blocos condicionados à permissão do módulo", e NÃO DEVE (MUST NOT) calcular os dados de um bloco que não mostra. Quando nenhum bloco é liberado, o painel DEVE (MUST) mostrar o texto "Nenhum indicador liberado para o seu perfil." O painel NÃO DEVE (MUST NOT) executar nenhuma ação: os links levam às telas que já executam cada uma, com as permissões delas.

#### Scenario: Painel com todos os blocos
- **GIVEN** um usuário com `PAINEL.VISUALIZAR`, `AGENDA.ANALISAR`, `AGENDA.VISUALIZAR`, `ENSALAMENTO.VISUALIZAR` e `ENSALAMENTO.IMPORTAR`
- **WHEN** ele abre `painel/`
- **THEN** a resposta é 200 com os blocos "Solicitações para decidir", "Ocupação dos espaços", "Pendências da grade" e "Importações sem conclusão"

#### Scenario: Painel sem blocos liberados
- **GIVEN** um usuário com `PAINEL.VISUALIZAR` e nenhuma das permissões de módulo
- **WHEN** ele abre `painel/`
- **THEN** a resposta é 200 com o texto "Nenhum indicador liberado para o seu perfil."

#### Scenario: Painel não altera dados
- **GIVEN** uma solicitação pendente
- **WHEN** um usuário abre o painel
- **THEN** a solicitação continua pendente e nenhum registro é criado

### Requirement: Blocos condicionados à permissão do módulo
Cada bloco DEVE (MUST) exigir, além de `PAINEL.VISUALIZAR`, a permissão do módulo dono dos dados: "Solicitações para decidir" exige `AGENDA.ANALISAR`; "Ocupação dos espaços" e "Pendências da grade" exigem `ENSALAMENTO.VISUALIZAR`; o item "Agendamentos em choque com aula" exige também `AGENDA.VISUALIZAR`; "Importações sem conclusão" exige `ENSALAMENTO.IMPORTAR`. A decisão DEVE (MUST) usar só `User.has_perm`. Cada link DEVE (MUST) aparecer somente quando o usuário tem a permissão da rota de destino.

#### Scenario: Sem análise da Agenda, sem solicitações
- **GIVEN** um usuário com `PAINEL.VISUALIZAR` e `ENSALAMENTO.VISUALIZAR`, sem `AGENDA.ANALISAR`
- **WHEN** ele abre o painel
- **THEN** o bloco "Solicitações para decidir" não aparece e nenhuma contagem de solicitação aparece na página

#### Scenario: Sem importar, sem importações
- **GIVEN** um usuário sem `ENSALAMENTO.IMPORTAR`
- **WHEN** ele abre o painel
- **THEN** o bloco "Importações sem conclusão" não aparece

#### Scenario: Superadmin vê todos os blocos
- **GIVEN** um superadmin ativo cujo perfil não concede nenhuma das permissões
- **WHEN** ele abre o painel
- **THEN** todos os blocos aparecem, pela regra geral de `User.has_perm`

### Requirement: Recortes de tempo e filtro de semestre
O painel DEVE (MUST) oferecer o filtro `semestre` com os semestres de `imported_semesters()`. O padrão DEVE (MUST) ser o semestre de código `current_semester_code(hoje)` quando ele está entre as opções, e o mais recente quando não está. Um valor que não é opção DEVE (MUST) ser ignorado, valendo o padrão. Os campos `semestre` e `ocupacao` DEVEM (MUST) ser campos de um formulário renderizado pelo renderizador do projeto, com o componente `ui/components/select.html`, e NÃO DEVEM (MUST NOT) ser montados à mão no template. A troca de qualquer um deles DEVE (MUST) manter o valor do outro. O filtro DEVE (MUST) valer só para "Pendências da grade". "Hoje" DEVE (MUST) ser a data local e "Semana atual" DEVE (MUST) ser de segunda a domingo da semana de hoje, sem depender do filtro. O título de cada bloco DEVE (MUST) dizer o recorte, com as datas no formato dd/mm/aaaa. Sem semestre importado, os blocos acadêmicos DEVEM (MUST) mostrar "Nenhum semestre importado." e o link para as importações a quem tem `ENSALAMENTO.IMPORTAR`.

#### Scenario: Semestre do dia como padrão
- **GIVEN** hoje é 01/10/2026 e existem os semestres importados `2026/1` e `2026/2`
- **WHEN** o painel é aberto sem filtro
- **THEN** as pendências da grade são de `2026/2`

#### Scenario: Semestre do dia ainda não importado
- **GIVEN** hoje é 01/10/2026 e só existe o semestre importado `2026/1`
- **WHEN** o painel é aberto sem filtro
- **THEN** as pendências da grade são de `2026/1`, com o código no título

#### Scenario: Filtro não muda a ocupação de hoje
- **GIVEN** hoje é 01/10/2026, dentro do período de `2026/2`
- **WHEN** o painel é aberto com `semestre=2026/1`
- **THEN** a ocupação de hoje continua sendo a de 01/10/2026

#### Scenario: Valor inválido no filtro
- **WHEN** o painel é aberto com `semestre=1999/9`
- **THEN** o painel usa o semestre padrão, sem erro

### Requirement: Solicitações para decidir
O bloco DEVE (MUST) mostrar três contagens feitas no banco: "Solicitações pendentes", as solicitações com `status=PENDENTE`; "Pendentes com horário passado", as pendentes cuja data e início, no fuso do campus, não são posteriores ao momento atual; e "Alternativas aguardando resposta", as solicitações com `status=ALTERNATIVA_SUGERIDA`. O bloco DEVE (MUST) listar no máximo cinco solicitações pendentes com início posterior ao momento atual, em ordem de data, início e criação, com o espaço, a data, o horário "das HH:MM às HH:MM", o solicitante e há quantos dias foi criada. Cada linha DEVE (MUST) levar a `agenda_review_detail`, e o bloco DEVE (MUST) ter o link para `agenda_review_list`. Estados aprovada, rejeitada e alternativa recusada NÃO DEVEM (MUST NOT) entrar em nenhuma das contagens.

As pendentes com horário passado DEVEM (MUST) aparecer como selo "N vencidas" no cartão de pendentes, e não como cartão próprio. Os rótulos dos cartões DEVEM (MUST) ser curtos: "Solicitações pendentes", "Aguardando resposta", "Aulas sem espaço" e "Importações abertas". O cartão inteiro DEVE (MUST) ser o link para a tela de destino.

#### Scenario: Contagens por estado
- **GIVEN** 3 solicitações pendentes, 1 com alternativa sugerida, 2 aprovadas e 1 rejeitada
- **WHEN** o painel é aberto
- **THEN** "Solicitações pendentes" mostra 3 e "Aguardando resposta" mostra 1

#### Scenario: Pendente com horário passado
- **GIVEN** agora é 01/10/2026 às 10:00 e há uma pendente para 01/10/2026 das 08:00 às 09:00 e outra para 02/10/2026 das 08:00 às 09:00
- **WHEN** o painel é aberto
- **THEN** o cartão de pendentes mostra o selo "1 vencidas" e a lista mostra só a de 02/10/2026

#### Scenario: Ordem pela proximidade
- **GIVEN** pendentes para 05/10/2026, 02/10/2026 e 03/10/2026, todas futuras
- **WHEN** o painel é aberto
- **THEN** a lista mostra 02/10/2026, 03/10/2026 e 05/10/2026, nessa ordem

#### Scenario: Limite da lista
- **GIVEN** 8 pendentes futuras
- **WHEN** o painel é aberto
- **THEN** a lista tem 5 linhas e "Solicitações pendentes" mostra 8

#### Scenario: Nenhuma pendente
- **GIVEN** nenhuma solicitação pendente
- **WHEN** o painel é aberto
- **THEN** o bloco mostra "Nenhuma solicitação pendente." e as contagens mostram 0

### Requirement: Ocupação dos espaços
O bloco DEVE (MUST) oferecer a escolha entre "Hoje" e "Semana" por um campo de seleção junto dos filtros, com "Hoje" como padrão, e a troca DEVE (MUST) manter o filtro de semestre. Para o período escolhido, o bloco DEVE (MUST) listar, por espaço, as horas ocupadas, a quantidade de aulas e a quantidade de agendamentos.

A ocorrência de aula DEVE (MUST) seguir a regra de `Allocation.occurs_on`, sem as ocorrências canceladas, em todos os semestres cujo período contém a data. O agendamento DEVE (MUST) ser todo `Booking` com intervalo na data. As horas ocupadas DEVEM (MUST) ser a soma da união dos intervalos de aulas e agendamentos do espaço em cada data: intervalos sobrepostos, inclusive a aula compartilhada por turmas, contam uma vez. A quantidade de aulas DEVE (MUST) contar uma vez as alocações de mesmo espaço, data e faixa. O bloco NÃO DEVE (MUST NOT) mostrar percentual de ocupação.

A lista DEVE (MUST) ter no máximo os dez espaços com mais horas, entre os que têm alguma ocupação, em ordem decrescente de horas e, no empate, pela ordem natural do nome. Os espaços ativos sem nenhuma ocorrência no período DEVEM (MUST) aparecer como o bloco "Sem ocupação" das pendências da grade, e não na lista de ocupação. Aula sem espaço NÃO DEVE (MUST NOT) entrar na ocupação. Cada espaço DEVE (MUST) levar à Grade do Ensalamento do espaço na data ou na semana.

A lista DEVE (MUST) ser mostrada como barras horizontais em horas, uma por espaço, com o segmento de aulas e o de agendamentos fora de aula em cores diferentes, as horas e as contagens em texto e a descrição da barra para a tecnologia assistiva. A soma dos segmentos DEVE (MUST) ser igual às horas exibidas: o trecho de agendamento sobreposto a aula entra uma vez, no segmento de aulas. No modo Semana, o bloco DEVE (MUST) mostrar também as horas ocupadas por dia, de segunda a domingo, em colunas com a mesma divisão, em que cada dia é a soma das horas dos espaços nele. O eixo dos gráficos DEVE (MUST) ser em horas.

Quando hoje, ou nenhuma data da semana, está no período de algum semestre, o bloco DEVE (MUST) mostrar "Nenhum semestre em andamento nesta data." acima dos agendamentos, que continuam listados. Quando o semestre de hoje existe sem período, o bloco DEVE (MUST) mostrar "O semestre 2026/2 não tem período definido. Defina o período na importação do ensalamento." com o código real.

#### Scenario: Aula compartilhada conta uma vez
- **GIVEN** hoje é segunda-feira, 05/10/2026, e duas turmas têm aula na sala 1/3 das 10:00 às 12:00
- **WHEN** a ocupação de hoje é calculada
- **THEN** a sala 1/3 tem 2 horas e 1 aula

#### Scenario: Ocorrência cancelada não conta
- **GIVEN** a aula da sala 1/3 de 05/10/2026 das 10:00 às 12:00 está cancelada
- **WHEN** a ocupação de hoje é calculada para 05/10/2026
- **THEN** a sala 1/3 não tem essa aula nem essas horas

#### Scenario: Agendamento sobre aula não soma duas vezes
- **GIVEN** na sala 1/3, em 05/10/2026, uma aula das 10:00 às 12:00 e um agendamento das 11:00 às 13:00
- **WHEN** a ocupação de hoje é calculada
- **THEN** a sala 1/3 tem 3 horas, 1 aula e 1 agendamento

#### Scenario: Aula encerrada não conta depois do fim
- **GIVEN** uma aula das segundas encerrada a partir de 05/10/2026
- **WHEN** a ocupação da semana de 05/10/2026 é calculada
- **THEN** essa aula não entra

#### Scenario: Segmentos somam o total
- **GIVEN** na sala 1/3, em 05/10/2026, uma aula das 10:00 às 12:00 e um agendamento das 11:00 às 13:00
- **WHEN** a ocupação de hoje é exibida
- **THEN** a barra da sala 1/3 tem 2 horas no segmento de aulas e 1 hora no de agendamentos, e o texto mostra 3 h

#### Scenario: Horas por dia na semana
- **GIVEN** na semana de 05/10/2026, a sala 1/3 com 2 horas na segunda e o auditório com 3 horas na segunda
- **WHEN** a ocupação da semana é exibida
- **THEN** a coluna de segunda mostra 5 h, e a de domingo mostra 0 h

#### Scenario: Só os dez mais ocupados
- **GIVEN** 12 espaços com aulas hoje
- **WHEN** a ocupação de hoje é calculada
- **THEN** a lista tem os 10 espaços com mais horas

#### Scenario: Espaço ativo sem ocupação
- **GIVEN** a sala 2/1 está ativa e não tem aula nem agendamento na semana
- **WHEN** a ocupação da semana é calculada
- **THEN** a sala 2/1 aparece em "Sem ocupação" e não aparece na lista ordenada

#### Scenario: Espaço inativo sem ocupação
- **GIVEN** a sala 9/9 está desativada e não tem aula
- **WHEN** a ocupação da semana é calculada
- **THEN** a sala 9/9 não aparece em nenhuma lista

#### Scenario: Fim de semana
- **GIVEN** hoje é sábado e há um agendamento hoje no auditório
- **WHEN** a ocupação de hoje é calculada
- **THEN** o auditório aparece com o agendamento e nenhuma aula é contada

#### Scenario: Semestre sem período
- **GIVEN** o semestre `2026/2` foi importado sem período
- **WHEN** a ocupação de hoje é calculada
- **THEN** o bloco mostra o aviso de período não definido de `2026/2`

#### Scenario: Consultas em número fixo
- **GIVEN** 5 espaços com aulas e, depois, 40 espaços com aulas
- **WHEN** a ocupação da semana é calculada nos dois casos
- **THEN** a quantidade de consultas ao banco é a mesma

### Requirement: Pendências da grade
O bloco DEVE (MUST) considerar as alocações vigentes do semestre escolhido: `valid_until` vazio ou igual ou posterior a hoje, e sem `valid_until` anterior a `valid_from`. Ele DEVE (MUST) mostrar, contando uma vez as alocações de mesma turma, disciplina, dia e faixa:

- "Aulas sem espaço": alocações com `space` vazio;
- "Aulas sem docente": alocações sem nenhum docente;
- "Possíveis conflitos de docente": pares de alocações com o mesmo docente, o mesmo dia da semana, faixas sobrepostas pela regra semiaberta, vigências que se cruzam e espaços diferentes, ou um deles vazio. Alocações no mesmo espaço, dia e faixa NÃO DEVEM (MUST NOT) ser conflito.

Cada item DEVE (MUST) listar no máximo cinco ocorrências, com turma, disciplina, dia e horário, e o link para a Grade do Ensalamento quando houver espaço. O texto do conflito DEVE (MUST) dizer "possível conflito". O bloco DEVE (MUST) mostrar ainda "Agendamentos em choque com aula", a quem tem `AGENDA.VISUALIZAR`: agendamentos com início posterior ao momento atual e até o fim do período do semestre escolhido, sobrepostos a uma ocorrência ativa de aula no mesmo espaço e data, com o link para a Agenda do espaço na data. As aulas sem espaço DEVEM (MUST) aparecer só no cartão "Aulas sem espaço" do topo, que abre a lista no mesmo modal, e não como bloco das pendências. As demais pendências DEVEM (MUST) aparecer como bloco com ícone, contagem e rótulo, com a contagem 0 em cinza e o ícone de confirmação, e o bloco inteiro DEVE (MUST) abrir os itens num modal carregado pelo htmx, na rota `painel/pendencias/<chave>/`, com os filtros do painel na URL, cinco itens por página numa tabela de duas colunas (descrição e botão de ação que leva à Grade ou à Agenda do espaço) e a troca de página dentro do modal, sem mudar o endereço da página. Sem o htmx, a mesma rota DEVE (MUST) mostrar a página completa. A rota DEVE (MUST) exigir `PAINEL.VISUALIZAR` e `ENSALAMENTO.VISUALIZAR`, e o bloco de agendamentos em choque também `AGENDA.VISUALIZAR`; uma chave desconhecida DEVE (MUST) responder 404. Com a contagem 0, o modal DEVE (MUST) mostrar "Nenhuma pendência de 2026/2." ou, no bloco "Sem ocupação", "Todos os espaços ativos têm ocupação no período."

#### Scenario: Itens em modal paginado
- **GIVEN** 12 espaços ativos sem ocupação hoje
- **WHEN** o bloco "Sem ocupação" é acionado
- **THEN** o modal abre com 5 espaços, a página 2 mostra os 5 seguintes e a página 3 os outros 2, sem sair do painel

#### Scenario: Aula sem espaço
- **GIVEN** no semestre `2026/2`, uma aula vigente de `Química Orgânica` sem espaço
- **WHEN** o painel é aberto com `semestre=2026/2`
- **THEN** "Aulas sem espaço" mostra 1 e lista a aula

#### Scenario: Versão encerrada não é pendência
- **GIVEN** uma alocação sem espaço com `valid_until` em 30/09/2026 e hoje é 01/10/2026
- **WHEN** o painel é aberto
- **THEN** ela não entra em "Aulas sem espaço"

#### Scenario: Aula com duas faixas conta uma vez por faixa e dia
- **GIVEN** uma turma com a mesma disciplina sem docente na segunda, em duas faixas
- **WHEN** o painel é aberto
- **THEN** "Aulas sem docente" mostra 2

#### Scenario: Docente em dois espaços ao mesmo tempo
- **GIVEN** o docente Ana Souza na sala 1/3 e no laboratório 2 às segundas das 10:00 às 12:00, ambas vigentes
- **WHEN** o painel é aberto
- **THEN** "Possíveis conflitos de docente" mostra 1

#### Scenario: Aula compartilhada não é conflito
- **GIVEN** o docente Ana Souza com duas turmas na sala 1/3 às segundas das 10:00 às 12:00
- **WHEN** o painel é aberto
- **THEN** "Possíveis conflitos de docente" mostra 0

#### Scenario: Faixas encostadas não são conflito
- **GIVEN** o mesmo docente das 10:00 às 11:00 numa sala e das 11:00 às 12:00 em outra
- **WHEN** o painel é aberto
- **THEN** não há possível conflito

#### Scenario: Vigências que não se cruzam
- **GIVEN** o mesmo docente em duas salas no mesmo horário, uma versão até 04/10/2026 e outra a partir de 05/10/2026
- **WHEN** o painel é aberto
- **THEN** não há possível conflito

#### Scenario: Agendamento em choque
- **GIVEN** um agendamento futuro na sala 1/3 em 12/10/2026 das 10:00 às 11:00 e, depois dele, uma importação que pôs aula na sala 1/3 às segundas das 10:00 às 12:00
- **WHEN** o painel é aberto
- **THEN** "Agendamentos em choque com aula" lista esse agendamento

### Requirement: Importações sem conclusão
O bloco DEVE (MUST) contar e listar as importações com `kind='ENSALAMENTO'` e situação `VALIDADA`, `PENDENTE` ou `COM_ERROS`, das mais antigas para as mais recentes, no máximo cinco, com o arquivo, a situação com o rótulo do model e a data de envio, cada uma levando a `space_allocation_import_detail`. Importações de usuários NÃO DEVEM (MUST NOT) entrar. O cartão "Importações abertas" DEVE (MUST) mostrar a contagem, inclusive 0, e a lista DEVE (MUST) aparecer só quando houver alguma.

#### Scenario: Importação parada
- **GIVEN** uma importação do ensalamento com situação "Precisa de decisão" e outra concluída
- **WHEN** o painel é aberto
- **THEN** o bloco mostra 1 importação, a que precisa de decisão

#### Scenario: Importação de usuários fora
- **GIVEN** uma importação de usuários com erros
- **WHEN** o painel é aberto
- **THEN** ela não aparece no bloco

### Requirement: Texto e visual do painel
Todo texto do painel DEVE (MUST) seguir as regras de texto da interface, com os termos do glossário ("solicitação de agendamento", "agendamento", "pendente", "ocupado", "espaço"). Números DEVEM (MUST) usar o formato da localização do projeto, e horas com fração DEVEM (MUST) aparecer com vírgula decimal (1,5 h). Estado NÃO DEVE (MUST NOT) ser indicado só pela cor. Cartão de contagem com zero DEVE (MUST) mostrar o número 0, e não esconder o cartão. Abaixo de 640 px, as tabelas DEVEM (MUST) virar blocos de rótulo e valor, e a página NÃO DEVE (MUST NOT) rolar na horizontal.

#### Scenario: Página passa nas verificações da interface
- **WHEN** os testes de texto, de classes e de contraste do app `ui` rodam
- **THEN** o template do painel passa em todos
