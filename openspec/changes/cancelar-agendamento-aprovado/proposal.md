## Why

Depois de aprovado, o agendamento ocupa o espaço até acontecer, sem volta. Quando a aula deixa de ser necessária, o espaço continua ocupado na Agenda, no calendário público e no painel, e ninguém mais consegue solicitá-lo. A D11 da Change `agendar-uso-eventual-dos-espacos` deixou o cancelamento para uma Change própria, que decide quem cancela, o prazo e o efeito na Grade.

## What Changes

- Estado novo `CANCELADA` na solicitação de agendamento, com quem cancelou, quando e o motivo, que é opcional.
- `BookingRequest.cancel`: cancela a solicitação aprovada até 1 hora antes do início do agendamento. Cancelam quem solicitou e quem tem `AGENDA.ANALISAR`.
- O agendamento é excluído no cancelamento, e o espaço fica disponível na Agenda, na Grade, no calendário público e no painel.
- Botão "Cancelar agendamento" no detalhe de "Minhas solicitações" e no detalhe da análise, com modal de confirmação e o campo do motivo.
- Notificação "Agendamento cancelado" para a outra parte: quem aprovou, quando quem solicitou cancela, e quem solicitou, quando quem analisa cancela.
- Selo "Cancelada", evento no histórico, auditoria da transição e da exclusão do agendamento, e a situação no relatório de solicitações.

### Fora do escopo

- Prazo configurável e cancelamento depois do prazo.
- Permissão própria para cancelar.
- Ação de cancelar no card da Grade da Agenda.

## Capabilities

### Modified Capabilities

- `agenda`: cancelamento de agendamento aprovado.

## Impact

- `bookings/models.py`, `bookings/forms.py`, `bookings/views.py`, `bookings/urls.py` e `bookings/notifications.py`; migration `bookings/0003_cancellation`.
- `notices/catalog.py` (tipo `AGENDA_CANCELADA`) e `reports/requests.py` (situação cancelada).
- Templates `cancel_form_modal.html`, `my_request_detail.html`, `review_detail.html` e `partials/request_record.html`.
