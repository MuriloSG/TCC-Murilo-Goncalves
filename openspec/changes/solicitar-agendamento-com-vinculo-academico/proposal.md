## Why

A solicitação de agendamento da Agenda registra só o espaço, a data, o horário e a descrição. Quem analisa não sabe para qual docente, disciplina e turma o espaço é pedido, e nada impede um pedido para uma combinação que o ensalamento não tem. A Change `relacionar-professor-disciplina-turma` preparou os vínculos acadêmicos por semestre (`ClassOffering` e `TeachingAssignment`), estabelecidos pela importação. Esta Change passa a exigir esse vínculo na solicitação.

## What Changes

- A solicitação ganha o vínculo acadêmico (`BookingRequest.teaching_assignment`), de onde vêm o semestre, o docente, a disciplina e a turma, sem cópia desses dados.
- Quem solicita é o docente logado, reconhecido pelo `username`. O envio exige uma turma que seja vínculo atual do próprio docente no semestre da Agenda (o que contém a data), conferido no backend a cada envio.
- A data deve estar no período do semestre, e o semestre precisa ter período.
- O modal "Solicitar agendamento" passa a ter disciplina (as do docente logado), turma (as dele na disciplina escolhida), espaço, data, início, fim e descrição, sem campo de semestre, com as opções recarregadas pelo htmx na troca da data ou da disciplina. A faixa da Grade continua preenchendo o espaço, a data e o horário, que agora podem ser trocados.
- Uma etapa de revisão antes do envio, como na alteração de recorrência.
- O detalhe da solicitação e o registro de auditoria da criação mostram o vínculo.

### Fora do escopo

- Notificações novas, cancelamento e recorrência de agendamento.
- Vínculo acadêmico no `Booking`: ele é lido pela solicitação de origem.
- Conferência do vínculo na alternativa sugerida, que continua mudando só espaço, data e horário.
- Horário preso às faixas do semestre: as faixas aparecem como sugestão, e as regras de horário continuam as da Change `agendar-uso-eventual-dos-espacos`.

## Capabilities

### Modified Capabilities

- `agenda`: solicitação pelo docente logado, com uma das suas turmas, período do semestre e revisão antes do envio.

## Impact

- `bookings/models.py`: campo `teaching_assignment`, `prepare`, `check_assignment` e `check_period`.
- `schedule/models.py`: `teacher_of(user)`.
- `bookings/forms.py`, `bookings/views.py` e os templates do modal, da revisão e do detalhe.
- Migration `bookings/0003_booking_request_teaching_assignment`.
- Testes em `bookings/tests/`.
