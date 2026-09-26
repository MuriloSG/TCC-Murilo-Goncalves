## Why

Disciplinas (`Subject`) e turmas (`ClassGroup`) hoje só nascem pela importação do ensalamento e não têm tela: não é possível consultar, corrigir, cadastrar ou excluir uma disciplina ou uma turma sem reimportar a planilha. A Agenda já depende delas para a solicitação de agendamento com vínculo acadêmico, e um erro de grafia na planilha fica sem correção. Esta Change cria duas áreas administrativas independentes, com permissões próprias e com uma regra de escopo: ter a permissão não dá acesso a todos os registros, só aos que pertencem ao usuário, e o superadmin tem acesso global.

## What Changes

- **Área de Disciplinas** (`disciplinas/`): listar, ver detalhes, cadastrar, editar e excluir disciplina.
- **Área de Turmas** (`turmas/`): listar, ver detalhes, cadastrar, editar e excluir turma, sempre de um curso existente.
- **Permissões novas**: `DISCIPLINA.VISUALIZAR`, `DISCIPLINA.CRIAR`, `DISCIPLINA.EDITAR`, `DISCIPLINA.EXCLUIR`, `TURMA.VISUALIZAR`, `TURMA.CRIAR`, `TURMA.EDITAR` e `TURMA.EXCLUIR`, concedidas ao perfil `ADMINISTRADOR` pela migration de dados.
- **Escopo reaproveitado**: os registros "do usuário" são as disciplinas e turmas das ofertas em que o docente do usuário (`teacher_of`, `username` igual ao nome do docente) tem vínculo, atual ou histórico. Nenhuma relação nova entre `User` e disciplina, turma ou curso.
- **Superadmin global**: vê, edita e exclui qualquer disciplina ou turma, sem filtro de escopo.
- **Autorização no backend**: a permissão é conferida pelo `PermissionMiddleware` e o escopo pela consulta do model; registro fora do escopo responde 404 em detalhe, edição e exclusão, por GET e por POST.
- **Sem vínculo manual**: o cadastro não cria oferta (`ClassOffering`) nem vínculo de docente (`TeachingAssignment`). A relação acadêmica continua derivada só do ensalamento, como define a Change `relacionar-professor-disciplina-turma`.
- **Renomeação bloqueada com uso**: disciplina ou turma com oferta ou aula no ensalamento não pode ser renomeada, porque a importação a identifica pelo nome e criaria outro cadastro.
- **Exclusão protegida**: recusada com mensagem quando a disciplina ou a turma tem oferta ou aula no ensalamento. As restrições `PROTECT` continuam como estão.
- **Auditoria**: módulos `DISCIPLINA` e `TURMA`, com `CRIAR`, `ALTERAR` e `EXCLUIR`.

### Fora do escopo

- Código ou CI da disciplina: o model não tem esse campo e a planilha identifica a disciplina pelo nome.
- Origem `MANUAL`/`PLANILHA` em disciplina e turma.
- Outros nomes (alias) de disciplina ou turma para a importação reconhecer uma grafia antiga.
- Vínculo gravado entre `User` e `Teacher`, curso, disciplina ou turma.
- Cadastro de curso e de semestre.
- Alteração da importação do ensalamento.

## Capabilities

### New Capabilities

- `gestao-academica`: listagem, detalhe, cadastro, edição e exclusão de disciplinas e turmas, com a regra de escopo e a exceção do superadmin.

### Modified Capabilities

- `controle-acesso`: permissões dos módulos `DISCIPLINA` e `TURMA`.
- `auditoria`: registros dos módulos `DISCIPLINA` e `TURMA`.
- `ensalamento`: o cadastro manual de disciplina e turma não estabelece vínculo acadêmico, e a importação reaproveita o cadastro manual.

## Impact

- `accounts/permissions.py` e a migration de dados `accounts/0013_academic_permissions`.
- `schedule/models.py`: `visible_to`, operações de cadastro, edição e exclusão de `Subject` e `ClassGroup` e a exceção `AcademicRecordInUse`.
- `accounts/views.py`: gancho `get_target_queryset` em `OperationFormView` e `ConfirmedActionView`, para procurar o alvo só no escopo.
- `schedule/forms.py`, `schedule/views.py`, `schedule/urls.py`, templates em `schedule/templates/schedule/` e o menu em `ui`.
- `audit/catalog.py`: módulos e rótulos de campos.
- Testes em `schedule/tests/` e `accounts/tests/`.
- Nenhuma migration de schema.
