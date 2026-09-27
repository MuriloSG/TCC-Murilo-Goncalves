## Why

Hoje só o próprio docente solicita agendamento: `BookingRequestManager.prepare` usa o usuário logado como solicitante e confere a turma pelo docente dele (`teacher_of`). A coordenação e a secretaria recebem pedidos por outros canais e não têm como registrá-los na Agenda em nome do docente. Esta Change cria a permissão `AGENDA.CRIAR`, que permite criar a solicitação de agendamento em nome de outro usuário, escolhendo usuário, curso, disciplina e turma nessa ordem, com a cadeia conferida no backend.

## What Changes

- Permissão nova `AGENDA.CRIAR` no catálogo, por migration de dados, concedida ao perfil `ADMINISTRADOR`. O superadmin a recebe como todas as outras, sem regra nova.
- Rota nova `agenda/criar/`, com o modal "Criar solicitação para outro usuário": usuário, curso, disciplina, turma, espaço, data, início, fim e descrição, com a mesma revisão antes do envio.
- Selects dependentes pelo htmx, no padrão já usado no modal "Solicitar agendamento": a troca do usuário limpa curso, disciplina e turma; a do curso limpa disciplina e turma; a da disciplina limpa a turma.
- A cadeia usuário → curso → disciplina → turma vem dos vínculos atuais do ensalamento (`teacher_of` → `TeachingAssignment` → `ClassOffering` → `Subject` e `ClassGroup` → `Course`), sem relacionamento novo.
- `BookingRequestManager.prepare` e `submit` aceitam o solicitante e conferem a cadeia completa no model: a permissão de quem cria, o docente do solicitante, o curso, a disciplina e a turma. As regras de semestre, período, espaço, horário e conflito continuam as mesmas.
- A solicitação guarda quem a criou (`BookingRequest.created_by`) quando é criada em nome de outro usuário, e o detalhe e a auditoria mostram isso.

### Fora do escopo

- Criar o agendamento já aprovado: a solicitação criada continua `PENDENTE` e passa pela análise, como qualquer outra.
- Notificação nova para o usuário em nome de quem a solicitação foi criada.
- Mudança nas permissões existentes (`AGENDA.VISUALIZAR`, `AGENDA.SOLICITAR` e `AGENDA.ANALISAR`) e no fluxo "Solicitar agendamento" do próprio docente.
- Vínculo gravado entre `User` e `Teacher`: a correspondência continua pelo `username`.

## Capabilities

### Modified Capabilities

- `agenda`: criação de solicitação em nome de outro usuário, com a permissão `AGENDA.CRIAR` e a cadeia usuário, curso, disciplina e turma.

## Impact

- `accounts/permissions.py` e a migration `accounts/0014_booking_create_permission`.
- `bookings/models.py`: `created_by`, `check_assignment` com curso e disciplina, `prepare` e `submit` com o solicitante; migration `bookings/0004_booking_request_created_by`.
- `schedule/models.py`: consulta dos usuários que correspondem a um docente.
- `bookings/forms.py`, `bookings/views.py`, `bookings/urls.py`, `bookings/templatetags/agenda.py` e os templates do modal, da revisão, da Grade e do detalhe.
- Testes em `accounts/tests/test_catalog.py` e `bookings/tests/`.
