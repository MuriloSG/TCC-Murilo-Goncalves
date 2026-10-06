## ADDED Requirements

### Requirement: Quantidade de alunos na solicitação
A solicitação de agendamento DEVE (MUST) pedir a quantidade de alunos, um inteiro de 1 a 999, nos modais "Solicitar agendamento" e "Criar solicitação para outro usuário". A operação do model DEVE (MUST) recusar o valor ausente ou fora da faixa, sem gravar nada. A quantidade DEVE (MUST) aparecer na revisão antes do envio, no detalhe da solicitação para o solicitante e para quem analisa, e nas listas de solicitações. O agendamento criado na aprovação ou no aceite da alternativa DEVE (MUST) guardar a mesma quantidade.

#### Scenario: Quantidade informada
- **WHEN** Ana solicita o Laboratório de Informática 2 informando 30 alunos
- **THEN** a solicitação é criada com 30 alunos, e o detalhe da análise mostra "Quantidade de alunos" com 30

#### Scenario: Quantidade ausente ou inválida
- **WHEN** Ana envia a solicitação sem a quantidade ou com 0
- **THEN** o formulário mostra o erro no campo e nenhuma solicitação é criada

#### Scenario: Aprovação
- **GIVEN** uma solicitação pendente com 30 alunos
- **WHEN** quem analisa a aprova
- **THEN** o agendamento criado tem 30 alunos

#### Scenario: Solicitação antiga
- **GIVEN** uma solicitação criada antes desta Change
- **WHEN** o detalhe é aberto
- **THEN** a quantidade aparece como "—"
