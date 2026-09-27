## Why

A importação do ensalamento só cadastrava as salas da lista da planilha que tinham aula. As salas sem aula no semestre ficavam fora do cadastro e, por isso, não apareciam nos calendários do sistema, e quem consulta o horário não conseguia ver que elas estão livres a semana toda.

## What Changes

- Toda sala da lista de salas da planilha passa pela classificação dos espaços, com ou sem aula. A sala sem aula que não identifica espaço e não tem parecido é cadastrada ativa e sem alocação; os calendários já mostram a grade vazia de todo espaço ativo (Change `listar-salas-sem-aula`).
- A sala sem aula com nome parecido vira pendência, como as demais, para não cadastrar duplicado. Ela não torna ambíguo o nome de uma sala usada por aula.
- A sala sem aula que identifica um espaço inativo fica como está, porque a desativação é decisão do cadastro.
- Sai o aviso `sala_sem_aula` e a linha do quadro de espaços que contava as salas sem aula. O uso do nome sem aula aparece como "Sem aula nesta planilha".

### Fora do escopo

- A Grade, a Agenda e o calendário público não mudam.

## Capabilities

### Modified Capabilities

- `ensalamento`: o catálogo de espaços da planilha cadastra as salas sem aula.

A classificação dos espaços segue a mesma regra; o requisito dela ainda está na Change `manipulacao-dos-espacos`, que não foi arquivada e foi atualizada junto.

## Impact

- `schedule/spaces.py`: `read_found()` e `candidates_of()`; `Resolution` perde `unused`.
- `schedule/imports.py`: `execute_space()`, sem `unused_space_plan()` e sem o aviso `sala_sem_aula`.
- `schedule/views.py`: `usage_text()` e o quadro de espaços da prévia.
- Com a planilha corrigida, `Lab. Química` passa a precisar de decisão na primeira importação.
- Sem migration.
