## Context

### O que existe hoje

| Conceito | Onde | Como está modelado |
|---|---|---|
| Semestre letivo | `schedule.models.Semester` | só o `code` (`2026/2`), sem datas |
| Faixa de horário | `TimeSlot` | início e fim, por semestre |
| Espaço, curso, turma, disciplina, docente | `Space`, `Course`, `ClassGroup`, `Subject`, `Teacher` | catálogos válidos entre semestres |
| Aula recorrente | `Allocation` | semestre, turma, disciplina, `weekday`, `time_slot`, espaço opcional, docentes, `origin` (`IMPORTADA` ou `MANUAL`); única por semestre, turma, dia, faixa e disciplina; índices por semestre e espaço e dia, e por semestre e dia e faixa |
| Importação | `imports` + `schedule/imports.py` | acrescenta e atualiza, nunca exclui (D13 de `importar-ensalamento-da-planilha`) |
| Grade | `schedule/timetable.py`, `SpaceAllocationGridView`, `grid.html` | semana típica de uma sala: `Week` → `Day` → `Cell`/`Continued` → `Entry`; faixas seguidas unidas em bloco; contagem de faixas ocupadas e disponíveis; filtros `semestre` e `sala` |
| Semestre padrão | `current_semester_code(today)` | janeiro a junho é `/1`, julho a dezembro é `/2` |

Três fatos decidem a arquitetura:

1. **A alocação já é uma regra de recorrência.** "Toda segunda-feira, 19:00 - 20:40, sala 10, disciplina A, no semestre 2026/2" é exatamente uma `Allocation` (uma por faixa, D9 da Change de importação). Nada é gravado por data, e isso não muda.
2. **O semestre não tem vigência.** Sem data de início e de fim, a regra não pode ser posta num calendário. É a única lacuna de modelagem para as visões semanal e mensal.
3. **A Grade já separa estrutura e origem.** Os templates recebem `Week`, sem `Allocation` (D4 e D11 de `visualizar-grade-do-ensalamento`). Basta pôr, entre as alocações e a `Week`, uma camada de ocorrências datadas.

### O que é e o que não é a Grade

A Grade **consulta e apresenta** a ocupação de um espaço num intervalo de datas. Ela não cria, não altera e não exclui ocupação, nem do ensalamento nem de reserva. A tela de reserva é outra funcionalidade, de uma Change futura, e escreve os dados que a Grade depois lê.

```
Planilha ──importação──▶ Allocation (regra semanal)  ─┐
                                                      ├─▶ fontes de ocupação ─▶ ocorrências do intervalo ─▶ Grade (semana | mês)
Tela de reserva (futura) ──▶ reservas (futuras)      ─┘
```

### Termos

Seguindo o glossário (seção 9.4 das convenções) e a Constitution (P7):

- **disponível** e **ocupado** para o estado da faixa. "Livre" não é usado em nenhum texto exibido.
- **reserva** para a ocupação criada pela tela futura. "Agendamento" fica só como palavra desta análise, nunca na interface.
- **ocorrência**: uma aula ou reserva numa data e numa faixa. É um conceito de cálculo, não um registro.

## Goals / Non-Goals

**Goals**

- Dar vigência ao semestre, com o menor acréscimo possível.
- Calcular as ocorrências de qualquer intervalo de datas a partir das regras, sem gravá-las.
- Mostrar o mesmo cálculo em visão semanal e mensal, com navegação e com as faixas disponíveis visíveis.
- Deixar definido, sem implementar, como a alteração da recorrência, as exceções e as reservas entram depois.

**Non-Goals**

- Tela de reserva e qualquer escrita de ocupação pela Grade.
- Versões da alocação, exceções por data e feriados como dados (ficam para a Change que tiver a tela que os cria, conforme a seção 1 das convenções: cada Change cria só o que usa).
- Conflito ou choque além do que a Grade já mostra (D13 de `visualizar-grade-do-ensalamento`).

## Decisions

### D1. A alocação continua sendo a regra de recorrência, sem linha por data

Não se cria `Occurrence` no banco, nem uma linha por aula dada. Uma disciplina de quatro faixas por semana num semestre de vinte semanas continua sendo quatro `Allocation`, e não oitenta registros. A ocorrência é **calculada** quando a Grade pede um intervalo (D4).

*Alternativa descartada:* materializar as ocorrências na confirmação da importação. Multiplicaria as linhas por cerca de vinte, obrigaria a reimportação a sincronizar milhares de datas e faria de uma mudança de sala uma atualização em massa.

### D2. O semestre ganha período: `start_date` e `end_date`

`Semester` ganha `start_date` e `end_date` (`DateField`, `null=True`), com uma `CheckConstraint` de início anterior ou igual ao fim. Os dois são preenchidos juntos ou nenhum dos dois.

- **Opcionais**, porque os semestres existentes não têm período, a planilha não o traz (D16 da Change de importação) e a importação não muda nesta Change.
- **Por que no semestre, e não na alocação:** toda aula do semestre vale do primeiro ao último dia letivo. Uma data por alocação repetiria o mesmo par em centenas de linhas. A vigência própria de uma alocação só aparece quando alguém muda a recorrência no meio do semestre (D10).
- **Regra no model:** `Semester.define_period(start_date, end_date)` valida e grava numa transação, e recusa com `ValidationError` o início depois do fim e um período maior que 366 dias. O ano do período não precisa ser o do código, porque o calendário do campus pode atravessar o ano.

### D3. O período é definido por um modal aberto pela Grade

"Definir período" é uma ação de gestão pequena, e segue as convenções (seção 6): `ModalView` pelas classes base de `accounts/views.py`, rota `ensalamento/semestres/<pk>/periodo/` (pela chave, porque o código tem barra), `login_required` no `urls.py`, formulário com as duas datas e resposta `HttpResponseClientRedirect` para a Grade no mesmo semestre.

- **Permissão:** `ENSALAMENTO.IMPORTAR`, a de quem já administra o semestre ao importá-lo. Não se cria permissão nova.
- **Auditoria:** registro `ALTERAR` do recurso `SEMESTRE` (novo no catálogo), com o código e o período anterior e o novo.
- **Sem período:** a Grade mostra a semana típica de hoje, sem datas e sem navegação, com o aviso "Período do semestre 2026/2 não definido." e o botão "Definir período" para quem pode. A visão mensal fica indisponível com o mesmo aviso. Assim nada do que funciona hoje deixa de funcionar.

A Grade é uma consulta, e o modal não a transforma em tela de cadastro: ele só abre por cima dela, como os modais das demais telas.

### D4. O cálculo das ocorrências: regra × datas do intervalo

`schedule/occupancy.py`:

```
Occurrence(date, start, end, space_id, source, kind, entry)   frozen dataclass

occupancy(space, start_date, end_date, sources) -> list[Occurrence]
    para cada fonte: fonte.occurrences(space, start_date, end_date)
    ordena por data, início, e pelo texto da entrada
```

A fonte do ensalamento, `AllocationSource`:

1. Descobre os semestres cujo período cruza `[start_date, end_date]` (uma consulta).
2. Lê as alocações da sala nesses semestres com `select_related` e `prefetch_related` (duas consultas), como `space_week` já faz.
3. Para cada data do intervalo, recortada ao período do semestre, emite uma ocorrência por alocação cujo `weekday` é o dia da data.

O custo em banco é fixo (três consultas), qualquer que seja o intervalo. O custo em memória é alocações × dias, pequeno: uma sala tem dezenas de alocações e um mês tem cerca de 22 dias úteis. Um intervalo que atravessa dois semestres funciona sem caso especial.

`kind` diz o que a ocorrência é: `ENSALAMENTO` nesta Change, `RESERVA` depois (D12). `entry` é o `Entry` que a Grade já usa (disciplina, turma com curso, docentes, etapa), para que o card não mude.

### D5. Qualquer intervalo, a mesma função

A semana e o mês são só dois intervalos passados a `occupancy`. Uma visão de dia, de quinzena ou uma consulta de disponibilidade para a tela de reserva usam a mesma função, sem mudar o modelo. A disponibilidade de uma faixa numa data é o complemento: faixa do semestre × data dentro do período, menos as ocorrências (D9).

### D6. Fontes de ocupação

Uma fonte é qualquer objeto com `occurrences(space, start_date, end_date)`. A Grade monta a lista de fontes num lugar só (`grid_sources()` em `schedule/occupancy.py`), que nesta Change devolve `[AllocationSource()]`. Não se cria classe base abstrata nem registro dinâmico: uma lista explícita é suficiente e fácil de testar, e a Change de reserva acrescenta um item a ela.

Ensalamento e reserva ficam **separados na origem** (cada um no seu model, com as suas regras e a sua tela) e **juntos só na consulta**. A Grade não conhece `Allocation` nem a futura reserva: recebe ocorrências.

### D7. Visão semanal com datas

- **URL:** `?visao=semana&semestre=2026/2&sala=1/13&semana=2026-10-05`. `semana` é qualquer data da semana; a Grade usa a segunda-feira dela. Valor inválido cai no padrão, com 200.
- **Padrão:** a semana de hoje, quando hoje está no período do semestre; antes dele, a primeira semana; depois dele, a última.
- **Linhas:** as faixas com aula no semestre, como hoje, iguais para toda sala. Faixas seguidas com as mesmas ocorrências continuam virando um bloco (D5 e D6 de `visualizar-grade-do-ensalamento`), agora por data.
- **Colunas:** segunda a sexta, com o dia e a data ("Seg 05/10"). "Hoje" é a data de hoje, e não mais o dia da semana. O dia fora do período mostra "Fora do semestre" e não conta faixas.
- **Navegação:** "Semana anterior", "Próxima semana" e "Hoje", como links (`href` e `hx-get`, atualizando só `#grade` e a URL), com o intervalo "05/10/2026 a 09/10/2026" no título. Os links ficam desabilitados fora do período.
- **Contagem:** faixas ocupadas e disponíveis da semana, só com os dias dentro do período.

### D8. Visão mensal: o mapa de ocupação do mês

**Papel.** A visão mensal responde "em quais dias deste mês a sala está ocupada, e quanto". Ela é um **mapa de ocupação** do ensalamento, e não um calendário genérico de eventos: não lista compromissos por extenso, não tem horas soltas, não tem arrastar nem criar. O detalhe de cada aula continua sendo da visão semanal, e o mês leva a ela.

**Mesmo cálculo, sem estrutura paralela.** O mês chama `occupancy(space, primeiro_dia_util, ultimo_dia_util, grid_sources())`, a mesma função da semana. `Month` → `MonthWeek` → `MonthDay` em `timetable.py` são só apresentação, montados das mesmas ocorrências e das mesmas faixas do semestre que formam as linhas da semana. Nada é gravado.

**Forma proposta.**

- As semanas do mês nas linhas e segunda a sexta nas colunas, as mesmas colunas da visão semanal. Sábado e domingo não aparecem, como na semana.
- Cada dia mostra a data e uma **tira de faixas**: uma marca por faixa do semestre, na mesma ordem das linhas da semana, preenchida com a cor da etapa quando a faixa está ocupada e vazia quando está disponível. É a coluna do dia da Grade semanal, comprimida. Junto da tira, o texto "5 de 12 faixas ocupadas", para que o estado não dependa só da cor (seção 9.7 das convenções), e o `aria-label` do dia com a data e as mesmas contagens.
- Dia sem ocupação: a tira vazia e "Nenhuma faixa ocupada", sem frase de preenchimento.
- Dias de outro mês: só a data, esmaecida, sem tira. Dias fora do período do semestre: "Fora do semestre", sem tira e sem contagem.
- "Hoje" marcado como na semana.
- O dia inteiro é um link para a semana dele (`href` e `hx-get`), com o mesmo semestre e a mesma sala. Não abre formulário nem modal.

**Navegação e semestre.**

- URL: `?visao=mes&semestre=2026/2&sala=1/13&mes=2026-10`. Padrão: o mês de hoje, quando hoje está no período; antes dele, o primeiro mês do período; depois, o último. `mes` inválido cai no padrão, com 200.
- "Mês anterior", "Próximo mês" e "Hoje", desabilitados além do primeiro e do último mês que tocam o período. O mês que só em parte está no período mostra o resto como "Fora do semestre".
- A alternância "Semana" e "Mês" fica ao lado dos filtros, como links de abas, preservando semestre, sala e a data de referência: da semana vai ao mês da segunda-feira dela; do mês, à semana do primeiro dia do período dentro dele, ou de hoje quando hoje está nele.

**Abaixo de 640 px.** Os dias do mês dentro do período viram uma lista, um por linha, com a data, a tira e a contagem.

**Coerência com a semana.** Mesmo card de fundo, mesmos tokens de etapa (D14 de `visualizar-grade-do-ensalamento`), mesma legenda, e a tira segue a ordem das linhas da semana para que o olho reconheça a manhã, a tarde e a noite nos dois lugares.

**Decisões de interface pendentes do autor** (seção 9.8 das convenções, tela nova):

- **P1. Referência visual do mês.** Antes da prévia estática.
- **P2. Conteúdo do dia:** a tira de faixas com a contagem (proposta acima), ou a lista das aulas em blocos com horário e disciplina, até três e "mais N". A tira mantém o mês como mapa; a lista aproxima do calendário genérico que se quer evitar. A recomendação é a tira.
- **P3. Cor da tira:** pela etapa, como os cards, ou um tom único de "ocupado". A recomendação é a etapa, que já tem legenda.

### D9. Faixa disponível: visualmente vazia, semanticamente disponível

*Decisão do autor em 25/09/2026.* Mantém-se a decisão da Change `visualizar-grade-do-ensalamento`: a célula sem ocorrência fica **visualmente vazia**, como na planilha, para não poluir a Grade. A informação existe para a tecnologia assistiva: a célula tem o texto "Disponível" em `sr-only` e o `aria-label` com o dia, a data e a faixa ("Segunda-feira, 05/10/2026, das 21:00 às 21:50, disponível").

Três situações distintas, que nunca se confundem:

| Situação | Estrutura | Na tela |
|---|---|---|
| Faixa disponível numa data do período | `Cell.state = available` | célula vazia, "Disponível" para o leitor de tela, e conta na faixa de situação |
| Dia fora do período do semestre | `Day.in_period = False` | "Fora do semestre", visível, sem células e sem contagem |
| Semestre sem período, ou sem ensalamento | sem `Week` datada | aviso da Grade (D3), e não uma grade vazia |

A faixa disponível não é erro: a Grade lê só alocações confirmadas (D15 de `visualizar-grade-do-ensalamento`) e não tem estado de erro. Ela também não é ausência de dados, porque só existe dentro do período de um semestre com faixas.

"Disponível" é um estado calculado, e não um dado nem uma ocorrência: não existe registro de faixa disponível. Abaixo de 640 px, cada dia continua listando só as faixas ocupadas, com o total de disponíveis no título do dia ("3 faixas disponíveis"), e "Sala disponível o dia todo." quando não há ocupação, como hoje.

Os estados que a estrutura distingue são `Cell.state`: `available` e `occupied`, e o `kind` das entradas diz se a ocupação é do ensalamento ou, depois, de reserva.

### D10. Alteração futura da recorrência: versões por vigência (não implementada)

**Situação nesta Change.** A `Allocation` representa a **regra vigente**, e só ela. Não existe histórico de regra. Por isso uma reimportação que muda a sala ou os docentes de uma alocação (`update` de D13 da Change de importação) muda também a representação das semanas anteriores: a Grade de agosto passa a mostrar a sala nova. É uma limitação conhecida e aceita.

**O que não se cria agora.** Nenhum `valid_from`, `valid_until`, `replaces`, tabela de versões ou de histórico. Nenhuma funcionalidade desta Change os usa (seção 1 das convenções), e a importação não muda. A solução fica só descrita abaixo.

**Solução futura.** Quando a tela de edição de alocação existir, uma mudança "a partir de 01/10, terça-feira, sala 12" **não altera** a alocação existente. Ela:

1. encerra a alocação atual, gravando `valid_until = 30/09`;
2. cria uma alocação nova com `valid_from = 01/10`, o dia, a faixa e a sala novos, e `origin = MANUAL`, apontando para a anterior (`replaces`).

A Change que fizer isso acrescenta a `Allocation` os campos `valid_from` e `valid_until`, opcionais (vazio é "desde o início" e "até o fim do semestre"), e troca a restrição `allocation_unique` por uma que inclua `valid_from`, com a validação no model de que duas versões da mesma identidade não se sobrepõem. O cálculo de D4 só precisa de mais um recorte: a data tem de estar em `[valid_from, valid_until]`.

Exemplo, num semestre de 01/08 a 15/12:

| Regra | Vigência | Dia, faixa e sala |
|---|---|---|
| A | 01/08 a 30/09 (`valid_until = 30/09`) | segunda-feira, 19:00 - 20:40, sala 10 |
| B | 01/10 ao fim do semestre (`valid_from = 01/10`, `replaces = A`) | terça-feira, 19:00 - 20:40, sala 12 |

A Grade de setembro calcula as ocorrências pela regra A, e a de outubro pela regra B, sem nenhuma ocorrência gravada.

Por que versões, e não editar a regra: as ocorrências passadas são calculadas da regra, então editar a regra reescreveria o passado. Com versões, cada período lê a regra que valia nele. Interromper a recorrência é só gravar `valid_until`; mudar a data inicial ou final é a mesma coisa. A Change de versões decide também se a reimportação passa a criar versão em vez de atualizar.

### D11. Exceções por data (não implementadas)

Para o que acontece numa data só, sem criar recorrência inteira, a Change futura cria `AllocationException`: alocação, data, tipo e os dados substitutos.

| Situação | Representação |
|---|---|
| Aula cancelada em 12/10 | exceção `CANCELADA` na data |
| Aula de 12/10 transferida para 14/10 | exceção `TRANSFERIDA` em 12/10, com a data, a faixa e a sala novas |
| Sala trocada só em 12/10 | exceção `ALTERADA` em 12/10, com a sala nova |
| Atividade que não ocorre numa semana | uma exceção `CANCELADA` por data da semana |
| Aula a mais, fora da recorrência | reserva pontual (D12), e não exceção, porque não tem regra de origem |

O cálculo aplica as exceções depois de expandir a regra: tira as canceladas e as transferidas da data original, e põe as transferidas e as alteradas com os dados novos. É uma consulta a mais, pelas exceções da sala no intervalo, e continua sem depender do tamanho do intervalo. Um feriado, se virar dado, é uma exceção aplicada a todas as alocações da data, numa tabela de dias sem aula.

### D12. Reservas na Grade, depois (não implementadas)

A Change da tela de reserva cria o model dela, com as regras, as permissões e a aprovação, num app próprio, e uma fonte `ReservationSource` que devolve `Occurrence` com `kind = RESERVA` e uma `entry` com o título da reserva e o solicitante. Ela acrescenta a fonte a `grid_sources()`. A Grade passa a mostrar a reserva na faixa, com um selo "Reserva" com ícone e texto (a cor nunca é o único sinal), e a faixa deixa de contar como disponível.

A Grade não cria, não edita e não cancela reserva, não tem formulário de reserva e não tem regra de reserva. As reservas são criadas e mantidas pela tela de reserva, numa Change futura, e a Grade apenas as recebe como mais uma fonte de ocupação. Se a tela de reserva quiser partir da Grade, será por um link para a tela dela, com a sala, a data e a faixa na URL, decidido naquela Change.

### D13. O que é reutilizado e o que é novo

| Reutilizado sem mudança | Mudado | Novo |
|---|---|---|
| `Allocation`, `TimeSlot`, catálogos, `Weekday`, índices | `Semester` (período) | `schedule/occupancy.py` |
| `Entry`, `Cell`, `Continued`, `build_day` (bloco de faixas) | `Week` e `Day` (data, "Fora do semestre", estado) | `Month`, `MonthWeek`, `MonthDay` em `timetable.py` |
| `GridFilterForm`, `current_semester_code`, `spaces_of`, `imported_semesters` | `space_week` passa a receber o intervalo e as ocorrências | modal "Definir período" |
| Importação, auditoria da importação, permissões | `grid.html` e o parcial da célula | recurso `SEMESTRE` na auditoria |

## Risks / Trade-offs

- **Semestres sem período.** Até alguém defini-lo, a Grade fica na semana típica. O aviso e o botão na própria Grade tornam o passo visível.
- **Reimportação muda o passado (D10).** Registrada; resolvida pela Change de versões.
- **Feriados aparecem como ocupados.** Sem calendário de dias sem aula, um feriado mostra as aulas do dia. Fica para D11.
- **Datas fora do período digitadas na URL.** Caem no padrão, sem erro.
- **Custo por requisição.** Três consultas e um laço em memória por intervalo; medido na implementação contra a planilha de referência.

## Migration Plan

Uma migration no `schedule`, acrescentando `start_date`, `end_date` e a restrição ao `Semester`, sem dados. Os semestres existentes ficam sem período e continuam funcionando na semana típica. A rota `ensalamento/` mantém o nome e os filtros atuais; `visao`, `semana` e `mes` são opcionais. Reverter é remover os campos: nenhuma outra tabela depende deles.

## Decisões confirmadas pelo autor

Em 25/09/2026:

| Questão | Decisão | Onde está |
|---|---|---|
| Histórico da reimportação | sem versionamento nesta Change; a `Allocation` é a regra vigente, a limitação fica registrada e a solução futura descrita | D10 |
| Faixa disponível | visualmente vazia; "Disponível" só para a tecnologia assistiva; distinta de erro e de ausência de dados | D9 |
| Visão mensal | mapa de ocupação pelo mesmo cálculo, com a proposta definida antes da implementação | D8 |
| Reservas | a Grade não cria, não edita e não cancela reserva; as reservas entram depois como fonte de ocupação | D6, D12 |
| Recorrência futura | encerrar a regra atual e criar outra com nova vigência, sem materializar ocorrências | D10 |

## Open Questions

Ainda dependem do autor:

1. **Referência visual da visão mensal** (D8, P1), antes da prévia estática.
2. **Conteúdo do dia no mês** (D8, P2): tira de faixas com contagem (recomendada) ou lista das aulas.
3. **Cor da tira** (D8, P3): pela etapa (recomendada) ou tom único.
4. **Quem define o período** (D3): `ENSALAMENTO.IMPORTAR` (proposto) ou permissão própria.
5. **Período sugerido no modal** (D3): sugerir datas padrão pelo código do semestre ou começar com os campos vazios.
