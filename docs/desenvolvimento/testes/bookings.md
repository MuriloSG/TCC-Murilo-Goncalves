# Testes do app `bookings`

Solicitações de agendamento, análise, alternativa, cancelamento e Grade da Agenda. Comportamento descrito em [agenda](../../funcionalidades/agenda.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `base.py`: relógio fixado em 01/10/2026 às 10:00, semestre 2026/2 com período e aula às quintas, vínculo do docente sem alocação e uma solicitação pronta do usuário.

## Regras da solicitação

### `test_models.py`

Solicitação, conflitos e máquina de estados, no model.

| Classe | O que garante |
|---|---|
| `SubmitTests` | Cria solicitação pendente sem agendamento; descrição e quantidade de alunos obrigatórias; fim depois do início; recusa início no passado, espaço inativo, conflito com agendamento aprovado ou com o ensalamento e data fora do período do semestre; pendente não ocupa o horário; exige `AGENDA.SOLICITAR` |
| `WeekendTests` | Sábado e domingo recusados, inclusive na alternativa; fora do semestre, o período é informado primeiro; solicitações e alternativas anteriores à regra ainda podem ser aprovadas e aceitas |
| `ConflictTests` | Intervalos que se tocam não conflitam; outro espaço ou dia também não; a checagem usa duas consultas; o banco recusa agendamentos sobrepostos |
| `ApproveTests` | Aprovar cria o agendamento no horário original; recusa horário tomado depois, início já passado e falta da permissão de análise |
| `RejectTests` | Rejeitar exige e grava o motivo, também depois de uma alternativa |
| `SuggestTests` | A alternativa mantém os dados originais, com mensagem opcional; recusa igual ao original, ocupada ou inválida; nova substitui a anterior; aceitar cria o agendamento com a alternativa, se livre; recusar encerra sem agendamento; só o solicitante responde |
| `TransitionTests` | Só as transições da tabela são aceitas; decisão dupla recusada |
| `CancelTests` | Solicitante e analista cancelam e liberam o horário até uma hora antes do início, contando a alternativa aceita; outro usuário e solicitações não aprovadas recusados |
| `ConcurrentApprovalTests` | Aprovações simultâneas criam um só agendamento |
| `SpaceDeletionTests` | Espaço com solicitação não é excluído |

### `test_academic_request.py`

Turma opcional na solicitação de quem tem `AGENDA.SOLICITAR`.

| Classe | O que garante |
|---|---|
| `AssignmentTests` | Turma própria grava o vínculo; turma de outro docente e sem turma aceitas; turma de outro semestre e vínculo histórico recusados; quem não é docente solicita; exige a permissão e semestre com período; falha depois de gravar desfaz tudo |
| `ScreenTests` | Disciplinas de todos os docentes do curso, turmas pela disciplina, semestre pela data; revisão antes do envio; disciplina, turma, semestre e ids forjados recusados ou ignorados; data fora de todo semestre; detalhe mostra o vínculo |
| `SubjectCheckTests` | O model confere curso e disciplina mesmo sem o formulário |

### `test_on_behalf_request.py`

Solicitação criada em nome de outro usuário, com `AGENDA.CRIAR`.

| Classe | O que garante |
|---|---|
| `AccessTests` | Exige a permissão, inclusive na operação; superadmin passa; o horário da grade abre o modal de criação para quem só cria; quem cria e solicita tem o atalho no rodapé |
| `ChainOptionsTests` | Usuários ativos com `AGENDA.SOLICITAR`; cursos, disciplinas e turmas do semestre em cadeia, pelo htmx e na ordem exigida; trocar um campo limpa só os seguintes; a data define o semestre |
| `ChainSecurityTests` | O servidor recusa fim de semana, turma de outro docente, disciplina de outro curso, turma de outra disciplina, usuário sem a permissão, inativo e ids desconhecidos |
| `ChainModelTests` | O model confere curso, disciplina, semestre, permissão e situação do usuário sem o formulário |
| `CreationTests` | Revisão antes do envio; a solicitação pertence ao usuário escolhido; a auditoria grava solicitante e criador; a aprovação cria o agendamento dele; criar para si exige `AGENDA.SOLICITAR` |

### `test_notifications.py`

| Classe | O que garante |
|---|---|
| `RequestedTests` | Nova solicitação notifica analistas ativos e o superadmin, uma vez cada, e não o próprio solicitante; recusa não notifica |
| `DecisionTests` | Aprovação, rejeição e alternativa notificam o solicitante; decisões inválidas não notificam; a mensagem é cortada no limite |
| `AnswerTests` | Aceite e recusa da alternativa notificam quem sugeriu; se ele está inativo ou perdeu a permissão, os demais analistas |
| `CancelTests` | Cancelamento pelo solicitante notifica quem aprovou; pelo analista, o solicitante; recusa não notifica |

### `test_audit.py`

`AuditTests`: criação, aprovação (transição e agendamento), rejeição com motivo, aceite e recusa da alternativa e cancelamento (com o agendamento apagado) são auditados; operações recusadas não.

## Telas

### `test_agenda_grid.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Abre com a permissão de visualizar; o menu tem a Agenda separada do Ensalamento |
| `GridTests` | Semana com aulas e agendamentos aprovados, ocupando cada faixa cruzada; pendente fora; nome do solicitante só para o analista; visão de mês; espaço inativo não oferecido |
| `OtherCalendarsTests` | O agendamento aprovado aparece na Grade do Ensalamento sem a linha do solicitante e no calendário público só para a turma e o docente dele, sem horário nem descrição |
| `QueryTests` | Número fixo de consultas na semana e no mês |
| `WeekendTests` | No fim de semana abre a semana seguinte |
| `OwnAgendaTests` | "Todas as agendas" é o padrão; a própria agenda esconde as dos outros sem liberar os horários deles |

### `test_request_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Abre com a permissão de solicitar |
| `CreateTests` | Modal preenchido pelo horário; envio cria pendente; campos obrigatórios, conflito, fim de semana e espaço inativo forjado recusados; o calendário só oferece dias úteis |
| `GridActionTests` | Só horário futuro e livre oferece a solicitação |
| `MyRequestsTests` | "Minhas solicitações" só com as próprias, cada estado identificado, consultas sem crescer com as linhas; detalhe com original, alternativa e motivo; solicitação de outro dá 404 |
| `AnswerTests` | Aceitar e recusar alternativa; ocupada, de outro usuário ou sem alternativa recusadas |
| `CancelTests` | Cancelar a própria; após o prazo ou de outro recusado |

### `test_review_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Abre com a permissão de analisar |
| `ListTests` | Por padrão, só o que precisa de decisão; consultas sem crescer com as linhas |
| `DetailTests` | O detalhe tem o necessário para decidir, sem dados pessoais desnecessários; encerrada sem ações |
| `DecisionTests` | Aprovar, rejeitar e sugerir pela tela, com o formulário começando no original; recusas por horário tomado, motivo vazio, igual ao original, ocupada, fim de semana e transição inválida |
| `CancelTests` | Cancelar aprovada; pendente sem cancelamento |
