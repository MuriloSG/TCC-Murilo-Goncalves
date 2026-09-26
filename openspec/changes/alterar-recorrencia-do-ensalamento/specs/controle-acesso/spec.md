## ADDED Requirements

### Requirement: Permissão de alteração da recorrência
O catálogo DEVE (MUST) ter a permissão `ENSALAMENTO.ALTERAR_RECORRENCIA`, com a descrição "Alterar a recorrência de uma aula do ensalamento a partir de uma data", concedida pela migration ao perfil de sistema `ADMINISTRADOR`. Ela DEVE (MUST) ser distinta de `ENSALAMENTO.CANCELAR_OCORRENCIA`: uma não concede a outra, e ser docente da aula NÃO DEVE (MUST NOT) conceder a alteração da recorrência. A rota da alteração DEVE (MUST) declarar a permissão, verificada pelo middleware com a resposta de acesso restrito já usada, e a operação do model DEVE (MUST) conferi-la de novo.

#### Scenario: Cancelar não concede alterar
- **GIVEN** um usuário com `ENSALAMENTO.CANCELAR_OCORRENCIA` e sem `ENSALAMENTO.ALTERAR_RECORRENCIA`
- **WHEN** ele abre a alteração da recorrência de uma aula
- **THEN** a resposta é 403

#### Scenario: Superadmin altera
- **WHEN** um superadmin ativo altera a recorrência de uma aula
- **THEN** a alteração é executada
