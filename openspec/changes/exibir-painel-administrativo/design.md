## Context

O painel reúne dados que já existem em três apps:

| Dado | Model e campos | Observações que afetam o cálculo |
|---|---|---|
| Semestre | `schedule.Semester` (`code`, `start_date`, `end_date`) | O período é opcional. Sem ele, a alocação não vira ocorrência datada. |
| Faixa de horário | `schedule.TimeSlot` (`semester`, `start_time`, `end_time`) | Única por semestre e par início/fim. Duas faixas podem se sobrepor. |
| Aula | `schedule.Allocation` (`semester`, `class_group`, `subject`, `space` opcional, `teachers` M2M, `weekday` de segunda a sexta, `time_slot`, `valid_from`, `valid_until`) | Duas alocações no mesmo espaço, dia e faixa são a aula compartilhada, e não conflito. A vigência vazia vale o semestre inteiro. Encerramento e alteração criam versões com vigência. |
| Ocorrência cancelada | `schedule.AllocationException` (`allocation`, `date`, `kind=CANCELADA`) | O único tipo é o cancelamento. `Allocation.objects.active_on(day)` já exclui a ocorrência cancelada. |
| Oferta e vínculo docente | `schedule.ClassOffering`, `schedule.TeachingAssignment` (`is_current`) | A oferta nasce da alocação. Não existe oferta sem aula de origem. |
| Espaço | `schedule.Space` (`name`, `is_active`) | Sem capacidade, tipo, prédio nem horário de funcionamento. |
| Solicitação de agendamento | `bookings.BookingRequest` (`status`, `space`, `date`, `start_time`, `end_time`, `created_at`, `decided_at`, `responded_at`, `suggested_*`) | Estados `PENDENTE`, `APROVADA`, `REJEITADA`, `ALTERNATIVA_SUGERIDA`, `ALTERNATIVA_RECUSADA`. Abertas: `BookingRequest.OPEN`. A aprovação recusa horário passado (`check_slot`). Não há expiração automática. |
| Agendamento | `bookings.Booking` (`space`, `starts_at`, `ends_at`) | Criado na aprovação ou no aceite. Não tem estado nem cancelamento: todo agendamento existente vale. Não se sobrepõe a outro agendamento do mesmo espaço (`ExclusionConstraint`). |
| Importação | `imports.Import` (`kind`, `status`, `created_at`, `resolved_at`) | `kind='ENSALAMENTO'` para a grade. Abertas: `VALIDADA`, `PENDENTE`, `COM_ERROS`. |

Consultas reaproveitadas: `Allocation.objects.active_on`, `AllocationException.objects.cancelled`, `Allocation.occurs_on`, `imported_semesters`, `current_semester_code`, `monday_of`, `listed_spaces`, `natural_key`, `bookings.occupancy.allocation_conflict` (como referência da regra de sobreposição semiaberta), `BookingRequest.OPEN`.

Telas de destino dos links: `agenda_review_list`, `agenda_review_detail`, `agenda_grid`, `space_allocation_grid`, `space_allocation_import_list`, `space_allocation_import_detail`.

Controle de acesso: `login_required` na URL, `permission_required` na view, verificação pelo `PermissionMiddleware` e `User.has_perm` como único ponto de decisão. A página inicial (`HomeView`) redireciona ao primeiro item do `MENU` liberado.

## Goals / Non-Goals

**Goals:**

- Mostrar, numa tela, o que pede ação do administrador: solicitações para decidir, aulas incompletas, possíveis conflitos, importações paradas.
- Mostrar onde há ocupação e onde há espaço sem uso, hoje e na semana, sem percentual e sem contar duas vezes o mesmo intervalo.
- Usar só dados que existem, com consultas em número fixo, independente da quantidade de espaços.

**Non-Goals:**

- Medir uso real dos espaços. Aula programada e agendamento aprovado não comprovam que o espaço foi usado.
- Taxa de ocupação, adequação à capacidade e análise por tipo de espaço ou prédio: os dados não existem.
- Executar decisões no painel.

## Avaliação dos indicadores

Legenda de prioridade: **V1** entra nesta Change; **Adiado** é viável mas fica para depois; **Descartado** não se sustenta com os dados atuais.

| # | Indicador | Decisão que apoia | Fonte | Viável hoje | Riscos | Prioridade |
|---|---|---|---|---|---|---|
| A1 | Solicitações pendentes | Abrir a fila de análise | `BookingRequest.status=PENDENTE` | Sim | Nenhum | V1 |
| A2 | Pendentes com horário já passado | Rejeitar o que não pode mais ser aprovado | `status=PENDENTE` e início `<= agora` | Sim | A aprovação já recusa; o indicador só antecipa | V1 |
| A3 | Pendentes pedidas por último | Priorizar a decisão | `status=PENDENTE`, início `> agora`, as 5 de `created_at` mais recente, mostradas por `date`, `start_time` | Sim | Nenhum | V1 (lista, 5 itens) |
| A4 | Pendentes há mais tempo | Priorizar pela espera | `created_at` | Sim | Duplica A3 na prática; a lista mostra a espera em cada linha | V1 dentro de A3 |
| A5 | Alternativas sugeridas aguardando resposta | Saber o que depende do solicitante | `status=ALTERNATIVA_SUGERIDA` | Sim | O administrador não age; é contexto | V1 (contagem) |
| A6 | Agendamentos de hoje | Preparar o dia | `Booking.starts_at` na data | Sim | Já aparece na ocupação de hoje | V1 dentro de B2 |
| A7 | Distribuição por estado | Histórico da fila | `status` | Sim | Contagem acumulada sem período não leva a ação | Adiado |
| A8 | Tempo médio de decisão | Agilidade do atendimento | `decided_at - created_at` | Parcial | A alternativa aceita tem `responded_at`; a média mistura casos | Adiado |
| A9 | Dias e horários de maior procura | Planejar disponibilidade | `date`, `start_time` | Sim | Pouco volume no início dá leitura frágil | Adiado |
| B1 | Horas de aula por espaço na semana | Ver espaços mais e menos usados | Ocorrências do ensalamento | Sim, com período | Aula compartilhada e faixas sobrepostas inflam a soma se não forem unidas | V1 (dentro de B3) |
| B2 | Ocupação de hoje por espaço | Saber o que acontece hoje | `active_on(hoje)` e `Booking` do dia | Sim, com período | Hoje fora do período: sem aula | V1 |
| B3 | Ocupação da semana por espaço | Ver concentração e ociosidade | Ocorrências da semana e `Booking` | Sim, com período | Idem B1 | V1 |
| B4 | Horários disponíveis por espaço | Achar horário para atividade | Grade do espaço | Já existe na Grade e na Agenda | Repetir a Grade no painel duplica tela | Descartado (link) |
| B5 | Espaços sem ocupação no período | Redistribuir turmas | Espaços ativos sem ocorrência | Sim | Zero é fato; "pouca utilização" exigiria limiar arbitrário | V1 (só zero) |
| B6 | Taxa percentual de ocupação | Dimensionar infraestrutura | Exige horário de funcionamento | Não | Percentual inventado | Descartado |
| B7 | Mapa de ocupação por dia e horário | Achar picos | Ocorrências por faixa | Sim | Útil, mas é uma visualização nova; fica para a segunda versão | Adiado |
| C1 | Aulas sem espaço | Concluir o ensalamento | `Allocation.space IS NULL` | Sim | Contar por aula vigente, e não por versão encerrada | V1 |
| C2 | Aulas sem docente | Conferir a grade | `Allocation.teachers` vazio | Sim | Idem C1 | V1 |
| C3 | Ofertas sem docente atual | Conferir a oferta | `ClassOffering` sem `TeachingAssignment.is_current` | Sim | Mesmo fato de C2 visto pela oferta; duplicaria | Descartado |
| C4 | Disciplinas ofertadas sem aula | Pendência de planejamento | `ClassOffering` sem alocação atual | Parcial | A oferta só nasce da alocação; o resultado seria só a aula encerrada, e não pendência | Descartado |
| C5 | Possíveis conflitos de docente | Corrigir a grade | Mesmo docente, mesmo dia, faixas que se sobrepõem, espaços diferentes, vigências que se cruzam | Sim | Aula compartilhada no mesmo espaço é legítima e fica fora | V1 |
| C6 | Possíveis conflitos de turma | Corrigir a grade | Mesma turma, mesmo dia, faixa sobreposta | Sim | Turma dividida entre laboratórios é legítima e não se distingue nos dados | Adiado |
| C7 | Agendamento em choque com aula | Remarcar o agendamento | `Booking` futuro sobreposto a ocorrência ativa | Sim | A importação não confere agendamentos; o choque pode existir | V1 |
| C8 | Aulas canceladas e horas liberadas | Acompanhar ocorrências | `AllocationException` | Sim | Contexto, sem ação; já existe a lista de exceções | Adiado |
| D1 | Importações sem conclusão | Concluir ou descartar | `Import.kind='ENSALAMENTO'`, `status` aberto | Sim | Nenhum | V1 |
| D2 | Linhas com erro por importação | Corrigir a planilha | `ImportRow` | Sim | Detalhe técnico; está no detalhe da importação | Descartado (link) |
| D3 | Semestre sem período definido | Definir o período | `Semester.start_date` vazio | Sim | Sem ele, B2 e B3 não existem | V1 (aviso) |
| E1 | Carga horária por docente | Conferir distribuição | Ocorrências por docente | Sim | Não é a carga de trabalho; exposição individual | Adiado |
| E2 | Aulas por curso | Visão da oferta | `class_group.course` | Sim | Contexto, sem ação | Adiado |
| E3 | Comparação entre semestres e evolução | Planejamento | Vários semestres | Parcial | Depende de períodos preenchidos | Adiado |
| E4 | Usuários, auditoria, e-mails, IPs | Administração do sistema | Outros apps | Sim | Não é decisão da Direção de Ensino | Descartado do painel |

## Decisions

### D1. Painel com permissão própria, blocos com a permissão do módulo

`PAINEL.VISUALIZAR` libera a rota. Cada bloco exige, além dela, a permissão do módulo dono dos dados: `AGENDA.ANALISAR` para as solicitações, `ENSALAMENTO.VISUALIZAR` para a ocupação e as pendências da grade, `AGENDA.VISUALIZAR` para o item de agendamentos em choque, `ENSALAMENTO.IMPORTAR` para as importações. A view não calcula o bloco que o usuário não pode ver. Assim, conceder o painel não abre dados de outro módulo, e um perfil personalizado pode ter o painel com só parte dos blocos.

Alternativa descartada: liberar o painel só pela soma das permissões dos módulos, sem permissão própria. Ficaria sem como retirar o painel de um perfil sem retirar os módulos.

### D2. Item "Painel" no início do menu

O item entra primeiro no `MENU`, com prefixo `panel_`. Quem tem a permissão abre o painel depois do login, pela regra já existente do `HomeView`. Quem não tem continua abrindo o primeiro módulo liberado.

### D3. Três recortes de tempo, sempre rotulados

- **Hoje:** a data local do servidor. Não depende do filtro.
- **Semana atual:** de segunda a domingo da semana de hoje (`monday_of`). Não depende do filtro. Domingo e sábado só têm agendamentos, porque o ensalamento é de segunda a sexta.
- **Semestre escolhido:** filtro `semestre`, com as opções de `imported_semesters()`. O padrão é o semestre de código `current_semester_code(hoje)`, quando ele está entre as opções, e o mais recente, quando não está. Vale para as pendências da grade.

A ocupação de hoje e da semana usa todos os semestres cujo período contém as datas, pela mesma regra de `AllocationSource`, e não o filtro. O título de cada bloco diz o recorte ("Hoje, 01/10/2026", "Semana de 28/09/2026 a 04/10/2026", "Semestre 2026/2").

### D4. Ocupação pela união dos intervalos

Por espaço e período, o painel junta os intervalos das ocorrências de aula não canceladas e dos agendamentos, e soma a união. Aula compartilhada, faixas sobrepostas e agendamento sobre aula contam uma vez. Ao lado das horas, o painel mostra a quantidade de aulas e de agendamentos como contagem de ocorrências, e nunca soma essas duas contagens às horas.

Uma ocorrência é a mesma de `Allocation.occurs_on` sem exceção na data. Para não fazer quatro consultas por espaço, `schedule` ganha uma função que devolve as ocorrências de todos os espaços num intervalo em três consultas fixas (semestres, alocações com espaço e cancelamentos), sem os docentes, que a ocupação não usa. A regra continua sendo `occurs_on` e `AllocationException.objects.cancelled`, sem cópia.

Os espaços listados são os de `listed_spaces` dos semestres envolvidos, em ordem decrescente de horas e, no empate, pela ordem natural do nome. Aula sem espaço não entra na ocupação; ela aparece nas pendências.

### D5. Sem percentual e sem limiar de "pouca utilização"

O sistema não sabe o horário de funcionamento nem a disponibilidade de cada espaço. O painel mostra horas e o fato "sem ocupação" (zero), e nenhum valor relativo.

### D6. Aula vigente nas pendências da grade

Uma alocação conta nas pendências quando é do semestre escolhido e a vigência não terminou antes de hoje (`valid_until` vazio ou `>= hoje`) e não termina antes de começar (`valid_until >= valid_from` quando os dois existem). Versão encerrada, que só guarda histórico, não é pendência. A contagem é de aulas, agrupando as alocações de mesma turma, disciplina, dia e faixa.

### D7. Conflito de docente só entre espaços diferentes

Há possível conflito quando o mesmo docente está em duas alocações vigentes do semestre, no mesmo dia da semana, com faixas que se sobrepõem pela regra semiaberta, com vigências que se cruzam e com espaços diferentes ou um deles vazio. Duas alocações no mesmo espaço, dia e faixa são a aula compartilhada e ficam fora. O texto diz "possível conflito", porque a planilha pode trazer arranjos que os dados não distinguem.

### D8. Agendamento em choque com aula

Agendamentos com início a partir de agora, até o fim do semestre escolhido, são conferidos contra as ocorrências ativas do mesmo espaço na mesma data, com a regra de `allocation_conflict`. Isso acontece quando uma importação ou uma recorrência criada depois põe aula sobre um agendamento aprovado. Não há ação de cancelar agendamento no sistema, então o item leva à Agenda do espaço na data.

### D9. Sem auditoria de acesso ao painel

A view não declara `audit_resource`. O painel só agrega dados que já têm telas auditadas, e registrar cada abertura da página inicial encheria o log sem informação.

Ponto para revisão: se o orientador quiser rastrear o acesso, basta declarar o recurso, sem outra mudança.

### D10. Atualização a cada requisição, sem cache

As consultas são em número fixo e agregam no banco onde o ORM permite (contagens das solicitações e das importações, existência de docente). A união de intervalos e o conflito de docente são feitos em Python sobre as alocações de um semestre, que são centenas, e não milhares. Sem cache, sem tarefa agendada e sem tabela de resumo. Se a medição mostrar lentidão, a primeira medida é índice, e não cache.

## Risks / Trade-offs

- **Semestre sem período** → a ocupação de hoje e da semana fica vazia. Mitigação: aviso explícito com o código do semestre e o link para a importação, onde o período é definido.
- **Hoje fora do período de qualquer semestre** (férias) → a ocupação mostra só agendamentos, com o texto que diz que não há semestre em andamento.
- **Docente com nome divergente na planilha** vira dois `Teacher`, e o conflito some. Limitação dos dados, registrada na spec.
- **Aula com espaço inativo** continua contando para o espaço, como na Grade (`listed_spaces`).
- **Fuso:** `Booking` é `DateTimeField` com fuso; a comparação com a data local usa `timezone.localtime`, como a Agenda.
- **Volume de solicitações:** a lista do bloco tem no máximo cinco itens; a contagem é feita no banco com o índice `booking_request_status_idx`.

## Visual

Prévia: `painel-previa.html`, nesta pasta, com dados de exemplo. Referências enviadas pelo autor em 01/10/2026: um painel com menu lateral escuro, cartões de contagem e gráficos de barra, rosca e área; e o painel "Aprovação de Crédito", com faixa de filtros e barras horizontais por categoria.

### Adaptado

- **Cartões de contagem no topo** (as duas referências): cinco cartões com rótulo, número grande e uma linha de contexto ou link. O primeiro, "Solicitações pendentes", usa o fundo `brand-surface` com `on-brand`, como o cartão em destaque da primeira referência. É o único uso da cor de marca como fundo na área de conteúdo.
- **Filtros no cabeçalho** (segunda referência): semestre e Hoje ou Semana como campos de seleção, à direita do título.
- **Barras horizontais por categoria** (blocos "Status" da segunda referência): a ocupação por espaço vira barras de horas, empilhando aulas (`stage-undergraduate-bar`, o verde das aulas) e agendamentos (`booking-bar`, o violeta dos agendamentos na Agenda). O eixo é em horas, e não em percentual. As horas e as contagens aparecem em texto ao lado, e a barra tem `aria-label`.
- **Colunas por período** (barras da primeira referência): no modo Semana, as horas ocupadas por dia, de segunda a domingo, com a mesma divisão de cores. No modo Hoje, este gráfico não aparece.
- **Cartões brancos com borda fina e sombra pequena** sobre o fundo `page`, com cantos `rounded-lg`.

### Retirado

- Rosca com percentual (45%): o painel não calcula percentual (D5).
- Gráfico de área ondulado e minicalendário: não respondem a nenhuma pergunta do painel.
- Menu lateral azul-marinho, avatar grande e perfil no topo do menu: o sistema mantém o menu lateral claro (`sidebar`) e o layout `ui/layouts/app.html`.
- Laranja, azul-marinho e o verde da segunda referência: substituídos pelos tokens do sistema. Âmbar e vermelho só aparecem como estado (pendência e possível conflito), sempre com texto e ícone.
- Textos em inglês, "Lorem ipsum", botões "Check now" e números sem contexto.
- Faixa de cabeçalho escura com totais: os totais ficam nos cartões, e o cabeçalho segue o `page_head` das demais telas.

### Colunas sem degradê

As colunas por dia dividem aulas e agendamentos com corte nítido, e não com o degradê da imagem de referência, porque a seção 9.6 das convenções proíbe gradiente decorativo.

### Divisão das barras sem soma enganosa

As barras somam aulas e agendamentos, mas o total é a união dos intervalos (D4). Quando um agendamento se sobrepõe a uma aula, o trecho sobreposto entra uma vez, na cor da aula: o segmento violeta é só o tempo de agendamento fora de aula. A soma dos dois segmentos é sempre igual ao total exibido.

### Tokens novos

Nenhum. Os gráficos usam `stage-undergraduate-bar`, `booking-bar`, `hover` (trilho da barra), `divider` e `text-muted`, que já têm pares de contraste. As larguras e alturas das barras vêm de proporções calculadas na view e vão para o template como classe de uma escala fechada de 5 em 5% (`bar-w-0` a `bar-w-100`, `bar-h-0` a `bar-h-100`), definida no `app.css`, porque `style=` é proibido nos templates.

### Organização

Revisão de 01/10/2026, a pedido do autor: menos texto e mais equilíbrio.

1. Cabeçalho só com "Painel" e os dois campos de seleção. Os campos são de um formulário Django (`PanelFilterForm`, com `semestre` e `ocupacao`) renderizado pelo `ui.forms.FormRenderer`, que usa o componente `ui/components/select.html` e o `select.js`. Sem JavaScript, o `select` nativo continua funcionando. As opções são poucas e fixas, então não há `data-select-source`. Os selects nativos da prévia são só ilustração.
2. Quatro cartões de contagem, cada um com ícone em quadro de cor suave, número e rótulo curto, e o cartão inteiro como link. As pendentes com horário passado viram o selo "N vencidas" no cartão de pendentes.
3. Duas linhas de duas colunas (3/5 e 2/5):
   - "Espaços mais ocupados" (barras) e "Para decidir" (lista com a data em bloco, espaço, horário, solicitante e espera);
   - "Horas ocupadas por dia" (colunas, com hoje destacado no rótulo) e "Pendências da grade" (quatro blocos com ícone, número e rótulo).
4. Sem rodapés explicativos nem descrições abaixo dos títulos. A regra da união dos intervalos fica na spec e na descrição acessível das barras.
5. Responsivo: dois cartões por linha abaixo de 1100 px, uma coluna abaixo de 760 px, um cartão por linha abaixo de 420 px.
