## Context

### O que existe hoje (conferido no código)

| Conceito | Onde | Situação |
|---|---|---|
| Semestre letivo | `Semester` (`code` `2026/2`, `start_date`, `end_date` opcionais) | sem período, a Grade mostra a semana típica |
| Faixa de horário | `TimeSlot` (por semestre) | `semester_slots()` devolve as faixas com aula |
| Espaço | `Space` (nome atual, `SpaceName`, `origin`, `source_import`, `is_active`) | a Grade filtra pelo nome atual e lista também os inativos com aula |
| Docente | `Teacher` (só `name`, o nome da planilha) | `Allocation.teachers` é M2M; **não há chave estrangeira para `User`** |
| Usuário | `User` (`email` único, `name`, `username` opcional e único sem diferenciar a caixa, `is_active`, `is_superadmin`) | o docstring de `Teacher` diz que o nome "guarda o mesmo valor que o `User.username`" e que isso torna possível "uma correspondência futura exata" |
| Curso e nível | `Course` (`name`, `stage`: `GRADUACAO` "Graduação", `ENSINO_MEDIO` "Ensino médio") | o nível vem da aba da planilha |
| Turma | `ClassGroup` (`course`, `label` livre: `4º PERÍODO`, `1º ANO A`, `1º ANO Meio Ambiente`) | o período ou ano só existe no texto do rótulo |
| Aula recorrente | `Allocation` (semestre, turma, disciplina, espaço opcional, docentes, `weekday`, `time_slot`, `origin`) | índices `(semester, space, weekday)`, `(semester, weekday, time_slot)`, `(semester, class_group)` |
| Ocorrências | `occupancy(space, …)` junta `grid_sources()` | presa a uma sala e aberta a fontes futuras (reservas) |
| Grade | `timetable.py` (`build_week`, `build_day`, `Week`, `Day`, `Cell`, `Entry`, `week_dates`, `month_dates`, `clamp`, `natural_key`, `group_label`), `SpaceAllocationGridView`, `grid.html`, `timetable_cell.html` | filtros `semestre`, `sala`, `visao`, `semana`, `mes` |
| Acesso | `login_required` no `urls.py`, `PermissionMiddleware` pelo `permission_required`, `AuditMiddleware` pelo `audit_resource` | cada middleware só age quando a view declara o atributo |

Dados de desenvolvimento em 25/09/2026: 1 semestre (`2026/2`, com período), 1.499 alocações, 87 espaços (1 inativo), 129 docentes, 15 cursos, 56 turmas, 15 faixas. 74 alocações sem espaço e 8 sem docente. A sala mais usada tem 59 alocações por semana.

As conclusões da investigação foram confirmadas: nenhum filtro exige mudança de modelo; o período da turma não é dado estruturado; `occupancy()` não serve à página pública porque passa por `grid_sources()`.

## Goals / Non-Goals

**Goals**

- Página pública, só de leitura, com o ensalamento acadêmico confirmado, filtrável e usável no celular.
- Isolamento da área autenticada: rota, view, formulário, consulta, templates e layout próprios.
- Exposição mínima: só os campos do card.
- No máximo 8 consultas por requisição, qualquer que seja o filtro e o intervalo.

**Non-Goals**

- Reserva, exceção ou qualquer escrita.
- Mudar o modelo, a importação, a Grade autenticada ou o `grid.html`.
- Cache, rate limit, CDN.

## Decisions

### D1. Rota `calendario/`

A rota fica em `schedule/urls.py`, sem `login_required`, com o nome `public_calendar`, e é a única rota pública desta Change: não há rota de fragmento, de opções, de exportação nem de API. A view só aceita GET (`http_method_names = ['get', 'head']`); os demais métodos recebem 405.

### D2. View pública isolada

`PublicCalendarView(TemplateView)`, em `schedule/public_views.py`, não declara `permission_required` nem `audit_resource`, não herda de view autenticada (`SpaceAllocationGridView`, `OperationFormView`, `ModalView`, `ConfirmedActionView`) e não lê `request.user`. Ela só chama `schedule/public.py` e renderiza o template público. Tudo o que é exposto sem login fica nesses dois módulos e nos templates de `schedule/templates/schedule/public/`.

Sem `permission_required`, o `PermissionMiddleware` deixa a requisição passar; sem `audit_resource`, o `AuditMiddleware` não grava acesso. Nenhum middleware muda, e `SpaceAllocationGridView` continua com `login_required` e `ENSALAMENTO.VISUALIZAR`.

### D3. Só o ensalamento acadêmico, sem `occupancy()` nem `grid_sources()`

A página pública consulta explicitamente `Allocation` e nunca chama `occupancy()`, `grid_sources()` nem `AllocationSource`. Reservas, exceções ou outras fontes que entrarem em `grid_sources()` não chegam à página pública; mostrá-las exigiria outra Change. Um teste acrescenta uma fonte a `grid_sources()` e confere que a ocorrência dela não aparece.

### D4. Docentes e e-mail

**Origem das opções.** O filtro "Docente" lista só `Teacher` com alocação no semestre escolhido. A tabela de usuários nunca é a origem das opções: superadmins, administradores, contas técnicas e usuários sem vínculo de docente não aparecem, porque não são `Teacher` do ensalamento. Um docente sem conta de usuário aparece normalmente.

**E-mail.** `Teacher` não tem chave estrangeira para `User`. A ligação que o domínio já prevê é a correspondência exata do `Teacher.name` com o `User.username`, sem diferenciar a caixa. O card mostra o e-mail do usuário **ativo** cujo `username` corresponde ao nome do docente; sem correspondência, ou com o usuário inativo, o card mostra só o nome. A correspondência nunca é aproximada, por prefixo ou ignorando acentos.

A consulta dos e-mails recebe só os nomes dos docentes que estão nas aulas encontradas e lê só `username` e `email`:

```python
User.objects.annotate(key=Lower('username'))
    .filter(key__in=[name.casefold() for name in names], is_active=True)
    .values_list('username', 'email')
```

Ela usa o índice da restrição `Lower('username')` e não lê nome civil, perfis, permissões, `is_superadmin`, senha, datas nem auditoria. Superadmin ou administrador que seja docente no ensalamento aparece como docente, pelo nome e pelo e-mail, e nada indica o perfil dele.

O `User` não tem outros dados pessoais (telefone, CPF, endereço), e nenhum outro campo dele é lido.

### D5. Dados exibidos

Cada aula é um `PublicEntry` (dataclass sem referência a model): data, início e fim, disciplina, curso e turma (`group_label`), nível (só para a cor e o texto acessível), sala pelo nome atual ou "Sem sala definida", e docentes, cada um com nome e e-mail opcional.

Não aparecem: IDs, outros nomes do espaço, origem ou situação do espaço, importação, auditoria, perfil, permissões, reservas, "Choque", contagem de faixas ocupadas do campus, nem link da área autenticada além de "Entrar".

A consulta das alocações usa `only()` com as colunas desse card, para não carregar entidades completas.

### D6. Filtros e combinação

| Parâmetro | Valor | Opções | Aplicação no banco |
|---|---|---|---|
| `semestre` | código (`2026/2`) | o atual pela data e os semestres com alocação | `semester=` |
| `sala` | nome atual | espaços com alocação no semestre, ativos ou inativos, na ordem natural | `space=` |
| `docente` | `Teacher.name` | docentes com alocação no semestre | `teachers=` |
| `curso` | `Course.name` | cursos com turma alocada no semestre | `class_group__course=` |
| `nivel` | `graduacao` ou `ensino-medio` | "Graduação" e "Ensino médio" (`Stage`) | `class_group__course__stage=` |
| `inicio`, `fim` | `aaaa-mm-dd` | datas | montagem das datas |

- Combinação por "e". Combinação sem aula mostra o estado vazio, sem erro.
- O nome é comparado sem diferenciar a caixa com as opções carregadas, e só o registro encontrado entra na consulta. Valor fora das opções é descartado sem mensagem.
- As opções não dependem umas das outras.
- A sala inativa aparece nas opções quando tem alocação no semestre; sem alocação, não aparece. Como a lista de opções é por semestre, e não por intervalo, uma sala inativa com aula no semestre pode ser escolhida para um intervalo em que não tem aula, e o resultado é o estado vazio.
- Não existe filtro por período ou ano da turma.

### D7. Semestre e datas

- O semestre é o semestre letivo, com o padrão da Grade: o atual pela data e, com código desconhecido, o atual.
- As duas datas são obrigatórias. Na primeira visita, o formulário vem preenchido com a semana de hoje (segunda a sexta), levada para dentro do período do semestre com `clamp`; essas datas contam como informadas. Na URL, uma data sem a outra é recusada com "Informe a data inicial e a data final."; data em formato inválido, com "Informe uma data válida."; a final antes da inicial, com "A data final deve ser igual ou posterior à data inicial."; intervalo com mais de 31 dias corridos, com "Escolha um intervalo de até 31 dias.". Na recusa, as aulas não são consultadas.
- As colunas são os dias de segunda a sexta do intervalo. O dia fora do período do semestre aparece como "Fora do semestre". O intervalo todo fora do período mostra "O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026." e não consulta aulas.
- Semestre sem período: a página mostra a semana típica, sem datas, com "Datas do semestre 2026/2 ainda não definidas. O calendário mostra a semana típica.", e os campos de data ficam desabilitados.
- Não há botões "Anterior", "Hoje" e "Próximo": o intervalo muda só pelos campos de data, para a tela ficar mais limpa (decisão do autor depois da conferência visual).

### D8. Filtro principal obrigatório

Sem `sala`, `docente` ou `curso` válidos, a página mostra "Escolha uma sala, um docente ou um curso." e não consulta faixas, aulas nem e-mails. Semestre, nível e datas sozinhos não bastam.

### D9. Reaproveitamento

**Reaproveitado:** `build_week` e `build_day`, `Week`, `Day`, `Continued`, `Outside`, `semester_slots`, `week_dates`, `monday_of`, `clamp`, `dates_between`, `Semester.contains`, `group_label`, `readable_course`, `readable_group`, `natural_key`, `imported_semesters`, `current_semester_code`, `ui/components/select.html` com o `select.js` (fonte fixa, sem rota de opções), e as classes CSS `timetable-*`.

**Não reaproveitado:** `SpaceAllocationGridView`, `GridFilterForm`, `occupancy()`, `grid_sources()`, `AllocationSource`, `Entry` (não tem sala nem e-mail), `Cell.kind` e `timetable_cell.html` (classificam "Choque" por faixa), `grid.html` (tem `perms`, "Ver importações", aviso administrativo) e `ui/layouts/app.html` (menu, usuário, notificações, websocket, modal, `hx-headers` com CSRF).

**Templates:** o calendário público tem marcação própria em `schedule/templates/schedule/public/`, com as mesmas classes CSS. Não há partial compartilhado com o `grid.html` nesta Change: o ganho seria pouco e acoplaria as duas áreas.

**Turmas juntas e choque:** as aulas da mesma faixa e do mesmo dia ficam na mesma célula, ordenadas por sala, curso e turma. "N turmas juntas" aparece só quando elas têm a mesma sala, a mesma disciplina e os mesmos docentes. Turma A na sala 1 e turma B na sala 2 no mesmo horário são duas aulas na mesma célula, cada uma com a sua sala, sem marca. "Choque" nunca aparece.

### D10. Consultas, índices e volume

No máximo 8 consultas por requisição, qualquer que seja o intervalo:

| # | Consulta | Junções e índice |
|---|---|---|
| 1 | semestres com alocação | `allocation.semester_id` (FK indexada) |
| 2 | salas do semestre | `allocation (semester, space, weekday)` |
| 3 | docentes do semestre | tabela intermediária (FK indexadas) + `allocation.semester_id` |
| 4 | cursos do semestre | `allocation (semester, class_group)` + `classgroup.course_id` |
| 5 | faixas do semestre | `timeslot.semester_id` |
| 6 | aulas filtradas, com `select_related` de disciplina, faixa, sala, turma e curso | índice do filtro principal; docente pela tabela intermediária |
| 7 | docentes das aulas (`prefetch_related`) | tabela intermediária por `allocation_id` |
| 8 | e-mails dos docentes das aulas | índice único `Lower('username')` |

Sem filtro principal, com o intervalo recusado ou fora do semestre, 5 a 8 não rodam. Nenhuma consulta é feita por dia, por célula ou por aula, e nada é carregado sem filtro para ser filtrado em Python. As datas são expandidas em Python só sobre as aulas já filtradas: hoje, no pior caso, 59 aulas por semana × 23 dias úteis, cerca de 300 ocorrências. As opções devolvem só nome ou código.

Nenhum índice novo é criado agora.

**Resultado do `EXPLAIN ANALYZE`** (25/09/2026, dados de desenvolvimento: 1.499 alocações, 1.597 vínculos com docentes, 129 docentes, 87 espaços, 130 usuários):

| Consulta | Plano | Tempo |
|---|---|---|
| semestres com alocação | seq scan em `allocation` + index scan em `semester_pkey` (memoize) | 0,38 ms |
| salas do semestre | hash join `allocation` × `space` | 0,31 ms |
| docentes do semestre | hash join na tabela intermediária | 0,58 ms |
| cursos do semestre | hash join `allocation` × `classgroup` × `course` | 0,45 ms |
| aulas do docente | **bitmap index scan** em `schedule_allocation_teachers_teacher_id`, depois index scans nas chaves de disciplina, turma, sala e faixa | 0,19 ms |
| docentes das aulas | **index scan** em `schedule_allocation_teachers_allocation_id` | 0,03 ms |
| faixas do semestre | **index only scan** em `schedule_allocation_time_slot_id` | 0,25 ms |
| e-mails | seq scan em `accounts_user` (130 linhas; o índice de `Lower('username')` só compensa com mais usuários) | 0,03 ms |

Os seq scans são sobre tabelas pequenas, que cabem numa página; o planejador prefere lê-las inteiras. Todas as consultas ficam abaixo de 1 ms. Consultas observadas por requisição: 4 sem filtro principal ou com intervalo recusado, e 8 com sala, docente ou curso, iguais numa semana e em 31 dias. O maior volume observado é o curso Informática em 31 dias, com 910 aulas na Grade.

### D11. Abuso e infraestrutura futura

- O filtro principal obrigatório e os 31 dias limitam o custo de cada requisição.
- Parâmetros com mais de 200 caracteres ou fora do formato são descartados.
- A página não grava sessão, cookie, auditoria nem registro de consulta.
- Rate limit e cache não existem no projeto e não entram nesta Change. A recomendação para a implantação é limitar requisições por IP e aplicar cache curto no proxy, na rota `calendario/`.

### D12. Layout público e SEO

`ui/layouts/public.html` estende `base.html` com uma barra fixa no topo, branca e com borda fina, só com a marca "SaliSpace" e o link "Entrar" em estilo de texto, seguida do título "Horários do campus" e dos filtros. O cabeçalho, os filtros e o calendário ficam centralizados, com a largura máxima de `--container-page`. O layout e o `main` com o calendário. Não inclui menu, sidebar, usuário, notificações, modal, formulário de sair nem `hx-headers` com o token CSRF, e não usa `user` nem `perms`. A Change confere que `notifications.js` não abre conexão sem o painel de notificações; se abrir, o layout público não o carrega. A página tem `<meta name="robots" content="noindex">`.

### D13. Celular

A página usa a mesma Grade em qualquer largura. Não existe outra representação só para o celular.

- **Filtros:** abaixo de 640 px ficam empilhados, um por linha na largura toda, com Data inicial e Data final lado a lado. Ficam num card sempre aberto, com a borda do calendário. Todos os controles têm pelo menos 44 px. Sala, Docente e Curso usam o select com busca; as datas usam `input type="date"`. Os selects atualizam pelo htmx; as datas aplicam no botão "Mostrar". Sem JavaScript, "Mostrar" envia o formulário.
- **Calendário:** a Grade rola na horizontal só dentro da própria área, rotulada e focável, com a coluna de horários e a linha dos dias fixas (`position: sticky`). A página nunca rola na horizontal a partir de 360 px. Abaixo de 640 px, a coluna de dia tem largura mínima para um card legível sem cortar o texto, e a área rola até "Hoje" quando ele está no intervalo.
- **Carregamento:** durante a requisição do htmx, o calendário fica com `aria-busy="true"` e "Mostrar" desabilitado (`busy.js`). Sem skeleton e sem spinner.

A Grade autenticada troca a tabela pela lista por dia abaixo de 640 px. A página pública não faz isso, pela decisão de não ter uma representação só para o celular.

### D14. Estados vazios e mensagens

| Situação | Texto |
|---|---|
| Nenhum filtro principal | "Escolha uma sala, um docente ou um curso." |
| Semestre sem aulas | "Nenhum horário publicado no semestre 2027/1." |
| Filtros sem aula no intervalo | nenhum texto: a Grade aparece com as células vazias |
| Intervalo fora do semestre | "O intervalo escolhido está fora do semestre 2026/2, de 01/06/2026 a 23/12/2026." |
| Data inválida | "Informe uma data válida." |
| Só uma data | "Informe a data inicial e a data final." |
| Data final antes da inicial | "A data final deve ser igual ou posterior à data inicial." |
| Mais de 31 dias | "Escolha um intervalo de até 31 dias." |
| Semestre sem período | "Datas do semestre 2026/2 ainda não definidas. O calendário mostra a semana típica." |


## Risks / Trade-offs

- **[E-mail é o identificador de login]** O e-mail exibido é o mesmo usado para entrar no sistema. A decisão do autor aceita isso; a proteção de login do allauth (limite de tentativas) continua valendo.
- **[Correspondência por `username`]** Depende de o administrador preencher o `username` igual ao nome da planilha. Sem isso, o docente aparece sem e-mail.
- **[Fonte futura de reservas]** → D3, com teste.
- **[Consulta ampla]** → D8 e 31 dias, no máximo 8 consultas.
- **[Grade larga no celular]** → rolagem só dentro da área, colunas fixas, largura mínima de coluna.
- **[Dados da planilha]** Cursos quase duplicados ("Eng. Alimento" e "Eng. Alimentos") aparecem como opções diferentes.

## Migration Plan

Não há migration. A rota nova é só acrescentada; nenhuma rota, view ou permissão existente muda. Reverter é retirar a rota.

### D15. Ajustes da implementação

- A rota é isenta de CSRF (`csrf_exempt` no `urls.py`) para que um POST receba 405, como a spec pede, e não 403 do middleware. A view não grava nada, não usa sessão e só aceita GET e HEAD.
- O `base.html` ganhou o bloco `head`, vazio por padrão, que a página pública usa para o `noindex`.
- O card de filtros tem a borda do calendário e fica sempre aberto; o título "Horários do campus" ficou só para leitores de tela e a linha de resumo saiu. Valores longos são cortados com reticências, e o card não corta a lista de opções aberta.
- Depois da conferência visual, o autor retirou "IFNMG Campus Salinas" do cabeçalho e os botões de navegação entre intervalos, e pediu o cabeçalho mais discreto e o conteúdo centralizado.
- O comportamento de tela vem de `ui/static/ui/js/calendar.js`, carregado só pelo layout público: rola a Grade até "Hoje" e marca `aria-busy` durante a requisição do htmx.
- As linhas da Grade pública vão da primeira à última aula mostrada no intervalo, e não por todas as faixas do semestre: um curso só de manhã e tarde não ganha as linhas da noite. As faixas vazias entre elas continuam. Sem aula no intervalo, a Grade aparece com todas as faixas do semestre e as células vazias, sem mensagem, para indicar os horários disponíveis (e, no futuro, onde uma reserva poderá ser pedida).
- A conferência no navegador, com uma cópia dos dados de desenvolvimento, mostrou o campo de data final passando da borda da tela a 360 px; os campos de data passaram a ter `min-width: 0`.

## Open Questions

Nenhuma. A imagem de referência (seção 9.8 das convenções) foi substituída pelos ajustes que o autor pediu sobre capturas da própria tela: cabeçalho discreto, filtros em card, sem navegação entre intervalos, Grade vazia sem mensagem.
