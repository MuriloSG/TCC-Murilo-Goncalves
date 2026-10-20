# Permissões

Controle de acesso por perfil (RBAC). Catálogo: `accounts/permissions.py`. Carga inicial: `create_catalog` em `accounts/migrations/0001_initial.py`. Verificação: `accounts.middleware.PermissionMiddleware` e `User.has_perm`.

## Como o acesso é decidido

1. A rota autenticada usa `login_required` no `urls.py`. Anônimo vai ao login com `next`.
2. A view declara `permission_required = permissions.CONSTANTE`. O `PermissionMiddleware` responde 403 sem ela.
3. Algumas views e operações conferem uma segunda permissão ou o vínculo de docente (tabela abaixo).
4. `User.has_perm`: inativo não tem nada; superadmin ativo tem tudo; os demais têm as permissões do perfil, exceto as `PERFIL.*`.
5. Templates usam `perms.RECURSO.ACAO` só para mostrar ou esconder links. Nenhum código decide acesso pelo código, pelo nome ou pela origem do perfil. Fora de `User.has_perm`, só a escolha do modal da Agenda (`creates_directly`) lê `is_superadmin`.
6. Nenhum perfil é especial para o código. Os perfis criados pela carga inicial são dados, editados e excluídos como qualquer outro.

## Catálogo e concessão inicial

As colunas A e D mostram o que a carga inicial concede aos perfis de exemplo `ADMINISTRADOR` e `DOCENTE`. É dado, e não regra: os dois são perfis comuns, com permissões alteráveis, e podem ser renomeados ou excluídos sem usuários. O superadmin tem todas.

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
| `CONFIGURACAO.EDITAR` | Editar as configurações do sistema (servidor de e-mail) | reservada | |
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
| `DISCIPLINA.ACESSAR_TODAS` | Alcançar todas as disciplinas, e não só as do próprio escopo | | |
| `TURMA.ACESSAR_TODAS` | Alcançar todas as turmas, e não só as do próprio escopo | | |

As duas permissões de alcance (`ACADEMIC_SCOPE_PERMISSIONS`) só ampliam o que `DISCIPLINA.*` e `TURMA.*` já liberam: sozinhas não abrem nenhuma rota. A carga inicial não as concede a nenhum perfil; a concessão é feita na tela de perfis.

`ADMINISTRATIVE_CAPABILITY` (as cinco primeiras `USUARIO.*`) define a [continuidade administrativa](regras-de-negocio.md#usuários-e-acesso).

## Superadmin

- Atributo `User.is_superadmin`, não perfil nem permissão. Controlado só por `create_superadmin` e `set_superadmin`.
- Tem todas as permissões, inclusive as reservadas `PERFIL.*` e `CONFIGURACAO.EDITAR`: só ele gerencia perfis e o servidor de e-mail, cuja configuração decide para onde vão os links de senha.
- Vê todas as disciplinas e turmas, porque `has_perm` responde sim para as permissões de alcance.
- Não precisa de perfil: `create_superadmin` cria a conta sem nenhum.
- Só um superadmin ativo altera o e-mail, o nome de usuário, o perfil ou a situação de outro superadmin. O nome continua editável por quem tem `USUARIO.EDITAR`.

## Cobertura de quem gere usuários

Ter a permissão da operação não basta: o executor precisa cobrir o que altera. A regra fica no model (`check_role_assignable` e `check_account_manageable` em `accounts/models.py`) e vale para a tela, o POST direto e a importação.

- Cadastrar, trocar perfil ou importar com um perfil exige ter todas as permissões desse perfil. Os formulários só oferecem esses perfis.
- Alterar e-mail, nome de usuário, perfil ou situação de outra conta exige ter todas as permissões que ela concede, mesmo com a conta inativa.
- O próprio nome de usuário, que liga a conta ao docente, só é alterado por outro usuário ou por um superadmin.
- Superadmin ativo cobre tudo. Comandos de gerenciamento chamam as operações sem executor e não passam por essa verificação.

### Vínculo com o docente

A conta é ligada ao docente do ensalamento pelo nome de usuário, comparado sem diferenciar caixa com `Teacher.name`. Os dois são únicos sem diferenciar caixa, então cada docente fica ligado a no máximo uma conta; para passar o vínculo a outra conta, é preciso primeiro tirar o nome da conta atual. Trocar o nome de usuário exige a cobertura acima e, quando liga ou desliga um docente, a auditoria da alteração traz `docente_desligado` e `docente_ligado` em `metadata`.

Risco aceito: quem cobre as permissões das duas contas pode mover o vínculo de um docente, e com ele o escopo de disciplinas e turmas e o cancelamento de ocorrências. A troca fica registrada. Docentes homônimos na planilha viram um só `Teacher` e dividem o escopo; isso vem da planilha e não do vínculo.

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
| Disciplinas e turmas | `DISCIPLINA.*`, `TURMA.*` | Sem `DISCIPLINA.ACESSAR_TODAS` ou `TURMA.ACESSAR_TODAS`, registro fora do escopo de docente responde 404 |
| Solicitar agendamento | `AGENDA.SOLICITAR` | Nenhuma ligada ao docente: a turma é opcional e, quando informada, precisa ser vínculo atual do semestre da data |
| Cancelar agendamento | `AGENDA.SOLICITAR` (próprio) ou `AGENDA.ANALISAR` | O model aceita quem solicitou ou quem analisa |
| Notificações (sino, abrir, marcar) | só login | Só as do próprio usuário |
| Central de ajuda (`/ajuda/`, `?tela=`) | só login | Cada funcionalidade e cada passo só aparecem, e só chegam ao HTML, com as permissões declaradas em `tutorials/catalog.py`; a ajuda da tela mostra só as funcionalidades da opção do menu de origem |

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

A central de ajuda abre pelo ícone do cabeçalho e da barra do celular, fora do `MENU`, para todo usuário autenticado; por isso não muda a página aberta por `/inicio/`.

## Permissão nova

1. Constante em `accounts/permissions.py`, incluída em `ALL_PERMISSIONS` e, se for de recurso novo, em `RESOURCE_LABELS`.
2. Migration de dados que só cria a permissão, com o código escrito literalmente, sem importar as constantes. Ela não concede a permissão a nenhum perfil e nunca procura perfil pelo código ou pelo nome.
3. `permission_required` na view e a rota em `PROTECTED_ROUTES` de `accounts/tests/test_route_protection.py`.
4. Depois do deploy, o superadmin concede a permissão aos perfis que devem recebê-la, pela tela de perfis.
