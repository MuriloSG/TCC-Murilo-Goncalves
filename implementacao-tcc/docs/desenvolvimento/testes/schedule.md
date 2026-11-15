# Testes do app `schedule`

Ensalamento, espaços, cursos, disciplinas e turmas, importação da planilha e calendário público. Comportamento descrito em [ensalamento](../../funcionalidades/ensalamento.md), [espaços](../../funcionalidades/espacos.md), [cursos, disciplinas e turmas](../../funcionalidades/disciplinas-e-turmas.md) e [calendário público](../../funcionalidades/calendario-publico.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `ImportTestCase`, em `test_import.py`: monta planilhas na estrutura da real, com abas de horário em blocos de dia, e o usuário que importa e altera o cadastro de espaços. É a base de `test_import_memory`, `test_import_queries` e `test_space_import`.
- `PublicCalendarTestCase`, em `test_public_calendar.py`: semestre 2026/2 com período, dois cursos e aulas em salas diferentes no mesmo horário. Reaproveitado em `test_public_cache`.
- Os testes de recorrência fixam o relógio com `mock.patch` em `django.utils.timezone`.
- As variações de um mesmo caso rodam com `self.case(...)` de `config/testing.py`, um `subTest` dentro de um savepoint desfeito ao final.

## Entidades do ensalamento

### `test_models.py`

| Classe | O que garante |
|---|---|
| `SemesterTests` | Código criado uma vez, no formato `AAAA/N` |
| `NamedRecordTests` | Nomes normalizados nas bordas e nos espaços repetidos; equivalente não duplica; acentos distinguem; prefixo nunca casa; vazio e repetido recusados |
| `ClassGroupTests` | O mesmo rótulo em dois cursos dá duas turmas; equivalente no mesmo curso não duplica; a etapa vem do curso |
| `TimeSlotTests` | Faixa única por semestre; início antes do fim |
| `AllocationTests` | Criar devolve as mudanças e a origem importada, também sem espaço ou sem docentes; aplicar de novo não muda, sem importar a ordem dos docentes; troca de espaço ou de docentes é atualização; duas turmas compartilham espaço, dia e faixa; faixa de outro semestre recusada |
| `SemesterPeriodTests` | Período definido sem auditoria própria; o mesmo não é mudança; recusas não alteram; `contains` só no período; `check_period` exige as datas sem período, aceita em branco com período e recusa uma só data ou período inválido |
| `CourseTests` | Cadastro normalizado e auditado; recusa nome repetido ou vazio e etapa desconhecida; curso em uso não é editado e com turma não é excluído |

### `test_class_offering.py`

| Classe | O que garante |
|---|---|
| `OfferingTests` | A mesma disciplina em vários semestres; vários docentes ou nenhum na oferta; registro idempotente; docente substituído fica como histórico e pode voltar; versão encerrada não torna o docente atual |
| `AvailableTests` | Combinações atuais docente, disciplina e turma em qualquer direção, só com vínculos atuais do semestre |

### `test_occupancy.py`

`OccupancyTests`: ocorrências de um espaço calculadas das alocações e nunca gravadas. Aula semanal na semana e no mês; nada fora do período, sem período, sem espaço ou em intervalo vazio; intervalo que cruza dois semestres; consultas que não crescem; outra fonte somada.

### `test_timetable.py`

| Classe | O que garante |
|---|---|
| `CurrentSemesterTests` | Cada metade do ano é um semestre |
| `SpaceWeekTests` | Semestres importados do mais novo; espaços do semestre pelo nome, inclusive ativos sem aula; linhas com todas as faixas; faixas seguidas viram um bloco sem cruzar o intervalo; entrada com disciplina, turma, docentes e etapa; contagens; hoje marcado |
| `DatedWeekTests` | Semana padrão dentro do período, primeira ou última fora dele; dias com data; ocorrências em bloco; horários livres contados; dias fora do período; vizinhas dentro do período |
| `CellKindTests` | Uma turma é simples; mesma disciplina e docentes é turma conjunta; diferente é choque; turma conjunta na semana com datas |
| `DatedMonthTests` | Uma coluna por dia útil; ocorrências em cada segunda; as mesmas células da semana; início das semanas e hoje; limites do primeiro e do último mês |

## Mudanças no ensalamento

### `test_recurrence_create.py`

| Classe | O que garante |
|---|---|
| `CreateModelTests` | Uma alocação por faixa do bloco; fim de vigência mantido; sem espaço; o superadmin cria sem a permissão no perfil; duração sem faixas seguintes, datas inválidas, espaço inativo e falta da permissão recusados com o motivo; grava a oferta e a auditoria, com as entradas do bloco ligadas entre si |
| `CreateConflictTests` | Espaço tomado, agendamento aprovado e mesma disciplina da turma na faixa recusados; turma conjunta e conflito fora da vigência aceitos |
| `CreateScreenTests` | Semestre desconhecido, 404; formulário preenchido pela célula; primeiro POST mostra o resumo sem gravar; recusa mantém o formulário; confirmação grava e volta à grade; ação só com a permissão |
| `CreateReimportTests` | A reimportação mantém a aula criada no sistema |

### `test_recurrence_change.py`

Alteração da recorrência a partir de uma data.

| Classe | O que garante |
|---|---|
| `VersioningTests` | A original termina na véspera e a nova começa na data com os mesmos dados, sem ocorrência duplicada; troca de sala, horário (o bloco inteiro), docente e dia; segunda alteração versiona a nova |
| `ValidationTests` | Recusa data passada, fora do semestre, que não é ocorrência, a primeira da recorrência, depois de um fim anterior, nada alterado, alocação ausente, aulas misturadas, espaço inativo, horário sem faixas seguidas, faixas além do semestre e falta da permissão, sem gravar, auditar ou mexer nos docentes da oferta |
| `ConflictTests` | Choque com outra aula, agendamento aprovado e a mesma disciplina da turma recusados; turma conjunta, a regra antiga, agendamento em outro horário e ocorrências canceladas ou encerradas não conflitam |
| `ExceptionTests` | Cancelamentos anteriores ficam e posteriores acompanham; o que não cabe na regra nova recusa |
| `TransactionTests` | Falha depois de encerrar a regra desfaz tudo |
| `AuditTests` | Cada alocação é auditada com o corte e a nova |
| `ViewTests` | O formulário explica a mudança; primeiro POST mostra o resumo e o conflito; confirmação grava o usuário e volta à grade ou abre a sala nova pelo htmx, com a duração do formulário; recusa no formulário; parâmetros manipulados, 404 |
| `GridTests` | Ação só com a permissão e em datas futuras |
| `AgendaTests` | A disponibilidade segue a regra nova |
| `ReimportTests` | A reimportação não reescreve as versões nem recria a regra antiga |
| `AcademicLinkTests` | Docentes da oferta preservados; docente trocado vira histórico |
| `DurationTests` | Aula maior ganha alocação na faixa extra, mantendo os cancelamentos, e menor encerra a que sobra; só a duração já é mudança |

### `test_recurrence_end.py`

| Classe | O que garante |
|---|---|
| `EndingTests` | Cada alocação termina na véspera e o passado fica, inclusive na aula ainda não iniciada, com cancelamentos mantidos e a auditoria; datas inválidas e o docente da aula recusados sem auditoria; cancelamentos não contam; a reimportação não recria a aula |
| `EndingScreenTests` | GET confirma sem alterar; alocação ou data desconhecidas, 404; POST encerra e volta à grade; ação só com a permissão e fora de semanas passadas |

### `test_occurrence_cancel.py`

| Classe | O que garante |
|---|---|
| `ModelTests` | Cancela cada alocação do bloco na data sem tocar a regra semanal, com auditoria por alocação; recusa data que não é ocorrência, repetição e alocação ausente; recusa de uma não cancela nenhuma |
| `AuthorizationTests` | O docente da aula cancela sem a permissão; a permissão e o superadmin cancelam qualquer aula; aula sem docente só com a permissão; outro docente, inativo e quem não tem vínculo nem permissão não |
| `CancelViewTests` | Confirmação nomeia a data; docente cancela por POST, com o usuário na auditoria; htmx mantém a semana; segundo cancelamento mostra a recusa; outro docente e parâmetros manipulados, 404 |
| `GridTests` | A ação do bloco leva as duas alocações, só para quem gere a aula; a ocorrência cancelada sai da semana e libera o espaço só nela e na faixa cancelada; a exceção não aparece no calendário público; lista de exceções completa com a permissão e só das próprias aulas para o docente |
| `ReimportTests` | A exceção sobrevive à reimportação |
| `AgendaScreenTests` | O docente cancela pela Agenda só as próprias aulas, sem acesso ao Ensalamento |

## Importação da planilha

### `test_spreadsheet.py`

Leitura de `schedule/tests/fixtures/planilha_example.xlsx`, com números que acusam mudança diante do arquivo real.

| Classe | O que garante |
|---|---|
| `StructureTests` | Retrato do arquivo real, total de linhas e catálogo antes das atividades; abas calculadas não lidas; os cinco dias de cada aba; nomes de espaço sem os parênteses da lista; coluna sem cabeçalho mantém a turma do bloco; título do curso |
| `ActivityReadingTests` | Células reais: atividade completa, com parênteses na disciplina, sem espaço, vários docentes (barra ou "e"), quebra de linha, duas por célula, espaço fora do catálogo citado só nas células; parênteses vazios, sem disciplina e sem parênteses são problema; prefixo e acentos não casam e a caixa é ignorada |
| `RealFileProblemTests` | Quantas atividades o arquivo real recusa |
| `UserSheetReadingTests` | Aba opcional `usuários - sistema`: ausente ou vazia não dá usuários; uma entrada por linha com valores crus; título e cabeçalho sem caixa e acentos; vem antes do catálogo; coluna faltando ou repetida recusa o arquivo |

### `test_import.py`

| Classe | O que garante |
|---|---|
| `PreviewTests` | A prévia planeja tudo sem alterar, com os valores da planilha nas linhas de catálogo e de atividade; sem aba de catálogo, catálogo vazio, sem semestre, semestre fora do formato e primeira importação sem datas recusados no envio; docente desconhecido é erro da linha |
| `ConfirmationTests` | Cria semestre e entidades com os detalhes da atividade; bloco seguido não é fundido; aba secundária dá a etapa; espaço e docente sem atividade cadastrados; valor repetido vira um registro |
| `ReimportTests` | Aula ausente no arquivo novo e espaço fora do catálogo são mantidos; espaço só nas células reconhecido; nova atividade entra; alocação manual e outro semestre intocados; aula alterada no sistema é mantida com aviso; atividade repetida é erro |
| `IdempotentReimportTests` | O mesmo arquivo três vezes mantém as linhas; troca de espaço e docentes atualiza a mesma aula; agendamento aprovado intocado |
| `DivergenceTests` | Dados alterados depois da prévia dão plano novo; a confirmação usa o semestre gravado |
| `RegisteredCourseTests` | Curso cadastrado reaproveitado pelo nome, sem caixa e espaços, mas não sem acentos; etapa divergente mantida com aviso |
| `PeriodImportTests` | A primeira importação define o período só na confirmação; prévia descartada e divergência não o alteram; reimportação com datas novas atualiza e audita, em branco mantém |
| `AuditTests` | Prévia só registra a prévia; resumo da confirmação e da reimportação; nenhum registro por entidade, exceto espaços |
| `RealSpreadsheetTests` | O arquivo real é pré-visualizado com as atividades que o campus precisa corrigir |
| `AcademicLinkTests` | Ofertas e docentes registrados; linha recusada não deixa vínculo; substituído vira histórico e pode voltar |
| `UserSheetTests` | Usuários da aba planejados e criados na confirmação com o perfil e casados com o docente; existente não é duplicado, atualizado nem reativado; erros de e-mail, duplicados, células, nome em uso, permissão e banco; erro de usuário bloqueia a importação inteira; prévia, divergência, erro inesperado e quem confirma sem permissão não deixam usuários |
| `SuggestedSpreadsheetTests` | Planilha sugerida com a aba de usuários lida por inteiro |

### `test_import_memory.py`

`ImportMemoryTests`: registro criado por linha recusada é criado de novo; grafias que diferem só na caixa usam a mesma disciplina; a oferta vem só das linhas mantidas; a trava alcança só as alocações.

### `test_import_queries.py`

`ImportQueryTests`: consultas da primeira prévia, da primeira confirmação e da prévia de reimportação limitadas pelos registros distintos, e não pelas linhas.

### `test_space_import.py`

| Classe | O que garante |
|---|---|
| `ClassificationTests` | Na primeira importação das planilhas reais, os espaços listados são propostos; ativo reconhecido pelo outro nome ou sem aulas; inativo pede decisão sem reativar, e sem aulas continua inativo; nomes parecidos, espaço listado sem aulas e nome só nas células pedem decisão |
| `DecisionTests` | Associar a espaço existente ou a nome da mesma importação e criar novo; reativação só pela decisão própria; retirar a decisão volta a pendência; importação final recusa; descarte e exclusão não tocam o cadastro; reconhecimento prevalece; duas importações criam o espaço uma vez |
| `PermissionTests` | Quem só importa não confirma o que altera o cadastro, mas conclui quando nada muda; reativação exige a permissão de situação; decisão sem a permissão recusada |

### `test_space_panel.py`

| Classe | O que garante |
|---|---|
| `PanelTests` | Quadro "Espaços desta importação": propostas no futuro e criados depois da conclusão; pendências de nome parecido e só nas células; com erros, só os nomes; quem só importa vê a mensagem sem controles e não confirma; permissão parcial mostra só as decisões permitidas; decisão sem a permissão recusada |
| `AutomaticRefreshTests` | A última decisão atualiza a prévia, as intermediárias só o quadro; falha mantém a decisão e oferece tentar de novo; decisão durante atualização recusada; escolher espaço cadastrado no modal |

### `test_similarity.py`

`SimilarNamesTests`: nomes parecidos reais são apontados, e nomes repetidos aparecem uma vez; os que não são parecidos e o nome igual, não.

### `test_views.py`

Telas da importação e da Grade do Ensalamento.

| Classe | O que garante |
|---|---|
| `UploadTests` | Sem semestre mostra o erro; envio cria a importação e abre a prévia, sem grade, com confirmar; histórico |
| `ConfirmationScreenTests` | Confirmação mostra os totais e audita autor e resumo; descarte não toca o domínio; filtros de linhas com totais e colunas próprias; filtro desconhecido, 404 |
| `GridScreenTests` | Semestre atual por padrão, mesmo sem importação; semestre e espaço pela URL, desconhecidos voltam ao padrão; semana com datas, navegação, primeira semana parcial e semana inválida; sem período, semana típica com aviso; mês atual, navegação e troca entre semana e mês |
| `ClashConfirmationTests` | Choque não bloqueia a confirmação |
| `ViewPermissionTests` | Quem só visualiza abre a grade sem as importações |
| `DeletionTests` | Exclusão só com a permissão e auditada; pendente não é excluída |

## Espaços

### `test_spaces.py`

`SpaceTests`: espaço manual ativo com seus nomes e auditado, e da planilha com a importação; encontrado por outro nome sem caixa; nome usado como outro nome ou de outro espaço recusado, citando-o; renomear guarda o anterior, outro nome promovido ou removido; origem, situação e alocações não mudam e sem mudança não há registro; nomes da importação com metadados; desativar e reativar uma vez; sem aulas, exclui com nomes e decisões, com aulas não.

### `test_space_views.py`

`SpaceScreenTests`: cada rota abre com sua permissão; lista com nomes, origem e situação em ordem natural, busca por outro nome, filtros e busca vazia que oferece limpar; controles seguem as permissões e as aulas, com link de auditoria para quem a vê; cadastro com outros nomes, edição que guarda o nome anterior, desativar, reativar e excluir pela tela; nome em uso como erro do campo e exclusão com aulas recusada.

## Cursos, disciplinas e turmas

### `test_course_views.py`

`ScreenTests`: cada rota abre com sua permissão; cadastro, edição e exclusão voltam à lista com a mensagem, e a exclusão com turmas é recusada; busca por nome e filtro por etapa; detalhe com as turmas e excluir só sem turmas; recusas como erro do formulário.

### `test_academic_views.py`

| Classe | O que garante |
|---|---|
| `ScopeTests` | O escopo de disciplinas e turmas segue o docente do usuário; sem docente, vazio; superadmin e permissão de alcance veem tudo do tipo, também pelas rotas; inativo perde o alcance; cada rota abre com sua permissão; detalhe, edição e exclusão fora do escopo dão 404 sem alterar |
| `ScreenTests` | O docente lista só as suas, com contagens não multiplicadas pelo escopo; sem docente, estado vazio; busca e filtro por curso; detalhe com ofertas, docentes e vínculo histórico; cadastro auditado e duplicado recusado; renomear só registro sem uso, sem mudança com o mesmo nome; em uso, com oferta, curso trocado e nome existente recusados; excluir só os sem uso, com auditoria |
| `ImportRegressionTests` | Cadastro manual não oferece nada à Agenda |

## Calendário público

### `test_public_calendar.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Visitante e autenticado veem o mesmo calendário, sem auditoria, cookie, CSRF nem layout autenticado, com `noindex` |
| `FutureSourceTests` | Fonte extra de ocupação nunca chega ao calendário público |
| `ExposedDataTests` | Cartão com disciplina, turma, espaço e docente, sem e-mail nem dados administrativos, também para docente com usuário inativo; aula sem sala; ids nunca nos filtros |
| `FilterTests` | Opções só de docentes do semestre, espaços ativos e inativos com aula, cursos alocados e turmas do curso; filtros combinados, turma e etapa; valor desconhecido, longo ou de outro curso descartado; nome sem caixa |
| `SemesterTests` | Semestre atual por padrão; sem alocações; sem período mostra a semana típica |
| `DateTests` | Semana de hoje por padrão; até 31 dias; fim de semana não é coluna; intervalos recusados explicam o motivo sem consultar |
| `GridTests` | Turmas em espaços diferentes não são choque; turmas conjuntas; horário livre só no filtro de espaço; todas as faixas do semestre; estados vazios, inclusive só com a etapa, sem consultar alocações |
| `QueryTests` | Consultas fixas, sem crescer com o intervalo nem com as aulas |
| `OriginalTimetableTests` | Horário original: semana típica importada com cancelamentos e versões ignorados, sem agendamentos; mesmos filtros sem datas e links de ida e volta |

### `test_public_ics.py`

`PublicIcsTests`: exporta só a turma escolhida, e sem filtro dá 404; a ocorrência cancelada fica de fora.

### `test_public_cache.py`

Cache das rotas públicas, descrito em [testes transversais](../testes.md#testes-transversais) e na seção 4 das [convenções](../convencoes.md#4-controle-de-acesso).

| Classe | O que garante |
|---|---|
| `KeyTests` | Chave com formato e tamanho fixos, igual para os mesmos parâmetros em qualquer ordem e diferente por parâmetro, recurso ou geração; recurso desconhecido recusado |
| `LookupTests` | Falta e acerto, com a geração lida uma vez por requisição; incrementar torna a entrada anterior inalcançável e a geração perdida é recriada sem reaproveitar; valor ilegível é falta; sem Redis, passa direto |
| `UnavailableTests` | Erro de conexão e timeout caem no banco; falha de escrita ou de invalidação não quebra a resposta; pausa de 30 segundos |
| `CommitTests` | Commit incrementa e rollback não, uma vez por transação, sem perder escrita depois de savepoint desfeito; mudanças de espaço, curso, usuário relevante e docente da alocação incrementam, login e senha não; escritas em massa e `clear_data` invalidam explicitamente; falha de invalidação mantém a escrita |
| `BookingInvalidationTests` | Solicitação, aprovação, cancelamento, alteração e exclusão de agendamento incrementam depois do commit; recusa não |
| `ImportInvalidationTests` | A prévia não invalida; a confirmação pelo worker invalida uma vez |
| `PublicViewCacheTests` | Cabeçalhos de falta e acerto sem cache do navegador, o mesmo conteúdo para o autenticado e fora do login e da senha; mesmo conteúdo com e sem cache; grafias compartilham a entrada e valor desconhecido não cria entrada; página e grade aquecidas sem consultas; troca de dia e de geração reconstroem; Redis fora serve do banco |
| `BulkWriteScanTests` | Toda escrita em massa nova foi revisada e as invalidações explícitas estão no lugar |
| `JsonSerializerTests` | O Redis guarda JSON, nunca pickle; tipo desconhecido recusado na escrita |
| `TolerantCacheTests` | Com o Redis fora, os limites de tentativa deixam de valer e o login não falha |
