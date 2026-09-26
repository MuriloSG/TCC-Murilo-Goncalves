## Context

| Conceito | Onde | Situação |
|---|---|---|
| Espaço | `schedule.Space` (`is_active`, nome atual) | alvo do agendamento |
| Aula recorrente | `schedule.Allocation` (semestre, `weekday`, `time_slot`, `space` opcional) | regra semanal; não muda nesta Change |
| Ocorrências | `schedule/occupancy.py` (`Occurrence`, `AllocationSource`, `grid_sources()`, `occupancy()`) | a Grade só lê ocorrências, com o tipo da fonte |
| Grade | `schedule/timetable.py` (`build_week`, `Week`, `Day`, `Cell`, `Entry`, `week_dates`, `month_dates`), `grid.html`, `timetable_cell.html`, classes `timetable-*` | usada pelo Ensalamento e pelo calendário público |
| Acesso | `login_required` no `urls.py`, `PermissionMiddleware` pelo `permission_required`, `AuditMiddleware` pelo `audit_resource` | padrão de toda área autenticada |
| Auditoria | `audit/catalog.py` (recursos e ações), `AuditLog` | recurso por módulo, ação por operação |

## Goals / Non-Goals

**Goals**

- Área Agenda própria, com a mesma Grade, as suas regras e as suas ações.
- Separar ensalamento recorrente, solicitação e agendamento aprovado.
- Garantir no banco que dois agendamentos aprovados não se sobrepõem no mesmo espaço, e no serviço que um agendamento não sobrepõe o ensalamento.
- Consultas em quantidade fixa por requisição.

**Non-Goals**

- Notificações, cancelamento, recorrência, edição de solicitação enviada, bloqueio por solicitação pendente.

## Decisions

### D1. App `bookings`, rota `agenda/`

O agendamento é um domínio novo, com estados, permissões e auditoria próprios. Fica num app próprio, `bookings`, que depende de `schedule` (espaço, ocorrências do ensalamento, Grade), e `schedule` não depende de `bookings`. As rotas, em português:

| Rota | View | Permissão |
|---|---|---|
| `agenda/` | `AgendaGridView` | `AGENDA.VISUALIZAR` |
| `agenda/solicitar/` (GET com `espaco`, `data`, `inicio`, `fim`; POST envia) | `BookingRequestCreateView` | `AGENDA.SOLICITAR` |
| `agenda/minhas-solicitacoes/` | `MyBookingRequestListView` | `AGENDA.SOLICITAR` |
| `agenda/minhas-solicitacoes/<id>/` | `MyBookingRequestDetailView` | `AGENDA.SOLICITAR` + dono |
| `agenda/minhas-solicitacoes/<id>/aceitar/` e `.../recusar/` | `AcceptSuggestionView`, `DeclineSuggestionView` | `AGENDA.SOLICITAR` + dono |
| `agenda/solicitacoes/` | `BookingRequestReviewListView` | `AGENDA.ANALISAR` |
| `agenda/solicitacoes/<id>/` | `BookingRequestReviewDetailView` | `AGENDA.ANALISAR` |
| `agenda/solicitacoes/<id>/aprovar/`, `.../rejeitar/`, `.../sugerir/` | `ApproveView`, `RejectView`, `SuggestView` | `AGENDA.ANALISAR` |

Todas com `login_required` no `urls.py` e `permission_required` na view (convenções, seção 4). A posse é verificada no `setup()`: o objeto das rotas `minhas-solicitacoes/` é carregado com `get_object_or_404(BookingRequest, pk=..., requested_by=request.user)`, e o ID de outro usuário responde 404, sem revelar que existe.

### D2. Permissões

`AGENDA.VISUALIZAR` (ver a Grade da Agenda), `AGENDA.SOLICITAR` (enviar solicitação, ver as próprias e responder à alternativa sugerida) e `AGENDA.ANALISAR` (ver as solicitações de todos, aprovar, rejeitar e sugerir alternativa). Não existe `AGENDA.GERENCIAR`. Responder à alternativa não tem permissão própria porque o que autoriza é a posse: separar a permissão não mudaria quem pode responder. Nenhuma das três é reservada ao superadmin. As constantes ficam no catálogo único `accounts/permissions.py`, como as de `ESPACO` e `ENSALAMENTO`, e a migration de dados em `accounts/migrations/`. A migration de dados as acrescenta ao catálogo e concede as três ao perfil `ADMINISTRADOR` e `AGENDA.VISUALIZAR` e `AGENDA.SOLICITAR` ao perfil `DOCENTE`, sem alterar as demais permissões concedidas.

`AGENDA.SOLICITAR` sem `AGENDA.VISUALIZAR` permite ver as próprias solicitações, mas não a Grade; o botão da faixa só aparece para quem tem as duas.

### D3. Modelo

`BookingRequest` (solicitação de agendamento):

- `requested_by` (FK `User`, PROTECT), `space` (FK `schedule.Space`, PROTECT), `date`, `start_time`, `end_time`, `description` (texto, obrigatório, até 500 caracteres, espaços nas pontas descartados);
- `status` (`PENDENTE`, `APROVADA`, `REJEITADA`, `ALTERNATIVA_SUGERIDA`, `ALTERNATIVA_RECUSADA`);
- `rejection_reason`, `suggested_space` (FK opcional), `suggested_date`, `suggested_start_time`, `suggested_end_time`, `suggestion_message`;
- `decided_by` (FK `User` opcional), `decided_at`, `responded_at`, `created_at`.
- `CheckConstraint`: `start_time < end_time`; quando há alternativa, `suggested_start_time < suggested_end_time`.

Os campos originais nunca mudam depois da criação: a alternativa fica nos campos `suggested_*`, para que o solicitante e quem analisa vejam o original e o sugerido lado a lado. O histórico mostrado na análise vem desses campos (criada em, decidida por e em, alternativa, resposta em), sem tabela de eventos; o histórico completo fica na auditoria.

`Booking` (agendamento):

- `request` (OneToOne `BookingRequest`, PROTECT), `space` (FK, PROTECT), `starts_at`, `ends_at` (`DateTimeField`, mesma data), `description` (cópia da solicitação), `requested_by` (FK), `approved_by` (FK), `created_at`.
- `CheckConstraint`: `starts_at < ends_at`.
- `ExclusionConstraint` (`btree_gist`): `space` com `=` e `TsTzRange(starts_at, ends_at, '[)')` com `&&`. É a garantia do banco contra dois agendamentos sobrepostos, inclusive em aprovações simultâneas.

Guardar data e hora da solicitação em campos separados segue o formulário (faixa da Grade); o `Booking` usa `DateTimeField` porque a restrição de exclusão precisa do intervalo.

`Allocation` não é tocada. Ensalamento, solicitação e agendamento são três conceitos em três tabelas.

Como a solicitação e o agendamento protegem o espaço (`PROTECT`), a exclusão de um espaço citado por uma solicitação seria recusada pelo banco. `Space.delete_space` traduz essa recusa em `SpaceWithBookings`, com a mensagem "O espaço … tem solicitações de agendamento na Agenda e não pode ser excluído. Desative o espaço.", no mesmo formato da recusa do espaço com aulas.

### D4. Máquina de estados

| De | Para | Quem | Operação | Efeito |
|---|---|---|---|---|
| (nova) | `PENDENTE` | solicitante com `AGENDA.SOLICITAR` | `BookingRequest.objects.submit` | valida e grava |
| `PENDENTE` | `APROVADA` | `AGENDA.ANALISAR` | `approve` | verifica disponibilidade e cria `Booking` com o horário original |
| `PENDENTE` | `REJEITADA` | `AGENDA.ANALISAR` | `reject(reason)` | motivo obrigatório |
| `PENDENTE` | `ALTERNATIVA_SUGERIDA` | `AGENDA.ANALISAR` | `suggest(...)` | alternativa diferente do original e disponível no momento; mensagem opcional |
| `ALTERNATIVA_SUGERIDA` | `ALTERNATIVA_SUGERIDA` | `AGENDA.ANALISAR` | `suggest(...)` | substitui a alternativa (quando a anterior deixou de estar disponível) |
| `ALTERNATIVA_SUGERIDA` | `REJEITADA` | `AGENDA.ANALISAR` | `reject(reason)` | encerra |
| `ALTERNATIVA_SUGERIDA` | `APROVADA` | o solicitante | `accept_suggestion(user)` | verifica disponibilidade da alternativa e cria `Booking` com ela |
| `ALTERNATIVA_SUGERIDA` | `ALTERNATIVA_RECUSADA` | o solicitante | `decline_suggestion(user)` | encerra sem agendamento |

`APROVADA`, `REJEITADA` e `ALTERNATIVA_RECUSADA` são finais nesta versão. Cada operação roda em `transaction.atomic`, relê a solicitação com `select_for_update`, confere o estado atual e o ator e lança `InvalidTransition` (derivada de `ValidationError`) fora da tabela. A view só chama a operação e mostra a mensagem.

Aprovação ou aceite recusados por conflito não mudam o estado: a solicitação continua `PENDENTE` (quem analisa pode rejeitar ou sugerir alternativa) ou `ALTERNATIVA_SUGERIDA` (quem analisa pode sugerir outra ou rejeitar; o solicitante pode recusar).

Aprovação e aceite de solicitação cujo início já passou são recusados, pelo mesmo motivo da criação.

### D5. Conflito

Intervalo semiaberto `[início, fim)`: há conflito quando `início < outro_fim` e `fim > outro_início`. `14:00–15:00` e `15:00–16:00` não conflitam.

`bookings/occupancy.py` expõe `conflicts(space, date, start, end, exclude_booking=None)`, com duas consultas:

1. ensalamento: `Allocation` do espaço, do semestre com período que contém a data, do `weekday` da data, com `time_slot__start_time < end` e `time_slot__end_time > start`, `exists()`;
2. agendamento: `Booking` do espaço com `starts_at < fim` e `ends_at > início`, `exists()`.

A verificação vale na criação (recusa imediata, com a mensagem do horário ocupado), na sugestão, na aprovação e no aceite. A garantia final contra agendamentos sobrepostos é a `ExclusionConstraint`; uma `IntegrityError` dela vira a mesma mensagem de horário ocupado.

O ensalamento não pode ser coberto por restrição de banco, porque é regra semanal. A importação do ensalamento continua sem detecção de conflito (spec `ensalamento`): um agendamento aprovado antes de uma reimportação que ocupe o mesmo horário continua existindo, e os dois aparecem na célula. Esse caso fica como risco registrado.

### D6. Concorrência

A solicitação pendente não trava nada (ela é só uma intenção). A aprovação e o aceite, dentro da transação, fazem `select_for_update` da linha do `Space` alvo antes de verificar os conflitos e criar o `Booking`. Isso serializa as decisões do mesmo espaço, sem travar os demais nem a Grade (que só lê). Mesmo sem a trava, a `ExclusionConstraint` impede os dois agendamentos sobrepostos; a trava existe para que a verificação contra o ensalamento e a criação aconteçam sem outra decisão no meio.

### D7. Grade da Agenda

A Agenda tem a sua lista de fontes, `agenda_sources()` = `[AllocationSource(), BookingSource()]`, e chama `schedule.occupancy.occupancy(space, start, end, sources=agenda_sources())`, que já aceita `sources`. `grid_sources()` do Ensalamento não muda. `BookingSource` devolve `Occurrence` com `kind='AGENDAMENTO'`, com uma consulta por requisição (os agendamentos do espaço no intervalo, `only` nos campos do card).

A marcação da Grade é reaproveitada pelas estruturas de `timetable.py` e pelas classes `timetable-*`. A Agenda tem o seu template (`bookings/agenda.html`) e o seu card, para colocar a ação "Solicitar agendamento" na faixa disponível sem mexer no `grid.html` do Ensalamento, que continua só de consulta. Se um trecho de template da Grade precisar ser comum, ele é extraído para um include em `schedule/templates/schedule/`, sem mudar o HTML gerado para o Ensalamento.

As faixas das linhas continuam as do semestre, e o agendamento aparece em todas as faixas que cruza (`dated_grid(..., by_overlap=True)` em `schedule/timetable.py`, sem mudar a Grade do Ensalamento). Um agendamento que não cruza nenhuma faixa do semestre, como no almoço, ganha uma linha própria com o seu intervalo, para que nenhum uso aprovado fique fora da Grade. Os auxiliares de datas da Grade (`parse_date`, `parse_month`, `month_reference`, `occupation_text`) passaram para `timetable.py`, e o cabeçalho dos dias e a navegação viraram os includes `schedule/partials/timetable_head.html` e `timetable_nav.html`, usados pelas duas telas.

Card do agendamento: selo "Agendamento" (texto e ícone, não só cor), a descrição e o horário. O card da aula continua como está e ganha, na Agenda, o selo "Ensalamento". O nome do solicitante só aparece para quem tem `AGENDA.ANALISAR`.

Semana e mês, navegação, dias, faixas e comportamento abaixo de 640 px são os da Grade autenticada. Não há representação própria para o celular.

A faixa disponível, na Agenda, é um botão (com `aria-label` "Solicitar agendamento" e dia, data e horário) que abre o modal pelo htmx com a URL `agenda/solicitar/?espaco=...&data=...&inicio=...&fim=...`. Sem `AGENDA.SOLICITAR` ela é a célula vazia de sempre. Dia fora do semestre continua "Fora do semestre", mas a solicitação num dia fora do semestre é aceita, porque o uso eventual não depende do período letivo; para isso, a visão da Agenda mostra as faixas do semestre vigente mesmo nos dias sem aula.

### D8. Formulário da solicitação

Campos: `space`, `date`, `start_time`, `end_time`, `description`. Os quatro primeiros vêm preenchidos da faixa; início e fim podem ser ajustados (o fim deve ser depois do início, na mesma data). O espaço e a data são `readonly` (convenções, seção 5), e um valor forjado chega ao model e é recusado pelas mesmas regras. Espaço inativo, data e início no passado, fim antes do início e conflito são recusados com erro no formulário.

### D9. Auditoria

Recursos novos em `audit/catalog.py`: `SOLICITACAO_AGENDAMENTO` ("Solicitações de agendamento") e `AGENDAMENTO` ("Agendamentos"). Ações novas: `APROVAR`, `REJEITAR`, `SUGERIR`, `ACEITAR`, `RECUSAR`.

| Evento | Recurso | Ação |
|---|---|---|
| solicitação criada | `SOLICITACAO_AGENDAMENTO` | `CRIAR` |
| aprovada | `SOLICITACAO_AGENDAMENTO` | `APROVAR` |
| rejeitada (com motivo) | `SOLICITACAO_AGENDAMENTO` | `REJEITAR` |
| alternativa sugerida | `SOLICITACAO_AGENDAMENTO` | `SUGERIR` |
| alternativa aceita | `SOLICITACAO_AGENDAMENTO` | `ACEITAR` |
| alternativa recusada | `SOLICITACAO_AGENDAMENTO` | `RECUSAR` |
| agendamento criado | `AGENDAMENTO` | `CRIAR` |

Os valores anteriores e posteriores trazem só o estado e os campos que mudaram; a descrição entra só na criação. Operação recusada não gera registro. As views das telas declaram `audit_resource` como as demais.

### D10. Notificações futuras

Nada é enviado nesta Change. Transições que poderão notificar numa Change futura: solicitação criada (para quem tem `AGENDA.ANALISAR`), aprovada, rejeitada e alternativa sugerida (para o solicitante), alternativa aceita ou recusada (para quem decidiu). As operações do model ficam como o único ponto dessas transições, para que a notificação entre ali, por `transaction.on_commit`.

### D11. Cancelamento

Fora desta Change. O estado `CANCELADA` e a ação de cancelar um agendamento aprovado (por quem solicitou ou por quem analisa, antes do início) ficam para uma Change própria, que decidirá quem cancela, o prazo e o efeito na Grade. Nenhum campo é criado antecipadamente.

### D12. Glossário

A seção 9.4 das convenções diz "solicitação de reserva" e "reserva". O autor pediu "Agenda", "Solicitar agendamento", "solicitação de agendamento" e "agendamento". Os termos do autor prevalecem: o glossário passa a ter "solicitação de agendamento" (não "pedido", "reserva pendente") e "agendamento" (não "reserva", "agendamento confirmado"). Estados exibidos: "Pendente", "Aprovada", "Rejeitada", "Alternativa sugerida" e "Alternativa recusada"; "Aguardando" continua fora, e a lista do solicitante destaca "Resposta pendente" na solicitação com alternativa.

### D13. Desempenho e índices

Grade da Agenda: as consultas da Grade do Ensalamento mais uma de agendamentos, fixas, qualquer que seja o intervalo. Listas paginadas com `select_related('space', 'suggested_space', 'requested_by')` e `only` nos campos exibidos, sem consulta por linha. Verificação de conflito: duas consultas `exists()`.

Índices:

- `Booking`: a `ExclusionConstraint` já cria o índice GiST `(space, tstzrange)`, usado pela `BookingSource` e pela verificação.
- `BookingRequest`: `(requested_by, -created_at)` para "Minhas solicitações" e `(status, date)` para a lista de análise.
- Ensalamento: o índice `(semester, space, weekday)` existente atende à verificação.

Os planos são conferidos com `EXPLAIN` e registrados aqui na implementação.

### D14. Tela nova

Antes das telas, o autor envia a imagem de referência (convenções, seção 9.8), e o que foi adaptado ou retirado fica registrado aqui.

## Risks / Trade-offs

- **Reimportação sobre um agendamento aprovado** → a importação não conhece o agendamento; os dois aparecem na célula. Mitigação futura: aviso na prévia da importação.
- **Trava por espaço** → decisões simultâneas do mesmo espaço esperam uma à outra; o custo é pequeno, porque a transação é curta.
- **Alternativa não reservada** → a alternativa sugerida pode ser ocupada antes do aceite; o aceite verifica de novo e quem analisa pode sugerir outra.
