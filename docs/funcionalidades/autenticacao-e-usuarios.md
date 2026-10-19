# Autenticação, usuários e perfis

Implementação: app `accounts`. Regras consolidadas em [regras de negócio](../regras/regras-de-negocio.md#usuários-e-acesso) e [permissões](../regras/permissoes.md).

## Autenticação

| Rota | Nome | View |
|---|---|---|
| `/contas/login/` | `account_login` | allauth, com `accounts.forms.LoginForm` |
| `/contas/logout/` | `account_logout` | `accounts.views.LogoutView` (só POST; confirmação em modal) |
| `/contas/senha/recuperar/` | `account_reset_password` | allauth |
| `/contas/senha/redefinir/<uidb36>-<key>/` | `account_reset_password_from_key` | allauth |

- Login por e-mail e senha (`ACCOUNT_LOGIN_METHODS = {'email'}`). Não há cadastro público (`AccountAdapter.is_open_for_signup` devolve `False`).
- Usuário inativo com a senha correta recebe a mesma resposta de senha errada, e a recusa é auditada (`AccountAdapter.authenticate`).
- A recuperação não revela se o e-mail existe (`ACCOUNT_PREVENT_ENUMERATION`). O link vale pelo `PASSWORD_RESET_TIMEOUT` padrão do Django (3 dias), serve uma vez e é recusado para usuário inativo (`accounts.tokens.PasswordResetTokenGenerator`). Redefinir a senha não faz login.
- O pedido de recuperação só grava no outbox o envio `REDEFINIR_SENHA` (`PasswordResetForm.save`); o link é gerado e enviado pelo `worker`. A requisição nunca fala com o SMTP, então a resposta e o tempo são os mesmos para e-mail existente, inexistente ou com o servidor de e-mail fora do ar. Pedidos repetidos não duplicam o envio pendente.
- Limites de tentativas: os padrões do allauth, com mensagens reescritas no adaptador.
- Senha: validadores do Django (similaridade com e-mail e nome, tamanho mínimo, senha comum, só números).
- Sessões encerradas: desativar a conta, redefinir a senha ou outra pessoa trocar o e-mail ou o perfil da conta (pela tela, pela importação ou por comando) encerra todas as sessões dela, e o próximo acesso pede login. A troca feita pela própria conta mantém a sessão, e uma alteração que não muda o e-mail nem o perfil não encerra nada. O mecanismo é o hash de autenticação que o Django guarda na sessão e confere a cada requisição, inclusive no WebSocket: `User.session_epoch` entra nesse hash e é incrementado pela troca (`end_sessions_if_changed_by_another`), o que funciona com qualquer backend de sessão e não toca nas sessões de outras contas.

## Usuários

| Ação | Rota | Permissão | Operação |
|---|---|---|---|
| Listar e buscar | `/usuarios/` | `USUARIO.VISUALIZAR` | `User.objects.search(term, status)` |
| Cadastrar | `/usuarios/novo/` | `USUARIO.CRIAR` | `User.objects.register` |
| Editar nome, e-mail e nome de usuário | `/usuarios/<pk>/editar/` | `USUARIO.EDITAR` | `User.update_details` |
| Trocar perfil | `/usuarios/<pk>/perfil/` | `USUARIO.ALTERAR_PERFIL` | `User.change_role` |
| Desativar e reativar | `/usuarios/<pk>/desativar/`, `/reativar/` | `USUARIO.ALTERAR_SITUACAO` | `User.deactivate`, `User.reactivate` |

- A busca compara trecho do nome, do e-mail ou do nome de usuário, sem caixa, e filtra por situação (`ativos`, `inativos`). Lista paginada de 5 em 5 (`ui.pagination.PAGE_SIZE`).
- O cadastro cria o usuário sem senha utilizável e grava no outbox o e-mail `LINK_SENHA`. Ninguém define a senha de outra pessoa.
- A troca de perfil gera a notificação `PERFIL_ALTERADO` ao usuário, mesmo inativo.
- Não existe exclusão de usuário pela interface. O comando `delete_users` existe para o ambiente de desenvolvimento.

## Perfis

| Ação | Rota | Permissão (reservada ao superadmin) |
|---|---|---|
| Listar e ver as permissões | `/perfis/`, `/perfis/<pk>/` | `PERFIL.VISUALIZAR` |
| Criar (em duas etapas: dados e permissões) | `/perfis/novo/` | `PERFIL.CRIAR` |
| Editar nome e descrição | `/perfis/<pk>/editar/` | `PERFIL.EDITAR` |
| Definir as permissões | `/perfis/<pk>/permissoes/` | `PERFIL.ALTERAR_PERMISSOES` |
| Excluir | `/perfis/<pk>/excluir/` | `PERFIL.EXCLUIR` |

As permissões aparecem agrupadas por módulo (`accounts.permissions.RESOURCE_LABELS`). O código do perfil não muda depois da criação.

## Superadmin

Atributo do usuário, controlado só por comando:

```bash
make manage cmd="create_superadmin"                         # pede e-mail, nome e senha
make manage cmd="set_superadmin maria@ifnmg.edu.br --grant"
make manage cmd="set_superadmin maria@ifnmg.edu.br --revoke"
```

- `create_superadmin` cria o usuário ativo, com senha (validada pela mesma política) e sem perfil, sem depender de e-mail nem de nenhum perfil cadastrado. Recusa e-mail já cadastrado. Não exige o domínio `@ifnmg.edu.br`.
- `--revoke` é recusado quando deixaria o sistema sem capacidade administrativa.

## Importação de usuários

Rotas em `/usuarios/importacoes/`, acessadas pelo botão "Importações" da lista de usuários ou, para quem tem `USUARIO.IMPORTAR` sem `USUARIO.VISUALIZAR`, pelo item Usuários do menu. O ciclo de vida é o do [motor de importação](../arquitetura/motor-de-importacao.md).

| Ação | Permissão |
|---|---|
| Histórico, envio, modelo, detalhe, andamento, confirmação e descarte | `USUARIO.IMPORTAR` |
| Excluir importação descartada, com erros ou que falhou | `USUARIO.EXCLUIR_IMPORTACAO` |

Arquivo: CSV em UTF-8, separador `;`, colunas `E-mail`, `Nome`, `Perfil` (código do perfil, por exemplo `DOCENTE`) e `Nome de usuário`. As quatro colunas precisam estar no cabeçalho; `Nome de usuário` pode ter células vazias. O modelo é baixado em `/usuarios/importacoes/modelo/`.

Cada linha é identificada pelo e-mail:

- E-mail novo: cadastro, como pela tela (exige `USUARIO.CRIAR` e o domínio institucional; envia o link de senha depois da confirmação).
- E-mail existente: atualiza nome (`USUARIO.EDITAR`), nome de usuário (`USUARIO.EDITAR`) e perfil (`USUARIO.ALTERAR_PERFIL`). O e-mail e a situação não mudam. Usuário inativo gera aviso e continua inativo. `Nome de usuário` vazio mantém o valor atual.
- A falta de permissão para o que a linha muda vira erro da linha.
- A continuidade administrativa é verificada uma vez, no fim, e não a cada linha (`deferred_administrative_continuity`).

## Testes

`accounts/tests/`: `test_authentication.py`, `test_password.py`, `test_models.py`, `test_continuity.py`, `test_roles.py`, `test_role_views.py`, `test_user_views.py`, `test_user_search.py`, `test_superadmin_protection.py`, `test_commands.py`, `test_user_import.py`, `test_user_import_views.py`, `test_route_protection.py`.

O que cada classe garante está no catálogo de testes do app [`accounts`](../desenvolvimento/testes/accounts.md).
