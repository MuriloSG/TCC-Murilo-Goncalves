## Why

A sala 1/3 está cadastrada e ativa, mas não tem aula no semestre, e por isso não aparecia na Grade do Ensalamento nem no calendário público. Quem consulta o horário não conseguia ver que a sala está disponível a semana toda.

## What Changes

- A escolha de sala da Grade do Ensalamento e do calendário público passa a listar **todos os espaços ativos**, com ou sem aula, mais os inativos que têm aula no semestre.
- Uma sala sem aula mostra a Grade com as faixas do semestre e as células vazias.
- A regra fica numa função só, `listed_spaces()` em `schedule/timetable.py`, usada pelas duas telas.

### Fora do escopo

- Espaços inativos sem aula continuam fora das opções.
- A Agenda não muda: ela já lista todos os espaços ativos.

## Capabilities

### Modified Capabilities

- `calendario-publico`: as opções de sala incluem os espaços ativos sem alocação.

A Grade autenticada do Ensalamento segue a mesma regra; o requisito dela ainda está na Change `visualizar-grade-do-ensalamento`, que não foi arquivada.

## Impact

- `schedule/timetable.py`: `listed_spaces()` e `spaces_of()`.
- `schedule/public.py`: `semester_options()`.
- Testes em `schedule/tests/test_timetable.py` e `schedule/tests/test_spaces_without_lessons.py`.
- Sem migration.
