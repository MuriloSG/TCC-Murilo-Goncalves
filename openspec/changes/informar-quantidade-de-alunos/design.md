## Context

A solicitação passa por `BookingRequestManager.prepare`, que confere tudo sem gravar, e por `submit`, que grava. Os dois são chamados por `BookingRequestCreateView` e por `BookingOnBehalfCreateView`, que repassam os campos de `REQUEST_FIELDS` como ocultos na revisão.

## Decisions

### D1. Campo anulável no banco, obrigatório na operação
As solicitações e os agendamentos que já existem não têm a quantidade. Por isso a coluna é `null=True`, e `prepare` recusa o valor ausente com "Informe a quantidade de alunos.". As telas mostram "—" nos registros antigos.

### D2. Faixa de 1 a 999
`PositiveSmallIntegerField` com `MinValueValidator(1)` e `MaxValueValidator(999)`. O formulário repete a faixa, e o model confere de novo pelo `full_clean`.

### D3. Cópia no agendamento
`Booking` guarda a própria quantidade, copiada em `BookingManager.book`, como já faz com a descrição. Assim o agendamento continua completo sem depender da solicitação.
