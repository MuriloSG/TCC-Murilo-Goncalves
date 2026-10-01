## ADDED Requirements

### Requirement: Permissão do painel administrativo
O catálogo DEVE (MUST) ter a permissão `PAINEL.VISUALIZAR`, com a descrição "Visualizar o painel administrativo", do recurso `PAINEL` com o rótulo "Painel", concedida pela migration ao perfil de sistema `ADMINISTRADOR` sem alterar as demais permissões dos perfis existentes. Ela NÃO DEVE (MUST NOT) ser reservada ao superadmin. Ela DEVE (MUST) liberar somente a rota `painel/`: NÃO DEVE (MUST NOT) conceder `AGENDA.ANALISAR`, `AGENDA.VISUALIZAR`, `ENSALAMENTO.VISUALIZAR`, `ENSALAMENTO.IMPORTAR`, `ESPACO.*` nem nenhuma outra permissão, e nenhuma permissão de módulo DEVE (MUST) conceder o painel.

#### Scenario: Anônimo é levado ao login
- **WHEN** um visitante sem sessão abre `painel/`
- **THEN** ele é redirecionado ao login com o endereço de retorno

#### Scenario: Sem a permissão
- **GIVEN** um usuário com `AGENDA.ANALISAR` e sem `PAINEL.VISUALIZAR`
- **WHEN** ele abre `painel/`
- **THEN** a resposta é 403

#### Scenario: Painel não abre a análise
- **GIVEN** um usuário com `PAINEL.VISUALIZAR` e sem `AGENDA.ANALISAR`
- **WHEN** ele abre `agenda/solicitacoes/`
- **THEN** a resposta é 403

#### Scenario: Migration preserva os perfis
- **GIVEN** uma instalação em que o superadmin retirou `USUARIO.EDITAR` do perfil `ADMINISTRADOR`
- **WHEN** a migration que acrescenta `PAINEL.VISUALIZAR` é aplicada
- **THEN** `ADMINISTRADOR` passa a conceder `PAINEL.VISUALIZAR` e continua sem `USUARIO.EDITAR`

#### Scenario: Concedida a perfil personalizado
- **GIVEN** um superadmin ativo e o perfil personalizado `COORDENACAO`
- **WHEN** ele concede `PAINEL.VISUALIZAR` a `COORDENACAO`
- **THEN** a permissão é concedida
