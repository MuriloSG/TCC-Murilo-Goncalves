# gestao-academica Specification

## Purpose
TBD - created by archiving change gerenciar-disciplinas-e-turmas. Update Purpose after archive.
## Requirements
### Requirement: Escopo de disciplinas e turmas
As disciplinas e as turmas de um usuário DEVEM (MUST) ser as que aparecem numa oferta de disciplina em que o docente correspondente ao usuário, reconhecido pelo nome igual ao `username` sem diferenciar a caixa, tem vínculo atual ou histórico. Usuário sem docente correspondente NÃO DEVE (MUST NOT) ter disciplina nem turma no escopo. O superadmin DEVE (MUST) ter acesso a todas as disciplinas e turmas, sem filtro de escopo. O escopo DEVE (MUST) ser aplicado na consulta ao banco, e NÃO DEVE (MUST NOT) existir relação gravada nova entre usuário e disciplina, turma ou curso.

#### Scenario: Docente vê só as próprias disciplinas
- **GIVEN** o usuário `joao` com `DISCIPLINA.VISUALIZAR`, o docente `joao` vinculado à oferta de Matemática e nenhuma oferta de Física com ele
- **WHEN** ele acessa a lista de disciplinas
- **THEN** Matemática é listada e Física não

#### Scenario: Vínculo histórico mantém o escopo
- **GIVEN** o docente `joao` com vínculo `is_current=False` na oferta de Química
- **WHEN** o usuário `joao` acessa a lista de disciplinas
- **THEN** Química é listada

#### Scenario: Usuário sem docente correspondente
- **GIVEN** um usuário com `TURMA.VISUALIZAR` cujo `username` não corresponde a nenhum docente
- **WHEN** ele acessa a lista de turmas
- **THEN** a lista mostra "Nenhuma turma cadastrada."

#### Scenario: Superadmin vê todos os registros
- **GIVEN** 30 disciplinas e 12 turmas, parte delas sem nenhuma oferta
- **WHEN** o superadmin acessa as listas
- **THEN** todas as 30 disciplinas e as 12 turmas são alcançáveis pela paginação

### Requirement: Acesso direto fora do escopo
Detalhe, edição e exclusão de disciplina ou turma fora do escopo DEVEM (MUST) responder 404, por GET e por POST, sem alterar dados, mesmo quando o usuário tem a permissão da operação. Esconder links na interface NÃO DEVE (MUST NOT) ser a única proteção.

#### Scenario: Detalhe por URL fora do escopo
- **GIVEN** o usuário `joao` com `DISCIPLINA.VISUALIZAR` e a disciplina Física fora do escopo dele
- **WHEN** ele acessa `disciplinas/<pk de Física>/`
- **THEN** a resposta é 404

#### Scenario: Edição forjada fora do escopo
- **GIVEN** o usuário `joao` com `TURMA.EDITAR` e a turma 3º período fora do escopo dele
- **WHEN** ele envia por POST um rótulo novo para essa turma
- **THEN** a resposta é 404 e a turma não muda

#### Scenario: Exclusão forjada fora do escopo
- **GIVEN** o usuário `joao` com `DISCIPLINA.EXCLUIR` e a disciplina Física fora do escopo dele e sem aulas
- **WHEN** ele envia por POST a exclusão de Física
- **THEN** a resposta é 404 e Física continua cadastrada

### Requirement: Lista de disciplinas e de turmas
As listas DEVEM (MUST) mostrar só o escopo do usuário, paginadas, com busca pelo nome da disciplina ou pelo rótulo e pelo curso da turma, filtro de curso nas turmas, o número de ofertas e de aulas de cada registro e as ações permitidas pelas permissões do usuário. Sem registros DEVEM (MUST) mostrar "Nenhuma disciplina cadastrada." ou "Nenhuma turma cadastrada.", e com filtro sem resultado "Nenhuma disciplina encontrada." ou "Nenhuma turma encontrada.".

#### Scenario: Busca na lista de turmas
- **GIVEN** o superadmin e as turmas `1º período` de Agronomia e `2º período` de Informática
- **WHEN** ele busca por `agro`
- **THEN** só a turma de Agronomia é listada

### Requirement: Detalhe de disciplina e de turma
O detalhe DEVE (MUST) mostrar os dados do registro e as ofertas por semestre, com as turmas ou as disciplinas e os docentes de cada uma, identificando só o vínculo histórico, com o docente atual mostrado apenas pelo nome.

#### Scenario: Detalhe da disciplina
- **GIVEN** a disciplina Matemática ofertada em 2026/2 para o 2º período com o docente `joao` atual
- **WHEN** o usuário `joao` abre o detalhe
- **THEN** são exibidos 2026/2, 2º período e `joao`, sem a palavra "atual"

### Requirement: Cadastro de disciplina e de turma
Cadastrar disciplina DEVE (MUST) exigir `DISCIPLINA.CRIAR` e cadastrar turma DEVE (MUST) exigir `TURMA.CRIAR`. A disciplina DEVE (MUST) ter nome, e a turma curso existente e rótulo, com a normalização e a unicidade sem diferenciar a caixa já existentes. O cadastro NÃO DEVE (MUST NOT) criar oferta de disciplina nem vínculo de docente, porque a relação acadêmica é derivada do ensalamento.

#### Scenario: Cadastro válido
- **GIVEN** um usuário com `DISCIPLINA.CRIAR`
- **WHEN** ele cadastra a disciplina `  Artes   Visuais `
- **THEN** a disciplina `Artes Visuais` é criada, sem nenhuma oferta, e a mensagem é "Disciplina Artes Visuais cadastrada."

#### Scenario: Disciplina duplicada
- **GIVEN** a disciplina `Matemática`
- **WHEN** um usuário com `DISCIPLINA.CRIAR` cadastra `matemática`
- **THEN** o cadastro é recusado com "Já existe disciplina com este nome." e nada é criado

#### Scenario: Turma duplicada no curso
- **GIVEN** a turma `2º período` de Agronomia
- **WHEN** um usuário com `TURMA.CRIAR` cadastra `2º PERÍODO` em Agronomia
- **THEN** o cadastro é recusado com "Já existe uma turma com este rótulo neste curso."

#### Scenario: Cadastro inválido
- **WHEN** um usuário com `TURMA.CRIAR` envia o cadastro com o rótulo em branco
- **THEN** o formulário mostra o erro e nada é criado

### Requirement: Edição de disciplina e de turma
Editar DEVE (MUST) exigir `DISCIPLINA.EDITAR` ou `TURMA.EDITAR` e o registro no escopo. A disciplina PODE (MAY) ter o nome alterado e a turma o rótulo, com a mesma validação do cadastro. A renomeação DEVE (MUST) ser recusada no backend, com mensagem e sem alterar dados, quando o registro tem oferta ou aula no ensalamento, porque a próxima importação criaria outro cadastro com o nome da planilha. O curso da turma NÃO DEVE (MUST NOT) ser alterado, e um curso forjado DEVE (MUST) ser recusado com "O curso da turma não pode ser alterado.". Salvar o mesmo valor NÃO DEVE (MUST NOT) alterar nada.

#### Scenario: Superadmin renomeia registro sem uso
- **GIVEN** a disciplina Robótica sem oferta e sem aula, fora do escopo de qualquer docente
- **WHEN** o superadmin altera o nome para `Robótica I`
- **THEN** a disciplina passa a se chamar `Robótica I`

#### Scenario: Renomeação de disciplina com aula
- **GIVEN** a disciplina Matemática com aula no ensalamento, no escopo do usuário com `DISCIPLINA.EDITAR`
- **WHEN** ele envia o nome `Matemática I`
- **THEN** a edição é recusada com mensagem que diz que a disciplina não pode ser renomeada e o nome continua `Matemática`

#### Scenario: Curso forjado na edição
- **GIVEN** a turma `1º ano` de Informática
- **WHEN** o superadmin envia a edição com o curso Agronomia
- **THEN** a edição é recusada com "O curso da turma não pode ser alterado." e a turma não muda

### Requirement: Exclusão de disciplina e de turma
Excluir DEVE (MUST) exigir `DISCIPLINA.EXCLUIR` ou `TURMA.EXCLUIR` e o registro no escopo, com confirmação por GET e execução por POST com CSRF. A exclusão DEVE (MUST) ser recusada com mensagem, sem alterar dados, quando o registro tem oferta ou aula no ensalamento. As restrições `PROTECT` existentes NÃO DEVEM (MUST NOT) ser alteradas, e a exclusão NÃO DEVE (MUST NOT) remover ofertas nem vínculos.

#### Scenario: Exclusão sem uso
- **GIVEN** a disciplina Robótica sem oferta e sem aula
- **WHEN** o superadmin confirma a exclusão
- **THEN** Robótica é excluída e a mensagem é "Disciplina Robótica excluída."

#### Scenario: Exclusão de disciplina com aula
- **GIVEN** a disciplina Física com aula no ensalamento
- **WHEN** o superadmin confirma a exclusão
- **THEN** a exclusão é recusada com "A disciplina Física tem ofertas ou aulas no ensalamento e não pode ser excluída." e nada muda

#### Scenario: Exclusão de turma só com oferta
- **GIVEN** a turma `2º período` com oferta de Química e sem aula dessa oferta
- **WHEN** um usuário com `TURMA.EXCLUIR` e a turma no escopo confirma a exclusão
- **THEN** a exclusão é recusada com mensagem e nada muda

