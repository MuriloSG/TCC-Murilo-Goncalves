## 1. App `accounts` e modelos

- [x] 1.1 Criar a app `accounts` na raiz do projeto e registrá-la em `INSTALLED_APPS`, sem criar diretórios que esta Change não usa (D1)
- [x] 1.2 Criar o model `User` derivado de `AbstractBaseUser`, sem `PermissionsMixin`, com `email`, `name`, `is_active`, `is_superadmin`, `created_at`, `USERNAME_FIELD = "email"` e `REQUIRED_FIELDS = ["name"]` (D2)
- [x] 1.3 Definir `AUTH_USER_MODEL = "accounts.User"` e remover `django.contrib.admin` de `INSTALLED_APPS` e a rota `/admin/` de `config/urls.py` (D2, D17)
- [x] 1.4 Normalizar o e-mail no manager (sem espaços nas pontas e em minúsculas) e garantir a unicidade no banco com `UniqueConstraint` sobre `Lower("email")` (D2)
- [x] 1.5 Criar o model `Role` com `code` (formato `^[A-Z]+(_[A-Z]+)*$`, único), `name` (único sem diferenciar maiúsculas), `description` e `is_system` (D3)
- [x] 1.6 Criar o model `Permission` com `code` no formato `RECURSO.ACAO`, `description` e as propriedades `resource` e `action`, sem colunas para elas (D4)
- [x] 1.7 Criar as tabelas intermediárias explícitas `UserRole` e `RolePermission`, com `role` em `PROTECT` no vínculo do usuário e `CASCADE` nas concessões (D5)
- [x] 1.8 Garantir no banco no máximo um perfil por usuário, com `UniqueConstraint` sobre `UserRole.user` (D6)
- [x] 1.9 Gerar a migration `0001` do esquema e aplicar com `make migrate`
- [x] 1.10 Escrever `accounts/tests/test_models.py` cobrindo normalização e unicidade do e-mail, formato e unicidade dos códigos, nome de perfil repetido, segundo perfil recusado e perfil com usuários protegido pelo `PROTECT` (D20)

## 2. Catálogo de permissões e carga inicial

- [x] 2.1 Criar `accounts/permissions.py` com as constantes das cinco permissões de `USUARIO` e das cinco de `PERFIL` (D8)
- [x] 2.2 Definir `ADMINISTRATIVE_CAPABILITY` como lista explícita das cinco permissões de `USUARIO`, sem nenhuma permissão de `PERFIL` (D10)
- [x] 2.3 Definir `SUPERADMIN_RESERVED_PERMISSIONS` com as cinco permissões de `PERFIL` (D21)
- [x] 2.4 Criar a migration de dados `0002` que grava o catálogo de permissões, cria os perfis do sistema `ADMINISTRADOR` e `DOCENTE` com `is_system = True` e concede a `ADMINISTRADOR` as cinco permissões de `USUARIO`, sem conceder nenhuma reservada (D9)
- [x] 2.5 Escrever `accounts/tests/test_catalog.py` verificando que os códigos do banco são iguais às constantes, que o conjunto reservado é disjunto da capacidade administrativa e que o estado da carga é o esperado (D20)

## 3. Ponto único de decisão de acesso

- [x] 3.1 Implementar `User.effective_permissions()`, vazio para inativos, todo o catálogo do banco para o superadmin ativo (só exibição) e a união das permissões dos perfis, sem as reservadas, para os demais (D7)
- [x] 3.2 Guardar o resultado na instância do usuário, de modo que alterações valham a partir da próxima requisição (D7)
- [x] 3.3 Implementar `User.has_perm(perm, obj=None)` na ordem anônimo, inativo, superadmin ativo e permissões efetivas, ignorando o parâmetro `obj` (D7, D14)
- [x] 3.4 Implementar `User.has_perms(perm_list)` e `User.has_module_perms(resource)`, este usado por `perms.RECURSO` nos templates (D7)
- [x] 3.5 Escrever `accounts/tests/test_authorization.py` cobrindo anônimo, inativo, superadmin ativo e inativo, permissão fora do perfil, independência do nome do perfil, permissão reservada gravada diretamente e alteração refletida numa nova instância (D20)

## 4. Capacidade e continuidade administrativa

- [x] 4.1 Implementar `User.has_administrative_capability()` a partir de `has_perms(ADMINISTRATIVE_CAPABILITY)`, sem consultar código ou nome do perfil (D10)
- [x] 4.2 Implementar `User.objects.with_administrative_capability()`, a mesma regra em consulta, para contar os usuários com capacidade (D10)
- [x] 4.3 Criar a exceção de domínio `AdministrativeContinuityViolation`, derivada de `ValidationError`, com mensagem em português (D10)
- [x] 4.4 Criar o mecanismo reutilizável de continuidade: transação, bloqueio das linhas dos usuários ativos com `select_for_update` ordenado por `pk`, aplicação da alteração e contagem no estado final (D10)
- [x] 4.5 Implementar `User.deactivate()` com a verificação de continuidade, preservando nome, e-mail, senha, perfil e `is_superadmin` (D13)
- [x] 4.6 Implementar `User.reactivate()` sem verificação de continuidade (D13)
- [x] 4.7 Implementar `User.set_superadmin(value)`, com verificação de continuidade só na remoção, sem criar regra de "sempre existir um superadmin ativo" (D10, D16)
- [x] 4.8 Escrever `accounts/tests/test_continuity.py` cobrindo capacidade por superadmin e por perfil, perfil renomeado, perfil personalizado, bloqueios e permissões de desativação e de remoção de superadmin, e o cenário de concorrência do protocolo (D20)

## 5. Operações de gestão de usuários no model

- [x] 5.1 Implementar a propriedade `User.role`, que devolve o único perfil vinculado (D6)
- [x] 5.2 Implementar `User.objects.register(email, name, role)`, que cria numa transação o usuário ativo, com senha inutilizável, `is_superadmin = False` e o vínculo com o perfil, sem aceitar senha nem `is_superadmin` como argumento (D12)
- [x] 5.3 Validar no `register` nome obrigatório, formato do e-mail, e-mail já em uso sem diferenciar maiúsculas nem situação, e perfil obrigatório, sem deixar usuário sem perfil quando a operação falha (D6)
- [x] 5.4 Implementar `User.change_role(role)`, que troca o vínculo numa transação, com a verificação de continuidade (D6, D10)
- [x] 5.5 Implementar `User.update_details(executor, name, email)`, que altera só nome e e-mail e lança `SuperadminOnlyOperation` quando o e-mail de um superadmin é alterado por quem não é superadmin ativo (D16)
- [x] 5.6 Escrever os testes das operações de usuário e `accounts/tests/test_superadmin_protection.py` na parte de model (D20)
- [x] 5.7 Sincronizar em `update_details`, na mesma transação, os registros `EmailAddress` do allauth do usuário, para que o e-mail antigo deixe de autenticar (D11, depende da seção 7)

## 6. Operações de gestão de perfis no model

- [x] 6.1 Criar as exceções `ReservedPermissionNotGrantable`, `SystemRoleProtected` e `RoleInUse`, todas derivadas de `ValidationError`, com a de `RoleInUse` informando quantos usuários estão vinculados (D21, D22)
- [x] 6.2 Implementar `Role.objects.create_role(code, name, description, permissions)`, sempre com `is_system = False` e sem conceder nenhuma permissão por padrão (D22)
- [x] 6.3 Implementar `role.update_details(name, description)`, que não recebe `code` nem `is_system` e vale também para perfis do sistema (D3, D22)
- [x] 6.4 Implementar `role.set_permissions(permissions)`, que recebe o conjunto final, grava a diferença, recusa permissões reservadas e códigos fora do catálogo, e verifica a continuidade quando retira permissão de `ADMINISTRATIVE_CAPABILITY` (D21, D22)
- [x] 6.5 Fazer `set_permissions` adquirir o mesmo bloqueio de D10, na mesma ordem, para serializar com desativações, trocas de perfil e remoções de superadmin (D10, D22)
- [x] 6.6 Implementar `role.delete_role()`, recusada para perfil do sistema e para perfil com qualquer usuário vinculado, ativo ou inativo (D22)
- [x] 6.7 Escrever `accounts/tests/test_roles.py` cobrindo criação, edição, definição de permissões, exclusão, permissões reservadas, continuidade e o cenário de concorrência com a desativação (D20)

## 7. Autenticação com django-allauth

- [x] 7.1 Acrescentar `django-allauth` ao `requirements.txt`, fixado com `==`, e reconstruir a imagem com `make up` (D19)
- [x] 7.2 Registrar `allauth` e `allauth.account` em `INSTALLED_APPS`, o `AccountMiddleware` em `MIDDLEWARE` e, se a versão exigir, `django.contrib.sites` com `SITE_ID` (D11)
- [x] 7.3 Definir `AUTHENTICATION_BACKENDS` só com o backend do allauth e aplicar as migrations com `make migrate` (D11)
- [x] 7.4 Configurar o allauth: login só por e-mail, sem username, e-mail único, verificação de e-mail desligada, logout só por POST, recuperação por link, sem login automático após redefinir e sem envio para endereços não cadastrados (D11, D12)
- [x] 7.5 Criar `accounts/adapters.py` com o adapter que fecha o cadastro público e registrá-lo em `ACCOUNT_ADAPTER` (D11)
- [x] 7.6 Ligar em `config/urls.py` somente as rotas do allauth usadas por esta Change (login, logout e as quatro etapas da recuperação de senha), em português, sem incluir `allauth.urls` inteiro (D11, D14)
- [x] 7.7 Configurar `LOGIN_URL`, `LOGIN_REDIRECT_URL` e `LOGOUT_REDIRECT_URL` para a página inicial autenticada (D14)
- [x] 7.8 Configurar o e-mail por variáveis de ambiente, com `DJANGO_EMAIL_BACKEND` e `DEFAULT_FROM_EMAIL` no `compose.yaml` e o backend de console como padrão de desenvolvimento (D19)
- [x] 7.9 Sobrescrever os templates do allauth em `accounts/templates/account/`, em português e na base visual do projeto (D11, D18)

## 8. Criação inicial e recuperação de senha

- [x] 8.1 Confirmar que um usuário criado por `register` fica com senha inutilizável e não autentica antes de definir a senha (D12)
- [x] 8.2 Disparar na view de cadastro, após o commit (`transaction.on_commit`), a solicitação de recuperação do allauth para o e-mail do novo usuário, usando o formulário público do allauth (D12)
- [x] 8.3 Avisar quem cadastrou quando o envio do e-mail falhar, mantendo o usuário cadastrado, sem oferecer reenvio pelo administrador (D12)
- [x] 8.4 Verificar, e ajustar no adapter ou em subclasse quando necessário, que o usuário inativo não recebe e-mail e que um link emitido antes da desativação não redefine a senha (D12)

## 9. Comandos de gerenciamento

- [x] 9.1 Criar `accounts/management/commands/create_superadmin.py`, que pede e-mail, nome e a senha duas vezes sem eco, valida a senha pelos `AUTH_PASSWORD_VALIDATORS` e cria numa transação o usuário ativo, superadmin, com o perfil `ADMINISTRADOR` (D16)
- [x] 9.2 Recusar no `create_superadmin` e-mail já cadastrado, indicando na mensagem o comando `set_superadmin` (D16)
- [x] 9.3 Criar `accounts/management/commands/set_superadmin.py`, que concede ou remove `is_superadmin` pelo e-mail, usando a operação do model e, na remoção, a regra de continuidade (D16)
- [x] 9.4 Escrever `accounts/tests/test_commands.py` cobrindo criação, e-mail repetido, senha fraca, concessão, remoção e remoção recusada pela continuidade (D20)

## 10. Base da interface

- [x] 10.1 Criar o template base do projeto e o `403.html` amigável, em português, sem Tailwind nesta Change (D18)
- [x] 10.2 Criar a página inicial autenticada em `inicio/`, exigindo só autenticação, mostrando apenas os atalhos permitidos ao usuário pelo `perms` (D14)
- [x] 10.3 Confirmar que `/admin` não existe e que a raiz `/` continua livre para a consulta pública de outra Change (D14, D17)

## 11. Gestão de usuários na interface

- [x] 11.1 Criar em `accounts/forms.py` os formulários de cadastro, de edição e de troca de perfil, declarando explicitamente os campos aceitos, sem senha e sem `is_superadmin` (D12, D16)
- [x] 11.2 Exibir o e-mail como somente leitura no formulário de edição quando o alvo for superadmin e o executor não for superadmin ativo (D16)
- [x] 11.3 Criar as views de listagem, cadastro, edição, troca de perfil, desativação e reativação como class-based views que declaram a permissão em `permission_required`, com `login_required` nas URLs e a verificação no `PermissionMiddleware` (D14)
- [x] 11.4 Aceitar as ações de situação somente por POST com CSRF, com confirmação (D13)
- [x] 11.5 Mostrar as recusas de regra de negócio (continuidade, proteção de superadmin, e-mail em uso) como mensagem de erro, sem alterar dados (D15)
- [x] 11.6 Criar as rotas de `usuarios/` conforme a tabela de D14 e os templates correspondentes (D14)

## 12. Gestão de perfis na interface

- [ ] 12.1 Criar os formulários de criação, de edição e de permissões de perfil, sem `is_system`, com `code` só na criação e sem oferecer as permissões reservadas (D21, D22)
- [ ] 12.2 Agrupar as permissões por recurso no formulário e na consulta do perfil, usando a propriedade `resource` (D4, D22)
- [ ] 12.3 Criar as views de listagem, consulta, criação, edição, permissões e exclusão declarando as constantes `PERFIL.*` em `permission_required`, com `login_required` nas URLs, sem verificar `is_superadmin` (D14, D21)
- [ ] 12.4 Mostrar na listagem código, nome, se é do sistema e a quantidade de usuários vinculados (D22)
- [ ] 12.5 Aceitar a exclusão somente por POST com CSRF, após confirmação, e mostrar as recusas (perfil do sistema, perfil em uso) como mensagem de erro (D22)
- [ ] 12.6 Criar as rotas de `perfis/` conforme a tabela de D14 e os templates correspondentes (D14)

## 13. Testes de integração

- [ ] 13.1 Escrever `accounts/tests/test_authentication.py`: login por e-mail com maiúsculas, senha errada, usuário inativo, usuário sem senha definida, logout por POST, ausência de cadastro público e das rotas de gestão de e-mail, sessão perdendo validade após a desativação e e-mail antigo sem autenticar após a troca (D20)
- [ ] 13.2 Escrever `accounts/tests/test_password.py`: e-mail disparado pelo cadastro, definição da senha pelo link, link reutilizado, chave adulterada, link invalidado pela troca de e-mail, senha fraca, resposta igual para e-mail desconhecido, usuário inativo sem e-mail, recuperação do superadmin e sessões antigas invalidadas (D20)
- [x] 13.3 Escrever `accounts/tests/test_user_views.py`: para cada rota de usuários, anônimo redirecionado ao login com `next`, autenticado sem permissão com 403, com permissão executando, superadmin com perfil `DOCENTE` acessando, violação de continuidade com erro e ações de situação só por POST (D20)
- [ ] 13.4 Escrever `accounts/tests/test_role_views.py`: para cada rota de perfis, 403 para usuário com todas as permissões de `USUARIO`, acesso do superadmin ativo, formulário sem permissões reservadas, POST com reservada recusado, exclusão só por POST, POST sem CSRF com 403 e alteração de permissões valendo na próxima requisição (D20)
- [x] 13.5 Completar `accounts/tests/test_superadmin_protection.py` com a parte de views, inclusive `is_superadmin` enviado no POST sendo ignorado (D20)
- [ ] 13.6 Executar `make test` e confirmar que toda a suíte passa no PostgreSQL (D20)

## 14. Documentação e verificação final

- [ ] 14.1 Documentar no `README.md` a criação do primeiro superadmin com `make manage cmd="create_superadmin"` e o uso de `set_superadmin` (D16)
- [ ] 14.2 Documentar no `README.md` as variáveis de e-mail e o comportamento padrão de desenvolvimento, com o link aparecendo no console por `make logs` (D12, D19)
- [ ] 14.3 Percorrer as quatro specs desta Change e confirmar que cada cenário tem teste ou verificação manual correspondente
- [ ] 14.4 Executar `make manage cmd="makemigrations --check --dry-run"` e confirmar que não há migration pendente
- [ ] 14.5 Executar `openspec validate gerenciar-usuarios-e-controle-de-acesso --strict` e corrigir o que for apontado
