## Why

A solicitação de agendamento traz só uma descrição em texto livre. Quem analisa não sabe quantos alunos vão usar o espaço e decide sem conferir se a sala comporta a turma. Esta Change pede a quantidade de alunos na solicitação e a mostra em todas as telas da análise.

## What Changes

- Campo novo "Quantidade de alunos" no modal "Solicitar agendamento" e no modal "Criar solicitação para outro usuário". É obrigatório e aceita um inteiro de 1 a 999.
- `BookingRequest.student_count` e `Booking.student_count`. O agendamento copia o valor da solicitação na aprovação e no aceite da alternativa.
- `BookingRequestManager.prepare` e `submit` recebem `student_count`, recusam o valor ausente ou fora da faixa e o registram na auditoria como `quantidade_alunos`.
- A quantidade aparece na revisão antes do envio, no detalhe da solicitação (o do solicitante e o da análise) e numa coluna "Alunos" nas listas.

### Fora do escopo

- Capacidade dos espaços e comparação com a quantidade informada.
- Quantidade de alunos na notificação, no relatório de solicitações e no calendário público.

## Capabilities

### Modified Capabilities

- `agenda`: quantidade de alunos na solicitação de agendamento.

## Impact

- `bookings/models.py`, `bookings/forms.py` e `bookings/views.py`; migration `bookings/0002_student_count`.
- Templates `request_summary_modal.html`, `partials/request_record.html` e `partials/request_table.html`; ícone `ui/icons/users-round.svg`.
