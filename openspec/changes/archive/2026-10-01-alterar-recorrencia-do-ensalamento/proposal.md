## Why

A alocação é a regra semanal de uma aula no semestre inteiro, e a única forma de mudá-la hoje é a reimportação, que reescreve também as semanas que já passaram. O cancelamento de uma ocorrência (Change `cancelar-ocorrencia-do-ensalamento`, entregue sem artefatos próprios) resolve uma data, mas não uma mudança duradoura: quando a aula de segunda passa da HV 1 para a HV 2 a partir de 05/10, o sistema precisa mostrar a HV 1 até 04/10 e a HV 2 dali em diante, sem perder o histórico, sem duas aulas na mesma data e sem que uma nova importação desfaça a decisão.

## What Changes

- **Vigência da alocação**: `valid_from` e `valid_until`, vazios na alocação da planilha. A ocorrência passa a exigir a data dentro da vigência, em `Allocation.occurs_on` e em `Allocation.objects.active_on`, as duas regras que a Grade, a Agenda e o calendário público já usam.
- **Alteração da recorrência a partir de uma data**: a alocação é encerrada na véspera e uma versão nova começa na data, com dia da semana, horário, espaço e docentes informados e o resto copiado. Tudo numa transação, com auditoria.
- **Regras da data**: de hoje em diante, no período do semestre, ocorrência da regra atual e posterior ao início da vigência.
- **Conflitos na alteração**: recusa quando o espaço está ocupado por outra aula que forma choque (disciplina ou docentes diferentes) ou por agendamento aprovado, em alguma ocorrência não cancelada da versão nova. A turma junta é aceita. A importação continua sem detectar conflito.
- **Exceções**: as anteriores ao corte ficam na versão encerrada; as do corte em diante passam para a versão nova, ou a alteração é recusada quando a data não é ocorrência dela.
- **Reimportação**: uma identidade com versão manual não é alterada nem recriada pela planilha, e a linha recebe um aviso.
- **Permissão** `ENSALAMENTO.ALTERAR_RECORRENCIA`, concedida ao perfil `ADMINISTRADOR` de sistema, separada de `ENSALAMENTO.CANCELAR_OCORRENCIA`.
- **Interface**: ação "Alterar recorrência" no card da Grade datada, de hoje em diante, com formulário em modal e resumo "Antes / A partir de / Depois" antes da confirmação.
- **Auditoria** no módulo novo `ENSALAMENTO`, com a alocação original, o corte, os campos alterados e a alocação nova. O histórico administrativo é a consulta da auditoria.

### Fora do escopo

- Encerrar a recorrência inteira sem versão nova, transferência automática de aulas, outros tipos de exceção, edição por docente, notificações e tela própria de histórico.
- Relação entre alocação e usuário.

## Capabilities

### Modified Capabilities

- `ensalamento`: vigência da alocação, ocorrências dentro da vigência, conflito só na alteração manual, reimportação que preserva a versão manual, alteração da recorrência e o cancelamento de ocorrência, que ainda não estava na spec.
- `controle-acesso`: permissão `ENSALAMENTO.ALTERAR_RECORRENCIA`.
- `auditoria`: registro da alteração da recorrência e da transferência de exceção.

## Impact

- `schedule/models.py`: campos, restrições, `occurs_on`, `active_on`, `apply`, `plan_recurrence` e `change_recurrence`.
- `schedule/imports.py`, `schedule/public.py`, `schedule/forms.py`, `schedule/views.py`, `schedule/urls.py`, `schedule/timetable.py` e templates da Grade e do modal.
- `accounts/permissions.py`, `audit/catalog.py`, `ui/styles/app.css`.
- Migrations `schedule/0006_allocation_validity` e `accounts/0012_change_recurrence_permission`.
