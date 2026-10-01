## ADDED Requirements

### Requirement: Item do painel no menu
O menu lateral DEVE (MUST) ter o item "Painel" em primeiro lugar, com um ícone da biblioteca Lucide, levando a `painel/` e liberado por `PAINEL.VISUALIZAR`. Como a página aberta depois do login é o primeiro item liberado, quem tem a permissão DEVE (MUST) abrir o painel depois do login, e quem não tem DEVE (MUST) continuar abrindo o primeiro módulo liberado.

#### Scenario: Administrador abre o painel depois do login
- **GIVEN** um usuário com `PAINEL.VISUALIZAR` e `ENSALAMENTO.VISUALIZAR`
- **WHEN** ele abre `inicio/`
- **THEN** ele é redirecionado a `painel/`

#### Scenario: Docente continua na Agenda
- **GIVEN** um usuário com `AGENDA.VISUALIZAR` e sem `PAINEL.VISUALIZAR`
- **WHEN** ele abre `inicio/`
- **THEN** ele é redirecionado a `agenda/` e o menu não tem o item "Painel"
