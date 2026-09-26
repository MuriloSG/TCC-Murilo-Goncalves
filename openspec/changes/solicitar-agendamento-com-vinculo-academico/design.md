## Context

`BookingRequestManager.submit` cria a solicitação pendente depois de conferir a permissão, os campos e os conflitos (`check_slot`, com o ensalamento e os agendamentos aprovados). Só a aprovação e o aceite criam `Booking`. O modal é aberto pela faixa da Grade da Agenda, com o espaço e a data não editáveis (D8 da Change `agendar-uso-eventual-dos-espacos`). `TeachingAssignment.objects.available(semester, teacher, subject, class_group)` devolve os vínculos atuais do semestre numa consulta só.

## Decisions

### D1. Uma FK para o vínculo
`BookingRequest.teaching_assignment` → `TeachingAssignment`, `PROTECT`. O vínculo já identifica o docente e a oferta (semestre, disciplina e turma), então a solicitação não guarda quatro FKs que poderiam ficar incoerentes entre si. O vínculo nunca é excluído, e o `PROTECT` garante isso também para ele. O campo fica nulo só nas solicitações anteriores a esta Change. `Booking` não muda e chega ao vínculo pela solicitação.

### D2. Quem solicita é o docente
O docente é o usuário logado, reconhecido por `teacher_of(user)`: o nome do docente igual ao `username`, sem diferenciar a caixa, a mesma regra de `manages` (D7 da Change importar-ensalamento-da-planilha, sem vínculo gravado entre `Teacher` e `User`). O usuário que não corresponde a um docente não solicita: o modal avisa e o model recusa.

`BookingRequestManager.prepare` confere, nesta ordem: permissão; docente do usuário; semestre e turma informados; turma como vínculo atual do próprio docente no semestre (`check_assignment`); semestre com período e data dentro dele (`check_period`); campos da solicitação; espaço, horário e conflitos (`check_slot`). `submit` chama `prepare` e grava a solicitação, a auditoria e a notificação numa transação. O ensalamento não é tocado.

### D3. Formulário: disciplina e turmas do docente, semestre da Agenda
Os campos são `subject`, `teaching_assignment` (rótulo "Turma"), `space`, `date`, `start_time`, `end_time` e `description`. Não há campo de semestre: o semestre é o da Agenda, o que tem a data no período (`semester_of`), calculado no servidor a cada requisição, e a data fora de qualquer semestre é recusada. Um semestre enviado na requisição é ignorado. A disciplina lista as disciplinas dos vínculos atuais do docente no semestre, e a turma só as turmas da disciplina escolhida, tudo de uma consulta (`available(semester, teacher=...)`). A data e a disciplina têm `hx-get` para a mesma rota, com os valores de `#request-fields`, e o htmx troca só esse bloco. As opções só orientam: um ID fora delas é recusado pelo formulário, e o model confere de novo. A faixa da Grade preenche espaço, data e horário, e todos podem ser trocados.

### D4. Horário
O início e o fim continuam livres, como na Change `agendar-uso-eventual-dos-espacos`, cuja spec admite um pedido das 14:00 às 16:00 num semestre com a aula das 14:10 às 15:00. As faixas do semestre aparecem como sugestão (`datalist`) no início e no fim. Prender o horário às faixas mudaria essa regra e fica para uma decisão futura.

### D5. Revisão antes do envio
O primeiro envio chama `prepare` e mostra a revisão (semestre, docente, turma, disciplina, espaço, data e horário, descrição) no mesmo modal, com os valores em campos ocultos. O envio com `confirmar` chama `submit`, que confere tudo de novo. É o mesmo padrão da alteração de recorrência.

### D6. Consultas
O formulário faz uma consulta para o docente do usuário, uma para o semestre da data, uma para os vínculos atuais do docente e uma para as faixas; os `queryset` dos campos só são consultados na validação. As listas e o detalhe carregam o vínculo com `select_related`, sem consulta por linha.

## Risks / Trade-offs

- Sem JavaScript, a troca da data ou da disciplina não recarrega as opções sozinha. O backend recusa qualquer turma inválida, e a página completa funciona com a faixa da Grade e as turmas do semestre dela.
- A correspondência entre usuário e docente depende do `username` igual ao nome do docente na planilha. Um docente sem `username` correspondente não consegue solicitar até o `username` ser ajustado.
