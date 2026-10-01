## Why

Uma aula do ensalamento só sai da Grade data a data: o cancelamento de ocorrência resolve um dia, e a alteração da recorrência move a aula, mas nenhuma das duas encerra a aula. Uma disciplina que terminou antes do fim do semestre, uma turma que foi desfeita ou uma aula cadastrada por engano continuam ocupando o espaço até 18/12, e a coordenação só tem o caminho de cancelar uma data por vez. Falta encerrar a recorrência inteira a partir de uma data, sem apagar o que já aconteceu.

## What Changes

- **Encerramento da recorrência a partir de uma data**: as alocações do bloco recebem o fim da vigência na véspera da data, e a aula deixa de gerar ocorrência dali em diante. As ocorrências anteriores continuam na Grade, na Agenda, no calendário público e na auditoria.
- **Aula que ainda não começou**: quando a data do encerramento é a primeira da vigência ou anterior a ela, a aula fica sem nenhuma ocorrência. A vigência passa a admitir um fim anterior ao início, com esse significado, e a `CheckConstraint` que exigia o fim igual ou posterior ao início sai.
- **Regras da data**: de hoje em diante, no período do semestre e ocorrência da regra atual, as mesmas da alteração da recorrência, menos a exigência de ser posterior ao início da vigência.
- **Nada é excluído**: as alocações continuam no banco, a regra que proíbe excluir alocação permanece e a reimportação não recria a aula encerrada, porque ela passa a ter vigência definida.
- **Permissão** `ENSALAMENTO.ENCERRAR_RECORRENCIA`, concedida ao perfil de sistema `ADMINISTRADOR`, separada de `ENSALAMENTO.ALTERAR_RECORRENCIA`, de `ENSALAMENTO.CRIAR_RECORRENCIA` e de `ENSALAMENTO.CANCELAR_OCORRENCIA`.
- **Interface**: ação "Encerrar recorrência" no card da Grade datada, de hoje em diante, com confirmação que diz quantas aulas deixam de existir, a partir de quando e que as anteriores continuam.
- **Auditoria**: registro `ALTERAR` no módulo `ENSALAMENTO` por alocação encerrada, com o fim da vigência, a data do encerramento e a quantidade de aulas encerradas.

### Fora do escopo

- Excluir as alocações do banco, que a spec continua proibindo, e desfazer um encerramento, que é a alteração da recorrência ou um cadastro novo.
- Mudar o cancelamento de uma ocorrência, que continua como está, e reativar uma ocorrência cancelada.
- Encerrar várias aulas de uma vez, encerrar por docente e notificar quem é afetado.

### Dependência

Esta Change parte das Changes `alterar-recorrencia-do-ensalamento`, já arquivada, e `criar-recorrencia-do-ensalamento`, de onde vêm a vigência, as conferências da data e o padrão de confirmação. A Change `criar-recorrencia-do-ensalamento` DEVE ser arquivada antes desta.

## Capabilities

### Modified Capabilities

- `ensalamento`: encerramento da recorrência, vigência sem nenhuma ocorrência e reimportação que preserva a aula encerrada.
- `controle-acesso`: permissão `ENSALAMENTO.ENCERRAR_RECORRENCIA`.
- `auditoria`: registro do encerramento da recorrência.

## Impact

- `schedule/models.py`: `end_recurrence` e `plan_ending` no `AllocationManager`, a `CheckConstraint` da vigência e o texto da regra na docstring.
- `schedule/views.py`, `schedule/urls.py`, `schedule/templates/schedule/partials/timetable_cell.html` e os templates da confirmação.
- `accounts/permissions.py`, `audit/catalog.py`, `ui/styles/app.css`.
- Migrations `schedule/0009_allocation_validity_without_occurrence` e `accounts/0016_end_recurrence_permission`.
