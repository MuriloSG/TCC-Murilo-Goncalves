## Why

O calendário público mostra a Grade datada, já com as alterações de recorrência, as ocorrências canceladas e os agendamentos. Quem consulta não tinha como ver o horário original do semestre: a aula de Matemática de toda segunda some na data cancelada e não há onde conferir que ela continua sendo de segunda.

## What Changes

- Nova rota pública `/horario-original/`, com view, template e consulta próprios, sem login, só GET e HEAD.
- A tela mostra a semana típica, por dia da semana e sem datas, só com as alocações importadas (`Origin.IMPORTED`), ignorando a vigência, os cancelamentos e os agendamentos.
- Os filtros são os do calendário público (semestre, sala, docente, curso, nível e turma), sem as datas.
- O calendário público ganha o botão "Ver horário original", e a tela original o botão "Ver calendário atual", mantendo os filtros escolhidos.
- A leitura dos filtros passa para `read_filters()` em `schedule/public.py`, usada pelas duas telas.

## Capabilities

### Modified Capabilities

- `calendario-publico`: horário original em rota pública própria.

## Impact

- `schedule/public.py`, `schedule/public_views.py`, `schedule/forms.py`, `schedule/urls.py`.
- Templates `schedule/public/` divididos em `filters.html` e `grid.html`, e o novo `original.html`.
- `openspec/conventions.md`: duas rotas públicas.
- Testes em `schedule/tests/test_public_calendar.py` e `accounts/tests/test_route_protection.py`.
- Sem migration.
