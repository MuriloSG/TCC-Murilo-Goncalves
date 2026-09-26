## Context

`Teacher`, `Course` e `Subject` são `NamedRecord`, únicos pelo nome sem diferenciar a caixa e válidos para todos os semestres. `ClassGroup` é a turma, única por curso e rótulo, também sem semestre. `Allocation` guarda semestre, turma, disciplina, dia, faixa, espaço, docentes (M2M), origem e vigência. Sua identidade é `(semester, class_group, weekday, time_slot, subject, valid_from)`. A importação (`SpaceAllocationImport.execute_activity`) resolve curso, turma, disciplina, faixa e docentes e chama `Allocation.objects.apply`. Cada linha roda num savepoint, a prévia desfaz a transação inteira e a confirmação reexecuta e só grava com plano idêntico (D7 e D8 da Change importar-planilhas). A alteração de recorrência encerra a alocação na véspera do corte e cria uma versão nova com a mesma turma, disciplina e semestre.

## Goals / Non-Goals

**Goals:** representar de forma explícita, por semestre, qual disciplina é ofertada para qual turma e por quais docentes; estabelecer isso só pela importação; preservar o histórico; oferecer à Agenda uma consulta sem N+1 das combinações atuais.

**Non-Goals:** `Booking` com disciplina e turma, interface da Agenda, cadastro manual, vínculo `Teacher` e `User`, FK de `Allocation` para a oferta.

## Decisions

### D1. Reusar as entidades existentes
`Subject` é a disciplina, `ClassGroup` é a turma, `Course` é o curso e `Teacher` é o docente. Nenhuma entidade nova duplica esses conceitos. A disciplina continua global (D12 da Change importar-ensalamento-da-planilha) e a turma continua sem semestre. O semestre entra na oferta, e não nelas.

### D2. Oferta por semestre
`ClassOffering(semester, subject, class_group)`, com FKs `PROTECT` e `UniqueConstraint` `class_offering_unique`. Ela é a relação N:N entre disciplina e turma, dentro de um semestre: a mesma disciplina em 2026/1 e 2026/2 gera duas ofertas, e o histórico de cada semestre fica intacto. Não existe relação global `Teacher ↔ Subject`. A oferta existe mesmo sem docente, porque a planilha traz atividade sem docente reconhecido.

### D3. Histórico e disponibilidade atual
`TeachingAssignment(offering, teacher, is_current)`, com FKs `PROTECT` e `UniqueConstraint` `teaching_assignment_unique`. São dois conceitos diferentes:

- **Histórico**: todas as linhas de `TeachingAssignment` da oferta. Nenhuma linha é excluída automaticamente.
- **Disponibilidade atual**: as linhas com `is_current=True`.

A semântica de `is_current`, registrada na docstring do model, é:

- `True`: o docente está presente em alguma alocação atual da oferta;
- `False`: o vínculo é preservado como histórico, mas o docente não está em nenhuma alocação atual da oferta.

`is_current` não significa "docente responsável pela disciplina": é só um reflexo das alocações atuais. **Alocação atual da oferta** é a alocação com o mesmo semestre, disciplina e turma e sem fim de vigência (`valid_until IS NULL`), a versão mais recente de cada aula. A importação grava a vigência vazia. A alteração de recorrência encerra a versão anterior com `valid_until = corte - 1` e copia para a nova o `valid_until` da anterior, que é vazio. As versões encerradas pertencem ao histórico da recorrência e não contam.

Exemplo, 2026/2, Matemática, turma 2º período: a planilha trazia João e passa a trazer Maria. O histórico fica com João `is_current=False` e Maria `is_current=True`. A Agenda oferece Maria, e João continua registrado. Se João aparecer numa importação posterior, a mesma linha volta a `True`, sem linha nova.

Justificativa para não excluir: o vínculo é um fato acadêmico do semestre e será referenciado pelo `Booking` no futuro. Apagá-lo perderia o histórico e quebraria referências, enquanto a marcação resolve a disponibilidade sem perder nada. A oferta também nunca é excluída: quando as alocações somem da planilha, elas são preservadas (D13), e a oferta também.

### D4. Sem FK em `Allocation`
A oferta é identificada pela mesma tripla `(semester, subject, class_group)` que a alocação já tem. Uma FK duplicaria esses dados e poderia ficar incoerente com eles, e exigiria mudar a identidade e as leituras da Grade. Mudar dia, faixa ou espaço nunca altera a tripla, então a oferta não é afetada. As consultas entre alocação e oferta usam o índice existente `allocation_group_idx (semester, class_group)`.

### D5. Registro pela importação
`ClassOfferingManager.record(semester, subject, class_group)` faz o get-or-create da oferta e chama `offering.sync_assignments()`. Essa operação consulta os docentes das alocações atuais da oferta, cria com `bulk_create(ignore_conflicts=True)` os vínculos que faltam, marca `is_current=True` nos presentes e `is_current=False` nos ausentes, sem `delete`. `execute_activity` chama `record` depois de `Allocation.objects.apply`, inclusive quando `apply` devolve `unchanged`.

- A chamada roda no savepoint da linha: linha com erro ou pendência desfaz a oferta junto; a prévia e a divergência desfazem tudo; a confirmação grava na mesma transação da importação.
- A oferta não entra no `RowPlan`, então a comparação entre prévia e confirmação continua determinística.
- A operação é idempotente, e as restrições de unicidade garantem que nada se duplica.
- Não há auditoria própria: o registro é o resumo da importação (D13 e D15).
- Não há tela nem rota: nenhum cadastro manual estabelece vínculo.

### D6. Alteração de recorrência
`RecurrenceChange.execute` chama `ClassOffering.objects.record(...)` depois de `version.teachers.set(...)`, na transação de `change_recurrence`.

- Mudar só dia, horário ou espaço mantém a tripla e os docentes, então os vínculos não mudam.
- Trocar João por Maria cria o vínculo de Maria com `is_current=True`. João continua registrado, com `is_current=False` se não estiver em outra alocação atual da oferta.
- Nenhuma alteração de horário, espaço ou docente vira exclusão de vínculo, e a relação acadêmica sobrevive às versões da alocação.
- A recusa da alteração desfaz a transação inteira, vínculos inclusive.

### D7. Consulta da Agenda e índices
`TeachingAssignmentQuerySet.available(semester, teacher=None, subject=None, class_group=None)` filtra `is_current=True` e `offering__semester`, aplica os filtros informados e usa `select_related('teacher', 'offering__subject', 'offering__class_group__course')`. Com uma consulta só, ela atende os três sentidos (docente → disciplinas → turmas, disciplina → turmas → docentes e turma → disciplinas → docentes), agrupados em Python. `is_available(semester, teacher, subject, class_group)` é `.available(...).exists()`, para validar um envio. Só combinações gravadas aparecem: com João → Matemática → 2º período e sem João → Física → 2º período, a segunda nunca é oferecida.

Índices: `class_offering_unique` cobre `(semester, subject, class_group)`, e é acrescentado `Index(semester, class_group)`. `teaching_assignment_unique` cobre `(offering, teacher)`, e é acrescentado `Index(teacher, offering)` para a consulta a partir do docente.

### D8. Backfill
A migration de dados `0008_backfill_class_offering` percorre as alocações existentes agrupadas pela tripla, cria as ofertas e os vínculos de todos os docentes que aparecem em alguma versão, e marca `is_current` pela regra de D3. O reverso não faz nada, porque a migration de schema remove as tabelas.

## Risks / Trade-offs

- `sync_assignments` roda a cada atividade da importação, o que dá uma consulta por linha. Ela usa o índice da tripla e está limitada ao máximo de linhas da importação. → Aceito, e um cache por execução pode ser acrescentado se a medição mostrar necessidade.
- `is_current` depende de `valid_until IS NULL`. Se no futuro existir encerramento de recorrência sem versão nova, a regra precisa ser revista. → Registrado aqui.
