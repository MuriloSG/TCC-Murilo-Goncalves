## ADDED Requirements

### Requirement: Permissões de disciplinas e turmas
O catálogo DEVE (MUST) conter as permissões `DISCIPLINA.VISUALIZAR`, `DISCIPLINA.CRIAR`, `DISCIPLINA.EDITAR`, `DISCIPLINA.EXCLUIR`, `TURMA.VISUALIZAR`, `TURMA.CRIAR`, `TURMA.EDITAR` e `TURMA.EXCLUIR`, exibidas nos módulos "Disciplinas" e "Turmas". Listar e ver detalhes exige `VISUALIZAR`, cadastrar exige `CRIAR`, editar exige `EDITAR` e excluir exige `EXCLUIR`, cada uma do seu módulo. A permissão NÃO DEVE (MUST NOT) dar acesso a registro fora do escopo definido na spec `gestao-academica`. A migration que as acrescenta DEVE (MUST) concedê-las ao perfil `ADMINISTRADOR` sem alterar as demais permissões dos perfis existentes, e elas NÃO DEVEM (MUST NOT) ser reservadas ao superadmin.

#### Scenario: Permissões acrescentadas a uma instalação existente
- **GIVEN** uma instalação em que o perfil `COORDENACAO` concede somente `USUARIO.VISUALIZAR`
- **WHEN** a migration das permissões de disciplina e turma é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder as oito permissões e `COORDENACAO` continua só com `USUARIO.VISUALIZAR`

#### Scenario: Sem a permissão
- **GIVEN** um usuário ativo, sem superadmin, cujo perfil concede só `DISCIPLINA.VISUALIZAR`
- **WHEN** ele envia por POST o cadastro de uma disciplina ou acessa a lista de turmas
- **THEN** as duas requisições são recusadas com 403 e nada é criado

#### Scenario: Visitante não autenticado
- **WHEN** um visitante não autenticado acessa qualquer rota de disciplinas ou turmas
- **THEN** ele é redirecionado para a página de login, com o endereço de retorno

#### Scenario: Exclusão sem CSRF
- **GIVEN** um usuário com `TURMA.EXCLUIR` e a turma no escopo
- **WHEN** a exclusão é enviada por POST sem o token CSRF
- **THEN** a requisição é recusada com 403 e a turma continua cadastrada
