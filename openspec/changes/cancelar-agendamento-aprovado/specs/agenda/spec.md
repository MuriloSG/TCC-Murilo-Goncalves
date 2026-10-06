## ADDED Requirements

### Requirement: Cancelamento de agendamento aprovado
O sistema DEVE (MUST) permitir cancelar uma solicitação de agendamento aprovada enquanto faltar mais de 1 hora para o início do agendamento. Podem cancelar quem solicitou e quem tem `AGENDA.ANALISAR`. O cancelamento DEVE (MUST) passar a solicitação para `CANCELADA`, guardar quem cancelou, quando e o motivo, que é opcional, e excluir o agendamento, de modo que o espaço fique disponível na Agenda, na Grade, no calendário público e no painel. O cancelamento NÃO DEVE (MUST NOT) ser aceito em outro estado, a menos de 1 hora do início nem por outro usuário sem `AGENDA.ANALISAR`, e a recusa NÃO DEVE (MUST NOT) alterar dados. O botão "Cancelar agendamento" DEVE (MUST) aparecer no detalhe da solicitação para quem solicitou e no detalhe da análise, só quando o cancelamento é possível. O cancelamento DEVE (MUST) notificar a outra parte: quem aprovou, quando quem solicitou cancela, e quem solicitou, quando quem analisa cancela.

#### Scenario: Quem solicitou cancela
- **GIVEN** o agendamento aprovado de Ana no Laboratório de Informática 2 em 15/10/2026, das 14:00 às 16:00
- **WHEN** Ana cancela às 10:00 de 15/10/2026
- **THEN** a solicitação fica cancelada, o agendamento é excluído, o laboratório fica disponível das 14:00 às 16:00 e quem aprovou recebe "Agendamento cancelado"

#### Scenario: Quem analisa cancela
- **WHEN** um usuário com `AGENDA.ANALISAR` cancela o agendamento de Ana informando o motivo
- **THEN** a solicitação fica cancelada com o motivo, e Ana recebe "Agendamento cancelado"

#### Scenario: Menos de 1 hora para o início
- **WHEN** Ana tenta cancelar às 13:30 o agendamento das 14:00
- **THEN** o cancelamento é recusado com "O agendamento só pode ser cancelado até 1 hora antes do início." e o agendamento continua

#### Scenario: Estado sem agendamento
- **WHEN** alguém tenta cancelar uma solicitação pendente, rejeitada ou já cancelada
- **THEN** o cancelamento é recusado e nada muda

#### Scenario: Outro usuário
- **WHEN** um docente sem `AGENDA.ANALISAR` tenta cancelar a solicitação de Ana
- **THEN** a rota responde 404 e a operação do model recusa
