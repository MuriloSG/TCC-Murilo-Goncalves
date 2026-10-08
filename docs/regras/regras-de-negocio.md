# Regras de negócio

Regras confirmadas no código e nos testes em 08/10/2026. Cada regra indica onde é aplicada. As permissões estão em [permissoes.md](permissoes.md). O que não está implementado fica no fim.

Convenção geral: as regras ficam nas operações dos models e managers, que lançam `ValidationError` ao recusar e não gravam nada nesse caso. As telas só exibem a recusa.

## Usuários e acesso

| Regra | Onde |
|---|---|
| O login é pelo e-mail. O e-mail é único sem diferenciar a caixa e é gravado em minúsculas | `User`, `UserManager.normalize_email`, `user_email_unique_ci` |
| Usuário cadastrado pela tela ou por importação precisa de e-mail `@ifnmg.edu.br`. A edição e o `create_superadmin` não exigem o domínio | `validate_institutional_email`, `UserCreateForm.clean_email`, `UserImport.create` |
| O usuário nasce sem senha utilizável e recebe o link para defini-la. Ninguém define a senha de outra pessoa | `UserManager.register` |
| Cada usuário tem exatamente um perfil | `UserRole`, restrição `user_role_one_per_user` |
| O nome de usuário (`username`) é opcional, gravado como informado (espaços internos reduzidos) e único sem diferenciar a caixa. Não é credencial | `User.clean`, `normalize_username`, `user_username_unique_ci` |
| Usuário inativo não entra (resposta igual à de senha errada), não redefine senha por link antigo e não tem permissão nenhuma | `AccountAdapter.authenticate`, `PasswordResetTokenGenerator`, `User.has_perm` |
| Só um superadmin ativo altera o e-mail de um superadmin | `User.update_details`, `SuperadminOnlyOperation` |
| **Continuidade administrativa:** nenhuma operação pode deixar o sistema sem usuário ativo que seja superadmin ou cujo perfil conceda todas as permissões `USUARIO.VISUALIZAR`, `CRIAR`, `EDITAR`, `ALTERAR_PERFIL` e `ALTERAR_SITUACAO`. Vale para desativar, trocar perfil, retirar superadmin e retirar permissões de perfil | `administrative_continuity`, `ensure_administrative_continuity`, `Role.set_permissions` |
| Na importação de usuários, a continuidade é conferida uma vez, no fim, e não entre linhas | `deferred_administrative_continuity`, `UserImport.check_file` |
| A troca de perfil notifica o usuário, mesmo inativo | `User.change_role` |
| Não há exclusão de usuário pela interface | |

### Vínculo entre usuário e docente

| Regra | Onde |
|---|---|
| Um usuário corresponde a um docente do ensalamento quando `Teacher.name` é igual a `User.username`, sem diferenciar a caixa. Não há chave estrangeira | `teacher_of`, `manages`, `teacher_users` |
| Sem `username`, ou com usuário inativo, não há correspondência | `teacher_of` |

## Perfis

| Regra | Onde |
|---|---|
| Código em maiúsculas sem acento, palavras separadas por `_` (`^[A-Z]+(_[A-Z]+)*$`), único e imutável. Nome único sem diferenciar a caixa | `Role`, `role_code_format`, `role_name_unique_ci` |
| Perfis do sistema (`ADMINISTRADOR`, `DOCENTE`) não podem ser excluídos | `Role.delete_role`, `SystemRoleProtected` |
| Perfil com usuários vinculados não pode ser excluído | `RoleInUse` |
| As permissões `PERFIL.*` são reservadas ao superadmin: não podem ser concedidas a perfil e, se estiverem num perfil, não valem | `grantable_permissions`, `User.effective_permissions` |
| Perfil novo nasce sem permissões até que o superadmin as escolha | `RoleManager.create_role` |

## Importações (todas)

Regras do ciclo de vida em [motor de importação](../arquitetura/motor-de-importacao.md). Resumo:

- Arquivo recusado na leitura não cria importação.
- A prévia executa as operações reais e desfaz. A confirmação reexecuta e só aplica se o plano for idêntico; senão, mostra o novo plano.
- Só `VALIDADA` é confirmada. `PENDENTE` exige decisão. Com operação pendente, toda ação é recusada na hora.
- Só `COM_ERROS`, `DESCARTADA` e `FALHOU` podem ser excluídas.
- A execução usa as permissões de quem pediu. Falta de permissão para o que a linha faz vira erro da linha.

## Ensalamento

### Semestre e período

| Regra | Onde |
|---|---|
| Código `AAAA/1` ou `AAAA/2` | `SEMESTER_CODE_PATTERN` |
| Período: as duas datas ou nenhuma; início até o fim; no máximo 366 dias | `Semester.clean`, `semester_period_valid` |
| O período só é definido no envio da importação. Semestre novo ou sem período exige as duas datas; em branco, mantém o atual | `SemesterManager.check_period`, `SpaceAllocationImport.apply_period` |
| Semestre do dia: janeiro a junho é `/1`, julho a dezembro é `/2` | `timetable.current_semester_code` |

### Importação da planilha

| Regra | Onde |
|---|---|
| Nada é excluído. Alocação que saiu da planilha continua | `AllocationManager.apply` |
| A identidade da alocação é semestre, turma, dia, faixa e disciplina (mais o início da vigência). Duas alocações podem ter o mesmo espaço, dia e faixa: é aula compartilhada, não conflito | `allocation_unique` |
| Alocação existente só tem espaço e docentes atualizados. Alocação alterada no sistema (com vigência) não é tocada pela planilha | `Allocation.update_details`, `AllocationManager.apply` |
| Reimportação idempotente: cada item é procurado pela identidade e o registro existente é reaproveitado (aula pela identidade acima; curso, disciplina e docente pelo nome sem diferenciar maiúsculas; turma por curso e rótulo; faixa por semestre, início e fim; espaço por qualquer nome dele). Reimportar a mesma planilha não cria nem altera nada, e as chaves continuam as mesmas. Agendamentos aprovados não são alterados nem cancelados | `AllocationManager.apply`, `NamedManager.resolve`, `IdempotentReimportTests` |
| Curso existente com a mesma grafia é reaproveitado com a etapa cadastrada, mesmo quando a aba indica outra; a linha recebe o aviso `curso_etapa_graduacao_mantida` ou `curso_etapa_ensino_medio_mantida` e é processada | `execute_activity`, `COURSE_STAGE_KEPT`, `RegisteredCourseTests` |
| A mesma alocação descrita em mais de uma célula é erro em todas as células | `repeated_activities` |
| Docente fora da lista de `Validação de Dados` é erro da linha | `schedule/activities.py` |
| A importação não detecta conflito de espaço nem de docente | `Allocation` (docstring) |
| Usuário da aba `usuários - sistema` só é cadastrado se o e-mail não existir; existente nunca é alterado. E-mail ou nome de usuário repetido na aba é erro em todas as linhas | `SpaceAllocationImport.execute_user`, `repeated_users` |
| Cada faixa da planilha é uma alocação; faixas seguidas não são unidas | `schedule/sheets.py`, `AllocationManager.apply` |

### Aulas e ocorrências

| Regra | Onde |
|---|---|
| A alocação ocorre numa data quando o dia da semana bate, a data está no período do semestre, dentro da vigência (`valid_from`, `valid_until`) e sem exceção nessa data | `Allocation.occurs_on`, `AllocationManager.active_on` |
| Sem período no semestre, nenhuma data é ocorrência: a Grade mostra a semana típica | `Semester.contains` |
| Cancelar ocorrência: só para docente da aula ou quem tem `ENSALAMENTO.CANCELAR_OCORRENCIA`; a data precisa ser ocorrência; não cancela duas vezes. A regra semanal não muda | `AllocationExceptionManager.cancel` |
| Alterar, cadastrar e encerrar recorrência: data de hoje em diante, dentro do período do semestre | `check_start` |
| Alterar recorrência: a data de corte precisa ser ocorrência da aula e posterior ao início da vigência. É preciso mudar ao menos um dado | `check_cut`, `plan_recurrence` |
| A versão nova não pode repetir turma, disciplina, dia e faixa de outra alocação vigente | `check_duplicates` |
| A versão nova não pode ocupar o espaço em nenhuma ocorrência em que haja outra aula (que não seja a mesma disciplina com os mesmos docentes) ou agendamento aprovado | `check_conflicts` |
| Uma ocorrência cancelada do corte em diante que não seja data da nova recorrência recusa a alteração, para não perder o cancelamento | `RecurrencePlan.load_exceptions` |
| Espaço desativado só é aceito se já era o da aula | `plan_recurrence`, `plan_creation` |
| As faixas precisam existir no semestre e ser seguidas (cada uma começa quando a anterior termina) | `consecutive_slots` |
| Cadastrar aula: de segunda a sexta; a última aula, se informada, não antes da primeira e dentro do período | `plan_creation` |
| Encerrar: grava o fim da vigência na véspera; a data precisa ser ocorrência; nada é excluído | `plan_ending`, `EndingPlan.execute` |
| Na Grade, turmas na mesma faixa com a mesma disciplina e os mesmos docentes são "turmas juntas"; o resto é choque, só sinalizado | `timetable.Cell.kind` |

## Espaços

| Regra | Onde |
|---|---|
| Cada grafia (nome atual ou outro nome) identifica um espaço só, sem diferenciar a caixa | `SpaceName`, `space_alias_unique_ci`, `refuse_taken` |
| Ao renomear, o nome anterior vira outro nome | `Space.update_details` |
| Origem (`MANUAL` ou `PLANILHA`) e importação de origem não mudam | `Space` |
| Desativar não mexe nas alocações | `Space.change_status` |
| Excluir só sem aulas no ensalamento e sem solicitações de agendamento | `Space.delete_space`, `SpaceInUse`, `SpaceWithBookings` |
| Espaço inativo não recebe solicitação, alternativa, aula nova nem alteração de aula para ele | `check_slot`, `plan_creation`, `plan_recurrence` |
| Na importação, um nome que precisa de decisão bloqueia a confirmação até ser decidido. A decisão exige a permissão de espaço do efeito (`ESPACO.CRIAR`, `EDITAR` ou `ALTERAR_SITUACAO`) e só é aplicada na confirmação | `schedule/spaces.py`, `SpaceDecisionManager` |

## Disciplinas, turmas e vínculos

| Regra | Onde |
|---|---|
| Disciplina única pelo nome em todo o sistema; turma única pelo rótulo dentro do curso; sem diferenciar a caixa | `subject_name_unique_ci`, `class_group_label_unique_ci` |
| Curso único pelo nome, sem diferenciar a caixa; nome e etapa obrigatórios | `course_name_unique_ci`, `NamedRecord.clean` |
| Curso com alguma turma com oferta ou aula não tem nome nem etapa alterados; curso com turmas não é excluído | `Course.update_details`, `Course.delete_course`, `CourseInUse` |
| O curso da turma não muda | `ClassGroup.update_details` |
| Disciplina ou turma com oferta ou aula não pode ser renomeada nem excluída | `AcademicRecordInUse` |
| O escopo visível é o do docente correspondente ao usuário; só o superadmin vê todos. Perfil `ADMINISTRADOR` sem docente correspondente tem escopo vazio | `teacher_scope`, `SubjectQuerySet.visible_to`, `ClassGroupQuerySet.visible_to`; testes em `schedule/tests/test_academic_views.py` |
| A oferta e os vínculos nunca são excluídos automaticamente. Vínculo atual é o do docente presente numa alocação atual (sem `valid_until`) da oferta | `ClassOffering`, `sync_offerings` |

## Agenda

| Regra | Onde |
|---|---|
| Só quem corresponde a um docente do ensalamento solicita, e só para turmas de vínculos atuais dele no semestre. A disciplina e o curso informados precisam ser os do vínculo | `check_assignment` |
| Quem tem `AGENDA.CRIAR` cria em nome de outro usuário ativo, que também precisa ser docente com vínculo atual | `BookingRequestManager.prepare`, `teacher_users` |
| O semestre precisa ter período, e a data, estar dentro dele | `bookings.models.check_period` |
| Só de segunda a sexta: sábado e domingo são recusados na solicitação (própria ou em nome de outro) e na alternativa sugerida. O calendário do campo de data desabilita esses dias (`data-weekdays-only`), mas a regra vale no servidor sem JavaScript. A aprovação e o aceite da alternativa não conferem o dia, para não travar solicitações anteriores à regra | `bookings.models.check_weekday` |
| Descrição obrigatória (até 500 caracteres). Quantidade de alunos obrigatória, de 1 a 999 | `BookingRequest` |
| Fim depois do início; início no futuro; espaço ativo | `check_slot` |
| Conflito: intervalo semiaberto `[início, fim)`. Há conflito com aula que ocorre na data (fora as canceladas) ou com agendamento aprovado. `14:00–15:00` não conflita com `15:00–16:00` | `bookings.occupancy.find_conflict` |
| A solicitação não reserva o horário. A disponibilidade é conferida de novo na aprovação e no aceite da alternativa, com o espaço travado | `approve`, `accept_suggestion` |
| O banco impede dois agendamentos sobrepostos no mesmo espaço | `ExclusionConstraint` `booking_no_overlap` (extensão `btree_gist`) |
| Rejeitar exige motivo | `reject` |
| A alternativa precisa mudar espaço, data ou horário e estar disponível no momento | `suggest` |
| Só quem solicitou aceita ou recusa a alternativa | `check_owner` |
| Os dados originais da solicitação nunca mudam; a alternativa fica em campos próprios | `BookingRequest` |
| Cancelar: só agendamento aprovado, até 1 hora antes do início, por quem solicitou ou por quem tem `AGENDA.ANALISAR`. Exclui o `Booking` e mantém o histórico na solicitação e na auditoria | `BookingRequest.cancel` |
| Detalhe de solicitação de outro usuário responde 404 | `MyBookingRequestDetailView` |

## Calendário público

| Regra | Onde |
|---|---|
| Só `/` e `/horario-original/` abrem sem login, além do fluxo de autenticação | `accounts/tests/test_route_protection.py` (`PUBLIC_ROUTES`) |
| Exige filtro por sala, docente ou curso. Intervalo de até 31 dias | `schedule/public.py` |
| Não mostra descrição de agendamento, e-mail nem IDs | `PublicEntry`, `PublicBooking`, templates `schedule/public/` |
| O horário original não mostra versões alteradas, cancelamentos nem agendamentos | `original_timetable` |
| Toda gravação nos dados das telas públicas invalida o cache depois do commit | `schedule/public_cache.py` |

## Notificações

| Regra | Onde |
|---|---|
| Uma notificação por destinatário, com o texto copiado. Criada na transação da operação: rollback não notifica | `notices/events.py` |
| Publicação manual só com os tipos `INFORMACAO`, `SUCESSO`, `AVISO`, só para usuários ativos | `NotificationManager`, `resolve_recipients` |
| Notificação de outro usuário não abre (404). Marcar como lida é POST | `notices/views.py` |

## Auditoria

| Regra | Onde |
|---|---|
| Registro só de inclusão; alteração e exclusão são recusadas | `AuditLog.save`, `AuditLog.delete` |
| Gravado na transação da operação | `AuditLog.objects.record` |
| Senhas, tokens e chaves nunca são gravados | `sanitize`, `SmtpSettings.audit_values` |
| Ação e módulo só do catálogo | `audit/catalog.py` |

## E-mails

| Regra | Onde |
|---|---|
| Sem servidor SMTP configurado, nenhum e-mail sai; os do outbox ficam retidos sem gastar tentativas | `outbox/worker.py`, `AccountAdapter.send_mail` |
| Com usuário SMTP, a segurança não pode ser "Nenhuma" | `SmtpSettings.validate` |
| O link de definição de senha não é enviado a usuário excluído, inativo ou que já definiu a senha | `accounts/emails.py` |

## Não implementado ou não confirmado

| Item | Situação |
|---|---|
| Página com todas as notificações do usuário | Não implementada (tarefa 6.2 de `notificar-usuarios`). Só o sino, com as 10 mais recentes |
| Recorrência de agendamento | Não existe. O agendamento é numa data só |
| Capacidade do espaço e conferência da quantidade de alunos | Não existe. A quantidade é só informativa |
| Rate limit das rotas públicas | Fora da aplicação; o proxy de produção não está no repositório |
| Notificação por e-mail | Não existe |
