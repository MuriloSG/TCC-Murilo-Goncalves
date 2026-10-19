# Testes do app `audit`

Registro e consulta da auditoria. Comportamento descrito em [auditoria](../../funcionalidades/auditoria.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Registro

### `test_records.py`

| Classe | O que garante |
|---|---|
| `SanitizeTests` | Campos sensíveis são descartados |
| `ActorTests` | Sem contexto, o autor é o sistema; `acting_as` é restaurado ao sair; a origem de importação mantém o executor |
| `RecordTests` | O registro usa o autor do contexto ou o sistema; códigos fora do catálogo recusados; campos sensíveis descartados; ação nova só precisa entrar no catálogo, de onde vêm os rótulos |
| `IntegrityTests` | Registro gravado não é salvo de novo, atualizado por `QuerySet.update` nem excluído |

### `test_access.py`

`AccessRecordTests`: o acesso a cada tela é registrado com o próprio recurso. O IP encaminhado só vale com proxy declarado. Fragmento e modal do htmx não contam como acesso, mas a mesma rota sem JavaScript conta. Acesso recusado, redirecionamento do anônimo, POST, o início e o download do modelo não são registrados.

### `test_authentication.py`

| Classe | O que garante |
|---|---|
| `AuthenticationRecordTests` | Login, login recusado (sem usuário e nunca com a senha), logout por POST, pedido de recuperação para qualquer e-mail e troca de senha são registrados; GET no logout não |
| `TypedEmailTests` | Do que foi digitado, só um e-mail válido fica na auditoria |

### `test_changes.py`

| Classe | O que garante |
|---|---|
| `UserChangeTests` | Cadastro, edição (só os campos alterados), troca de perfil, desativação e reativação registradas; sem mudança ou com recusa, nada é registrado; comandos de superadmin entram como ação do sistema |
| `RoleChangeTests` | Criação, edição, troca de permissões e exclusão de perfil registradas; mesmas permissões e exclusão recusada não registram |
| `ImportChangeTests` | A prévia registra a importação e nenhum usuário; a confirmação registra a importação e cada usuário; descarte registrado; download do modelo é exportação |
| `SystemActionTests` | E-mail enviado e falha de envio registrados como ação do sistema; nova tentativa não |

## Consulta

### `test_query.py`

| Classe | O que garante |
|---|---|
| `AuthorizationTests` | Abre com a permissão; consultar a auditoria também é auditado |
| `FilterTests` | Mais recentes primeiro; filtros por ação, recurso, origem, id do registro, período e usuário, combinados; filtros inválidos ignorados; resultado vazio oferece limpar |
| `DetailTests` | Detalhe com os valores gravados, em modal pelo htmx e em página sem ele; ação do sistema sem usuário |

### `test_options.py`

| Classe | O que garante |
|---|---|
| `UserOptionsTests` | Opções de usuário com nome e e-mail, busca em toda a base e por e-mail sem diferenciar a caixa |
| `PaginatedFieldTests` | A página renderiza só a primeira página de opções; a opção escolhida aparece mesmo fora dela e o filtro continua valendo |
