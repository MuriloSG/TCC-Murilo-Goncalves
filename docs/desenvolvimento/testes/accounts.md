# Testes do app `accounts`

Autenticação, usuários, perfis, permissões, superadmin, comandos de gerenciamento e importação de usuários. Comportamento descrito em [autenticação, usuários e perfis](../../funcionalidades/autenticacao-e-usuarios.md) e em [permissões](../../regras/permissoes.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `roles.py`: `role_with`, `management_role` e `requester_role` montam perfis só pelas permissões, sem depender dos perfis da carga inicial.

## Autenticação e sessão

### `test_authentication.py`

Login pelo allauth, logout e encerramento de sessões.

| Classe | O que garante |
|---|---|
| `UsernameIsNotACredentialTests` | O nome de usuário não autentica; só o e-mail |
| `LoginPageTests` | A tela pede só e-mail e senha, oferece recuperação de senha e não tem cadastro, fechado também no adapter |
| `LoginTests` | Login bem-sucedido vai para o início; o e-mail é comparado sem diferenciar a caixa |
| `InvalidCredentialsTests` | Senha errada e e-mail desconhecido têm o mesmo erro; usuário sem senha não entra; o excesso de tentativas bloqueia até a senha certa |
| `InactiveUserTests` | Usuário e superadmin inativos não entram; a reativação devolve o login; a sessão de quem foi desativado vira anônima |
| `SessionsAfterChangeByAnotherTests` | Trocar o e-mail ou o perfil de outra conta encerra todas as sessões dela, e só dela; a própria alteração mantém as próprias sessões |
| `LogoutTests` | POST encerra a sessão e vai ao login; GET não encerra |
| `EmailChangeTests` | Depois da troca, só o e-mail novo autentica |

### `test_password.py`

Definição e recuperação de senha pelo link.

| Classe | O que garante |
|---|---|
| `UnusablePasswordTests` | Usuário cadastrado define a senha pelo link |
| `InactiveUserTests` | Inativo não recebe e-mail; link emitido ou aberto antes da desativação não troca a senha |
| `RecoveryRequestTests` | Ativo recebe o link; e-mail desconhecido tem a mesma resposta e nenhum envio; excesso de pedidos é recusado; o superadmin recupera o acesso |
| `RecoveryWithoutSmtpTests` | Sem SMTP o pedido é respondido e o link espera no outbox; SMTP com falha dá a mesma resposta para e-mail conhecido e desconhecido; pedidos repetidos mantêm um só link pendente |
| `ResetTests` | A senha nova substitui a antiga sem fazer login; link de uso único, com validade, invalidado pela troca de e-mail; senha fraca recusada sem gastar o link; a troca encerra as sessões existentes |

### `test_emails.py`

`PasswordLinkTests`: o cadastro registra o link no outbox sem enviar; o superadmin criado por comando não recebe link; o link usa a URL do site e os templates da recuperação, vai para o e-mail atual e é descartado quando o envio deixa de fazer sentido; o worker não consome o limite público de recuperação.

## Autorização

### `test_authorization.py`

`User.has_perm` como único ponto de decisão.

| Classe | O que garante |
|---|---|
| `InactiveUserTests` | Usuário e superadmin inativos não têm permissão |
| `RolePermissionsTests` | Concede o que o perfil tem e nega o resto; `has_perms` exige todas; `has_module_perms` por recurso inteiro; permissão reservada gravada direto no banco não vale; a decisão não depende do código nem do nome do perfil; permissões do perfil anterior não ficam; cálculo uma vez por instância |
| `SuperadminTests` | Superadmin ativo tem qualquer permissão, inclusive fora do catálogo, e as efetivas são o catálogo |
| `TemplatePermsTests` | `perms` dos templates usa `has_perm` e `has_module_perms` |
| `AuthorityTests` | Quem gere usuários só atribui perfil e altera conta que já cobre com as próprias permissões; formulários só oferecem perfis cobertos; POST forjado é recusado; troca de nome de usuário que move vínculo de docente aparece destacada na auditoria |

### `test_middleware.py`

`PermissionMiddlewareTests`: lê `permission_required` de views em classe e em função; views sem o atributo ficam a cargo da URL; anônimo nunca chega a uma view com permissão; inativo é recusado.

### `test_route_protection.py`

Matriz central de proteção das rotas, descrita em [testes transversais](../testes.md#testes-transversais). `RouteProtectionTests` confere que toda rota está em `PROTECTED_ROUTES` ou `PUBLIC_ROUTES`, que cada view declara a permissão esperada, o redirecionamento do anônimo com `next`, o 403 sem a permissão, que nome ou código de perfil não concede nada, que perfil só com a permissão da rota passa (exceto reservadas), que o superadmin sem perfil passa e que POST sem CSRF é recusado.

### `test_catalog.py`

| Classe | O que garante |
|---|---|
| `PermissionConstantsTests` | Códigos no formato `RECURSO.ACAO`; capacidade administrativa é a gestão de usuários sem a importação; reservadas são as de perfil e de configuração |
| `InitialCatalogTests` | Códigos do banco iguais às constantes, todos com descrição; `ADMINISTRADOR` concede tudo que não é reservado e `DOCENTE` só a solicitação de agendamento; nenhum perfil tem permissão reservada nem de alcance acadêmico |

## Regras do usuário e do perfil

### `test_models.py`

| Classe | O que garante |
|---|---|
| `UserModelTests` | O e-mail é o identificador de login; sem os atributos padrão do usuário do Django |
| `UserDatabaseTests` | E-mail normalizado; e-mail que difere só na caixa recusado na validação e no banco |
| `UsernameTests` | Nome de usuário mantém acentos e abreviações, apara e junta espaços, vazio vira nulo; único sem diferenciar a caixa (acento diferencia), inclusive de inativos, na validação e no banco |
| `RoleTests` | Código do perfil no formato válido; nome aparado e único sem diferenciar a caixa |
| `PermissionTests` | Recurso e ação derivados do código; código malformado recusado |
| `UserRoleTests` | Um perfil por usuário; perfil com usuário não é excluído |
| `RegisterTests` | `register` cria usuário ativo, com um perfil e senha inutilizável; normaliza e-mail e nome; não aceita superadmin nem senha; recusa dados inválidos e e-mail em uso sem criar nada |
| `UpdateDetailsTests` | `update_details` altera só nome e e-mail, remove os endereços antigos do allauth, não sobrescreve a situação alterada por outro e recusa dados inválidos mantendo os valores |

### `test_continuity.py`

Regra de continuidade administrativa: sempre resta alguém ativo com a capacidade de gerir usuários.

| Classe | O que garante |
|---|---|
| `AdministrativeCapabilityTests` | Quem tem a capacidade: superadmin ativo ou perfil com todas as permissões exigidas, inclusive personalizado; reservadas não contam e extras não importam |
| `DeactivationTests` | O último capaz não é desativado; com outro capaz, pode; desativar mantém os dados e tira as permissões na mesma instância |
| `ReactivationTests` | Reativar devolve perfil, senha e superadmin, sem checagem |
| `SuperadminStatusTests` | Conceder e retirar superadmin; retirar do último capaz é recusado, salvo se ele mantém a capacidade pelo perfil |
| `ChangeRoleTests` | Troca o único perfil e atualiza as permissões da instância; o último capaz pelo perfil não perde o perfil |
| `ContinuityGuardTests` | A checagem vale para o estado final, desfaz a alteração e trava os usuários ativos em ordem de `pk` |
| `ConcurrentDeactivationTests` | Desativações simultâneas mantêm um usuário capaz (`TransactionTestCase`) |
| `DeferredContinuityTests` | Dentro do bloco adiado só o estado final é checado; fora dele, cada operação; o bloco fecha mesmo após exceção |

### `test_roles.py`

| Classe | O que garante |
|---|---|
| `CreateRoleTests` | Cria perfil com ou sem permissões; recusa dados inválidos, permissão reservada ou fora do catálogo sem criar nada |
| `UpdateRoleDetailsTests` | Altera só nome e descrição; o código não muda, nem em perfil inicial; nome vazio ou repetido recusado |
| `SetPermissionsTests` | Concede e retira na mesma chamada, inclusive em perfil inicial; conjunto vazio aceito; vale para todos os usuários do perfil; reservada e fora do catálogo recusadas; retirar permissão da capacidade respeita a continuidade |
| `DeleteRoleTests` | Exclui perfil sem usuários, inicial ou não; recusa com usuários ativos ou só inativos; libera depois que os usuários trocam de perfil |
| `ConcurrentPermissionChangeTests` | Retirada de permissão e desativação simultâneas mantêm um usuário capaz |

### `test_superadmin_protection.py`

| Classe | O que garante |
|---|---|
| `SuperadminEmailProtectionTests` | Só superadmin ativo altera o e-mail de outro superadmin, ativo ou inativo; o nome pode ser alterado por qualquer gestor; vale a situação gravada no banco |
| `SuperadminProtectionViewTests` | O e-mail fica somente leitura para o gestor comum e o POST forjado é recusado com erro; `is_superadmin` enviado na requisição é ignorado; gestor comum não desativa nem troca o perfil de superadmin |

## Comandos de gerenciamento

### `test_commands.py`

| Classe | O que garante |
|---|---|
| `CreateSuperadminTests` | Cria superadmin ativo sem perfil, mesmo sem perfis cadastrados; recusa e-mail em uso, senhas diferentes, fracas e e-mail inválido |
| `SetSuperadminTests` | Concede e retira, respeitando a continuidade; e-mail desconhecido; exige exatamente uma ação |
| `DeleteUsersTests` | Apaga usuários e vínculos mantendo perfis e superadmins; recusa sem superadmin ativo; resposta diferente de "sim" não apaga |
| `SetPasswordsTests` | Define a senha padrão de todos; resposta diferente de "sim" mantém as senhas |

### `test_command_environment.py`

Trava dos comandos destrutivos, descrita em [testes transversais](../testes.md#testes-transversais).

| Classe | O que garante |
|---|---|
| `EnvironmentRefusalTests` | Recusa fora de `local`, com valor ambíguo ou ausente, sem tomar `DEBUG` como prova, antes da pergunta de confirmação |
| `DatabaseRefusalTests` | Recusa sem banco local declarado, com identidade diferente, sem marca ou com outra marca, banco operacional com nome de teste e nome efetivo divergente; mensagens sem configuração |
| `LocalDatabaseTests` | `set_passwords`, `delete_users` e `flush` rodam no banco local simulado |
| `LocalClearDataTests` | `clear_data` roda no banco local marcado e no banco de teste do runner |
| `TestRunnerAuthorizationTests` | O `flush` do projeto substitui o nativo; o runner registra os bancos que cria e esvazia o registro ao final, mesmo com falha |

## Telas

### `test_user_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Basta a permissão da rota; superadmin com perfil de docente tem acesso; a lista mostra só as ações permitidas |
| `CreateTests` | Cadastro com nome de usuário; recusa nome em uso, dados inválidos, mais de um perfil e e-mail em uso; sem campo de senha nem de superadmin |
| `CreateSendTests` | O cadastro registra o link de senha em `on_commit`, pela mesma rota da recuperação; recusa não registra link |
| `UpdateTests` | Altera só nome e e-mail; recusa nome de usuário de outro, nome vazio e e-mail de outro |
| `ChangeRoleTests` | Troca o perfil; recusa mais de um; violação da continuidade aparece e nada muda |
| `StatusTests` | Desativa e reativa por POST; o último capaz não se desativa; com outro capaz, pode |

### `test_role_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | A negação vem antes das regras; superadmin com perfil de docente tem acesso |
| `ListAndDetailTests` | Lista com tipo e usuários vinculados; detalhe com as permissões concedidas por recurso |
| `CreateTests` | Oferece só permissões concedíveis; cria com ou sem permissões; recusa dados inválidos e reservada com o motivo |
| `UpdateTests` | Código visível e não editável; altera só nome e descrição |
| `PermissionsTests` | Concede e retira na mesma requisição; reservada recusada; a mudança vale na próxima requisição dos vinculados |
| `DeleteTests` | GET só confirma; exclui perfil sem usuários, inicial ou não; perfil em uso informa quantos usuários tem |

### `test_home.py`

| Classe | O que garante |
|---|---|
| `HomeTests` | O início abre o primeiro item que o perfil concede; sem módulos, mostra o aviso de acesso restrito |
| `DeniedAccessTests` | A página de negação é o 403 amigável e vem antes da regra de continuidade |
| `ChangesOnTheSameSessionTests` | Troca de perfil encerra a sessão e o próximo login tem o acesso novo; superadmin concedido e retirado por comando |

### `test_user_search.py`

| Classe | O que garante |
|---|---|
| `ManagerSearchTests` | Busca por trecho do nome, do e-mail e do nome de usuário, sem diferenciar a caixa, combinada com a situação |
| `ListSearchViewTests` | Busca na tela, sem resultado e estado vazio original; o htmx responde só a tabela quando é o alvo |
| `PaginatedSearchTests` | A paginação mantém a busca |

### `test_modals.py`

| Classe | O que garante |
|---|---|
| `FormModalTests` | GET pelo htmx responde o fragmento e sem htmx a página; POST inválido mantém o modal sem gravar; sucesso responde `HX-Redirect` mantendo busca e filtro da origem; criação de perfil abre a etapa de permissões no mesmo modal |
| `ConfirmationModalTests` | Desativação, reativação e exclusão pelo htmx; recusa volta para a origem com a mensagem |

### `test_form_initial.py`

`EditFormsShowCurrentValuesTests`: os formulários de edição do usuário, de troca de perfil e de edição de perfil mostram os valores atuais apesar do `initial` do `FormView`.

### `test_screens.py`

| Classe | O que garante |
|---|---|
| `UserListScreenTests` | Selos de situação com palavra e ícone; botão de editar com `aria-label`; "Mais ações" e menu compacto do celular seguindo as permissões; células com o rótulo da coluna |
| `MessagesScreenTests` | Mensagens de erro de operação e de sucesso |
| `FormScreenTests` | Campo com erro, opcional e com ajuda associada; permissões agrupadas por recurso, com contagem; busca e seleção ocultas sem JavaScript |
| `RoleScreenTests` | Estado vazio de permissões; cartões não aninhados; um botão primário por tela; as mesmas ações em todo perfil |

### `test_interface_text.py`

| Classe | O que garante |
|---|---|
| `AuthenticationMessagesTests` | Login sem mensagem; logout mostra a sessão encerrada; textos de credenciais incorretas e e-mail inválido |
| `PasswordResetTextTests` | Aviso de envio na terceira pessoa; senhas diferentes |
| `ManagementScreensTextTests` | Confirmação de desativação; perfil sem descrição; exclusão de perfil com usuários orienta trocar o perfil; e-mail inválido no cadastro e na edição |

## Importação de usuários

### `test_user_import.py`

Definição da importação sobre o motor do app `imports`.

| Classe | O que garante |
|---|---|
| `UsernameTests` | Cria e atualiza o nome de usuário; célula vazia mantém o atual; duplicado no arquivo ou de outro usuário recusado; trocar exige a permissão de edição |
| `ActionTests` | Cria na confirmação; planeja troca de perfil e de nome; grafia diferente fica inalterada; perfil desconhecido; e-mail de outro domínio não é cadastrado, mas usuário existente dele é atualizado; inativo continua inativo; perfil de superadmin só muda por superadmin; o e-mail nunca muda |
| `PermissionTests` | Perfil não coberto recusado; cada mudança exige sua permissão e linhas inalteradas só a de importar; a permissão é conferida para quem confirma e de novo quando o worker executa |
| `ContinuityTests` | Rebaixar e promover no mesmo arquivo é aceito; arquivo que deixa o sistema sem administrador é recusado; as telas continuam checando depois |
| `OutboxTests` | Só os usuários criados recebem o link; divergência não registra link |
| `ScreenEquivalenceTests` | Cada recusa das telas tem linha equivalente na importação, com a mesma mensagem |
| `ConcludedMessageTests` | Mensagens de conclusão |

### `test_user_import_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | As telas pedem só a permissão de importar; acesso direto segue cada permissão; excluir importação tem permissão própria; importação de outro tipo dá 404; a lista de usuários mostra as ações só com a permissão |
| `UploadTests` | Arquivo válido cria a prévia e a abre, também pelo htmx; arquivo rejeitado mostra o erro sem criar nada; formulário `multipart` |
| `DetailTests` | Prévia validada oferece confirmar e descartar; com erros, mostra linha e coluna sem confirmar; erro de arquivo; histórico só de importações de usuários |
| `LineNumberFilterTests` | Filtro por número de linha, inválido descartado, combinado com o filtro de situação |
| `ConfirmAndDiscardTests` | Confirmar aplica e informa o link; mensagem de divergência; descartar pergunta no GET; segunda confirmação recusada |
| `TemplateTests` | Modelo em UTF-8 com BOM e ponto e vírgula |
| `PaginationTests` | Linhas da prévia paginadas, com o resumo contando todas |
| `ImportDeletionTests` | Exclusão de importação descartada só com a permissão |
| `ProcessingTests` | Prévia pendente mostra o quadro sem ações; rota de andamento responde 204 enquanto pendente; aviso de demora pelo horário do pedido e limite das configurações; falhas mostram a mensagem; descarte recusado enquanto pendente |
