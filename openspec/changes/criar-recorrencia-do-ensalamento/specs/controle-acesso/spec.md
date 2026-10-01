## ADDED Requirements

### Requirement: Permissão de criação da recorrência
O catálogo DEVE (MUST) ter a permissão `ENSALAMENTO.CRIAR_RECORRENCIA`, com a descrição "Cadastrar uma aula recorrente no ensalamento", concedida pela migration ao perfil de sistema `ADMINISTRADOR`. Ela DEVE (MUST) ser distinta de `ENSALAMENTO.ALTERAR_RECORRENCIA`, de `ENSALAMENTO.CANCELAR_OCORRENCIA` e de `ENSALAMENTO.IMPORTAR`: nenhuma concede a outra, e ser docente NÃO DEVE (MUST NOT) conceder a criação. A rota da criação DEVE (MUST) declarar a permissão, verificada pelo middleware com a resposta de acesso restrito já usada, e a operação do model DEVE (MUST) conferi-la de novo. Um superadmin ativo DEVE (MUST) executar a criação sem que a permissão esteja concedida ao perfil dele, pela regra geral de `User.has_perm`, e nenhuma view, template ou operação DEVE (MUST) decidir o acesso lendo `is_superadmin`.

#### Scenario: Alterar não concede criar
- **GIVEN** um usuário com `ENSALAMENTO.ALTERAR_RECORRENCIA` e sem `ENSALAMENTO.CRIAR_RECORRENCIA`
- **WHEN** ele abre o cadastro de aula do ensalamento
- **THEN** a resposta é 403

#### Scenario: Importar não concede criar
- **GIVEN** um usuário com `ENSALAMENTO.IMPORTAR` e sem `ENSALAMENTO.CRIAR_RECORRENCIA`
- **WHEN** ele envia o cadastro de uma aula
- **THEN** a operação é recusada e nenhuma alocação é gravada

#### Scenario: Superadmin cadastra sem a permissão concedida
- **GIVEN** um superadmin ativo cujo perfil não tem `ENSALAMENTO.CRIAR_RECORRENCIA`
- **WHEN** ele cadastra uma aula do ensalamento
- **THEN** a aula é cadastrada

#### Scenario: Anônimo não alcança a rota
- **WHEN** um visitante sem sessão abre a rota do cadastro de aula
- **THEN** ele é redirecionado ao login com o endereço de retorno
