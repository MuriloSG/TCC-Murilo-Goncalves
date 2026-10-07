## Why

O cadastro da aula deixa escolher a duração em faixas seguidas, mas a alteração da recorrência só troca o horário mantendo a mesma quantidade de faixas (D2 da Change `alterar-recorrencia-do-ensalamento`). Para estender ou encurtar uma aula a partir de uma data, era preciso encerrar a recorrência e cadastrar outra.

## What Changes

- O formulário "Alterar recorrência" passa a ter "Horário de início" e "Duração", como o cadastro, com a duração atual já escolhida.
- A alteração aceita outra quantidade de faixas seguidas. As faixas que continuam seguem a regra atual: a alocação é encerrada na véspera e a versão nova começa na data.
- Quando a duração aumenta, cada faixa a mais ganha uma alocação nova, com auditoria de criação e com as ocorrências canceladas da aula da data em diante.
- Quando a duração diminui, as faixas que sobram são só encerradas na véspera da data, com auditoria do fim da vigência.

### Fora do escopo

- Duração diferente em semanas alternadas.
- Criar faixa de horário fora das do semestre.

## Capabilities

### Modified Capabilities

- `ensalamento`: alteração da recorrência com outra duração.

## Impact

- `schedule/models.py` (`plan_recurrence`, `change_recurrence`, `RecurrenceAddition`, `RecurrenceRemoval`, `RecurrencePlan.removals`).
- `schedule/forms.py` (`RecurrenceChangeForm.duracao`, `duration_choices`) e `schedule/views.py`.
