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

`Semester` ganha `start_date` e `end_date` (`DateField`, `null=True`), com uma `CheckConstraint` de início anterior ou igual ao fim. Os dois são preenchidos juntos ou nenhum dos dois. O semestre é o **único** lugar do período: a importação só o informa (D3), e não existe outra estrutura que o guarde.

- **Opcionais**, porque os semestres existentes não têm período e a planilha não o traz (D16 da Change de importação).
- **Por que no semestre, e não na alocação:** toda aula do semestre vale do primeiro ao último dia letivo. Uma data por alocação repetiria o mesmo par em centenas de linhas. A vigência própria de uma alocação só aparece quando alguém muda a recorrência no meio do semestre (D10).
- **Regra no model:** `Semester.define_period(start_date, end_date)` valida e grava, e recusa com `ValidationError` uma data sem a outra, o início depois do fim e um período maior que 366 dias. O ano do período não precisa ser o do código, porque o calendário do campus pode atravessar o ano. A operação devolve se o período mudou e **não grava auditoria própria**, porque quem a chama é a importação, que audita o resumo (D3).

### D3. O período é informado no envio da importação

*Revisto pelo autor em 25/09/2026.* A primeira versão desta Change definia o período por um modal "Definir período" aberto pela Grade. O autor decidiu que o período pertence ao momento em que o ensalamento do semestre entra no sistema, a importação, e que a Grade é só consulta. O modal, a rota `ensalamento/semestres/<pk>/periodo/`, o botão e o recurso `SEMESTRE` da auditoria saem.

**Como a importação funciona hoje** (motor `imports` e `schedule/imports.py`):

1. O envio tem, além do arquivo, os campos próprios declarados em `upload_fields`; hoje só `Semestre`. O valor de cada campo próprio é gravado nos valores de **todas** as linhas, como coluna lógica (D16 da Change de importação), para que a confirmação reexecute sem receber nada de novo.
2. A prévia chama `run()` dentro de um savepoint que é **desfeito**: `lock()` resolve o semestre pelo código das linhas (`Semester.objects.resolve`, que cria o semestre se não existir) e trava as alocações dele; depois cada linha executa.
3. A confirmação refaz `run()` com as linhas gravadas e só aplica se o plano refeito for idêntico ao da prévia; senão desfaz e substitui o plano.

**Onde capturar as datas.** No mesmo lugar do semestre: dois campos próprios do envio, "Início do semestre" e "Fim do semestre" (`DateField`, `type="date"`), gravados como as colunas lógicas `Início` e `Fim` em todas as linhas, no formato `AAAA-MM-DD`. Assim o período segue exatamente o caminho do código do semestre: vai para as linhas, é visto na prévia e é reaplicado na confirmação a partir das linhas, sem estado fora delas.

**Onde aplicar.** Em `lock()`, logo depois de resolver o semestre: com as duas datas nos valores, chama `state.semester.define_period(inicio, fim)`. Como `lock()` roda dentro da transação da execução:

- **na prévia**, o período é gravado e desfeito com o resto, como o semestre recém-criado;
- **na confirmação**, é gravado junto com as alocações, na mesma transação; se o plano divergir, é desfeito com elas;
- **no descarte** ou numa importação `COM_ERROS`, o semestre não muda.

O período não entra no plano das linhas, que continua sendo o das entidades. Ele é determinístico, porque vem dos valores gravados, e por isso não precisa entrar na comparação da confirmação.

**Validação no envio.** As regras do período (as duas datas juntas, início até o fim, no máximo 366 dias) são do model. O formulário de envio as aplica antes de ler o arquivo, chamando a validação do `Semester` sobre as datas informadas, e uma recusa é **erro do formulário de envio, sem criar importação**, como o código do semestre fora do formato. Para isso o motor ganha uma capacidade pequena: a importação específica pode declarar `clean_upload(values)`, chamada com os valores dos campos próprios já limpos, para validações que envolvem mais de um campo. O motor continua sem conhecer a regra: só chama o gancho e põe as recusas no formulário.

**Rótulo dos campos.** Os dois campos não são obrigatórios para o formulário, porque a obrigatoriedade depende do semestre, e o renderizador marcaria "(opcional)". Eles declaram `conditional = True`, e o renderizador não marca o campo condicional como opcional; a ajuda do início diz a regra.

**Exibição.** O resumo do detalhe mostra os campos próprios uma vez, e a tabela de linhas deixa de repeti-los: sem recorte escolhido, as colunas são as do arquivo (`file_columns`), sem as colunas lógicas do envio, como o requisito do motor já pedia. As datas são gravadas em `AAAA-MM-DD`, que é dado, e exibidas em dd/mm/aaaa (seção 9.5 das convenções): a importação específica pode declarar `upload_display(label, value)`, e o motor usa o valor exibido quando existir.

**Datas e reimportação.** *Decisão do autor em 25/09/2026.*

| Envio | Semestre novo ou sem período | Semestre com período |
|---|---|---|
| Início e fim preenchidos | grava o período | **atualiza** o período, se diferente |
| Início e fim em branco | **recusado**: as duas datas são obrigatórias | **preserva** o período existente |
| Só uma das datas | **recusado** | **recusado** |

- As duas datas vão sempre juntas, e o fim é a data real informada: o sistema não infere o fim pelo código (`/1`, `/2`).
- A obrigatoriedade depende do semestre, então a validação conjunta (`clean_upload`) consulta o `Semester` do código informado: sem semestre ou sem período, as datas são obrigatórias. A consulta é leitura, feita no formulário, fora da execução.
- Datas em branco nunca apagam o período, assim como uma alocação ausente da planilha não é excluída.
- A ajuda dos campos diz que, num semestre com período, deixá-los em branco mantém o período atual.
- **Limitação registrada:** mudar o período numa reimportação muda as semanas e os meses mostrados, inclusive os anteriores, porque as ocorrências são calculadas do período atual (D4). É a mesma natureza da limitação de D10.

**Auditoria.** O resumo auditado da confirmação ganha o período informado (`inicio`, `fim`) nos metadados, ao lado do semestre, e o período anterior quando ele mudou (`inicio_anterior`, `fim_anterior`). Não há registro separado do semestre: a regra da Change de importação é auditar o resumo, e não cada entidade.

**O que acontece com o que já foi feito.**

- **Dados:** o período já definido pelo modal está em `Semester.start_date` e `end_date`, o mesmo lugar que a importação usa. **Não há migração de dados** nem de esquema: a migration `0002_semester_period` continua como está.
- **Código:** saem `SemesterPeriodView`, `SemesterPeriodForm`, a rota `semester_period`, os templates `semester_period*.html`, o botão "Definir período" da Grade e os testes do modal. `define_period` fica, sem auditoria própria.
- **Auditoria:** sai o recurso `SEMESTRE` do catálogo. Registros antigos com esse código, se houver, continuam no banco e aparecem com o código no lugar do rótulo.

**Sem período na Grade.** A regra continua: a semana típica, sem datas, sem o campo "Visualização", com o aviso. O aviso deixa de oferecer o botão e passa a dizer onde se define o período: "Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre." Para quem tem `ENSALAMENTO.IMPORTAR`, o botão "Ver importações" continua no topo da página.

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

### D8. Visão mensal: a Grade semanal expandida para o mês

*Revisto pelo autor em 25/09/2026, depois da primeira prévia.* A proposta anterior, de um mapa com uma tira de faixas e a contagem "N de M faixas ocupadas" por dia, foi **descartada**. A visão mensal é a **mesma Grade da visão semanal**, com mais colunas.

**Mesmo cálculo, sem estrutura paralela.** O mês chama `occupancy(space, primeiro_dia_util, ultimo_dia_util)`, a mesma função da semana, e monta a mesma estrutura: `Week` com uma `Day` por dia útil do mês, as mesmas `Row`, `Cell`, `Continued` e `Outside`, e as mesmas faixas do semestre nas linhas. `build_week` passa a receber a lista de datas, em vez de só a segunda-feira. Não existe `Month` nem outra estrutura para o mês, e nada é gravado.

**Forma.**

- As faixas de horário na lateral, fixas na rolagem horizontal, iguais às da semana.
- Uma coluna por dia útil do mês (segunda a sexta), com o número do dia e o dia da semana abreviado: `01 TER`, `02 QUA`. Sábado e domingo não aparecem, como na semana, porque o ensalamento só tem segunda a sexta.
- Uma linha mais forte antes de cada segunda-feira, separando as semanas.
- As células são as da semana: o card com a disciplina, a turma com o curso e os docentes, a cor da etapa, o bloco de faixas seguidas, o agrupamento "N turmas juntas" e "Choque: N turmas neste horário" (D9a).
- A faixa disponível fica visualmente vazia, com o nome acessível (D9). O dia fora do período é uma coluna com "Fora do semestre", sem células, como na semana.
- "Hoje": a coluna do dia atual marcada como na semana; o botão "Hoje" abre o mês atual e rola até essa coluna.
- A legenda das etapas, como na semana.
- Somente consulta: nenhum formulário, nenhum clique que crie, edite ou cancele ocupação.

**Quantidade de dias e responsividade.** Um mês tem de 20 a 23 dias úteis, e a Grade não cabe na tela. A solução é a **rolagem horizontal da própria Grade**, dentro do card, com a coluna de horários e a linha dos dias fixas (`position: sticky`), e não outra forma de visualização:

- cada coluna tem largura fixa (cerca de 150 px; 136 px abaixo de 640 px), suficiente para o card da semana com o texto um pouco menor;
- a área da Grade tem altura máxima e rola nos dois sentidos, para que a linha dos dias continue à vista;
- a página não rola na horizontal: só a área da Grade, que é uma região rotulada e focável pelo teclado;
- abaixo de 640 px continua sendo a Grade, com a mesma rolagem, e não a lista por dia da visão semanal;
- quem precisa ver a semana inteira sem rolagem usa a visão semanal, que continua existindo.

**Navegação e semestre.** URL `?visao=mes&semestre=2026/2&sala=1/13&mes=2026-10`. Padrão: o mês de hoje dentro do período, ou o primeiro ou o último mês dele; `mes` inválido cai no padrão, com 200. "Mês anterior", "Hoje" e "Próximo mês", desabilitados além dos meses que tocam o período. A troca entre semana e mês é o campo de seleção "Visualização", com as opções "Semana" e "Mês", junto do semestre e da sala, pelo componente `ui/components/select.html` e o mesmo gatilho htmx dos outros filtros; sem JavaScript, vale o botão "Mostrar". *Decisão do autor em 25/09/2026, no lugar das abas da primeira implementação.* O formulário envia a semana ou o mês mostrados em campos ocultos (`semana`, `mes`), e a view traduz a referência: da semana para o mês da segunda-feira dela; do mês para a semana de hoje, quando hoje está no mês, ou a do primeiro dia do mês no período. O campo só aparece quando o semestre tem período, porque sem ele não há mês. "Hoje" no mês é um link comum para `#hoje`, a coluna do dia atual, para que o navegador role a Grade até ela.

**Consulta.** O mês é consultado numa quantidade fixa de consultas, como a semana (D4). A página do mês tem cerca de quatro vezes as células da semana; o tempo de resposta é medido na implementação.

**Prévia.** `grade-mensal-previa.html`, estática, com a sala 1/13 da planilha de referência em setembro de 2026 (com "Hoje") e em agosto de 2026 (com dias fora do semestre). O choque de quinta-feira às 21:00 é ilustrativo, porque a sala 1/13 não tem choque na planilha.

**Decididos pelo autor em 25/09/2026:**

- **P1. Prévia aprovada.**
- **P4. Sala no card:** não aparece. O pedido cita a sala e "Sem sala" nas células. A Grade é de uma sala, escolhida no filtro, então todo card dela é daquela sala, e uma alocação sem sala não aparece em sala nenhuma (requisito de ocorrências). O card não repete a sala nem mostra "Sem sala", como na prévia.

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

### D9a. Turmas juntas e choque na Grade datada

*Decisão do autor em 25/09/2026.* O agrupamento da Grade da importação (D13 de `visualizar-grade-do-ensalamento`) volta à Grade do ensalamento confirmado. Quando mais de uma turma ocupa a sala na mesma faixa do mesmo dia, a célula agrupa os cards numa moldura só, com "N turmas juntas" (mesma disciplina e mesmos docentes, tom neutro, ícone `users`) ou "Choque: N turmas neste horário" (tom de aviso, ícone `triangle-alert`). Assim o segundo card não parece pertencer à faixa seguinte.

A classificação é uma propriedade de `Cell`, calculada das entradas da célula (`kind` e `group_count`), sem dado gravado e sem mudar o cálculo das ocorrências: vale para a semana típica e para a datada, e valerá para as ocorrências de outra fonte. O choque continua só sendo mostrado, sem recusa.

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
| `Entry`, `Cell`, `Continued`, `build_day` (bloco de faixas) | `Week` e `Day` (data, "Fora do semestre", estado) | `build_week` sobre uma lista de datas, para a semana e o mês |
| `GridFilterForm`, `current_semester_code`, `spaces_of`, `imported_semesters` | `space_week` passa a receber o intervalo e as ocorrências; `SpaceAllocationImport` ganha os campos próprios de início e fim | ganchos `clean_upload` e `upload_display` no motor de importação |
| Importação, auditoria da importação, permissões | `grid.html` e o parcial da célula | recurso `SEMESTRE` na auditoria |

## Risks / Trade-offs

- **Semestres sem período.** Até uma importação do semestre informar o período, a Grade fica na semana típica, com o aviso que diz onde informá-lo.
- **Período fora do plano.** A mudança de período não entra no plano das linhas nem na comparação da confirmação; é determinística, porque vem dos valores gravados, e aparece no resumo e na auditoria.
- **Reimportação muda o passado (D10).** Registrada; resolvida pela Change de versões.
- **Feriados aparecem como ocupados.** Sem calendário de dias sem aula, um feriado mostra as aulas do dia. Fica para D11.
- **Datas fora do período digitadas na URL.** Caem no padrão, sem erro.
- **Custo por requisição.** Três consultas e um laço em memória por intervalo; medido na implementação contra a planilha de referência.

## Migration Plan

Uma migration no `schedule`, acrescentando `start_date`, `end_date` e a restrição ao `Semester`, sem dados. A revisão de D3 não muda o esquema nem os dados: o período continua no semestre. Os semestres existentes ficam sem período e continuam funcionando na semana típica. A rota `ensalamento/` mantém o nome e os filtros atuais; `visao`, `semana` e `mes` são opcionais. Reverter é remover os campos: nenhuma outra tabela depende deles.

## Decisões confirmadas pelo autor

Em 25/09/2026:

| Questão | Decisão | Onde está |
|---|---|---|
| Histórico da reimportação | sem versionamento nesta Change; a `Allocation` é a regra vigente, a limitação fica registrada e a solução futura descrita | D10 |
| Faixa disponível | visualmente vazia; "Disponível" só para a tecnologia assistiva; distinta de erro e de ausência de dados | D9 |
| Reservas | a Grade não cria, não edita e não cancela reserva; as reservas entram depois como fonte de ocupação | D6, D12 |
| Recorrência futura | encerrar a regra atual e criar outra com nova vigência, sem materializar ocorrências | D10 |
| Visão mensal | a Grade semanal expandida para os dias úteis do mês, com rolagem horizontal; a tira de faixas e a contagem por dia foram descartadas | D8 |
| Turmas juntas e choque | agrupados na célula, como na Grade da importação | D9a |
| Troca entre semana e mês | campo de seleção "Visualização" junto dos filtros, e não abas | D8 |
| Prévia da Grade mensal e sala no card | prévia aprovada; o card não repete a sala nem mostra "Sem sala" | D8 |
| Onde se define o período | no envio da importação do semestre, e não na Grade; o modal "Definir período" sai | D3 |
| Datas do período | juntas; obrigatórias no semestre novo ou sem período; em branco preservam o período existente; uma só é recusada; o fim nunca é inferido | D3 |
| Auditoria do período | nos metadados do resumo da importação, com o anterior quando muda; sem o recurso `SEMESTRE` | D3 |
| Aviso da Grade sem período | "Período do semestre 2026/2 não definido. Informe o início e o fim na próxima importação do semestre." | D3 |

## Open Questions

Nenhuma.

## Conferência no navegador

Em 25/09/2026, com a planilha de referência importada no banco `visual_check` e o período de 05/08/2026 a 18/12/2026:

- **Visão semanal e modal do período** (o modal sai com a revisão de D3): sem rolagem horizontal em 360, 640, 1.024 e 1.280 px e com zoom de 200%; navegação entre semanas pelo htmx e sem JavaScript; foco no primeiro campo do modal, que fecha com Esc; a primeira semana mostra segunda e terça "Fora do semestre".
- **Tempo de resposta** da semana da sala 1/13: cerca de 40 ms depois da primeira carga.
- **Ajuste:** abaixo de 640 px, a faixa com mais de uma turma (turmas juntas) quebrava o segundo card para a coluna do horário. Os cards passaram a ficar num bloco próprio, com a altura do conteúdo. O defeito existia antes desta Change.
- **Turmas juntas:** na tabela, a faixa com duas turmas mostrava os dois cards empilhados na mesma célula, sem o agrupamento da Grade da importação, o que fazia o segundo card parecer estar na faixa seguinte. Corrigido por D9a, a pedido do autor.
- **Visão mensal**, com um choque ilustrativo acrescentado à sala 1/13 só no banco `visual_check` (quinta-feira, 21:00): a página não rola na horizontal em 360, 640, 1.024 e 1.280 px nem com zoom de 200%, e só a área da Grade rola; a coluna de horários fica fixa na rolagem horizontal e a linha dos dias na vertical; "Mês anterior" e "Próximo mês" funcionam pelo htmx e sem JavaScript, com "Mês anterior" desabilitado em agosto, que mostra 03/08 e 04/08 "Fora do semestre"; "Hoje" abre o mês atual e rola até a coluna de hoje; a troca Semana e Mês preserva o mês; turmas juntas e choque aparecem agrupados; a Grade não tem formulário nem ação de reserva.
- **Tempo de resposta** do mês da sala 1/13: cerca de 50 ms.
- **Choque real:** com o agrupamento, apareceu na sala 1/13 um choque da própria planilha, às quartas-feiras das 13:20 às 15:00 (Matérias primas alimentícias e Geometria euclidiana plana), que antes parecia estar na faixa das 15:20.
- **Observação:** "Hoje" é um link comum para `#hoje`, para que o navegador role a Grade até a coluna; por isso a página também rola até ela, e o cabeçalho do card sai de vista.
- **Período na importação** (revisão de D3), com a planilha importada pela tela: a primeira importação de `2026/2` sem datas é recusada, com o erro nos dois campos, que não dizem "(opcional)"; com as datas, a prévia e a importação concluída mostram 05/08/2026 e 18/12/2026, sem o formato `AAAA-MM-DD`; a Grade usa o período importado, com 03/08 e 04/08 "Fora do semestre", e não tem "Definir período"; a reimportação com as datas em branco mostra "Mantido" no resumo.
