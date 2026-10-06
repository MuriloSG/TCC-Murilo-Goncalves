## 1. Modelo

- [x] 1.1 Criar `student_count` em `BookingRequest` e `Booking` (migration `bookings/0002_student_count`)
- [x] 1.2 Receber `student_count` em `prepare` e `submit`, recusando o valor ausente, e registrá-lo na auditoria
- [x] 1.3 Copiar a quantidade para o agendamento em `BookingManager.book`

## 2. Interface

- [x] 2.1 Campo "Quantidade de alunos" nos dois formulários de solicitação
- [x] 2.2 Mostrar a quantidade na revisão, no detalhe e nas listas

## 3. Testes

- [x] 3.1 Quantidade obrigatória e dentro da faixa, no model e na tela
- [x] 3.2 Quantidade no detalhe da análise, na auditoria e no agendamento aprovado
