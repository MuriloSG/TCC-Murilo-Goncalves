## Context

A solicitação aprovada tem um `Booking` ligado a ela, com o espaço e o intervalo efetivos: os originais, na aprovação, ou os sugeridos, no aceite da alternativa. Todas as leituras de ocupação (`find_conflict`, `BookingSource`, o calendário público e o painel) e a `ExclusionConstraint` olham só para `Booking`.

## Decisions

### D1. O agendamento é excluído
O cancelamento exclui o `Booking` e passa a solicitação para `CANCELADA`. Assim nenhuma leitura de ocupação nem a restrição de exclusão precisa de filtro novo, e o espaço fica disponível no mesmo instante. O histórico fica na solicitação (`cancelled_by`, `cancelled_at`, `cancellation_reason`) e na auditoria, que registra a transição e a exclusão do agendamento com o espaço, a data e o horário.

### D2. Quem cancela
Quem solicitou, com `AGENDA.SOLICITAR`, e quem tem `AGENDA.ANALISAR`, sem permissão nova. A rota do solicitante carrega só as próprias solicitações (404 nas demais), e a da análise exige `AGENDA.ANALISAR`. A operação do model confere de novo.

### D3. Prazo de 1 hora
O cancelamento é aceito enquanto faltar mais de 1 hora para o início do agendamento (`CANCEL_DEADLINE`), para todos. O início vem do `Booking`, o que cobre a alternativa aceita. O prazo é fixo no código; um prazo configurável fica para quando houver pedido.

### D4. Motivo opcional
O motivo vai num campo de texto do modal, com o limite de 500 caracteres da rejeição, e aparece no detalhe e na auditoria.

### D5. Notificação para a outra parte
Quem cancela não é notificado. Quando quem solicitou cancela, a notificação vai para quem aprovou, ou para os demais que analisam quando ele está inativo ou sem a permissão, a mesma regra do aceite da alternativa (`deciders`). Quando quem analisa cancela, vai para quem solicitou.
