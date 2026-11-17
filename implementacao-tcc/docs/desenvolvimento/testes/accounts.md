# Testes do app `accounts`

Autenticação, usuários, perfis, permissões, superadmin, comandos de gerenciamento e importação de usuários. Comportamento descrito em [autenticação, usuários e perfis](../../funcionalidades/autenticacao-e-usuarios.md) e em [permissões](../../regras/permissoes.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `roles.py`: `role_with`, `management_role` e `requester_role` montam perfis só pelas permissões, sem depender dos perfis da carga inicial.

## Autenticação e sessão

### `test_authentication.py`

Login pelo allauth e encerramento de sessões. O que é do allauth (mesmo erro para senha errada e e-mail desconhecido, limite de tentativas, logout por POST) não é testado de novo.

| Classe | O que garante |
|---|---|
| `LoginTests` | A tela pede só e-mail e senha, oferece recuperação de senha e não tem cadastro, fechado também no adapter; o nome de usuário não autentica; login bem-sucedido vai para o início; o e-mail é comparado sem diferenciar a caixa |
| `InactiveUserTests` | Usuário e superadmin inativos não entram; a sessão de quem foi desativado vira anônima |
| `SessionsAfterChangeByAnotherTests` | Trocar o e-mail ou o perfil de outra conta encerra todas as sessões dela, e só dela; a própria alteração mantém as próprias sessões |
| `EmailChangeTests` | Depois da troca, só o e-mail novo autentica |

### `test_profile.py`

Informações pessoais do usuário logado.

| Classe | O que garante |
|---|---|
| `ProfileTests` | Qualquer usuário logado abre a tela, até sem perfil, e o anônimo vai ao login; a troca do nome ignora `email` e `username` forjados e é auditada; senha atual errada, senhas diferentes e senha fraca são recusadas; a troca certa mantém a sessão atual, encerra as outras e grava `SENHA_ALTERADA` |

### `test_password.py`

Definição e recuperação de senha pelo link.

| Classe | O que garante |
|---|---|
| `UnusablePasswordTests` | Usuário cadastrado define a senha pelo link |
| `InactiveUserTests` | Inativo não recebe e-mail; link emitido ou aberto antes da desativação não troca a senha |
| `RecoveryRequestTests` | Ativo recebe o link; e-mail desconhecido tem a mesma resposta e nenhum envio; o superadmin recupera o acesso |
| `RecoveryWithoutSmtpTests` | Sem SMTP o pedido é respondido e o link espera no outbox; SMTP com falha dá a mesma resposta para e-mail conhecido e desconhecido; pedidos repetidos mantêm um só link pendente |
| `ResetTests` | A senha nova substitui a antiga sem fazer login. Validade e uso único do link e os validadores de senha são do Django |

### `test_emails.py`

`PasswordLinkTests`: o cadastro registra o link no outbox sem enviar; o superadmin criado por comando não recebe link; o link usa a URL do site e os templates da recuperação, vai para o e-mail atual e é descartado quando o envio deixa de fazer sentido; o worker não consome o limite público de recuperação.

## Autorização

### `test_authorization.py`

`User.has_perm` como único ponto de decisão.

| Classe | O que garante |
|---|---|
| `PermissionDecisionTests` | Usuário e superadmin inativos não têm permissão; concede o que o perfil tem e nega o resto; `has_perms` exige todas; `has_module_perms` por recurso inteiro; permissão reservada gravada direto no banco não vale; cálculo uma vez por instância; superadmin ativo tem qualquer permissão, inclusive fora do catálogo, e as efetivas são o catálogo; `perms` dos templates usa `has_perm` e `has_module_perms` |
| `AuthorityTests` | Quem gere usuários só atribui perfil e altera conta que já cobre com as próprias permissões; formulários só oferecem perfis cobertos; POST forjado é recusado; troca de nome de usuário que move vínculo de docente aparece destacada na auditoria |

### `test_middleware.py`

`PermissionMiddlewareTests`: lê `permission_required` de views em classe e em função; anônimo nunca chega a uma view com permissão e vai ao login com o `next` codificado.

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
| `UserDatabaseTests` | E-mail normalizado; e-mail que difere só na caixa recusado na validação e no banco |
| `UsernameTests` | Nome de usuário mantém acentos e abreviações, apara e junta espaços, vazio vira nulo; único sem diferenciar a caixa (acento diferencia), inclusive de inativos, na validação e no banco |
| `RoleTests` | Código do perfil no formato válido; nome aparado e único sem diferenciar a caixa |
| `PermissionTests` | Recurso e ação derivados do código; código malformado recusado |
| `UserRoleTests` | Um perfil por usuário. Perfil com usuário não é excluído: `test_roles.py` |
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
| `ContinuityGuardTests` | A checagem vale para o estado final e desfaz a alteração |
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
| `SuperadminProtectionViewTests` | O e-mail fica somente leitura para o gestor comum, editável para o superadmin ativo, e o POST forjado é recusado com erro; `is_superadmin` enviado na requisição é ignorado |

## Comandos de gerenciamento

### `test_commands.py`

| Classe | O que garante |
|---|---|
| `CreateSuperadminTests` | Cria superadmin ativo sem perfil, mesmo sem perfis cadastrados; recusa e-mail em uso, senhas diferentes, fracas e e-mail inválido |
| `SetSuperadminTests` | Concede e retira, respeitando a continuidade; e-mail desconhecido; exige exatamente uma ação |
| `DeleteUsersTests` | Apaga usuários e vínculos mantendo perfis e superadmins; recusa sem superadmin ativo; resposta diferente de "sim" não apaga |
| `SetPasswordsTests` | Define a senha padrão de todos; resposta diferente de "sim" mantém as senhas |

### `test_er_diagram.py`

| Classe | O que garante |
|---|---|
| `ExportErDiagramTests` | Gera conceitual, físico e restrições, com a saída igual entre execuções. O desenho é conferido nas imagens geradas, e não por teste |

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
| `AccessTests` | Basta a permissão da rota; a lista mostra só as ações permitidas |
| `CreateTests` | Cadastro com nome de usuário, sem campo de senha nem de superadmin; dados inválidos, mais de um perfil, nome e e-mail em uso aparecem no formulário |
| `CreateSendTests` | O cadastro registra o link de senha em `on_commit` |
| `UpdateTests` | Altera só nome e e-mail, sem campo de senha; nome de usuário de outro, nome vazio e e-mail de outro aparecem no formulário |
| `ChangeRoleTests` | Troca o perfil; recusa mais de um; violação da continuidade aparece e nada muda |
| `StatusTests` | Desativa e reativa por POST; o último capaz não se desativa; com outro capaz, pode |

### `test_role_views.py`

| Classe | O que garante |
|---|---|
| `ListAndDetailTests` | Lista com tipo e usuários vinculados; detalhe com as permissões concedidas por recurso |
| `CreateTests` | Oferece só permissões concedíveis; cria com ou sem permissões; dados inválidos e reservada aparecem com o motivo |
| `UpdateTests` | Código visível e não editável; altera só nome e descrição; nome vazio ou de outro perfil recusado |
| `PermissionsTests` | Oferece só as concedíveis e mostra os vinculados; concede e retira na mesma requisição; o superadmin retira permissão da capacidade; reservada recusada; a mudança vale na próxima requisição dos vinculados |
| `DeleteTests` | GET só confirma; exclui perfil sem usuários, inicial ou não; perfil em uso informa quantos usuários tem |

### `test_home.py`

| Classe | O que garante |
|---|---|
| `HomeTests` | O início abre o primeiro item que o perfil concede; sem módulos, mostra o aviso de acesso restrito |
| `DeniedAccessTests` | A página de negação é o 403 amigável e vem antes da regra de continuidade |

### `test_user_search.py`

| Classe | O que garante |
|---|---|
| `ManagerSearchTests` | Busca por trecho do nome, do e-mail e do nome de usuário, sem diferenciar a caixa, combinada com a situação |
| `ListSearchViewTests` | Busca na tela, sem resultado e estado vazio original; o formulário mostra o estado atual; o htmx responde só a tabela quando é o alvo |

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
| `FormScreenTests` | Campo com erro, opcional e com ajuda associada; permissões agrupadas por recurso, com contagem. O restante da marcação é conferido pelas varreduras do app `ui` |

### `test_interface_text.py`

| Classe | O que garante |
|---|---|
| `AuthenticationMessagesTests` | Login sem mensagem; logout mostra a sessão encerrada; textos de credenciais incorretas e e-mail inválido |
| `PasswordResetTextTests` | Aviso de envio na terceira pessoa; senhas diferentes |
| `ManagementScreensTextTests` | E-mail inválido no cadastro e na edição |

## Importação de usuários

### `test_user_import.py`

Definição da importação sobre o motor do app `imports`.

| Classe | O que garante |
|---|---|
| `UsernameTests` | Cria e atualiza o nome de usuário; célula vazia mantém o atual; duplicado no arquivo ou de outro usuário recusado; trocar exige a permissão de edição |
| `ActionTests` | Cria na confirmação; planeja troca de perfil e de nome; grafia diferente fica inalterada; perfil desconhecido; e-mail de outro domínio não é cadastrado, mas usuário existente dele é atualizado; inativo continua inativo; perfil de superadmin só muda por superadmin; o e-mail nunca muda |
| `PermissionTests` | Perfil não coberto recusado; cada mudança exige sua permissão e linhas inalteradas só a de importar; a permissão é conferida para quem confirma e de novo quando o worker executa |
| `ContinuityTests` | Rebaixar e promover no mesmo arquivo é aceito; arquivo que deixa o sistema sem administrador é recusado |
| `OutboxTests` | Só os usuários criados recebem o link; divergência não registra link |
| `ScreenEquivalenceTests` | Cada recusa das telas tem linha equivalente na importação, com a mesma mensagem |
| `ConcludedMessageTests` | Mensagens de conclusão |

### `test_user_import_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | As telas pedem só a permissão de importar; importação de outro tipo dá 404; a lista de usuários mostra as ações só com a permissão |
| `UploadTests` | Arquivo válido cria a prévia e a abre; arquivo rejeitado mostra o erro sem criar nada |
| `DetailTests` | Prévia validada oferece confirmar e descartar; com erros, mostra linha e coluna sem confirmar; erro de arquivo; histórico só de importações de usuários |
| `LineNumberFilterTests` | Filtro por número de linha, inválido descartado, combinado com o filtro de situação |
| `ConfirmAndDiscardTests` | Confirmar aplica e informa o link; mensagem de divergência; descartar pergunta no GET; segunda confirmação recusada |
| `TemplateTests` | Modelo em UTF-8 com BOM e ponto e vírgula |
| `ImportDeletionTests` | O administrador exclui importação descartada |
| `ProcessingTests` | Prévia pendente mostra o quadro sem ações; rota de andamento responde 204 enquanto pendente; aviso de demora pelo horário do pedido e limite das configurações; falhas mostram a mensagem; descarte recusado enquanto pendente |
