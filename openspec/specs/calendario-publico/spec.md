# calendario-publico Specification

## Purpose
Consulta pública do ensalamento, sem autenticação, na rota `calendario/`: filtros por semestre, sala, docente, curso, nível e datas, a Grade com os dados mínimos de cada aula e o isolamento da área autenticada.
## Requirements
### Requirement: Rota pública do calendário
O sistema DEVE (MUST) oferecer o calendário público na rota `calendario/`, acessível sem autenticação, só pelos métodos GET e HEAD. A rota NÃO DEVE (MUST NOT) usar `login_required`, e a view NÃO DEVE (MUST NOT) declarar `permission_required` nem `audit_resource`. Os demais métodos DEVEM (MUST) ser recusados com 405. Nenhuma permissão nova DEVE (MUST) ser criada para o acesso. O mesmo conteúdo DEVE (MUST) ser entregue a visitantes e a usuários autenticados. A página DEVE (MUST) ter `<meta name="robots" content="noindex">`.

#### Scenario: Visitante abre o calendário
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa `calendario/`
- **THEN** a resposta é 200 com o calendário público
- **AND** ele não é redirecionado para a página de login

#### Scenario: Usuário autenticado vê o mesmo calendário
- **GIVEN** um usuário autenticado sem nenhuma permissão
- **WHEN** ele acessa `calendario/` com os mesmos filtros de um visitante
- **THEN** o conteúdo do calendário é o mesmo entregue ao visitante

#### Scenario: Método de escrita recusado
- **WHEN** um visitante envia POST para `calendario/`
- **THEN** a resposta é 405 e nada é gravado

#### Scenario: Página fora dos buscadores
- **WHEN** a página é aberta
- **THEN** o HTML contém `<meta name="robots" content="noindex">`

### Requirement: Isolamento da área autenticada
O calendário público DEVE (MUST) ter view, formulário, consulta, templates e layout próprios. Ele NÃO DEVE (MUST NOT) herdar nem chamar a view da Grade autenticada, NÃO DEVE (MUST NOT) usar o formulário da Grade, NÃO DEVE (MUST NOT) chamar `occupancy()` nem `grid_sources()` e NÃO DEVE (MUST NOT) ler `request.user`. Nenhuma rota existente DEVE (MUST) perder `login_required` ou `permission_required`. O layout público NÃO DEVE (MUST NOT) conter menu, sidebar, usuário, notificações, modal, token CSRF, nem link, ação ou formulário da área autenticada, exceto o link "Entrar" para a página de login.

#### Scenario: Visitante acessa só a rota pública
- **GIVEN** um visitante não autenticado
- **WHEN** ele acessa `calendario/` e depois `ensalamento/`
- **THEN** `calendario/` responde 200
- **AND** `ensalamento/` redireciona para a página de login com a indicação da página solicitada

#### Scenario: Grade autenticada protegida como antes
- **GIVEN** um usuário autenticado sem `ENSALAMENTO.VISUALIZAR`
- **WHEN** ele acessa `ensalamento/`
- **THEN** a resposta é 403

#### Scenario: Fonte futura de ocupação não aparece
- **GIVEN** uma fonte de ocupação de teste acrescentada a `grid_sources()`, com uma ocorrência na sala 10 numa data do intervalo
- **WHEN** o calendário público da sala 10 é aberto nesse intervalo
- **THEN** a ocorrência dessa fonte não aparece

#### Scenario: Layout sem elementos da área autenticada
- **WHEN** um usuário autenticado abre o calendário público
- **THEN** a página não mostra o menu, o nome do usuário, o perfil, as notificações nem o controle de sair
- **AND** a página não contém token CSRF

### Requirement: Dados expostos no calendário público
Cada aula do calendário público DEVE (MUST) mostrar só a data e o horário (pela posição na Grade), a disciplina, o curso e a turma, a sala pelo nome atual ou "Sem sala definida", os docentes pelo nome e, quando houver, o e-mail de cada docente, e o nível pela cor com o texto para tecnologia assistiva. A página NÃO DEVE (MUST NOT) expor IDs de registro, outros nomes do espaço, origem ou situação do espaço, dados da importação, dados de auditoria, nome civil, perfil, permissões, situação ou qualquer outro dado de usuário além do e-mail do docente, reservas, solicitações, exceções, nem a marca "Choque". Os valores dos filtros na URL e nos campos DEVEM (MUST) ser nomes e códigos, e nunca IDs. A consulta das aulas DEVE (MUST) carregar só as colunas usadas no card.

#### Scenario: Card da aula
- **GIVEN** a alocação de Banco de Dados, Informática 2º ano A, sala 10, docente Aldo Gomes, segunda-feira das 07:00 às 07:50
- **WHEN** o calendário da sala 10 é aberto numa semana do período que contém uma segunda-feira
- **THEN** a célula de segunda-feira das 07:00 às 07:50 mostra "Banco de Dados", "Informática, 2º ano A", "10" e "Aldo Gomes"

#### Scenario: Aula sem sala
- **GIVEN** uma alocação sem espaço do docente Aldo Gomes
- **WHEN** o calendário do docente é aberto numa data dessa aula
- **THEN** o card mostra "Sem sala definida"

#### Scenario: Dados administrativos ausentes
- **GIVEN** a sala 10 criada por uma importação, com o outro nome "Sala Dez", e um registro de auditoria dessa importação
- **WHEN** o calendário da sala 10 é aberto
- **THEN** o HTML não contém "Sala Dez", a origem, a importação, a auditoria, "Choque" nem o ID da sala, do docente, do curso, da turma ou da alocação

### Requirement: Docentes do calendário público
As opções do filtro "Docente" DEVEM (MUST) ser só os docentes do ensalamento (`Teacher`) com alocação no semestre escolhido. As opções NÃO DEVEM (MUST NOT) vir da tabela de usuários, e um usuário que não é docente do ensalamento NÃO DEVE (MUST NOT) aparecer nelas, qualquer que seja o perfil dele. Um docente sem usuário correspondente DEVE (MUST) aparecer nas opções e nos cards, só com o nome. O e-mail de um docente DEVE (MUST) ser exibido só quando existe um usuário ativo cujo `username` corresponde exatamente ao nome do docente, sem diferenciar maiúsculas de minúsculas; a correspondência NÃO DEVE (MUST NOT) ser aproximada, por prefixo ou ignorando acentos. Do usuário correspondente, só o e-mail DEVE (MUST) ser lido e exibido.

#### Scenario: Usuário que não é docente
- **GIVEN** um superadmin e um administrador sem `Teacher` com o nome deles
- **WHEN** as opções do filtro "Docente" são montadas
- **THEN** nenhum dos dois aparece

#### Scenario: Docente com usuário correspondente
- **GIVEN** o docente `Aldo Gomes` e o usuário ativo com `username` `aldo gomes` e e-mail `aldo.gomes@ifnmg.edu.br`
- **WHEN** o calendário do docente é aberto
- **THEN** os cards dele mostram "Aldo Gomes" e "aldo.gomes@ifnmg.edu.br"
- **AND** o nome civil e o perfil desse usuário não aparecem

#### Scenario: Docente sem usuário
- **GIVEN** o docente `Érica` sem usuário com esse `username`
- **WHEN** o calendário dela é aberto
- **THEN** ela aparece nas opções e nos cards só com o nome

#### Scenario: Usuário inativo
- **GIVEN** o docente `Adailton` e o usuário inativo com `username` `Adailton`
- **WHEN** o calendário do docente é aberto
- **THEN** o card mostra só o nome, sem e-mail

### Requirement: Filtros do calendário público
O calendário público DEVE (MUST) aceitar pela URL os filtros `semestre` (código do semestre letivo), `sala` (nome atual do espaço), `docente` (nome do docente), `curso` (nome do curso), `nivel` (`graduacao` ou `ensino-medio`, exibidos como "Graduação" e "Ensino médio"), `inicio` e `fim` (datas `aaaa-mm-dd`). Os filtros DEVEM (MUST) ser combinados por "e" e aplicados na consulta ao banco. O nome informado DEVE (MUST) ser comparado sem diferenciar maiúsculas de minúsculas com as opções carregadas, e só o registro encontrado DEVE (MUST) entrar na consulta. Um valor fora das opções, com mais de 200 caracteres ou fora do formato DEVE (MUST) ser descartado sem mensagem. As opções DEVEM (MUST) ser: os espaços com alocação no semestre, ativos ou inativos, na ordem natural do nome; os docentes com alocação no semestre; os cursos com turma alocada no semestre; os dois níveis que o sistema já tem. As opções NÃO DEVEM (MUST NOT) depender dos demais filtros. O sistema NÃO DEVE (MUST NOT) oferecer filtro pelo período ou ano da turma, nem outros níveis.

#### Scenario: Docente e sala combinados
- **GIVEN** o docente Aldo Gomes com aulas nas salas 10 e 12
- **WHEN** o calendário é aberto com `docente=Aldo Gomes&sala=10`
- **THEN** só as aulas dele na sala 10 aparecem

#### Scenario: Curso e nível incompatíveis
- **GIVEN** o curso Informática, de Ensino médio
- **WHEN** o calendário é aberto com `curso=Informática&nivel=graduacao`
- **THEN** a Grade aparece com as células vazias, sem erro e sem mensagem

#### Scenario: Valor desconhecido descartado
- **WHEN** o calendário é aberto com `sala=Inexistente&docente=Aldo Gomes`
- **THEN** o filtro de sala volta para todas as salas e o calendário mostra as aulas de Aldo Gomes

#### Scenario: Sala inativa com aula
- **GIVEN** a sala 7, inativa, com alocação no semestre `2026/2`
- **WHEN** as opções de sala de `2026/2` são montadas
- **THEN** a sala 7 está entre elas

#### Scenario: Sala inativa sem aula
- **GIVEN** a sala 8, inativa, sem alocação no semestre `2026/2`
- **WHEN** as opções de sala de `2026/2` são montadas
- **THEN** a sala 8 não está entre elas

#### Scenario: Curso sem aula fora das opções
- **GIVEN** um curso sem turma alocada no semestre `2026/2`
- **WHEN** as opções de curso de `2026/2` são montadas
- **THEN** esse curso não está entre elas

### Requirement: Filtro principal obrigatório
As aulas só DEVEM (MUST) ser consultadas quando há uma sala, um docente ou um curso válido nos filtros. Sem nenhum deles, a página DEVE (MUST) mostrar "Escolha uma sala, um docente ou um curso." e NÃO DEVE (MUST NOT) consultar faixas, aulas nem e-mails, mesmo com semestre, nível e datas informados.

#### Scenario: Primeira visita
- **WHEN** um visitante abre `calendario/` sem parâmetros
- **THEN** a página mostra os filtros e "Escolha uma sala, um docente ou um curso."
- **AND** nenhuma alocação é consultada

#### Scenario: Nível sozinho
- **WHEN** o calendário é aberto com `nivel=ensino-medio&inicio=2026-09-21&fim=2026-09-25`
- **THEN** a página mostra "Escolha uma sala, um docente ou um curso." e nenhuma alocação é consultada

### Requirement: Semestre do calendário público
O filtro `semestre` DEVE (MUST) representar o semestre letivo (`Semester`) e oferecer o semestre atual, calculado pela data, e os semestres com alocação confirmada, do mais recente ao mais antigo. Sem o parâmetro, ou com um código desconhecido, o semestre DEVE (MUST) ser o atual. Um semestre sem alocação DEVE (MUST) mostrar "Nenhum horário publicado no semestre 2027/1.". Um semestre sem período DEVE (MUST) mostrar a semana típica, sem datas, com "Datas do semestre 2026/2 ainda não definidas. O calendário mostra a semana típica.", com os campos de data desabilitados e as datas da URL ignoradas.

#### Scenario: Semestre padrão
- **GIVEN** a data de hoje 25/09/2026 e o semestre `2026/2` importado
- **WHEN** o calendário é aberto sem `semestre`
- **THEN** o semestre escolhido é `2026/2`

#### Scenario: Semestre sem aulas
- **WHEN** o calendário é aberto com `semestre=2027/1`, sem alocação
- **THEN** a página mostra "Nenhum horário publicado no semestre 2027/1."

#### Scenario: Semestre sem período
- **GIVEN** o semestre `2026/2` com alocações e sem período
- **WHEN** o calendário da sala 10 é aberto com `inicio=2026-09-21&fim=2026-09-25`
- **THEN** a página mostra a semana típica, sem datas, com o aviso do período não definido

### Requirement: Datas do calendário público
A data inicial e a data final DEVEM (MUST) ser informadas juntas. Na primeira visita, sem datas na URL, o formulário DEVE (MUST) vir preenchido com a segunda e a sexta-feira da semana de hoje, levada para dentro do período do semestre, e essas datas DEVEM (MUST) ser usadas. Com só uma data na URL, a página DEVE (MUST) mostrar "Informe a data inicial e a data final."; com data em formato inválido, "Informe uma data válida."; com a data final antes da inicial, "A data final deve ser igual ou posterior à data inicial."; com mais de 31 dias corridos entre as duas, "Escolha um intervalo de até 31 dias.". Na recusa, as aulas NÃO DEVEM (MUST NOT) ser consultadas. As colunas DEVEM (MUST) ser só os dias de segunda a sexta do intervalo, e o dia fora do período do semestre DEVE (MUST) aparecer como "Fora do semestre". Com o intervalo inteiro fora do período, a página DEVE (MUST) mostrar "O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026." e NÃO DEVE (MUST NOT) consultar aulas. A troca de intervalo DEVE (MUST) ser feita só pelos campos de data; a página NÃO DEVE (MUST NOT) ter botões de navegação entre intervalos.

#### Scenario: Intervalo padrão
- **GIVEN** a data de hoje quarta-feira, 23/09/2026, dentro do período de `2026/2`
- **WHEN** o calendário da sala 10 é aberto sem datas
- **THEN** as datas preenchidas são 21/09/2026 e 25/09/2026 e as colunas vão de 21/09/2026 a 25/09/2026

#### Scenario: Só uma data
- **WHEN** o calendário da sala 10 é aberto com `inicio=2026-09-21`
- **THEN** a página mostra "Informe a data inicial e a data final." e nenhuma alocação é consultada

#### Scenario: Data inválida
- **WHEN** o calendário da sala 10 é aberto com `inicio=2026-02-30&fim=2026-03-05`
- **THEN** a página mostra "Informe uma data válida." e nenhuma alocação é consultada

#### Scenario: Data final antes da inicial
- **WHEN** o calendário da sala 10 é aberto com `inicio=2026-09-25&fim=2026-09-21`
- **THEN** a página mostra "A data final deve ser igual ou posterior à data inicial."

#### Scenario: Intervalo acima do limite
- **WHEN** o calendário da sala 10 é aberto com `inicio=2026-09-01&fim=2026-10-15`
- **THEN** a página mostra "Escolha um intervalo de até 31 dias." e nenhuma alocação é consultada

#### Scenario: Intervalo fora do semestre
- **GIVEN** o semestre `2026/2` com o período de 01/06/2026 a 23/12/2026
- **WHEN** o calendário da sala 10 é aberto com `inicio=2027-02-01&fim=2027-02-05`
- **THEN** a página mostra "O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026." e nenhuma alocação é consultada

#### Scenario: Sem botões de navegação
- **WHEN** o calendário da sala 10 é aberto de 14/09/2026 a 25/09/2026
- **THEN** a página não mostra os botões "Anterior", "Hoje" e "Próximo"

#### Scenario: Fim de semana fora das colunas
- **WHEN** o calendário é aberto com `inicio=2026-09-21&fim=2026-09-27`
- **THEN** as colunas são de segunda-feira, 21/09/2026, a sexta-feira, 25/09/2026

### Requirement: Montagem do calendário público
O calendário DEVE (MUST) ser montado com a estrutura da Grade: nas linhas, as faixas do semestre da primeira à última aula mostrada no intervalo, com as vazias do meio, ou todas as faixas do semestre quando o intervalo não tem aula, dias nas colunas, faixas seguidas com as mesmas aulas unidas num bloco e "Hoje" marcado. As aulas da mesma faixa e do mesmo dia DEVEM (MUST) ficar na mesma célula, ordenadas pela sala, pelo curso e pela turma, cada uma com a sua sala. "N turmas juntas" DEVE (MUST) ser indicado só quando as aulas têm a mesma sala, a mesma disciplina e os mesmos docentes. A marca "Choque" NÃO DEVE (MUST NOT) aparecer. A faixa sem aula DEVE (MUST) ser anunciada à tecnologia assistiva como "disponível" só quando o único filtro principal é a sala; nos demais casos, como "sem aula".

#### Scenario: Turmas em salas diferentes no mesmo horário
- **GIVEN** a turma A na sala 1 e a turma B na sala 2 do curso Informática, com disciplinas diferentes, na mesma faixa
- **WHEN** o calendário do curso Informática é aberto
- **THEN** as duas aulas aparecem na mesma célula, cada uma com a sua sala, sem marca de choque nem de turmas juntas

#### Scenario: Turmas juntas na mesma sala
- **GIVEN** duas turmas de Licenciatura em Física com a mesma disciplina, os mesmos docentes e a mesma sala, na mesma faixa
- **WHEN** o calendário do curso é aberto
- **THEN** a célula mostra "2 turmas juntas"

#### Scenario: Linhas só até a última aula do resultado
- **GIVEN** o curso Informática com aulas até 17:00 e outros cursos com aulas até 22:40
- **WHEN** o calendário do curso Informática é aberto
- **THEN** a última linha da Grade é a faixa que termina às 17:00

#### Scenario: Faixa vazia na consulta por docente
- **WHEN** o calendário do docente Aldo Gomes é aberto e uma faixa de segunda-feira não tem aula dele
- **THEN** o texto para tecnologia assistiva da faixa diz "sem aula", e não "disponível"

### Requirement: Estados vazios do calendário público
Com o filtro principal válido e as datas aceitas, quando não há aula no intervalo, a página DEVE (MUST) mostrar só a Grade do intervalo com as células vazias e todas as faixas do semestre, sem mensagem de resultado vazio: o vazio indica que os horários estão disponíveis. Sem filtro principal, com data recusada ou com o intervalo fora do semestre, a Grade NÃO DEVE (MUST NOT) aparecer, e a página DEVE (MUST) mostrar a mensagem do caso. Os textos NÃO DEVEM (MUST NOT) ter frase motivacional. Durante a atualização pelo htmx, o calendário DEVE (MUST) ter `aria-busy="true"` e o botão "Mostrar" DEVE (MUST) ficar desabilitado, sem skeleton e sem spinner.

#### Scenario: Docente sem aulas no intervalo
- **GIVEN** o docente Aldo Gomes sem aulas às sextas-feiras
- **WHEN** o calendário dele é aberto com `inicio=2026-09-25&fim=2026-09-25`
- **THEN** a Grade de 25/09/2026 aparece com todas as faixas do semestre e as células vazias
- **AND** a página não mostra mensagem de resultado vazio

#### Scenario: Sala sem aulas no intervalo
- **GIVEN** a sala 7, inativa, com aulas no semestre e nenhuma de 21/09/2026 a 24/09/2026
- **WHEN** o calendário dela é aberto nesse intervalo
- **THEN** a Grade aparece com as células vazias, anunciadas como "disponível"

#### Scenario: Sem filtro principal
- **WHEN** o calendário é aberto sem sala, docente ou curso
- **THEN** a página mostra "Escolha uma sala, um docente ou um curso." e não mostra a Grade

### Requirement: Calendário público no celular
A página DEVE (MUST) usar a mesma Grade em qualquer largura e NÃO DEVE (MUST NOT) ter uma representação do calendário só para o celular. O cabeçalho DEVE (MUST) ser uma barra única e discreta, com a marca "SaliSpace" e o link "Entrar", discreto e com borda verde clara, sem outro conteúdo. O cabeçalho, os filtros e o calendário DEVEM (MUST) ficar centralizados, com a largura máxima das páginas do sistema. Os filtros DEVEM (MUST) ficar num card com a mesma borda do calendário, sem título visível e sem linha de resumo. Abaixo de 640 px, os filtros DEVEM (MUST) ficar empilhados na largura toda, com a data inicial e a final lado a lado. Valores longos DEVEM (MUST) ser cortados com reticências dentro do próprio campo, sem alargar a coluna nem a página, e a lista de opções aberta DEVE (MUST) aparecer inteira, sem ser cortada pelo card. Os controles DEVEM (MUST) ter alvo de toque de pelo menos 44x44 px, as datas DEVEM (MUST) usar o seletor nativo, e Sala, Docente e Curso DEVEM (MUST) usar o campo de seleção com busca. A Grade DEVE (MUST) rolar na horizontal só dentro da própria área, rotulada e focável, com a coluna de horários e a linha dos dias fixas, e a página NÃO DEVE (MUST NOT) rolar na horizontal a partir de 360 px. Abaixo de 640 px, a coluna de dia DEVE (MUST) ter largura mínima que mantenha o card legível, e a área DEVE (MUST) abrir rolada até "Hoje" quando ele está no intervalo.

#### Scenario: Celular com três semanas
- **GIVEN** uma tela de 360 px
- **WHEN** o calendário da sala 10 é aberto de 14/09/2026 a 02/10/2026
- **THEN** o calendário é a Grade com 15 dias, rolando na horizontal só dentro da própria área
- **AND** a página não rola na horizontal

#### Scenario: Lista de opções inteira
- **WHEN** o campo "Docente" é aberto
- **THEN** a lista de opções aparece inteira sobre o calendário, sem ser cortada pelo card de filtros

### Requirement: Desempenho do calendário público
Uma requisição do calendário público DEVE (MUST) usar no máximo 8 consultas ao banco: semestres, salas, docentes e cursos das opções, faixas do semestre, aulas filtradas, docentes das aulas e e-mails desses docentes. A quantidade NÃO DEVE (MUST NOT) crescer com o número de dias do intervalo, de aulas, de docentes ou de células, e NÃO DEVE (MUST NOT) haver consulta por dia, por célula ou por aula. Os filtros DEVEM (MUST) ser aplicados no banco, e as aulas NÃO DEVEM (MUST NOT) ser carregadas sem filtro para serem filtradas em Python. A consulta dos e-mails DEVE (MUST) receber só os nomes dos docentes das aulas encontradas. A página NÃO DEVE (MUST NOT) gravar sessão, cookie, auditoria ou qualquer registro.

#### Scenario: Consultas iguais numa semana e em 31 dias
- **GIVEN** o docente Aldo Gomes com aulas em várias salas
- **WHEN** o calendário dele é aberto numa semana e depois em 31 dias
- **THEN** as duas requisições usam a mesma quantidade de consultas, no máximo 8

#### Scenario: Sem filtro principal
- **WHEN** o calendário é aberto sem sala, docente ou curso
- **THEN** a requisição usa no máximo 4 consultas, nenhuma delas de alocação

#### Scenario: Página sem gravação
- **WHEN** um visitante abre o calendário da sala 10
- **THEN** nenhum registro de auditoria é criado e a resposta não define cookie

