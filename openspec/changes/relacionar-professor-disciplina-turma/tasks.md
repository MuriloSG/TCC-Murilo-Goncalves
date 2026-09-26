## 1. Modelo

- [x] 1.1 Criar `ClassOffering` com `class_offering_unique` e o índice `(semester, class_group)`
- [x] 1.2 Criar `TeachingAssignment` com `is_current`, `teaching_assignment_unique` e o índice `(teacher, offering)`, com a semântica de `is_current` na docstring
- [x] 1.3 Implementar `ClassOfferingManager.record` e `ClassOffering.sync_assignments`, sem exclusão
- [x] 1.4 Migration `0007_class_offering` (schema) e `0008_backfill_class_offering` (dados das alocações existentes)

## 2. Importação

- [x] 2.1 Chamar `ClassOffering.objects.record` em `execute_activity` depois de `Allocation.objects.apply`, sem mudar o `RowPlan`

## 3. Alteração de recorrência

- [x] 3.1 Chamar `ClassOffering.objects.record` em `RecurrenceChange.execute` depois de gravar os docentes da versão nova

## 4. Consulta

- [x] 4.1 Implementar `TeachingAssignmentQuerySet.available` e `is_available`, só com `is_current=True`

## 5. Verificação

- [x] 5.1 Testes do modelo: unicidade, disciplina com várias turmas, turma com várias disciplinas, mesma disciplina em vários semestres, vários docentes na mesma oferta, sincronização idempotente
- [x] 5.2 Testes da importação: criação, reimportação sem duplicar, docente substituído com `is_current=False`, retorno a `is_current=True`, semestre anterior intacto, rollback da prévia, da divergência e da linha com erro
- [x] 5.3 Testes da recorrência: dia, horário e espaço mantêm os vínculos, troca de docente preserva o histórico, recusa não deixa vínculo
- [x] 5.4 Testes da consulta: só `is_current=True`, combinação inexistente não aparece, uma consulta nos três sentidos
- [x] 5.5 Teste do backfill
- [x] 5.6 Rodar `make test` e `openspec validate --strict`
