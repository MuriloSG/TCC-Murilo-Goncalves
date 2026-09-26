## ADDED Requirements

### Requirement: Cadastro manual sem vínculo acadêmico
O cadastro, a edição e a exclusão de disciplina ou turma pelas telas de Disciplinas e Turmas NÃO DEVEM (MUST NOT) criar, alterar nem excluir oferta de disciplina ou vínculo de docente: a relação entre docente, disciplina, turma e semestre continua estabelecida só pelo ensalamento. A importação do ensalamento DEVE (MUST) continuar identificando disciplina e turma pelo nome, sem diferenciar a caixa, e reaproveitar o registro cadastrado manualmente com o mesmo nome.

#### Scenario: Importação reaproveita o cadastro manual
- **GIVEN** a disciplina `Robótica Educacional` cadastrada pela tela de Disciplinas
- **WHEN** uma importação traz `robótica educacional` para o 1º ano com o docente `joao`
- **THEN** nenhuma disciplina nova é criada, e a oferta e o vínculo atual de `joao` nascem pela importação

#### Scenario: Cadastro manual fora da Agenda
- **GIVEN** a disciplina `Artes` e a turma `6º período` cadastradas pelas telas
- **WHEN** a Agenda consulta as combinações atuais do semestre para o docente `joao`
- **THEN** nenhuma combinação com elas é oferecida
