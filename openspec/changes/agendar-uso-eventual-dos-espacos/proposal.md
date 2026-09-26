## Why

O ensalamento cobre só a ocupação acadêmica recorrente do semestre. O uso eventual de um espaço (uma reunião, uma defesa, um evento de extensão) hoje não tem registro no sistema: não há como pedir um horário disponível, analisar o pedido nem mostrar o uso aprovado junto das aulas. Sem isso, dois usos podem cair no mesmo espaço e horário, e ninguém sabe quem autorizou o quê.

Esta Change cria a **Agenda**, uma área autenticada própria, separada do Ensalamento, que mostra a mesma Grade de horários e permite solicitar o uso eventual de um espaço, analisar a solicitação e manter os agendamentos aprovados sem conflito com o ensalamento nem entre si.

## What Changes

- **Menu "Agenda"** com rota própria, `agenda/`, e view própria. O Ensalamento continua igual e não ganha fluxo de solicitação.
- **Grade compartilhada**: a Agenda usa as estruturas de `schedule/timetable.py` (`build_week`, `Week`, `Day`, `Cell`) e as classes `timetable-*`, com a sua própria lista de fontes de ocupação (ensalamento e agendamento). A Grade do Ensalamento continua só com a fonte `ENSALAMENTO`.
- **App novo `bookings`**, com dois models:
  - `BookingRequest` (solicitação de agendamento): o pedido do usuário, com espaço, data, início, fim, descrição obrigatória, estado, decisão e alternativa sugerida;
  - `Booking` (agendamento): o uso eventual aprovado, avulso, não recorrente, ligado à solicitação que o originou.
- **`Allocation` não muda.** O agendamento não é alocação.
- **Máquina de estados** da solicitação: `PENDENTE`, `APROVADA`, `REJEITADA`, `ALTERNATIVA_SUGERIDA` e `ALTERNATIVA_RECUSADA`, com as transições e os atores definidos na spec. Transição fora da tabela é recusada no model.
- **Conflito** por sobreposição de intervalo semiaberto `[início, fim)` com o ensalamento do espaço naquela data e com outro agendamento aprovado. A verificação acontece no model, na criação, na sugestão, na aprovação e no aceite, e o banco garante a ausência de sobreposição entre agendamentos com uma `ExclusionConstraint` do PostgreSQL.
- **Solicitação pendente não ocupa o horário.** A disponibilidade é verificada de novo na aprovação e no aceite, com o espaço travado por `select_for_update` durante a transação.
- **Permissões granulares** do recurso `AGENDA`: `AGENDA.VISUALIZAR`, `AGENDA.SOLICITAR` e `AGENDA.ANALISAR`. A resposta à alternativa sugerida exige `AGENDA.SOLICITAR` e ser o próprio solicitante.
- **Telas**: Grade da Agenda com a ação "Solicitar agendamento" na faixa disponível; "Minhas solicitações"; "Solicitações para análise", com o detalhe e as ações "Aprovar", "Rejeitar" e "Sugerir alternativa".
- **Auditoria** das mudanças de estado, com o recurso novo `SOLICITACAO_AGENDAMENTO` e o recurso `AGENDAMENTO`.
- **Glossário** da interface: "agendamento" e "solicitação de agendamento" passam a ser os termos do uso eventual, no lugar de "reserva" e "solicitação de reserva".

### Fora do escopo

- Notificações (as transições que poderão gerá-las ficam registradas no `design.md`).
- Cancelamento de agendamento aprovado: o conceito fica registrado, e a regra entra numa Change futura.
- Agendamento recorrente, agendamento em mais de um dia e edição de solicitação depois de enviada.
- Solicitação pendente bloqueando o horário.
- Mudança na importação do ensalamento, no calendário público e na Grade do Ensalamento.

## Capabilities

### New Capabilities

- `agenda`: a área Agenda, as permissões, a solicitação, a máquina de estados, a análise, a alternativa sugerida, os conflitos, a concorrência, a exibição na Grade, a auditoria e o desempenho.

### Modified Capabilities

- `ensalamento`: o requisito das fontes de ocupação deixa de prever que reservas entrem na Grade do Ensalamento; a Grade do Ensalamento continua só com o ensalamento e a Agenda monta a sua própria lista de fontes.

## Impact

- **`accounts/permissions.py`**: as três permissões de `AGENDA`.
- **`bookings/`** (app novo): `models.py`, `occupancy.py`, `forms.py`, `views.py`, `urls.py`, templates e testes.
- **Migrations**: extensão `btree_gist`, os dois models, os índices, a `ExclusionConstraint` e a migration de dados com as três permissões.
- **`schedule/timetable.py`**: só se algum auxiliar da Grade precisar ser extraído para uso comum, sem mudar o comportamento do Ensalamento.
- **`audit/catalog.py`**: recursos e ações novas.
- **`ui/templates/ui/components/navigation.html`**: o item "Agenda".
- **`openspec/conventions.md`** e o glossário dos testes do app `ui`: os termos do agendamento.
