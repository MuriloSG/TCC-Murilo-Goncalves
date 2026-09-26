## ADDED Requirements

### Requirement: Auditoria de disciplinas e turmas
Toda alteração real feita pelas áreas de disciplinas e turmas DEVE (MUST) gerar um registro do módulo `DISCIPLINA`, exibido como "Disciplinas", ou `TURMA`, exibido como "Turmas", com a chave do registro como identificador e o usuário responsável pelo contexto de auditoria atual: o cadastro com `CRIAR` e os valores posteriores (o nome da disciplina, ou o curso e o rótulo da turma); a edição com `ALTERAR` e só os campos que mudaram; e a exclusão com `EXCLUIR` e os valores anteriores. Uma operação recusada ou que não muda nada NÃO DEVE (MUST NOT) gerar registro, e a importação do ensalamento NÃO DEVE (MUST NOT) passar a gerar registros desses módulos.

#### Scenario: Edição auditada
- **GIVEN** a turma `1º ano` de Informática, sem oferta e sem aula
- **WHEN** o superadmin altera o rótulo para `1º ano A`
- **THEN** é gravado um registro `ALTERAR` do módulo `TURMA` com o responsável, `1º ano` como valor anterior e `1º ano A` como novo

#### Scenario: Exclusão recusada sem registro
- **GIVEN** a disciplina Matemática com aula no ensalamento
- **WHEN** o superadmin tenta excluí-la
- **THEN** nenhum registro do módulo `DISCIPLINA` é gravado
