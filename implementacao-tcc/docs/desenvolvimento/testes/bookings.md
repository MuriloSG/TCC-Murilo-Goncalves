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
| `ConflictTests` | Intervalos que se tocam não conflitam, nem com a aula; outro espaço ou dia também não; fim estendido sobre outro agendamento conflita, também na aprovação; o banco recusa agendamentos sobrepostos |
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
| `AssignmentTests` | Turma própria grava o vínculo; turma de outro docente e sem turma aceitas; turma de outro semestre e vínculo histórico recusados; quem não é docente solicita; exige semestre com período |
| `ScreenTests` | Disciplinas de todos os docentes do curso, turmas pela disciplina, semestre pela data; revisão antes do envio; disciplina, turma, semestre e ids forjados recusados ou ignorados; data fora de todo semestre; detalhe mostra o vínculo |
| `SubjectCheckTests` | O model confere curso e disciplina mesmo sem o formulário |

### `test_on_behalf_request.py`

Solicitação criada em nome de outro usuário, com `AGENDA.CRIAR`.

| Classe | O que garante |
|---|---|
| `AccessTests` | A operação exige a permissão; o horário da grade abre o modal de criação para quem só cria; quem cria e solicita tem o atalho no rodapé |
| `ChainOptionsTests` | Usuários ativos com `AGENDA.SOLICITAR`; cursos, disciplinas e turmas do semestre em cadeia, sem vínculos históricos; trocar um campo limpa só os seguintes; a data define o semestre |
| `ChainSecurityTests` | O servidor confere fim de semana, turma de outro docente, sem turma, disciplina de outro curso, turma de outra disciplina, usuário que não é docente, sem a permissão, inativo e ids desconhecidos |
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
| `GridTests` | Semana com aulas e agendamentos aprovados, ocupando cada faixa cruzada; pendente fora; nome do solicitante só para o analista; visão de mês |
| `OtherCalendarsTests` | O agendamento aprovado aparece na Grade do Ensalamento sem a linha do solicitante e no calendário público só para a turma e o docente dele, sem horário nem descrição |
| `WeekendTests` | No fim de semana abre a semana seguinte; no dia útil, a atual |
| `OwnAgendaTests` | "Todas as agendas" é o padrão; a própria agenda esconde as dos outros sem liberar os horários deles |

### `test_request_views.py`

| Classe | O que garante |
|---|---|
| `CreateTests` | Modal preenchido pelo horário; envio cria pendente; campos obrigatórios, conflito, fim de semana e espaço inativo forjado aparecem no formulário |
| `GridActionTests` | Só horário futuro e livre oferece a solicitação |
| `MyRequestsTests` | "Minhas solicitações" só com as próprias, cada estado identificado; detalhe com original, alternativa e motivo; solicitação de outro dá 404 |
| `AnswerTests` | Aceitar e recusar alternativa; resposta de outro usuário recusada |
| `CancelTests` | Cancelar a própria; de outro recusado. O prazo fica no model |

### `test_review_views.py`

| Classe | O que garante |
|---|---|
| `ListTests` | Por padrão, só o que precisa de decisão |
| `DetailTests` | O detalhe tem o necessário para decidir, sem dados pessoais desnecessários; encerrada sem ações |
| `DecisionTests` | Aprovar, rejeitar e sugerir pela tela, com o formulário começando no original; motivo vazio e sugestão igual ao original aparecem no formulário. As demais recusas ficam no model |
| `CancelTests` | Cancelar aprovada; pendente sem cancelamento |
