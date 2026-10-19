# Testes do app `schedule`

Ensalamento, espaços, cursos, disciplinas e turmas, importação da planilha e calendário público. Comportamento descrito em [ensalamento](../../funcionalidades/ensalamento.md), [espaços](../../funcionalidades/espacos.md), [cursos, disciplinas e turmas](../../funcionalidades/disciplinas-e-turmas.md) e [calendário público](../../funcionalidades/calendario-publico.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `ImportTestCase`, em `test_import.py`: monta planilhas na estrutura da real, com abas de horário em blocos de dia, e o usuário que importa e altera o cadastro de espaços. É a base de `test_import_memory`, `test_import_queries` e `test_space_import`.
- `PublicCalendarTestCase`, em `test_public_calendar.py`: semestre 2026/2 com período, dois cursos e aulas em salas diferentes no mesmo horário. Reaproveitado em `test_public_cache`.
- Os testes de recorrência fixam o relógio com `mock.patch` em `django.utils.timezone`.

## Entidades do ensalamento

### `test_models.py`

| Classe | O que garante |
|---|---|
| `SemesterTests` | Código criado uma vez, no formato `AAAA/N` |
| `NamedRecordTests` | Nomes normalizados nas bordas e nos espaços repetidos; equivalente não duplica; acentos distinguem; prefixo nunca casa; vazio e repetido recusados no model e no banco |
| `ClassGroupTests` | O mesmo rótulo em dois cursos dá duas turmas; equivalente no mesmo curso não duplica; a etapa vem do curso |
| `TimeSlotTests` | Faixa única por semestre; início antes do fim, também no banco |
| `AllocationTests` | Criar devolve as mudanças e a origem importada; aplicar duas vezes não muda; troca de espaço ou de docentes é atualização, sem importar a ordem; alocação sem espaço ou sem docentes |
| `SharedSpaceTests` | Duas turmas compartilham espaço, dia e faixa; mesma turma, faixa e disciplina recusada pelo banco |
| `SemesterIsolationTests` | Faixa de outro semestre recusada |
| `SemesterPeriodTests` | Período definido sem auditoria própria; o mesmo não é mudança; recusas não alteram; `check_period` exige as datas sem período, aceita em branco com período e recusa uma só data ou período inválido; `contains` só no período |
| `CourseTests` | Cadastro normalizado e auditado; recusa nome repetido ou vazio e etapa desconhecida; curso em uso não é editado e com turma não é excluído |

### `test_class_offering.py`

| Classe | O que garante |
|---|---|
| `OfferingTests` | A mesma disciplina em vários semestres; vários docentes ou nenhum na oferta; registro idempotente; docente substituído fica como histórico e pode voltar; versão encerrada não torna o docente atual |
| `AvailableTests` | Combinações atuais docente, disciplina e turma em qualquer direção, só com vínculos atuais do semestre, numa consulta |

### `test_occupancy.py`

`OccupancyTests`: ocorrências de um espaço calculadas das alocações e nunca gravadas. Aula semanal na semana e no mês, nada fora do período ou sem período, alocação sem espaço não ocupa, intervalo que cruza dois semestres, consultas que não crescem, outra fonte somada, intervalo vazio e espaço ausente.

### `test_timetable.py`

| Classe | O que garante |
|---|---|
| `CurrentSemesterTests` | Cada metade do ano é um semestre |
| `SpaceWeekTests` | Semestres importados do mais novo; espaços do semestre pelo nome, inclusive ativos sem aula; linhas com todas as faixas; faixas seguidas viram um bloco sem cruzar o intervalo; entrada com disciplina, turma, docentes e etapa; contagens; hoje marcado; consultas fixas |
| `DatedWeekTests` | Semana padrão dentro do período, primeira ou última fora dele; dias com data; ocorrências em bloco; horários livres contados; dias fora do período; vizinhas dentro do período |
| `CellKindTests` | Uma turma é simples; mesma disciplina e docentes é turma conjunta; diferente é choque |
| `DatedMonthTests` | Uma coluna por dia útil; ocorrências em cada segunda; as mesmas células da semana; início das semanas e hoje; limites do primeiro e do último mês |

## Mudanças no ensalamento

### `test_recurrence_create.py`

| Classe | O que garante |
|---|---|
| `CreateModelTests` | Uma alocação por faixa do bloco; fim de vigência mantido; duração sem faixas seguintes, datas inválidas e espaço inativo recusados com o motivo; sem espaço; grava a oferta e a auditoria, com as entradas do bloco ligadas entre si |
| `CreateConflictTests` | Espaço tomado, agendamento aprovado e mesma disciplina da turma na faixa recusados; turma conjunta e conflito fora da vigência aceitos |
| `CreatePermissionTests` | O model recusa sem a permissão; o superadmin cria |
| `CreateScreenTests` | Semestre desconhecido, 404; formulário preenchido pela célula; primeiro POST mostra o resumo sem gravar; confirmação grava e volta à grade; recusa mantém o formulário; ação só com a permissão |
| `CreateReimportTests` | A reimportação mantém a aula criada no sistema |

### `test_recurrence_change.py`

Alteração da recorrência a partir de uma data.

| Classe | O que garante |
|---|---|
| `VersioningTests` | A original termina na véspera e a nova começa na data, sem ocorrência duplicada; troca de sala, horário (o bloco inteiro), docente e dia; horário sem faixas seguidas recusado; segunda alteração versiona a nova |
| `ValidationTests` | Recusa data passada, fora do semestre, que não é ocorrência, a primeira da recorrência, depois de um fim anterior, nada alterado, alocação ausente, aulas misturadas e espaço inativo |
| `PermissionTests` | Sem a permissão, não altera |
| `ConflictTests` | Choque com outra aula e agendamento aprovado recusados; turma conjunta, a regra antiga e ocorrências canceladas ou encerradas não conflitam |
| `ExceptionTests` | Cancelamentos anteriores ficam e posteriores acompanham; o que não cabe na regra nova recusa; a nova versão pode ser cancelada |
| `TransactionTests` | Falha depois de encerrar a regra desfaz tudo |
| `AuditTests` | Cada alocação é auditada com o corte e a nova; recusa não; a tela grava o usuário |
| `ViewTests` | O formulário explica a mudança; primeiro POST mostra o resumo; confirmação volta à grade ou abre a sala nova pelo htmx; recusas no formulário e conflito no resumo; parâmetros manipulados, 404 |
| `GridTests` | Ação só com a permissão e em datas futuras; o versionamento não acrescenta consultas |
| `PublicCalendarTests` | Nada administrativo exposto |
| `AgendaTests` | A disponibilidade segue a regra nova |
| `ReimportTests` | A reimportação não reescreve as versões nem recria a regra antiga |
| `AcademicLinkTests` | Docentes da oferta preservados; docente trocado vira histórico |
| `DurationTests` | Aula maior ganha alocação na faixa extra, menor encerra a que sobra; só a duração já é mudança; faixas além do semestre recusadas |

### `test_recurrence_end.py`

| Classe | O que garante |
|---|---|
| `EndingTests` | Cada alocação termina na véspera e o passado fica; aula ainda não iniciada; datas inválidas recusadas com o motivo; cancelamentos mantidos e não contados; auditoria só no sucesso; a reimportação não recria a aula |
| `EndingPermissionTests` | O docente da aula não encerra; o superadmin encerra |
| `EndingScreenTests` | GET confirma sem alterar; POST encerra e volta à grade; alocação ou data desconhecidas, 404; ação só com a permissão e fora de semanas passadas |

### `test_occurrence_cancel.py`

| Classe | O que garante |
|---|---|
| `ModelTests` | Cancela cada alocação do bloco na data sem tocar a regra semanal; recusa data que não é ocorrência, repetição e alocação ausente; recusa de uma não cancela nenhuma |
| `AuthorizationTests` | O docente da aula cancela sem a permissão; outro docente, inativo e quem não tem vínculo nem permissão não; a permissão e o superadmin cancelam qualquer aula; aula sem docente só com a permissão |
| `CancelViewTests` | Confirmação nomeia a data; docente cancela por POST; htmx mantém a semana; outro docente e parâmetros manipulados, 404; segundo cancelamento mostra a recusa |
| `GridTests` | Ocorrência cancelada sai da semana; a ação do bloco leva as duas alocações; só para quem gere a aula; sem consulta por exceção |
| `PublicCalendarTests` | A exceção não é exposta |
| `AgendaTests` | A ocorrência cancelada libera o espaço, só nela e só na faixa cancelada |
| `ExceptionListTests` | Lista de exceções completa com a permissão e só das próprias aulas para o docente |
| `AuditTests` | Cada alocação cancelada auditada com o usuário; recusa não |
| `ReimportTests` | A exceção sobrevive à reimportação |
| `AgendaScreenTests` | O docente cancela pela Agenda só as próprias aulas, sem acesso ao Ensalamento |

## Importação da planilha

### `test_spreadsheet.py`

Leitura de `sources/planilha_example.xlsx`, com números que acusam mudança diante do arquivo real.

| Classe | O que garante |
|---|---|
| `StructureTests` | Retrato do arquivo real e total de linhas; nomes de espaço sem os parênteses da lista; catálogo antes das atividades; abas calculadas não lidas; os cinco dias de cada aba; coluna sem cabeçalho mantém a turma do bloco; título do curso |
| `ActivityReadingTests` | Atividade completa, com parênteses na disciplina, sem espaço, vários docentes (barra ou "e"), quebra de linha, duas por célula; espaço fora do catálogo é citado só nas células; grafia diferente, prefixo e acentos não casam e a caixa é ignorada; parênteses vazios, sem disciplina e sem parênteses são problema, sem perder as válidas da célula |
| `RealFileProblemTests` | Quantas atividades o arquivo real recusa |
| `UserSheetReadingTests` | Aba opcional `usuários - sistema`: ausente não dá usuários; uma entrada por linha com valores crus; título e cabeçalho sem caixa e acentos; coluna faltando ou repetida recusa o arquivo; vem antes do catálogo |

### `test_import.py`

| Classe | O que garante |
|---|---|
| `PreviewTests` | A prévia planeja tudo sem alterar; linhas de catálogo e de atividade guardam os valores da planilha; sem aba de catálogo ou catálogo vazio recusado; semestre obrigatório e no formato; docente desconhecido é erro da linha |
| `ConfirmationTests` | Cria semestre e entidades; bloco seguido não é fundido; mantém os detalhes da atividade; aba secundária dá a etapa; espaço e docente sem atividade cadastrados; valor repetido vira um registro; espaço só nas células reconhecido; mensagem com totais |
| `ReimportTests` | Sem mudanças, nada muda; troca de espaço e docentes atualiza; ausente no arquivo novo é preservada; nova atividade entra; alocação manual e outro semestre intocados; aula alterada no sistema é mantida com aviso; atividade repetida é erro |
| `IdempotentReimportTests` | O mesmo arquivo três vezes mantém as linhas; a mesma aula é atualizada; agendamento aprovado intocado |
| `DivergenceTests` | Dados alterados depois da prévia dão plano novo; a confirmação usa o semestre gravado |
| `RegisteredCourseTests` | Curso cadastrado reaproveitado pelo nome, sem caixa e espaços, mas não sem acentos; etapa divergente mantida com aviso |
| `PeriodImportTests` | A primeira importação define e exige o período; prévia, descarte e divergência não o alteram; reimportação com datas novas atualiza e audita, em branco mantém |
| `AuditTests` | Resumo da confirmação e da reimportação; nenhum registro por entidade, exceto espaços; prévia só registra a prévia |
| `RealSpreadsheetTests` | O arquivo real é pré-visualizado com as atividades que o campus precisa corrigir |
| `AcademicLinkTests` | Ofertas e docentes registrados; linha recusada não deixa vínculo; sem duplicar; substituído vira histórico e pode voltar; semestre anterior intocado |
| `UserSheetTests` | Usuários da aba reconhecidos, planejados e criados na confirmação com o perfil e casados com o docente; existente não é duplicado, atualizado nem reativado; erros de e-mail, duplicados, células, nome em uso, permissão e banco bloqueiam a importação inteira; prévia e divergência desfazem os usuários |
| `SuggestedSpreadsheetTests` | Planilha sugerida com a aba de usuários lida por inteiro |

### `test_import_memory.py`

`ImportMemoryTests`: registro criado por linha recusada é criado de novo; grafias que diferem só na caixa usam a mesma disciplina; a oferta vem só das linhas mantidas; a prévia desfaz a etapa final; a trava alcança só as alocações.

### `test_import_queries.py`

`ImportQueryTests`: consultas da primeira prévia, da primeira confirmação e da prévia de reimportação limitadas pelos registros distintos, e não pelas linhas.

### `test_space_import.py`

| Classe | O que garante |
|---|---|
| `ClassificationTests` | Na primeira importação, os espaços listados são propostos; outro nome reconhecido; inativo pede decisão sem reativar; nomes parecidos não são associados; nome só nas células pede decisão; espaço sem aulas não torna nomes ambíguos |
| `DecisionTests` | Associar a espaço existente ou a nome da mesma importação, criar novo e reativar; nome atual de inativo só aceita reativação; retirar a decisão volta a pendência; reconhecimento prevalece; importação final recusa; descarte não toca o cadastro; duas importações criam o espaço uma vez |
| `PermissionTests` | Quem só importa não confirma o que altera o cadastro; decisão sem a permissão recusada; reativação exige a permissão de situação |

### `test_space_panel.py`

| Classe | O que garante |
|---|---|
| `PanelTests` | Quadro "Espaços desta importação": propostas no futuro, pendências de nome parecido e só nas células; quem só importa vê a mensagem sem controles; permissão parcial mostra só as decisões permitidas; com erros, só os nomes; concluída lista os criados; lista de importações com a situação das decisões |
| `AutomaticRefreshTests` | A última decisão atualiza a prévia, as intermediárias só o quadro; retirar volta a pendência; falha mantém a decisão e oferece tentar de novo; decisão durante atualização ou sem permissão recusada; escolher espaço cadastrado no modal |

### `test_similarity.py`

`SimilarNamesTests`: nomes parecidos reais são apontados e os que não são, não; nome igual é reconhecimento; nomes repetidos aparecem uma vez.

### `test_views.py`

Telas da importação e da Grade do Ensalamento.

| Classe | O que garante |
|---|---|
| `AccessTests` | Com a permissão, lista e detalhe abrem |
| `UploadTests` | Envio cria a importação e abre a prévia; sem semestre mostra o erro |
| `ConfirmationScreenTests` | Prévia com linhas e confirmar; confirmação mostra os totais e audita autor e resumo; descarte não toca o domínio; histórico |
| `RowFilterTests` | Filtros com totais, por espaços, atividades e erros, cada um com suas colunas; filtro desconhecido, 404 |
| `GridScreenTests` | O menu abre a grade; semestre atual por padrão, mesmo sem importação; semestre e espaço pela URL, desconhecidos voltam ao padrão |
| `DatedGridScreenTests` | Sem período, semana típica com aviso; semana padrão, navegação e primeira semana parcial; semana inválida volta ao padrão |
| `MonthGridScreenTests` | Mês atual por padrão; navegação; troca entre semana e mês; sem período, sem seletor e com a semana típica |
| `ClashConfirmationTests` | Choque não bloqueia a confirmação |
| `ViewPermissionTests` | Quem só visualiza abre a grade sem as importações; o menu aponta para o permitido |
| `DeletionTests` | Exclusão só com a permissão e não de pendente |
| `UploadPeriodScreenTests` | O modal de envio tem arquivo, semestre e período |

## Espaços

### `test_spaces.py`

| Classe | O que garante |
|---|---|
| `RegisterTests` | Espaço manual ativo com seus nomes e auditado; encontrado por outro nome sem caixa; nome usado como outro nome ou de outro espaço recusado, citando-o; o banco garante um espaço por nome; origem planilha guarda a importação |
| `UpdateTests` | Renomear guarda o anterior; outro nome promovido ou removido; nome de outro espaço recusado; origem, situação e alocações não mudam; sem mudança, sem registro; nomes da importação com metadados |
| `StatusTests` | Desativar e reativar; a mesma situação não muda |
| `DeleteTests` | Sem aulas, exclui com nomes e decisões; com aulas, não |

### `test_space_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Cada rota com sua permissão; POST sem permissão ou sem CSRF não altera; o menu segue a visualização |
| `ListTests` | Nomes, origem e situação em ordem natural; busca por outro nome e filtros; busca vazia oferece limpar; só visualizar não mostra controles; excluir só sem aulas; link de auditoria para quem a vê |
| `OperationTests` | Cadastro com outros nomes; nome em uso é erro do campo; edição guarda o nome anterior; desativar, reativar e excluir pela tela |

## Cursos, disciplinas e turmas

### `test_course_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Rotas recusam sem a permissão; o menu segue a visualização |
| `OperationTests` | Cadastro auditado; edição de curso sem uso; exclusão sem turmas, e com turmas recusada com mensagem |
| `ScreenTests` | Cada rota com sua permissão; busca por nome e filtro por etapa, pelo htmx; excluir só sem turmas; detalhe com as turmas e o uso; recusas como erro do formulário |

### `test_academic_views.py`

| Classe | O que garante |
|---|---|
| `ScopeTests` | O escopo de disciplinas e turmas segue o docente do usuário; sem docente, vazio; superadmin e permissão de alcance veem tudo do tipo, mas sem a de visualizar não abrem nada; inativo perde o alcance |
| `AccessTests` | Cada rota com sua permissão; menu pela visualização |
| `OutOfScopeTests` | Detalhe, edição e exclusão fora do escopo dão 404 sem alterar |
| `ListTests` | O docente lista só as suas; sem docente, estado vazio; busca e filtro por curso; contagens não multiplicadas pelo escopo; htmx responde só a tabela |
| `DetailTests` | Detalhe com ofertas e docentes; vínculo histórico identificado |
| `CreateTests` | Cadastro auditado; duplicado recusado |
| `UpdateTests` | Renomear registro sem uso; em uso na grade ou com oferta recusado; mesmo nome não muda; curso forjado e nome existente recusados |
| `DeleteTests` | Exclusão de registro sem uso auditada; com aulas ou oferta recusada; ação só para os sem uso |
| `ImportRegressionTests` | Cadastro manual não oferece nada à Agenda |

## Calendário público

### `test_public_calendar.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Visitante e autenticado veem o mesmo calendário, só com GET e HEAD, sem auditoria, cookie, CSRF nem layout autenticado, com `noindex` |
| `FutureSourceTests` | Fonte extra de ocupação nunca chega ao calendário público |
| `ExposedDataTests` | Cartão com disciplina, turma, espaço e docente, sem e-mail nem dados administrativos; ids nunca nos filtros |
| `TeacherTests` | Opções só de docentes do semestre; só o nome; nomes ordenados sem consultas novas |
| `FilterTests` | Filtros combinados; valor desconhecido ou longo descartado; nome sem caixa; espaços ativos e inativos com aula; cursos alocados; etapa |
| `GroupFilterTests` | Turma só com curso, das turmas dele; de outro curso ou sem curso descartada |
| `PrincipalFilterTests` | Só a etapa não consulta alocações |
| `SemesterTests` | Semestre atual por padrão; sem alocações; sem período mostra a semana típica |
| `DateTests` | Semana de hoje por padrão; intervalos recusados explicam o motivo sem consultar; até 31 dias; fim de semana não é coluna |
| `GridTests` | Turmas em espaços diferentes não são choque; turmas conjuntas; horário livre só no filtro de espaço; todas as faixas do semestre |
| `EmptyStateTests` | Sem aulas, grade vazia; sem filtro principal ou com datas recusadas, sem grade |
| `QueryTests` | Consultas fixas, sem crescer com as aulas |
| `OriginalTimetableTests` | Horário original: só GET e HEAD, semana típica importada com cancelamentos e versões ignorados, sem agendamentos, mesmos filtros sem datas e links de ida e volta |

### `test_public_cache.py`

Cache das rotas públicas, descrito em [testes transversais](../testes.md#testes-transversais) e na seção 4 das [convenções](../convencoes.md#4-controle-de-acesso).

| Classe | O que garante |
|---|---|
| `KeyTests` | Chave com formato e tamanho fixos, igual para os mesmos parâmetros em qualquer ordem e diferente por parâmetro, recurso ou geração; recurso desconhecido recusado; TTLs |
| `LookupTests` | Falta e acerto; geração lida uma vez por requisição; incrementar torna a entrada anterior inalcançável; geração perdida é recriada sem reaproveitar; valor ilegível é falta; sem Redis, passa direto |
| `UnavailableTests` | Erro de conexão e timeout caem no banco, com pausa de 30 segundos; falha de escrita ou de invalidação não quebra a resposta |
| `CommitTests` | Commit incrementa e rollback não, uma vez por transação, sem perder escrita depois de savepoint desfeito; mudanças de espaço, curso, usuário relevante e docente da alocação incrementam, login e senha não; escritas em massa e `clear_data` invalidam explicitamente |
| `BookingInvalidationTests` | Aprovação, cancelamento, alteração e exclusão de agendamento incrementam depois do commit; recusa não |
| `ImportInvalidationTests` | A prévia não invalida; a confirmação pelo worker invalida uma vez |
| `PublicViewCacheTests` | Cabeçalhos de falta e acerto sem cache do navegador; mesmo conteúdo com e sem cache; grafias compartilham a entrada; página e grade aquecidas sem consultas; troca de dia reconstrói; Redis fora serve do banco; login e senha não usam o cache |
| `BulkWriteScanTests` | Toda escrita em massa nova foi revisada e as invalidações explícitas estão no lugar |
| `JsonSerializerTests` | O Redis guarda JSON, nunca pickle; tipo desconhecido recusado na escrita |
| `TolerantCacheTests` | Com o Redis fora, os limites de tentativa deixam de valer e o login não falha |
