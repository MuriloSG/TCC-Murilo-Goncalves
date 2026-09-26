## ADDED Requirements

### Requirement: Vínculo acadêmico da solicitação
Quem solicita um agendamento DEVE (MUST) ser o docente do ensalamento que corresponde ao usuário, reconhecido pelo nome do docente igual ao `username`, sem diferenciar a caixa. Um usuário que não corresponde a nenhum docente NÃO DEVE (MUST NOT) conseguir criar solicitação, e o modal DEVE (MUST) avisar isso. Toda solicitação DEVE (MUST) informar uma turma do docente, e a turma DEVE (MUST) ser um vínculo atual dele no semestre, estabelecido pela importação do ensalamento. A solicitação DEVE (MUST) guardar o vínculo, e não cópias do docente, da disciplina, da turma ou do semestre. O sistema NÃO DEVE (MUST NOT) aceitar vínculo de outro docente, de outro semestre ou histórico. A conferência DEVE (MUST) acontecer no backend a cada envio, e IDs adulterados na requisição DEVEM (MUST) passar pelas mesmas regras. A recusa NÃO DEVE (MUST NOT) gravar nada.

A data DEVE (MUST) estar no período do semestre, e um semestre sem período DEVE (MUST) ser recusado. A solicitação NÃO DEVE (MUST NOT) alterar o ensalamento, e a pendente NÃO DEVE (MUST NOT) ocupar o horário.

#### Scenario: Turma do próprio docente
- **GIVEN** o usuário `ana`, docente com Redes do `2º ANO A` em `2026/2`
- **WHEN** ela solicita o espaço para essa turma, numa data do período e num horário disponível
- **THEN** existe uma solicitação `PENDENTE` com esse vínculo e nenhum agendamento

#### Scenario: Turma de outro docente
- **GIVEN** Érica com Física do `2º ANO A` em `2026/2`, e Ana sem essa turma
- **WHEN** a requisição de Ana traz o vínculo de Érica
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Turma de outro semestre
- **GIVEN** Ana deu Física para o `2º ANO A` em `2026/1`
- **WHEN** a requisição traz esse vínculo com o semestre `2026/2`
- **THEN** a solicitação é recusada e nada é gravado

#### Scenario: Usuário que não é docente
- **WHEN** um usuário sem docente correspondente abre "Solicitar agendamento" ou envia a solicitação
- **THEN** o modal avisa que só docentes solicitam agendamento, e nada é gravado

#### Scenario: Data fora do período
- **WHEN** a solicitação é enviada para 07/01/2027 no semestre `2026/2`, que termina em 18/12/2026
- **THEN** a solicitação é recusada no campo da data e nada é gravado

### Requirement: Formulário da solicitação com as turmas do docente
O modal "Solicitar agendamento" DEVE (MUST) pedir, nesta ordem, disciplina, turma, espaço, data, início, fim e descrição, sem campo de docente e sem campo de semestre. O semestre DEVE (MUST) ser o da Agenda: o semestre com período que contém a data, calculado no servidor a cada envio, e a data fora de qualquer semestre DEVE (MUST) ser recusada. A disciplina DEVE (MUST) listar as disciplinas dos vínculos atuais do docente logado nesse semestre, e a turma DEVE (MUST) listar só as turmas do docente na disciplina escolhida, nenhuma de outro docente. A troca da data ou da disciplina DEVE (MUST) atualizar as opções seguintes sem fechar o modal. A faixa da Grade da Agenda DEVE (MUST) preencher o espaço, a data, o início e o fim, e todos PODEM (MAY) ser trocados. As faixas de horário do semestre DEVEM (MUST) aparecer como sugestão de início e de fim.

O primeiro envio DEVE (MUST) conferir a solicitação e mostrar a revisão com todos os dados, sem gravar. Só o envio da revisão DEVE (MUST) criar a solicitação, conferindo tudo de novo.

#### Scenario: Disciplina e turmas do docente logado
- **GIVEN** em `2026/2`, Ana com Redes do `2º ANO A` e Banco de Dados do `3º ANO A`, e Érica com Física do `2º ANO A`
- **WHEN** Ana abre "Solicitar agendamento" numa data de `2026/2` e escolhe Redes
- **THEN** a disciplina oferece Redes e Banco de Dados, e não Física
- **AND** a turma oferece só o `2º ANO A (INFORMÁTICA)`

#### Scenario: Semestre da Agenda
- **WHEN** o docente escolhe na Grade a faixa de 15/10/2026 das 16:00 às 18:00 do `Laboratório de Informática 2`
- **THEN** o modal mostra esse espaço, a data e o horário, com o semestre `2026/2` indicado na data e sem campo de semestre
- **AND** um semestre enviado na requisição é ignorado

#### Scenario: Revisão antes do envio
- **WHEN** o docente preenche o formulário e escolhe "Revisar solicitação"
- **THEN** o modal mostra o semestre, o docente, a turma, a disciplina, o espaço, a data e o horário e a descrição, e nenhuma solicitação existe
- **AND** "Enviar solicitação" cria a solicitação pendente
