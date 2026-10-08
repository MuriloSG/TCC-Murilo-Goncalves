# Permissões

Controle de acesso por perfil (RBAC). Catálogo: `accounts/permissions.py`. Carga inicial: `accounts/migrations/0002_system_roles_and_permissions.py`. Verificação: `accounts.middleware.PermissionMiddleware` e `User.has_perm`.

## Como o acesso é decidido

1. A rota autenticada usa `login_required` no `urls.py`. Anônimo vai ao login com `next`.
2. A view declara `permission_required = permissions.CONSTANTE`. O `PermissionMiddleware` responde 403 sem ela.
3. Algumas views e operações conferem uma segunda permissão ou o vínculo de docente (tabela abaixo).
4. `User.has_perm`: inativo não tem nada; superadmin ativo tem tudo; os demais têm as permissões do perfil, exceto as `PERFIL.*`.
5. Templates usam `perms.RECURSO.ACAO` só para mostrar ou esconder links. Nenhum código decide acesso pelo nome do perfil ou por `is_superadmin`, exceto o escopo de disciplinas e turmas (`teacher_scope`) e a escolha do modal da Agenda (`creates_directly`).

## Catálogo e perfis do sistema

A = `ADMINISTRADOR`, D = `DOCENTE`. O superadmin tem todas.

| Código | Descrição | A | D |
|---|---|---|---|
| `USUARIO.VISUALIZAR` | Listar e consultar usuários | ✓ | |
| `USUARIO.CRIAR` | Cadastrar usuário | ✓ | |
| `USUARIO.EDITAR` | Alterar nome, e-mail e nome de usuário | ✓ | |
| `USUARIO.ALTERAR_PERFIL` | Trocar o perfil de um usuário | ✓ | |
| `USUARIO.ALTERAR_SITUACAO` | Desativar e reativar usuário | ✓ | |
| `USUARIO.IMPORTAR` | Importar usuários e consultar o histórico | ✓ | |
| `USUARIO.EXCLUIR_IMPORTACAO` | Excluir importações de usuários descartadas, com erros ou que falharam | ✓ | |
| `PERFIL.VISUALIZAR` | Listar e consultar perfis | reservada | |
| `PERFIL.CRIAR` | Criar perfil personalizado | reservada | |
| `PERFIL.EDITAR` | Alterar nome e descrição | reservada | |
| `PERFIL.ALTERAR_PERMISSOES` | Definir as permissões de um perfil | reservada | |
| `PERFIL.EXCLUIR` | Excluir perfil personalizado sem usuários | reservada | |
| `AUDITORIA.VISUALIZAR` | Consultar a auditoria | ✓ | |
| `NOTIFICACAO.PUBLICAR` | Publicar notificações | ✓ | |
| `PAINEL.VISUALIZAR` | Ver o painel administrativo | ✓ | |
| `RELATORIO.VISUALIZAR` | Ver os relatórios | ✓ | |
| `CONFIGURACAO.EDITAR` | Editar as configurações do sistema (servidor de e-mail) | ✓ | |
| `ENSALAMENTO.VISUALIZAR` | Consultar a Grade do ensalamento | ✓ | |
| `ENSALAMENTO.IMPORTAR` | Importar o ensalamento | ✓ | |
| `ENSALAMENTO.EXCLUIR_IMPORTACAO` | Excluir importações de ensalamento descartadas, com erros ou que falharam | ✓ | |
| `ENSALAMENTO.CANCELAR_OCORRENCIA` | Cancelar a ocorrência de qualquer aula | ✓ | |
| `ENSALAMENTO.ALTERAR_RECORRENCIA` | Alterar a recorrência de uma aula | ✓ | |
| `ENSALAMENTO.CRIAR_RECORRENCIA` | Cadastrar aula recorrente | ✓ | |
| `ENSALAMENTO.ENCERRAR_RECORRENCIA` | Encerrar uma aula a partir de uma data | ✓ | |
| `ESPACO.VISUALIZAR` | Consultar a lista de espaços | ✓ | |
| `ESPACO.CRIAR` | Cadastrar espaço, inclusive pela importação | ✓ | |
| `ESPACO.EDITAR` | Alterar nomes, inclusive pela importação | ✓ | |
| `ESPACO.ALTERAR_SITUACAO` | Desativar e reativar, inclusive pela importação | ✓ | |
| `ESPACO.EXCLUIR` | Excluir espaço sem aulas | ✓ | |
| `AGENDA.VISUALIZAR` | Consultar a Grade da Agenda | ✓ | ✓ |
| `AGENDA.SOLICITAR` | Solicitar, acompanhar as próprias solicitações e responder à alternativa | ✓ | ✓ |
| `AGENDA.ANALISAR` | Analisar solicitações: aprovar, rejeitar, sugerir, cancelar | ✓ | |
| `AGENDA.CRIAR` | Criar solicitação em nome de outro usuário | ✓ | |
| `CURSO.VISUALIZAR`, `CRIAR`, `EDITAR`, `EXCLUIR` | Cursos, sem escopo de docente | ✓ | |
| `DISCIPLINA.VISUALIZAR`, `CRIAR`, `EDITAR`, `EXCLUIR` | Disciplinas do próprio escopo | ✓ | |
| `TURMA.VISUALIZAR`, `CRIAR`, `EDITAR`, `EXCLUIR` | Turmas do próprio escopo | ✓ | |

`ADMINISTRATIVE_CAPABILITY` (as cinco primeiras `USUARIO.*`) define a [continuidade administrativa](regras-de-negocio.md#usuários-e-acesso).

## Superadmin

- Atributo `User.is_superadmin`, não perfil nem permissão. Controlado só por `create_superadmin` e `set_superadmin`.
- Tem todas as permissões, inclusive as reservadas `PERFIL.*`: só ele gerencia perfis.
- Vê todas as disciplinas e turmas (os demais veem só o escopo de docente).
- Só um superadmin ativo altera o e-mail de outro superadmin. As demais ações sobre um superadmin (desativar, trocar perfil) seguem as permissões comuns e a continuidade administrativa.

## Verificações além da rota

| Rota ou operação | Permissão da rota | Conferência adicional |
|---|---|---|
| Cancelar ocorrência (`/ensalamento/...` e `/agenda/...`) | `ENSALAMENTO.VISUALIZAR` ou `AGENDA.VISUALIZAR` | `ENSALAMENTO.CANCELAR_OCORRENCIA` ou ser docente da aula (`manages`) |
| Exceções do ensalamento | `ENSALAMENTO.VISUALIZAR` ou `AGENDA.VISUALIZAR` | Sem `CANCELAR_OCORRENCIA`, só as aulas do próprio docente |
| Alterar, cadastrar, encerrar recorrência | a da ação | O model confere a mesma permissão de novo |
| Painel, blocos | `PAINEL.VISUALIZAR` | `AGENDA.ANALISAR`, `ENSALAMENTO.VISUALIZAR`, `ENSALAMENTO.IMPORTAR` por bloco; `AGENDA.VISUALIZAR` para choques |
| Mapa de calor | `RELATORIO.VISUALIZAR` | `ENSALAMENTO.VISUALIZAR` (403 sem ela) |
| Relatório de solicitações | `RELATORIO.VISUALIZAR` | `AGENDA.ANALISAR` (403 sem ela) |
| Importação de usuários, por linha | `USUARIO.IMPORTAR` | `USUARIO.CRIAR`, `EDITAR`, `ALTERAR_PERFIL` conforme o que a linha muda |
| Importação de ensalamento, decisão de espaço | `ENSALAMENTO.IMPORTAR` | `ESPACO.CRIAR`, `EDITAR` ou `ALTERAR_SITUACAO` conforme a decisão |
| Disciplinas e turmas | `DISCIPLINA.*`, `TURMA.*` | Registro fora do escopo de docente responde 404 |
| Solicitar agendamento | `AGENDA.SOLICITAR` | Usuário precisa corresponder a docente com vínculo atual |
| Cancelar agendamento | `AGENDA.SOLICITAR` (próprio) ou `AGENDA.ANALISAR` | O model aceita quem solicitou ou quem analisa |
| Notificações (sino, abrir, marcar) | só login | Só as do próprio usuário |

## Menu

`ui/navigation.py`. O item aparece quando a primeira rota dele é liberada; `/inicio/` abre o primeiro item liberado.

| Grupo | Item | Permissão |
|---|---|---|
| | Painel | `PAINEL.VISUALIZAR` |
| | Agenda | `AGENDA.VISUALIZAR` |
| Gestão acadêmica | Ensalamento | `ENSALAMENTO.VISUALIZAR` ou, sem ela, `ENSALAMENTO.IMPORTAR` (abre as importações) |
| | Espaços, Cursos, Disciplinas, Turmas | `ESPACO.VISUALIZAR`, `CURSO.VISUALIZAR`, `DISCIPLINA.VISUALIZAR`, `TURMA.VISUALIZAR` |
| Relatórios | Mapa de calor | `RELATORIO.VISUALIZAR` e `ENSALAMENTO.VISUALIZAR` |
| | Solicitações | `RELATORIO.VISUALIZAR` e `AGENDA.ANALISAR` |
| | Notificações | `NOTIFICACAO.PUBLICAR` |
| Administração | Usuários | `USUARIO.VISUALIZAR` ou, sem ela, `USUARIO.IMPORTAR` (abre as importações de usuários) |
| | Perfis e permissões, Auditoria | `PERFIL.VISUALIZAR`, `AUDITORIA.VISUALIZAR` |
| Configurações | E-mail | `CONFIGURACAO.EDITAR` |

As importações de usuários abrem pelo botão "Importações" da lista de usuários, mostrado com `USUARIO.IMPORTAR`, ou pelo item Usuários do menu para quem tem `USUARIO.IMPORTAR` sem `USUARIO.VISUALIZAR`. O menu só indica o caminho: cada tela exige a própria permissão no servidor. `USUARIO.IMPORTAR` não libera a lista nem o cadastro de usuários, e excluir uma importação exige `USUARIO.EXCLUIR_IMPORTACAO`.

## Permissão nova

1. Constante em `accounts/permissions.py`, incluída em `ALL_PERMISSIONS` e, se for de recurso novo, em `RESOURCE_LABELS`.
2. Migration de dados que cria a permissão e a concede aos perfis do sistema. A `0002` escreve os códigos literalmente, sem importar as constantes.
3. `permission_required` na view e a rota em `PROTECTED_ROUTES` de `accounts/tests/test_route_protection.py`.
4. Depois do deploy, o superadmin revisa os perfis personalizados: a permissão nova só chega aos perfis do sistema.
