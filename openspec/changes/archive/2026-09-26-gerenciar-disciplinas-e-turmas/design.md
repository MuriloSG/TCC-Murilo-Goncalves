## Context

`Subject` é um `NamedRecord`: só `name`, gravado como informado, único sem diferenciar a caixa (`subject_name_unique_ci`) e global a todos os cursos (D12 da Change importar-ensalamento-da-planilha). Não há código, CI nem origem. `ClassGroup` tem `course` (FK `PROTECT`) e `label`, único por curso e rótulo sem caixa (`class_group_label_unique_ci`), sem semestre e sem origem. A importação encontra ou cria os dois pelo nome (`Subject.objects.resolve`, `Course.objects.resolve` e `ClassGroup.objects.resolve`, em `SpaceAllocationImport.execute_activity`).

Referências a eles, todas `PROTECT`: `Allocation.subject` e `Allocation.class_group`; `ClassOffering.subject` e `ClassOffering.class_group`; `TeachingAssignment.offering`; e `BookingRequest.teaching_assignment`. O calendário público e a Grade leem pelas alocações.

Não existe vínculo gravado entre `User` e curso, disciplina, turma ou docente. O único mecanismo de pertencimento é `teacher_of(user)`: o docente cujo nome é igual ao `username`, sem diferenciar a caixa, regra usada pela Agenda e por `manages` (D7 da Change importar-ensalamento-da-planilha). A partir do docente, `TeachingAssignment → ClassOffering` chega às disciplinas e às turmas.

A referência de CRUD é o cadastro de espaços (Change `manipulacao-dos-espacos`): `SpaceListView`, `OperationFormView`, `ConfirmedActionView`, modais pelo htmx, `paginate`, busca no `QuerySet`, exclusão recusada com `SpaceInUse` e auditoria com `AuditLog.objects.record` e `record_changes`.

## Goals / Non-Goals

**Goals:** CRUD de disciplinas e de turmas, com permissões por módulo, escopo pelo docente do usuário, superadmin global, proteção no backend, integridade preservada e importação intacta.

**Non-Goals:** código ou CI de disciplina, origem dos registros, outros nomes, vínculo gravado entre usuário e docente, cadastro de curso ou de semestre, mudança na importação.

## Decisions

### D1. Escopo pelo docente do usuário
"Registro do usuário" é a disciplina ou a turma que aparece numa oferta em que o docente do usuário (`teacher_of(user)`) tem um `TeachingAssignment`, atual ou histórico. O histórico entra porque o vínculo é um fato acadêmico do usuário (D3 da Change relacionar-professor-disciplina-turma) e porque o vínculo registrado no cadastro manual nasce como histórico (D6). Usuário sem docente correspondente tem escopo vazio. Nenhuma relação nova é criada.

A regra fica numa única função do model, `SubjectQuerySet.visible_to(user)` e `ClassGroupQuerySet.visible_to(user)`, que filtram `offerings__assignments__teacher=teacher` com `distinct()`. A filtragem acontece no banco, nunca no template.

### D2. Superadmin
`visible_to` devolve todos os registros quando `user.is_superadmin` é verdadeiro. É a mesma exceção de `User.has_perm` e fica no model, como `manages`: views e templates nunca consultam `is_superadmin` (seção 4 das convenções). O superadmin pode excluir qualquer registro que a integridade permitir (D8).

### D3. Permissões
`DISCIPLINA.VISUALIZAR`, `DISCIPLINA.CRIAR`, `DISCIPLINA.EDITAR`, `DISCIPLINA.EXCLUIR`, `TURMA.VISUALIZAR`, `TURMA.CRIAR`, `TURMA.EDITAR` e `TURMA.EXCLUIR`, constantes em `accounts/permissions.py` (`SUBJECT_*`, `CLASS_GROUP_*`), rótulos "Disciplinas" e "Turmas" em `RESOURCE_LABELS`, e as descrições na migration `accounts/0013_academic_permissions`, que as concede ao `ADMINISTRADOR` sem mexer nas demais (padrão da `0009_space_permissions`). Não são reservadas ao superadmin. Cada view declara `permission_required`; o `PermissionMiddleware` responde 403.

### D4. Permissão e escopo nas views
A permissão é conferida antes da view (403). O objeto alvo é carregado no `setup()` com `get_object_or_404(Model.objects.visible_to(request.user), pk=pk)`: fora do escopo responde 404, igual a um ID inexistente, para não revelar a existência do registro. Vale para detalhe, edição e exclusão, em GET e em POST. Esconder botões com `perms` é só apresentação.

### D5. Listagem
Rotas: `disciplinas/`, `disciplinas/nova/`, `disciplinas/<pk>/`, `disciplinas/<pk>/editar/`, `disciplinas/<pk>/excluir/`; `turmas/`, `turmas/nova/`, `turmas/<pk>/`, `turmas/<pk>/editar/`, `turmas/<pk>/excluir/`, todas com `login_required` no `urls.py`.

- Disciplinas: busca pelo nome; colunas nome, número de ofertas e de aulas; ordem pelo nome.
- Turmas: busca pelo rótulo ou pelo curso e filtro de curso; colunas rótulo, curso, etapa, número de ofertas e de aulas; ordem do model (curso, rótulo).
- `get_queryset` parte de `visible_to(user)`, com `select_related` e `annotate(Count(..., distinct=True))`, e é paginado com `ui.pagination.paginate`. O formulário de filtros troca só a tabela pelo htmx, como na lista de espaços. O total exibido é o do escopo.
- Estados vazios: "Nenhuma disciplina cadastrada." e "Nenhuma turma cadastrada."; com filtro, "Nenhuma disciplina encontrada." e "Nenhuma turma encontrada.".
- Ações da linha pelo `perms`: detalhes, editar, excluir (só quando excluível) e "Ver auditoria" com `AUDITORIA.VISUALIZAR`. Tabela responsiva com o mesmo componente da lista de espaços.

### D6. Detalhe
Mostra os dados e as ofertas por semestre: na disciplina, as turmas e os docentes; na turma, as disciplinas e os docentes, com "histórico" só no vínculo que não é atual. Uma consulta com `select_related('semester', 'subject', 'class_group__course')` e `prefetch_related('assignments__teacher')`. As ofertas exibidas são todas as do registro, porque o registro já passou pelo escopo.

### D7. Cadastro sem vínculo acadêmico
- Disciplina: `name`.
- Turma: `course` (cursos existentes) e `label`.

`Subject.objects.register(name)` e `ClassGroup.objects.register(course, label)` validam com `full_clean` (normalização e mensagens de unicidade existentes), gravam e registram a auditoria numa transação. O cadastro **não** cria `ClassOffering` nem `TeachingAssignment`: a oferta e o docente da oferta são derivados do ensalamento (D5 da Change relacionar-professor-disciplina-turma, "nenhum cadastro manual estabelece vínculo"), e um vínculo criado pela tela seria uma relação acadêmica sem aula. Criar exige só a permissão. O registro criado fica fora do escopo de quem não é superadmin até a importação trazê-lo numa oferta com o docente do usuário.

### D8. Edição e campos imutáveis
- Disciplina: altera o nome. Turma: altera o rótulo. O curso da turma é imutável: no formulário ele é `readonly`, e um curso forjado chega ao model e é recusado com "O curso da turma não pode ser alterado.".
- **Renomeação bloqueada com uso**: com oferta ou aula no ensalamento, a importação identifica o registro pelo nome ou pelo rótulo, e renomear faria a próxima importação criar outro cadastro. `update_details` recusa com `AcademicRecordInUse` ("... tem ofertas ou aulas no ensalamento e não pode ser renomeada, porque a próxima importação criaria outro cadastro com o nome da planilha."). A tela avisa antes do envio, mas a recusa está no model.
- Salvar o mesmo valor não muda nada e não gera auditoria. As operações travam o registro com `select_for_update` e usam `record_changes`.
- Como o escopo de quem não é superadmin só alcança registros com oferta, na prática só o superadmin renomeia. É a consequência aceita das decisões 2 e 3.

### D9. Exclusão
`delete_subject()` e `delete_class_group()` travam o registro e recusam com `AcademicRecordInUse` ("... tem ofertas ou aulas no ensalamento e não pode ser excluída.") quando há `ClassOffering` ou `Allocation`. A solicitação de agendamento só alcança o registro por um `TeachingAssignment`, que exige oferta, então ela já está coberta. Sem uso, o registro é excluído com a auditoria; um `ProtectedError` inesperado vira a mesma recusa. Nenhum `on_delete` muda, sem exclusão lógica e sem exclusão de ofertas ou vínculos. GET mostra a confirmação e POST executa (`ConfirmedActionView`). A ação só aparece na lista para registro sem uso.

### D10. Importação
Sem alteração. `resolve` continua pelo nome, sem diferenciar a caixa, então uma disciplina ou turma cadastrada manualmente é reaproveitada quando a planilha traz o mesmo nome, e a partir daí a oferta e os vínculos nascem pela importação, como para qualquer registro.

### D11. Auditoria
Módulos `DISCIPLINA` ("Disciplinas") e `TURMA` ("Turmas") em `audit/catalog.py`, com a chave do registro: `CRIAR` com os valores posteriores (`name`, ou `curso` e `rotulo`); `ALTERAR` só com o que mudou; `EXCLUIR` com os valores anteriores. O responsável e a origem vêm do contexto de auditoria atual. Recusas não geram registro. As views declaram `audit_resource` para o registro de acesso.

### D12. Migrations
Só a migration de dados `accounts/0013_academic_permissions`. Nenhuma de schema: `visible_to` usa as relações existentes e os campos não mudam.

## Risks / Trade-offs

- O escopo depende do `username` igual ao nome do docente. → Mesma limitação da Agenda, já registrada.
- O `ADMINISTRADOR` recebe as permissões, mas sem docente correspondente vê listas vazias. → Aceito pelo autor; nenhuma permissão global nova.
- Quem não é superadmin só alcança registros com oferta, que não podem ser renomeados nem excluídos. → Aceito: a correção desses registros vem da planilha.
- `distinct()` com `annotate` exige `Count(distinct=True)`. → Coberto por teste de contagem.

## Decisões do autor

1. Vínculo manual, se existisse, nasceria com `is_current=False`. Revista a semântica de `ClassOffering` e `TeachingAssignment`, o cadastro não cria vínculo (D7).
2. Sem permissão de escopo global: superadmin global, demais pela permissão e pelo escopo.
3. Renomear registro com uso no ensalamento é bloqueado no backend (D8).
4. A disciplina continua identificada só pelo nome.
