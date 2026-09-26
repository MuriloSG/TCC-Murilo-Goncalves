## ADDED Requirements

### Requirement: Oferta de disciplina por semestre
O sistema DEVE (MUST) representar como entidade própria a oferta de disciplina: uma disciplina para uma turma num semestre, identificada pelo semestre, pela disciplina e pela turma. A disciplina e a turma DEVEM (MUST) continuar sendo as entidades existentes do ensalamento, válidas para todos os semestres, e o semestre DEVE (MUST) entrar na relação pela oferta. Uma disciplina PODE (MAY) ter várias turmas e uma turma PODE (MAY) ter várias disciplinas no mesmo semestre. A mesma disciplina para a mesma turma em semestres diferentes DEVE (MUST) gerar ofertas diferentes. O sistema NÃO DEVE (MUST NOT) guardar relação entre docente e disciplina fora de uma oferta.

O sistema DEVE (MUST) representar como entidade própria o docente da oferta, identificado pela oferta e pelo docente. Uma oferta PODE (MAY) ter vários docentes ou nenhum. O docente DEVE (MUST) ser a entidade existente do ensalamento, sem vínculo com usuário.

#### Scenario: Disciplina com várias turmas
- **GIVEN** o semestre `2026/2`
- **WHEN** João dá Matemática para o `1º Período A` e para o `2º Período`, e Maria dá Matemática para o `1º Período B`
- **THEN** existe uma única disciplina Matemática, com três ofertas em `2026/2`
- **AND** João está nas ofertas do `1º Período A` e do `2º Período`, e Maria na do `1º Período B`

#### Scenario: Mesma disciplina em semestres diferentes
- **GIVEN** a oferta de Matemática para o `2º Período` em `2026/1`
- **WHEN** a mesma disciplina é importada para a mesma turma em `2026/2`
- **THEN** existem duas ofertas, uma por semestre, e a de `2026/1` não muda

#### Scenario: Vários docentes na mesma oferta
- **WHEN** uma atividade de Banco de Dados do `4º período` traz os docentes João e Ana
- **THEN** a oferta tem dois vínculos, um para cada docente

### Requirement: Vínculos acadêmicos estabelecidos pela importação
A importação do ensalamento DEVE (MUST) ser a fonte das ofertas e dos vínculos de docente. Para cada atividade, ela DEVE (MUST) identificar ou criar a disciplina e a turma, registrar a oferta no semestre da importação, registrar os docentes da atividade na oferta e criar ou atualizar a alocação normalmente. O sistema NÃO DEVE (MUST NOT) exigir cadastro manual de oferta nem de vínculo, e NÃO DEVE (MUST NOT) oferecer tela para isso.

O registro DEVE (MUST) acontecer na transação da importação. A prévia, a confirmação recusada por divergência e a linha recusada NÃO DEVEM (MUST NOT) deixar oferta nem vínculo gravados. A reimportação DEVE (MUST) reaproveitar as ofertas e os vínculos existentes, sem duplicar, e NÃO DEVE (MUST NOT) alterar ofertas de outros semestres. A importação NÃO DEVE (MUST NOT) excluir oferta nem vínculo, inclusive quando a disciplina, a turma ou o docente deixam de aparecer na planilha. O registro NÃO DEVE (MUST NOT) mudar o plano das linhas.

#### Scenario: Atividade importada
- **WHEN** a importação de `2026/2` confirma uma atividade de Banco de Dados, do `4º período` de Sistemas de Informação, com o docente João
- **THEN** existem a oferta de Banco de Dados para o `4º período` em `2026/2`, o vínculo de João nela e a alocação da atividade

#### Scenario: Prévia não grava vínculo
- **WHEN** a prévia de uma importação é gerada
- **THEN** nenhuma oferta e nenhum vínculo novo permanecem gravados

#### Scenario: Linha recusada
- **WHEN** uma linha de atividade é recusada na confirmação
- **THEN** a oferta e o vínculo daquela linha não são gravados

#### Scenario: Reimportação sem duplicar
- **GIVEN** a importação confirmada de `2026/2`
- **WHEN** a mesma planilha é importada de novo
- **THEN** a quantidade de ofertas e de vínculos não muda

### Requirement: Histórico e disponibilidade atual dos docentes da oferta
O vínculo de docente DEVE (MUST) indicar se é atual. O vínculo DEVE (MUST) ser atual quando o docente está presente em alguma alocação atual da oferta, e histórico quando não está em nenhuma. Alocação atual da oferta é a alocação do mesmo semestre, disciplina e turma sem fim de vigência. O vínculo histórico DEVE (MUST) ser preservado. Um vínculo NÃO DEVE (MUST NOT) ser excluído automaticamente, e o mesmo vínculo DEVE (MUST) voltar a ser atual quando o docente voltar a uma alocação atual da oferta. Atual NÃO DEVE (MUST NOT) ser interpretado como docente responsável pela disciplina, e sim como presença nas alocações atuais.

#### Scenario: Docente substituído pela reimportação
- **GIVEN** Matemática para o `2º período` em `2026/2`, com João
- **WHEN** uma reimportação traz Maria no lugar de João em todas as aulas dessa oferta
- **THEN** o vínculo de João continua existindo e deixa de ser atual
- **AND** o vínculo de Maria é atual

#### Scenario: Docente volta a aparecer
- **GIVEN** o vínculo histórico de João com Matemática do `2º período` em `2026/2`
- **WHEN** uma importação posterior traz João de novo numa aula dessa oferta
- **THEN** o mesmo vínculo volta a ser atual, sem vínculo novo

### Requirement: Vínculos preservados na alteração de recorrência
A alteração da recorrência de uma aula DEVE (MUST) registrar na oferta os docentes da versão nova, na mesma transação da alteração. Ela NÃO DEVE (MUST NOT) excluir oferta nem vínculo. A mudança de dia, horário ou espaço NÃO DEVE (MUST NOT) alterar os vínculos. A troca de docente DEVE (MUST) tornar atual o docente novo e preservar o anterior, que deixa de ser atual quando não estiver em outra alocação atual da oferta. Uma alteração recusada NÃO DEVE (MUST NOT) deixar vínculo gravado.

#### Scenario: Mudança de horário e espaço
- **WHEN** a recorrência de Banco de Dados do `4º período` muda de dia, horário e espaço, com os mesmos docentes
- **THEN** a oferta e os vínculos continuam os mesmos, com a mesma indicação de atual

#### Scenario: Troca de docente na recorrência
- **GIVEN** a única aula de Matemática do `2º período` em `2026/2`, com João
- **WHEN** a recorrência é alterada a partir de uma data, com Maria no lugar de João
- **THEN** o vínculo de Maria é atual
- **AND** o vínculo de João continua existindo, sem ser atual

### Requirement: Consulta de combinações válidas para a Agenda
O sistema DEVE (MUST) oferecer uma consulta das combinações de docente, disciplina e turma de um semestre, filtrável por docente, por disciplina e por turma, que devolva só os vínculos atuais. Uma combinação que não existe como vínculo atual NÃO DEVE (MUST NOT) ser devolvida. A consulta DEVE (MUST) trazer docente, disciplina, turma e curso numa quantidade fixa de consultas ao banco, independente do número de resultados. Esta Change NÃO DEVE (MUST NOT) alterar o agendamento nem a interface da Agenda.

#### Scenario: Combinação inexistente
- **GIVEN** em `2026/2`, o vínculo atual de João com Matemática do `2º período`, e nenhum vínculo de João com Física do `2º período`
- **WHEN** as combinações de João em `2026/2` são consultadas
- **THEN** Matemática do `2º período` é devolvida e Física do `2º período` não

#### Scenario: Vínculo histórico fora da consulta
- **GIVEN** Maria atual e João histórico em Matemática do `2º período` em `2026/2`
- **WHEN** as combinações dessa disciplina são consultadas
- **THEN** só Maria é devolvida

#### Scenario: Consulta sem N+1
- **WHEN** as combinações de um semestre com várias ofertas e docentes são consultadas
- **THEN** o resultado completo é obtido com uma única consulta ao banco
