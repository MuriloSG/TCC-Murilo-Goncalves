## Why

A importação do ensalamento já cria o docente (`Teacher`), o curso (`Course`), a disciplina (`Subject`), a turma (`ClassGroup`), o semestre e as alocações. A relação "o docente João dá Banco de Dados para o 4º período de Sistemas de Informação em 2026/2", porém, só existe de forma implícita: para descobri-la é preciso percorrer as alocações e os docentes de cada uma. A Agenda vai precisar oferecer, ao criar um agendamento, só as combinações de docente, disciplina e turma que o ensalamento identificou num semestre, sem N+1 e sem oferecer combinação que nunca existiu. Esta Change prepara o domínio para isso, com a importação como fonte dos vínculos.

## What Changes

- **Oferta de disciplina** (`ClassOffering`): uma disciplina para uma turma num semestre, única por semestre, disciplina e turma. Uma disciplina tem várias turmas e uma turma tem várias disciplinas, sempre dentro de um semestre.
- **Docente da oferta** (`TeachingAssignment`): o vínculo entre um docente e uma oferta, único por oferta e docente, com `is_current`.
- **Histórico e disponibilidade atual separados**: o vínculo nunca é excluído automaticamente. `is_current=True` indica que o docente está numa alocação atual da oferta (sem fim de vigência). `is_current=False` indica um vínculo histórico preservado.
- **Importação como fonte**: cada atividade importada registra a oferta e sincroniza os docentes dela, no savepoint da linha e na transação da importação. A prévia desfaz tudo, a reimportação não duplica nada e nada é excluído.
- **Alteração de recorrência**: registra os vínculos da versão nova sem apagar os anteriores. Mudar dia, horário ou espaço não afeta os vínculos.
- **Consulta para a Agenda**: `TeachingAssignment.objects.available(...)` devolve, numa única consulta, as combinações atuais de um semestre, filtradas por docente, disciplina ou turma.
- **Backfill** das ofertas e dos vínculos a partir das alocações existentes.

### Fora do escopo

- Campos de disciplina ou turma em `Booking` e a interface da Agenda para escolhê-los.
- Cadastro ou edição manual de oferta e de vínculo.
- Vínculo entre `Teacher` e `User`, que continua como está (D7 da Change importar-ensalamento-da-planilha).
- FK de `Allocation` para a oferta.

## Capabilities

### Modified Capabilities

- `ensalamento`: entidades de oferta e de docente da oferta, vínculos estabelecidos pela importação, histórico e disponibilidade atual, preservação na alteração de recorrência e consulta de combinações válidas.

## Impact

- `schedule/models.py`: `ClassOffering`, `TeachingAssignment`, managers e chamada em `RecurrenceChange.execute`.
- `schedule/imports.py`: `execute_activity` registra a oferta depois de `Allocation.objects.apply`.
- Migrations `0007_class_offering` (schema) e `0008_backfill_class_offering` (dados).
- Testes em `schedule/tests/`.
- Nenhuma tela, rota, permissão ou registro de auditoria novo.
