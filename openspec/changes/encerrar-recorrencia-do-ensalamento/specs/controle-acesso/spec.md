## ADDED Requirements

### Requirement: Permissão de encerramento da recorrência
O catálogo DEVE (MUST) ter a permissão `ENSALAMENTO.ENCERRAR_RECORRENCIA`, com a descrição "Encerrar uma aula do ensalamento a partir de uma data", concedida pela migration ao perfil de sistema `ADMINISTRADOR`. Ela DEVE (MUST) ser distinta de `ENSALAMENTO.ALTERAR_RECORRENCIA`, de `ENSALAMENTO.CRIAR_RECORRENCIA` e de `ENSALAMENTO.CANCELAR_OCORRENCIA`: nenhuma concede a outra, e ser docente da aula NÃO DEVE (MUST NOT) conceder o encerramento. A rota do encerramento DEVE (MUST) declarar a permissão, verificada pelo middleware com a resposta de acesso restrito já usada, e a operação do model DEVE (MUST) conferi-la de novo. Um superadmin ativo DEVE (MUST) encerrar sem que a permissão esteja concedida ao perfil dele, pela regra geral de `User.has_perm`, e nenhuma view, template ou operação DEVE (MUST) decidir o acesso lendo `is_superadmin`.

#### Scenario: Cancelar ocorrência não concede encerrar
- **GIVEN** um usuário com `ENSALAMENTO.CANCELAR_OCORRENCIA` e sem `ENSALAMENTO.ENCERRAR_RECORRENCIA`
- **WHEN** ele abre o encerramento de uma aula
- **THEN** a resposta é 403

#### Scenario: Docente da aula não encerra
- **GIVEN** um usuário que é o docente da aula e não tem a permissão
- **WHEN** ele pede o encerramento da aula
- **THEN** a operação é recusada e nenhuma vigência muda

#### Scenario: Superadmin encerra sem a permissão concedida
- **GIVEN** um superadmin ativo cujo perfil não tem `ENSALAMENTO.ENCERRAR_RECORRENCIA`
- **WHEN** ele encerra uma aula
- **THEN** a aula é encerrada

#### Scenario: Anônimo não alcança a rota
- **WHEN** um visitante sem sessão abre a rota do encerramento
- **THEN** ele é redirecionado ao login com o endereço de retorno
