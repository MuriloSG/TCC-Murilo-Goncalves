## Context

O fluxo atual é o da Change `solicitar-agendamento-com-vinculo-academico`. `BookingRequestCreateView` (`agenda/solicitar/`, `AGENDA.SOLICITAR`) monta o `BookingRequestForm` com o docente do usuário logado (`teacher_of`), o semestre da data (`semester_of`) e as disciplinas e turmas de `TeachingAssignment.objects.available(semester, teacher=...)`. A data e a disciplina recarregam `#request-fields` por `hx-get` na mesma rota. O primeiro envio chama `BookingRequest.objects.prepare` e mostra a revisão; o envio com `confirmar=1` chama `submit`. `prepare` confere, nesta ordem, a permissão (`require`), o docente e a turma (`check_assignment`), o período (`check_period`), os campos (`full_clean`) e o espaço, o horário e os conflitos (`check_slot`). O `Booking` só nasce na aprovação (`approve`) ou no aceite da alternativa.

Relações encontradas no código:

| De | Para | Como |
|---|---|---|
| `User` | `Teacher` | `teacher_of(user)`: `Teacher.name` igual ao `User.username`, sem diferenciar a caixa; sem FK (D7 da Change importar-ensalamento-da-planilha) |
| `Teacher` | `TeachingAssignment` | FK `teacher`, `related_name='assignments'`; `is_current` separa o vínculo atual do histórico |
| `TeachingAssignment` | `ClassOffering` | FK `offering` |
| `ClassOffering` | `Semester`, `Subject`, `ClassGroup` | FKs, com a tripla única |
| `ClassGroup` | `Course` | FK `course` |
| `Allocation` | `Teacher` | M2M `teachers`; `ClassOffering.sync_assignments` deriva os vínculos das alocações atuais |

`Course` não tem ligação direta com `Subject` nem com `Teacher`: o curso de uma disciplina é sempre o curso da turma da oferta.

## Decisions

### D1. Fonte de verdade da cadeia: `TeachingAssignment.available`
A cadeia usuário → curso → disciplina → turma é lida dos vínculos atuais do semestre:

`User` → `teacher_of` → `Teacher` → `TeachingAssignment(is_current=True, offering__semester=semestre)` → `ClassOffering` → `Subject` e `ClassGroup` → `Course`.

É a mesma fonte que o fluxo atual já usa e que `check_assignment` já exige no model. `Allocation` não é usada diretamente: `sync_assignments` já resume as alocações atuais em `TeachingAssignment`, e ler as alocações criaria uma segunda regra para a mesma pergunta. `teacher_scope` (escopo das telas de Disciplinas e Turmas) também não serve, porque inclui vínculos históricos e ignora o semestre. Nenhuma entidade ou FK nova é criada para a cadeia.

O semestre vem da data, como hoje (`semester_of`). Por isso a cadeia é sempre a do semestre da data: um curso ou disciplina de outro semestre não aparece e é recusado.

### D2. "Criar agendamento" é criar a solicitação em nome do usuário
A spec da Agenda chama de agendamento o uso aprovado, e só `approve` e `accept_suggestion` criam `Booking`. O pedido desta Change é que o fluxo normal continue depois da escolha da turma, sem recriar regras. Então a operação cria a `BookingRequest` `PENDENTE` com `requested_by` igual ao usuário escolhido, pelo mesmo `prepare` e `submit`. A análise, a alternativa, a aprovação, a exclusão de sobreposição do banco e as notificações continuam como estão. O usuário escolhido vê a solicitação em "Minhas solicitações" e responde à alternativa como dono (`check_owner`).

Criar o agendamento já aprovado exigiria decidir sobre `AGENDA.ANALISAR`, a restrição de exclusão e as notificações de aprovação, e fica fora do escopo.

### D3. Validação da cadeia no model, numa função só
`check_assignment(user, semester, assignment)` passa a ser `check_assignment(requester, semester, assignment, course=None, subject=None)`:

1. `teacher_of(requester)`; sem docente, recusa com `not_a_teacher`, no campo `requested_for` quando a criação é em nome de outro usuário.
2. Semestre e turma obrigatórios, como hoje.
3. O vínculo precisa ser do docente, atual e do semestre, como hoje.
4. Quando informados, `assignment.offering.subject_id` precisa ser a disciplina e `assignment.offering.class_group.course_id` precisa ser o curso. A divergência é recusada no campo `teaching_assignment` (turma fora da disciplina) ou `subject` (disciplina fora do curso).

O fluxo do próprio docente passa a enviar também a disciplina, e ganha a conferência da disciplina que hoje só existe no formulário. As duas telas usam a mesma função, sem regra duplicada.

`prepare(user, space, day, start, end, description, semester=None, assignment=None, requester=None, course=None, subject=None)`:

- `requester` ausente ou igual a `user`: `require(user, AGENDA.SOLICITAR)`, como hoje.
- `requester` diferente de `user`: `require(user, AGENDA.CRIAR)`. O `requester` precisa estar ativo.
- `requested_by = requester or user`, e `created_by = user` só quando os dois são diferentes.
- `check_period`, `full_clean` e `check_slot` não mudam.

`submit` repassa os argumentos e grava, na mesma transação, a solicitação, a auditoria (com `solicitante` e `criada_por`) e a notificação.

### D4. Permissão `AGENDA.CRIAR`
- Constante `BOOKING_CREATE = 'AGENDA.CRIAR'` em `accounts/permissions.py`, dentro de `BOOKING_PERMISSIONS` (e, por ela, de `ALL_PERMISSIONS`).
- Migration `accounts/0014_booking_create_permission`, no formato da `0013`: `get_or_create` idempotente, concessão só ao perfil de sistema `ADMINISTRADOR`, sem tocar nas demais concessões. `DOCENTE` não recebe.
- Não é reservada ao superadmin. O superadmin a tem porque `User.has_perm` devolve todos os códigos da tabela `Permission` para ele; basta a migration criar o registro.
- A rota `agenda/criar/` tem `login_required` no `urls.py` e `permission_required = permissions.BOOKING_CREATE` na view, aplicada pelo `PermissionMiddleware`. A view não decide acesso.
- O model confere a permissão de novo em `prepare`, então uma chamada que escape da rota também é recusada.
- A spec de agenda proíbe `AGENDA.GERENCIAR` e "outra permissão genérica". `AGENDA.CRIAR` cobre uma única operação, e não é genérica.

### D5. Formulário: subclasse do atual
`BookingOnBehalfForm(BookingRequestForm)` acrescenta `requested_for` ("Usuário") e `course` ("Curso") antes de `subject`. O `__init__` do `BookingRequestForm` é dividido para que o docente venha de um método (`teacher_for`), que na subclasse usa o usuário escolhido. A ordem dos campos é usuário, curso, disciplina, turma, espaço, data, início, fim e descrição.

- **Usuário:** usuários ativos que correspondem a um docente com vínculo atual no semestre da data, numa consulta (`Exists` de `TeachingAssignment` com `teacher__name__iexact=OuterRef('username')`), ordenados pelo nome, com o rótulo "Nome (username)". O pedido fala em "qualquer usuário", mas `check_assignment` recusa quem não é docente; listar usuários sem docente só levaria a um curso sempre vazio. O campo é obrigatório e, pela seção 9.9 das convenções, não usa fonte paginada: todas as opções vêm no `select`, e a busca do `select.js` filtra no navegador.
- **Curso, disciplina e turma:** saem de uma única lista `available(semester, teacher=...)`, como hoje. Curso: os `class_group.course` dos vínculos. Disciplina: as dos vínculos cujo curso é o escolhido. Turma: os vínculos da disciplina e do curso escolhidos.
- Os `queryset` dos campos são exatamente essas listas: um ID fora delas é recusado pelo formulário com `invalid_choice`, e o model confere de novo (D3).

### D6. Dependência dos selects e limpeza
Mesmo mecanismo do fluxo atual: `hx-get` para a própria rota, `hx-include` e `hx-target` em `#request-fields`, `hx-select` do mesmo bloco e `hx-swap="outerHTML"`. Usuário, curso, disciplina e data têm o `hx-get`.

Hoje o formulário mantém o valor anterior quando ele ainda é uma opção válida. Com quatro níveis, isso deixaria a disciplina selecionada ao trocar de usuário quando os dois docentes têm a mesma disciplina. A limpeza é feita no servidor: o GET do htmx traz o campo que disparou a troca no cabeçalho `HX-Trigger-Name`, lido por `request.htmx.trigger_name` (`django-htmx`, já instalado). A view passa esse nome ao formulário, que remove dos dados os campos seguintes (`DEPENDENTS = {'requested_for': ('course', 'subject', 'teaching_assignment'), 'course': ('subject', 'teaching_assignment'), 'subject': ('teaching_assignment',)}`) antes de montar as opções. A troca da data refaz as opções, e o valor que deixou de ser válido sai sozinho, como hoje. A regra fica testável no servidor, sem JavaScript novo.

### D7. `created_by` na solicitação
`BookingRequest.created_by`: FK nula para `User`, `PROTECT`, `related_name='+'`, preenchida só quando a solicitação foi criada em nome de outro usuário. É o registro de quem agiu, e não parte da cadeia acadêmica. A auditoria já grava o ator, mas "Minhas solicitações" e a análise precisam mostrar "Criada por" sem consultar a auditoria. `requested_by` continua sendo o dono para todas as regras (posse, notificações, "Minha agenda").

### D8. Entrada pela Grade
A faixa disponível da Grade continua abrindo "Solicitar agendamento" para quem tem `AGENDA.SOLICITAR`. `request_url` recebe o nome da rota: quem tem `AGENDA.CRIAR` e não tem `AGENDA.SOLICITAR` abre `agenda/criar/` pela faixa. O modal "Solicitar agendamento" mostra o link "Criar para outro usuário" só com `perms.AGENDA.CRIAR`, levando espaço, data e horário. O cabeçalho da Agenda ganha o botão "Criar solicitação para outro usuário" com a mesma condição. Os `perms` só mostram ou escondem, e a rota continua protegida pelo middleware.

### D9. Consultas
Uma consulta para os usuários, uma para o semestre da data, uma para os vínculos atuais do docente escolhido (com `select_related` de disciplina, turma e curso) e uma para as faixas. Curso, disciplina e turma são filtrados em memória a partir dos vínculos. `request_related` ganha `created_by`.

## Risks / Trade-offs

- Sem JavaScript, a troca de usuário, curso ou disciplina não recarrega as opções sozinha. O backend recusa qualquer combinação inválida, e a página completa funciona com o envio do formulário.
- A correspondência entre usuário e docente continua dependendo do `username`. Um docente sem `username` correspondente não aparece na lista de usuários.
- O usuário escolhido pode não ter `AGENDA.SOLICITAR`. A solicitação é criada, mas ele não consegue responder a uma alternativa (`check_owner`). Não se exige essa permissão dele para não mudar a regra de posse; o caso fica registrado nos testes.
- A tela é nova, mas sem imagem de referência, por decisão do autor: o modal reaproveita o componente e o visual do modal "Solicitar agendamento", sem elemento novo.
