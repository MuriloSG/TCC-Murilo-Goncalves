# Plano de implementação: criar-agendamento-para-outro-usuario

Plano passo a passo da Change. As decisões e os motivos estão no `design.md` (D1 a D9). Este plano diz o que muda em cada arquivo, em que ordem e como cada parte é testada.

---

## 1. O que a investigação encontrou

### 1.1 Cadeia usuário, curso, disciplina e turma no código atual

```
User ──(teacher_of: Teacher.name iexact User.username, sem FK)──> Teacher
Teacher ──(FK teacher, related_name='assignments')──> TeachingAssignment [is_current]
TeachingAssignment ──(FK offering)──> ClassOffering [semester, subject, class_group]
ClassOffering.class_group ──(FK course)──> Course
```

- `schedule/models.py` `teacher_of(user)`: `Teacher.objects.filter(name__iexact=user.username).first()`, `None` para inativo ou sem `username`.
- `TeachingAssignment.objects.available(semester, teacher, subject, class_group)`: só `is_current=True` do semestre, com `select_related('teacher', 'offering__subject', 'offering__class_group__course')`. Já traz o curso sem consulta extra.
- `Course` só se liga ao resto por `ClassGroup.course`. Não há `Course` ↔ `Subject` nem `Course` ↔ `Teacher`.
- `Allocation.teachers` (M2M) é a origem dos vínculos: `ClassOffering.sync_assignments` resume as alocações atuais em `TeachingAssignment`. A Agenda já lê os vínculos, e não as alocações.
- `teacher_scope` (telas de Disciplinas e Turmas) inclui vínculos históricos e ignora o semestre, então não serve para a Agenda.

**Fonte de verdade escolhida:** `TeachingAssignment.available(semestre_da_data, teacher=teacher_of(usuario_escolhido))`. Nenhuma entidade nova (D1).

### 1.2 Fluxo atual de criação

- `agenda/solicitar/` → `BookingRequestCreateView(OperationFormView)`, `permission_required = AGENDA.SOLICITAR`.
- `BookingRequestForm`: disciplina e turma do docente logado, semestre pela data (`semester_of`), opções recarregadas por `hx-get` em `#request-fields`.
- 1º POST: `BookingRequest.objects.prepare(...)` e revisão (`request_summary_modal.html`). POST com `confirmar=1`: `submit(...)`.
- `prepare`: `require` → `check_assignment` → `check_period` → `full_clean` → `check_slot`.
- `submit`: transação com `save`, `AuditLog.record(CREATE, BOOKING_REQUEST)` e `announce(REQUESTED)`.
- `Booking` só nasce em `approve` e `accept_suggestion`.

### 1.3 Permissões

- Catálogo em `accounts/permissions.py`; entram no banco por migration de dados (a última é `0013_academic_permissions`).
- `PermissionMiddleware.process_view` lê `permission_required` e responde 403.
- `User.has_perm`: o superadmin tem todos os códigos de `Permission`, e os demais têm os dos perfis, menos os reservados.
- A Agenda tem `AGENDA.VISUALIZAR`, `AGENDA.SOLICITAR` e `AGENDA.ANALISAR` (`0010_booking_permissions`).

---

## 2. Passo a passo

### Passo 1. Permissão `AGENDA.CRIAR`

**`accounts/permissions.py`**
```python
BOOKING_CREATE = 'AGENDA.CRIAR'
BOOKING_PERMISSIONS = frozenset({BOOKING_VIEW, BOOKING_REQUEST, BOOKING_REVIEW, BOOKING_CREATE})
```

**`accounts/migrations/0014_booking_create_permission.py`**: cópia do formato da `0013`.
```python
PERMISSIONS = {'AGENDA.CRIAR': 'Criar solicitação de agendamento em nome de outro usuário'}
```
`get_or_create` da permissão e de `RolePermission` só para `Role(code='ADMINISTRADOR', is_system=True)`. O reverso exclui a permissão, e as concessões saem por CASCADE.

**Superadmin:** nada a fazer, porque `has_perm` já devolve todo código existente em `Permission`.

### Passo 2. Model

**`bookings/models.py`**

1. Campo:
   ```python
   created_by = models.ForeignKey(
       settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
       verbose_name='criada por',
   )
   ```
   Migration `bookings/0004_booking_request_created_by`.

2. Mensagens novas (texto conforme a seção 9 das convenções):
   - `REQUESTER_REQUIRED_MESSAGE = 'Escolha o usuário.'`
   - `COURSE_REQUIRED_MESSAGE = 'Escolha o curso.'`
   - `'O usuário {username} não corresponde a um docente do ensalamento. Escolha outro usuário.'`
   - `'Esta disciplina não está entre as disciplinas do usuário no curso escolhido. Escolha outra disciplina.'`
   - `'Esta turma não está entre as turmas do usuário na disciplina escolhida. Escolha outra turma.'`

3. `check_assignment(requester, semester, assignment, course=None, subject=None, field='requested_for')`: a única conferência da cadeia (D3):
   ```
   teacher = teacher_of(requester)            -> None: recusa (not_a_teacher)
   semester/assignment ausentes               -> recusa (required)
   assignment.teacher_id != teacher.pk
     or not assignment.is_current
     or offering.semester_id != semester.pk   -> recusa em teaching_assignment (not_available)
   subject e offering.subject_id != subject   -> recusa em teaching_assignment
   course e class_group.course_id != course   -> recusa em subject
   ```
   O curso e a disciplina são conferidos a partir do vínculo, que é a fonte de verdade. Assim a cadeia inteira fica garantida com uma leitura só (`assignment` já vem com `offering__class_group`).

4. `prepare(user, space, day, start, end, description, semester=None, assignment=None, requester=None, course=None, subject=None)`:
   ```python
   requester = requester or user
   on_behalf = requester.pk != user.pk
   require(user, permissions.BOOKING_CREATE if on_behalf else permissions.BOOKING_REQUEST)
   check_assignment(requester, semester, assignment, course, subject)
   check_period(semester, day)
   request = self.model(requested_by=requester, created_by=user if on_behalf else None, ...)
   request.full_clean(exclude=[..., 'created_by'], validate_constraints=False)
   check_slot(space, day, start, end)
   ```
   `teacher_of` já devolve `None` para usuário inativo, então o inativo é recusado sem regra nova.

5. `submit(...)` repassa os argumentos novos. A auditoria acrescenta `'solicitante': requester.username` e, quando houver, `'criada_por': user.username`. A notificação `REQUESTED` não muda (`reviewers` já exclui o `requested_by`).

**`schedule/models.py`**: consulta dos usuários da lista (D5), perto de `teacher_of`:
```python
def teacher_users(semester):
    """Usuários ativos que correspondem a um docente com vínculo atual no semestre."""
    return User.objects.filter(is_active=True).filter(Exists(
        TeachingAssignment.objects.filter(
            is_current=True, offering__semester=semester, teacher__name__iexact=OuterRef('username'),
        )
    )).order_by('name')
```
(Se `schedule` não puder importar `accounts.models.User` sem ciclo, a função fica em `bookings/forms.py` com `get_user_model()`.)

### Passo 3. Formulário

**`bookings/forms.py`**

1. Refatorar `BookingRequestForm.__init__` sem mudar o comportamento:
   - `teacher_for(self, user)` → `teacher_of(user)` (ponto de extensão);
   - `build_chain(self, assignments)` monta disciplina e turma a partir da lista.
   - `DEPENDENTS` e `clear_after(trigger)`: copiam `self.data` (`QueryDict.copy()`) e removem os campos seguintes ao que disparou.

2. `BookingOnBehalfForm(BookingRequestForm)`:
   ```python
   DEPENDENTS = {
       'requested_for': ('course', 'subject', 'teaching_assignment'),
       'course': ('subject', 'teaching_assignment'),
       'subject': ('teaching_assignment',),
   }
   field_order = ['requested_for', 'course', 'subject', 'teaching_assignment',
                  'space', 'date', 'start_time', 'end_time', 'description']
   requested_for = UserChoiceField(label='Usuário', empty_label='Escolha o usuário', ...)
   course = forms.ModelChoiceField(label='Curso', empty_label='Escolha o curso', ...)
   ```
   - `__init__(..., trigger='')`: `clear_after(trigger)` antes de tudo; semestre pela data; `requested_for.queryset = teacher_users(semester)`; docente = `teacher_of(usuário escolhido)`; `assignments = available(semester, teacher=...)`.
   - Curso: `{a.offering.class_group.course}`; disciplina: vínculos com `course_id` escolhido; turma: vínculos com curso e disciplina escolhidos.
   - `queryset` de cada campo = exatamente as opções (ID de fora → `invalid_choice`).
   - `hx-get`/`hx-include`/`hx-target`/`hx-select`/`hx-swap` em usuário, curso, disciplina e data, iguais aos do form atual.
   - Aviso quando o usuário escolhido não tem curso no semestre da data.

3. O fluxo do próprio docente passa `subject` ao model (argumento novo em `arguments`).

### Passo 4. View, URL e templates

**`bookings/views.py`**
```python
ON_BEHALF_FIELDS = ('requested_for', 'course', *REQUEST_FIELDS)

class BookingOnBehalfCreateView(BookingRequestCreateView):
    """Modal "Criar solicitação para outro usuário" (Change criar-agendamento-para-outro-usuario)."""
    permission_required = permissions.BOOKING_CREATE
    template_name = 'bookings/on_behalf_form.html'
    modal_template_name = 'bookings/on_behalf_form_modal.html'
    form_class = BookingOnBehalfForm
    fields = ON_BEHALF_FIELDS

    def get_form_kwargs(self):
        trigger = self.request.htmx.trigger_name if self.request.htmx else ''
        return super().get_form_kwargs() | {'refresh_url': reverse('agenda_create'), 'trigger': trigger or ''}

    def arguments(self, form):
        data = form.cleaned_data
        return [*super().arguments(form), data['requested_for'], data['course'], data['subject']]
```
- `BookingRequestCreateView.render_summary` passa a usar `self.fields` em vez da constante, para que os campos ocultos da revisão incluam usuário e curso.
- `request_related` ganha `'created_by'`.
- `AgendaGridView` põe `can_create` no contexto.

**`bookings/urls.py`**
```python
path('agenda/criar/', login_required(views.BookingOnBehalfCreateView.as_view()), name='agenda_create'),
```

**Templates**
- `bookings/on_behalf_form_modal.html` e `on_behalf_form.html`: título "Criar solicitação para outro usuário", mesmo `#request-fields`, `datalist`s e o botão "Revisar solicitação".
- `request_summary_modal.html`: linha "Solicitante" (sempre) e "Criada por" quando `prepared.created_by`.
- `partials/request_record.html` (detalhe e análise): "Criada por".
- `request_form_modal.html`: link "Criar para outro usuário" com `perms.AGENDA.CRIAR`, levando espaço, data e horário.
- `agenda.html`: botão no cabeçalho com `perms.AGENDA.CRIAR`; a faixa usa `agenda_create` quando `can_create and not can_request`.

**`bookings/templatetags/agenda.py`**: `request_url(space, day, start, end, busy=(), route='agenda_request_create')`.

### Passo 5. Testes
Detalhados na seção 3.

### Passo 6. Fechamento
`make test`, `openspec validate criar-agendamento-para-outro-usuario --strict`, conferência visual no banco `visual_check` com Playwright (computador e 360 px), um commit por etapa do `tasks.md`, sem coautor.

---

## 3. Testes previstos

Fixtures em `bookings/tests/base.py`: `academic()` já cria vínculos; acrescentar o parâmetro `course` para criar turmas em `INFORMÁTICA` e `AGROPECUÁRIA`, e `creator = user_with('secretaria@...', BOOKING_VIEW, BOOKING_CREATE)`. Os usuários de permissão não são superadmin (convenções 7).

Arquivo novo: `bookings/tests/test_on_behalf_request.py`.

### Permissão (`OnBehalfAccessTests`)
| Teste | Esperado |
|---|---|
| anônimo em GET `agenda/criar/` | redireciona ao login com `next` |
| com `AGENDA.SOLICITAR`, sem `AGENDA.CRIAR`, GET | 403 |
| sem `AGENDA.CRIAR`, POST com IDs válidos e `confirmar=1` | 403 e nenhuma `BookingRequest` |
| com `AGENDA.CRIAR` (sem superadmin), GET | 200 com o modal |
| superadmin cujo perfil não concede `AGENDA.CRIAR` | cria a solicitação |
| POST sem CSRF | 403 |
| `prepare` com `requester != user` e usuário sem `AGENDA.CRIAR` | `ValidationError(code='permission')` |
| `accounts/tests/test_catalog.py` | 36 permissões; `AGENDA.CRIAR` no `ADMINISTRADOR`, fora do `DOCENTE`; migration idempotente e sem alterar concessões de outros perfis |

### Usuário → Curso
- as opções de curso são só os cursos das turmas dos vínculos de Ana;
- o curso de Bruno não aparece;
- vínculo histórico e vínculo de outro semestre não trazem curso;
- a lista de usuários traz só usuários ativos com docente e vínculo atual no semestre (inativo e sem docente ficam fora).

### Curso → Disciplina
- as disciplinas são só as de Ana no curso escolhido;
- a disciplina de Ana em outro curso não aparece;
- a disciplina de outro docente no mesmo curso não aparece.

### Disciplina → Turma
- as turmas são só as de Ana na disciplina e no curso escolhidos;
- a turma de outro docente na mesma disciplina não aparece.

### Segurança (POST forjado, form e model)
| Combinação enviada | Esperado |
|---|---|
| usuário válido + curso de outro usuário | recusa em `course`, nada gravado |
| usuário válido + curso válido + disciplina de outro curso | recusa em `subject`, nada gravado |
| usuário válido + curso + disciplina válidos + turma de outro docente | recusa em `teaching_assignment`, nada gravado |
| usuário válido + curso + disciplina válidos + turma de outra disciplina do mesmo docente | recusa, nada gravado |
| usuário sem docente correspondente | recusa em `requested_for`, nada gravado |
| usuário inativo | recusa, nada gravado |
| IDs inexistentes | recusa, nada gravado |
| as mesmas combinações direto em `BookingRequest.objects.submit` | `ValidationError` (conferência do model, independente do form) |

### Dependência dos campos (GET htmx com `HX-Request` e `HX-Trigger-Name`)
- trigger `requested_for` com curso, disciplina e turma válidos para o novo usuário: os três voltam sem `selected`;
- trigger `course`: disciplina e turma sem escolha, usuário mantido;
- trigger `subject`: turma sem escolha, usuário e curso mantidos;
- troca da data para outro semestre: as opções são do novo semestre.

### Criação
- revisão sem gravar, com "Solicitante" e "Criada por";
- confirmação cria `PENDENTE` com `requested_by = Ana`, `created_by = criador`, o vínculo, e sem `Booking`;
- aparece em "Minhas solicitações" de Ana e não na do criador;
- auditoria com `solicitante` e `criada_por`;
- conflito com o ensalamento, horário no passado, espaço inativo, data fora do período e descrição vazia continuam recusados;
- falha depois de gravar desfaz tudo (mesmo padrão de `test_failure_after_saving_rolls_everything_back`);
- aprovação da solicitação criada em nome de Ana gera `Booking` com `requested_by = Ana`.

### Regressão do fluxo atual
- `bookings/tests/test_academic_request.py` continua passando;
- novo teste: o fluxo do próprio docente recusa a disciplina forjada também no model.

---

## 4. Arquivos da implementação

| Arquivo | Mudança |
|---|---|
| `accounts/permissions.py` | `BOOKING_CREATE` |
| `accounts/migrations/0014_booking_create_permission.py` | nova |
| `accounts/tests/test_catalog.py` | contagem e concessão |
| `bookings/models.py` | `created_by`, `check_assignment`, `prepare`, `submit` |
| `bookings/migrations/0004_booking_request_created_by.py` | nova |
| `schedule/models.py` | `teacher_users(semester)` |
| `bookings/forms.py` | refatoração do `BookingRequestForm` e `BookingOnBehalfForm` |
| `bookings/views.py` | `BookingOnBehalfCreateView`, `fields`, `request_related`, `can_create` |
| `bookings/urls.py` | `agenda/criar/` |
| `bookings/templatetags/agenda.py` | rota em `request_url` |
| `bookings/templates/bookings/on_behalf_form.html`, `on_behalf_form_modal.html` | novos |
| `bookings/templates/bookings/request_summary_modal.html`, `request_form_modal.html`, `agenda.html`, `partials/request_record.html` | solicitante, criada por e entradas |
| `bookings/tests/base.py`, `bookings/tests/test_on_behalf_request.py`, `bookings/tests/test_academic_request.py` | testes |

## 5. O que não muda
`check_period`, `check_slot`, `find_conflict`, a `ExclusionConstraint` de `Booking`, a máquina de estados, `approve`/`reject`/`suggest`/`accept_suggestion`, as notificações, as permissões existentes e as concessões dos perfis.

## 6. Diferenças na implementação

- A revisão mostra "Solicitante" e "Criada por" só quando a solicitação é criada em nome de outro usuário, para não mudar a revisão do fluxo do próprio docente.
- Aberto pelo botão do cabeçalho, sem faixa da Grade, o modal começa com a data do próximo dia letivo (`next_school_day`), para que a lista de usuários já venha do semestre dela e a escolha comece pelo usuário.
- O aviso do modal aparece quando nenhum usuário tem turma no semestre da data. Como a lista só traz usuários com vínculo, não existe o caso de usuário escolhido sem curso.
- No model, a disciplina que não é a da oferta é recusada no campo `teaching_assignment`, e o curso que não é o da turma, no campo `subject`. No formulário, cada ID fora das opções é recusado no próprio campo.
- `check_assignment` ganhou o parâmetro `on_behalf`, para que as mensagens falem do "usuário" e não de "suas turmas" quando a criação é em nome de outro.
- A atribuição da view se chama `field_names`, e não `fields`, para não se confundir com o atributo das views de model do Django.
- `accounts/tests/test_screens.py` passou de 30 para 31 permissões atribuíveis na tela de perfil.
- Entrada pela Grade, por decisão do autor: a faixa abre direto o modal de criar para outro usuário para o superadmin e para quem tem `AGENDA.CRIAR` sem `AGENDA.SOLICITAR` (`creates_directly` em `bookings/views.py`). Quem tem as duas abre "Solicitar agendamento", com um botão só com ícone no rodapé, junto do "Fechar", com a dica "Criar para outro usuário". O botão "Criar solicitação para outro usuário" do cabeçalho da Agenda foi retirado.
