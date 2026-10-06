## 1. Modelo

- [x] 1.1 Estado `CANCELADA` e os campos `cancelled_by`, `cancelled_at` e `cancellation_reason` (migration `bookings/0003_cancellation`)
- [x] 1.2 `BookingRequest.can_cancel` e `BookingRequest.cancel`, com o prazo de 1 hora, a exclusão do agendamento e a auditoria
- [x] 1.3 Notificação `AGENDA_CANCELADA` para a outra parte

## 2. Interface

- [x] 2.1 Rotas e modal "Cancelar agendamento" para quem solicitou e para quem analisa
- [x] 2.2 Selo "Cancelada", evento no histórico e motivo no detalhe
- [x] 2.3 Situação cancelada no relatório de solicitações

## 3. Testes

- [x] 3.1 Regras do cancelamento no model, notificação e auditoria
- [x] 3.2 Rotas, botão e relatório
