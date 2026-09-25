## Context

### Como os dados da planilha chegam à prévia

1. `WorkbookSource` (`imports/workbook.py`) abre o XLSX sem recalcular fórmulas e entrega o arquivo à definição.
2. `SpaceAllocationImport.read_cells` (`schedule/imports.py`) produz as linhas: primeiro uma por valor das listas de salas e de docentes da aba `Validação de Dados`, depois uma por atividade lida das células das duas abas de horário (`schedule/sheets.py`). Uma célula com duas atividades separadas por ` / ` vira duas linhas, com `#1` e `#2` na referência.
3. `ImportManager.preview` (`imports/models.py`) executa todas as linhas dentro de um savepoint e **desfaz** tudo. Só ficam gravados o `Import` e um `ImportRow` por linha, com os valores lidos e o plano.
4. A confirmação reexecuta as linhas a partir dos valores gravados, sem o arquivo.

A consequência para a Grade: **durante a prévia não existe nenhum `Allocation`, `Course`, `ClassGroup` nem `TimeSlot` no banco** para essa importação. A Grade precisa ser montada a partir dos `ImportRow`.

### O que representa cada atividade

Cada atividade é um `ImportRow` com `values` (JSON) nas colunas lógicas da definição:

| Coluna | Exemplo real | Observação |
|---|---|---|
| `Semestre` | `2026/1` | campo do envio, igual em todas as linhas |
| `Tipo` | `ATIVIDADE` | `SALA` e `DOCENTE` nas linhas dos catálogos |
| `Célula` | `Horário - Graduação!F3`, `...!AB40#2` | aba, coluna, linha e ordinal da atividade na célula |
| `Dia` | `SEGUNDA `, `TERÇA-FEIRA` | texto cru do bloco de dia |
| `Horário` | `07:20 - 08:10` | texto cru da faixa |
| `Turma` | `4º PERÍODO\nSist. de Informação` | cabeçalho cru da coluna: rótulo e nome curto do curso |
| `Curso` | `BACHARELADO EM SISTEMAS DE INFORMAÇÃO` | título da linha 1, vazio quando a planilha não o traz |
| `Atividade` | `CÁLCULO III (Viviane) (2/6)` | texto cru da atividade |

E o plano da linha: `action` (`create`, `update`, `unchanged` ou vazio com erro), `changes` (espaço e docentes, antes e depois), `warnings` (`curso_sem_titulo`) e `errors` (lista de `{column, code, message}`).

### Como dia, horário, turma, disciplina, docente e sala são representados

Todos são **texto cru** nos valores. A interpretação é feita pelas mesmas funções que a execução usa, todas puras e sem banco:

| Informação | Função | Resultado |
|---|---|---|
| Dia | `schedule.sheets.parse_weekday` | código `Weekday` (`SEGUNDA` a `SEXTA`) |
| Faixa | `schedule.sheets.parse_slot` | `(time, time)` |
| Turma e curso | `schedule.sheets.split_header` e o valor de `Curso` | rótulo normalizado e nome do curso (título ou nome curto) |
| Etapa | a aba da referência, por `SHEET_LAYOUTS` | `GRADUACAO` ou `ENSINO_MEDIO` |
| Disciplina, docentes e sala | `schedule.activities.resolve(texto, catálogo)` | `Activity` com `subject_name`, `teacher_names`, `space_name` e `problems` |
| Catálogo | `Catalog.build` com os nomes das linhas `DOCENTE` e `SALA` | o mesmo que `SpaceAllocationImport.lock` monta |
| Posição na planilha | a coluna e a linha da referência em `Célula` | ordem das turmas e dos cursos como na planilha |

Como a execução chegou ao plano com essas mesmas funções sobre esses mesmos valores, a Grade mostra exatamente o que a prévia executou.

### Como os erros são guardados e mostrados hoje

- **Erros do arquivo** (`Import.file_errors`): a estrutura da grade não foi encontrada. Nesse caso não há linhas, e a tela mostra só os alertas.
- **Erros da linha** (`ImportRow.errors`): `sala_desconhecida`, `docente_desconhecido`, `sem_disciplina`, `sem_parenteses`, `duplicate` e os de validação do model. Aparecem na coluna "Resultado" da tabela, e o select "Com erro" filtra as linhas.
- **Avisos da linha** (`ImportRow.warnings`): só `curso_sem_titulo`, que vale para a coluna de turma inteira.
- Na importação real de `sources/planilha_example.xlsx` são 147 linhas com erro em 1.706.

### O que a planilha real mostra

Medido em `sources/planilha_example.xlsx`:

| | `Horário - Graduação` | `Horário - Ensino Médio` |
|---|---|---|
| Cursos (grupos de colunas sob um título) | 9 | 5 |
| Turmas por curso | 4 ou 5 | 6, e 1 em Química e Meio Ambiente |
| Faixas com atividade | 15, das 07:20 às 22:40 | 9, das 07:20 às 17:00 |
| Células de atividade | 767 | 707 |
| Células iguais à da faixa anterior, na mesma turma e dia | 389 (51%) | 276 (39%) |
| Tamanho do texto da célula (mediana e máximo) | 46 e 228 caracteres | 32 e 84 caracteres |

Na planilha, a unidade visual é o **curso dentro do bloco de dia**: o título do curso sobre 4 a 6 colunas de turma, com uma coluna estreita vazia separando um curso do seguinte. Cerca de metade das células repete a aula da faixa anterior, porque as aulas duram duas ou três faixas seguidas.

### Limitações que afetam a Grade

1. **Não há objetos de domínio na prévia.** A Grade é montada dos valores das linhas, e não de `Allocation`. É isso que D4 resolve.
2. **Células vazias, linhas de intervalo e colunas sem nenhuma atividade não são gravadas.** A leitura só produz linha para célula preenchida. Uma turma sem nenhuma atividade no arquivo não aparece na Grade, e uma faixa sem atividade em nenhuma turma da etapa também não. Os intervalos são deduzidos (D6).
3. **A ordem da planilha só existe na referência da célula.** A coluna da referência dá a ordem das turmas e dos cursos, e a linha dá a ordem dos dias. `Allocation` não guarda essa ordem (D11).
4. **O nome do curso segue a regra da execução.** A coluna sem título na linha 1 usa o nome curto do cabeçalho, e duas grafias diferentes do nome curto viram dois cursos. A Grade mostra os cursos como a execução os resolve, e isso torna a divergência visível, em vez de escondê-la. Na planilha de referência isso acontece de verdade: o título de Engenharia de Alimentos é a fórmula `=UPPER(E:E)`, sem valor salvo no arquivo, e os cabeçalhos trazem `Eng. Alimento` numa coluna e `Eng. Alimentos` nas outras, e a prévia estática mostra os dois cursos lado a lado.
5. **Importação recusada não tem Grade.** Com erro do arquivo não há linhas, e a aba Grade mostra só os alertas do arquivo.
6. **A atividade com erro pode não ter disciplina ou docente reconhecidos.** `resolve` devolve o que reconheceu mesmo com problema, e o dia, a faixa e a turma não dependem do texto da atividade. Toda linha de atividade tem lugar na Grade, e a célula mostra o texto cru quando a disciplina não foi reconhecida.

### Referência visual

A referência da lógica é a própria planilha de ensalamento (`sources/planilha_example.xlsx`), e a referência visual é a imagem de uma grade semanal enviada pelo autor na segunda rodada da prévia estática. As duas foram adaptadas à `previa.html` da Change `definir-identidade-visual` e aos tokens do app `ui`, conforme a seção 9.8 das convenções. A prévia aprovada é `grade-previa.html`, nesta pasta. O que foi mantido, adaptado e retirado está em D12.

## Goals / Non-Goals

**Goals**

- Ver, para cada sala, a semana inteira do ensalamento importado: o que ocupa a sala em cada faixa de cada dia e o que está disponível.
- Mostrar, na própria Grade, as faixas em que mais de uma turma ocupa a mesma sala, separando as turmas juntas do choque.
- Achar o erro na Grade e resolvê-lo na Conferência, com um clique entre as duas.
- Manter a estrutura da Grade independente da origem, para servir depois ao ensalamento confirmado.

**Non-Goals**

- Mudar a leitura, a execução, o plano ou a confirmação da importação.
- Impedir a confirmação por causa de choque. O choque é mostrado, e não recusado (D13).
- Editar dados pela Grade.
- Visão por turma ou por docente.

## Decisions

### D1. A Grade é uma leitura das linhas da importação

A Grade é montada a cada requisição a partir dos `ImportRow` da importação, com as funções de D2 e sem gravar nada. Nenhum campo novo em `ImportRow` e nenhuma migration.

**Alternativa descartada:** gravar na prévia uma estrutura pronta da Grade. Duplicaria a interpretação que já está nas funções de leitura, e teria de ser mantida junto do plano.

**Custo:** uma consulta pelas linhas da importação (1.715 na planilha corrigida) e uma chamada de `resolve` por atividade. Os testes fixam a quantidade de consultas da view.

### D2. A interpretação reutiliza as funções da execução

A montagem usa `parse_weekday`, `parse_slot`, `split_header`, `strip_parentheses`, `Catalog.build` e `resolve`, as mesmas que `SpaceAllocationImport` usa, e a mesma regra de curso (título da linha 1, senão o nome curto do cabeçalho). Nenhuma função nova de interpretação de texto é criada.

### D3. Um único filtro: a sala

A Grade tem um filtro só, a **sala**, num select com todas as salas da lista de salas da aba `Validação de Dados`, na ordem da planilha. O padrão é a **primeira sala da lista**. A escolha vai na URL (`?sala=1/13`), pelo nome, para que o mesmo link sirva à Grade do ensalamento confirmado (D11). Uma sala que não existe na lista cai no padrão, sem erro. A troca de sala atualiza a Grade pelo htmx, com `hx-push-url`, e sem JavaScript o formulário GET tem o botão "Mostrar".

A Grade mostra a **semana inteira** da sala: as faixas de horário nas linhas, na ordem do início, e os dias de segunda a sexta nas colunas. A sala sem nenhuma atividade mostra a grade vazia e a faixa de situação com todas as faixas disponíveis.

As faixas das linhas são a união das faixas com atividade nas duas abas de horário, ordenadas pelo início. Toda sala mostra as mesmas linhas, para que duas salas possam ser comparadas.

**Por que a sala:** a pergunta que o autor quer responder na Grade é "como está a situação desta sala". A turma e o curso aparecem dentro de cada card.

**Abaixo de 640 px:** os dias ficam um abaixo do outro, com o nome do dia como título, e cada dia lista só as faixas com atividade. O dia sem atividade mostra "Sala disponível o dia todo.".

### D4. A estrutura da Grade não depende da origem

`schedule/timetable.py` define a estrutura em dataclasses, sem referência a `ImportRow` nem a `Allocation`:

```
RoomWeek(space, spaces, slots, days, occupied, available, error_count)
└── days: [Day(weekday, label, is_today, cells)]
    └── cells: {slot: Cell(entries, span, kind) | Continued}
        └── Entry(subject, class_group, course, stage, teachers,
                  raw_text, state, action, lines)
```

- `Cell.kind`: `single`, `joint` (turmas juntas) ou `clash` (choque), conforme D13.
- `Entry.state`: `ok` ou `error`. `raw_text` é o texto da planilha, mostrado no lugar da leitura quando há erro (D7).
- `Entry.action`: a ação do plano, guardada e ainda não exibida (D10).
- `Entry.lines`: os números das linhas da importação, para o link da Conferência.
- `Cell.span`: quantas faixas o bloco ocupa (D5). A faixa coberta por um bloco de cima é `Continued`.

A montagem a partir da importação é `room_week_from_import(importation, space_name, today)`. Os templates recebem só `RoomWeek`.

### D5. Faixas seguidas com as mesmas atividades viram um bloco

No mesmo dia, as faixas consecutivas da sala com as mesmas entradas (mesmo texto de atividade, mesma turma e mesmo estado) viram uma célula que ocupa todas elas (`rowspan`). O bloco não atravessa um intervalo (D6). Cada faixa continua sendo uma alocação, conforme D9 da Change `importar-ensalamento-da-planilha`: o bloco é só apresentação.

### D6. Intervalos não aparecem na Grade

A Grade não mostra linhas de intervalo nem de almoço, a pedido do autor. As faixas seguem uma abaixo da outra. O intervalo só é usado como regra: quando o fim de uma faixa é anterior ao início da seguinte, um bloco não continua de uma para a outra, e as duas aparecem como cards separados.

### D7. Erros na Grade, com a Grade limpa

| Onde | Como aparece |
|---|---|
| Card com erro | fundo e barra do estado de erro, ícone `circle-x` e o texto "Com erro", o texto da planilha no lugar da leitura, e o card é um link para a Conferência nas linhas dele. A dica no hover e no foco traz a primeira mensagem |
| Faixa de situação | "Prévia com erros." e a quantidade de atividades com erro nesta sala, com o link "Ver na conferência" |
| Atividade com erro sem sala reconhecida | não tem lugar na Grade de nenhuma sala; a faixa de situação informa quantas atividades com erro ficaram fora da Grade, com o link para a Conferência |
| Erros das listas de salas e de docentes | contados junto das atividades fora da Grade |

O card com erro mostra o texto da planilha, e não a leitura parcial: a prévia estática mostrou que a leitura de uma atividade com erro engana, com o docente dentro do nome da disciplina ou "Sem sala" onde havia sala.

### D8. Abas Grade e Conferência pelo motor de importação

O detalhe da importação ganha abas declaradas em `ImportScreens`:

- `ImportScreens.tabs`: sequência de `(rota, rótulo, ícone)`, vazia por padrão. Com abas, o detalhe mostra a navegação entre elas, com `aria-current` na aba atual.
- `ImportScreens.review_route`: a rota da tabela de linhas, `detail` por padrão.
- O título, as ações (confirmar, descartar, enviar corrigido), os alertas, os erros do arquivo e o resumo saem de `imports/detail.html` para `imports/partials/detail_head.html`, incluído pelas duas abas.

No ensalamento:

| Rota | Nome | View | Aba |
|---|---|---|---|
| `ensalamento/importacoes/<pk>/` | `space_allocation_import_detail` | `SpaceAllocationImportGridView` | Grade |
| `ensalamento/importacoes/<pk>/conferencia/` | `space_allocation_import_review` | `SpaceAllocationImportDetailView` | Conferência |

A Grade fica no nome `_detail`, para que os redirecionamentos depois do envio, da confirmação e do descarte e os links do histórico abram a Grade sem mudança. A Grade é a aba padrão também numa importação `COM_ERROS`.

### D9. Filtro da Conferência pelo número da linha

A tabela de linhas passa a aceitar `?numero=12&numero=13`, que mostra só as linhas com esses números, combinado com o recorte `linhas`. É o que o link de um card com erro usa. O filtro é do motor, porque o número da linha existe em toda importação. Um número que não é inteiro é descartado, sem 404. Com o filtro ativo, a tabela oferece o link "Mostrar todas as linhas".

### D10. Reimportação: a ação fica na estrutura, e não na tela

Cada `Entry` guarda a `action` do plano (`create`, `update`, `unchanged`). Mostrar "Novo", "Alterado" e "Sem alteração" nos cards fica para uma Change futura, que precisa só de um selo no card e de um filtro "Só o que muda". Nesta Change a ação não aparece.

### D11. A mesma Grade para o ensalamento confirmado, depois

Uma Change futura pode acrescentar `room_week_from_allocations(semester, space, today)`, que monta o mesmo `RoomWeek` a partir de `Allocation`, filtrando por `space`, com `ClassGroup.label`, `Course.name` e `Course.stage`, `weekday`, `TimeSlot`, `Subject.name` e os `Teacher`, e `state` sempre `ok`. Os templates desta Change servem sem mudança. A lista de salas vem de `Space`, pelo nome, porque a ordem da planilha não é gravada. O índice de `Allocation` por semestre, espaço, dia e faixa, criado na Change `importar-ensalamento-da-planilha`, atende essa consulta.

### D12. Da planilha e da imagem de referência para a interface

| Origem | Na Grade | Motivo |
|---|---|---|
| Lista de salas de `Validação de Dados` | opções do select de sala, na mesma ordem | D3 |
| Coluna `B` com a faixa | primeira coluna, fixa, com início e fim | mantido |
| Blocos de dia empilhados | dias nas colunas, a semana de uma sala numa tela | imagem de referência |
| `INTERVALO` e `ALMOÇO` | não aparecem | D6 |
| Texto da célula `Disciplina (Docente) (Sala)` | card com a disciplina em negrito, a turma com o curso (ícone `users`) e o docente (ícone `user-round`), cada um na sua linha | a sala já é o filtro |
| Nome do curso em caixa alta (`INFORMÁTICA`) | em caixa de frase no card (`Informática`) | legibilidade; o dado gravado não muda |
| Aula repetida em faixas seguidas | um card que ocupa as faixas | D5 |
| `[CHOQUE]` da aba `Ensalamento - Geral` | célula "Choque" ou "Turmas juntas" | D13 |
| Dia atual na imagem, com "Hoje" | coluna do dia atual com "Hoje" e fundo suave | imagem de referência |
| Datas sob os dias, na imagem | não usadas | a alocação é semanal e recorrente, sem data |
| "Grade publicada" e horário de atualização, na imagem | faixa de situação: situação da prévia e faixas ocupadas e disponíveis | o fato que existe nesta tela |
| "Período atual", na imagem | semestre da importação, só leitura | a importação é de um semestre |
| Cor do card por área, na imagem | barra lateral pela etapa, com legenda | D14 |
| "Arraste horizontalmente", na imagem | não usado | a semana cabe na largura; abaixo de 640 px os dias empilham |
| Cor de fundo por curso do ensino médio | não usada | seções 9.6 e 9.7 das convenções |
| Célula vazia | vazia, com "Disponível" só para o leitor de tela | decisão do autor; exceção registrada na seção 9.2 |

### D13. Turmas juntas e choque

Quando mais de uma turma ocupa a sala na mesma faixa do mesmo dia:

- **Turmas juntas**: todas têm a mesma disciplina (sem diferenciar maiúsculas de minúsculas) e os mesmos docentes. É a aula compartilhada, como Cálculo Diferencial e Integral III para a Licenciatura em Física e a Licenciatura em Matemática. A célula agrupa os cards sob "N turmas juntas", no tom neutro, com o ícone `users`.
- **Choque**: as disciplinas ou os docentes diferem. A célula agrupa os cards sob "Choque: N turmas neste horário", no tom de aviso, com o ícone `triangle-alert`.

A faixa de situação informa quantas faixas da semana têm choque nesta sala, e o select de sala marca as salas com choque ("1/11, com choque"). Na planilha corrigida, 9 salas têm choque.

O choque **não** é erro da importação: não entra nos erros das linhas, não impede a confirmação e não altera o plano. A Change `importar-ensalamento-da-planilha` decidiu que a alocação não é única por espaço, dia e faixa (D8 daquela Change), e isso continua valendo. A Grade só torna o choque visível, como a aba `Ensalamento - Geral` faz na planilha com `[CHOQUE]`.

### D14. Cor pela etapa

A barra lateral e o fundo do card indicam a etapa da turma: graduação e ensino médio. É a única cor da Grade além dos estados (erro, aviso e neutro) e da marca, e tem legenda no rodapé. A cor não é o único sinal: a turma e o curso estão escritos no card.

Os tokens novos, com os pares de contraste em `ui/contrast.py`:

| Token | Valor da prévia | Uso |
|---|---|---|
| `--color-stage-undergraduate-bar` | `#198F31` | barra do card da graduação |
| `--color-stage-undergraduate-bg` | `#EFFBEF` | fundo do card da graduação |
| `--color-stage-secondary-bar` | `#4F7FA8` | barra do card do ensino médio |
| `--color-stage-secondary-bg` | `#EEF3F8` | fundo do card do ensino médio |

O texto do card sobre os dois fundos usa `--color-text` e `--color-text-muted`, e os pares entram no teste de contraste.

## Risks / Trade-offs

- **Montagem a cada requisição.** A Grade de uma sala interpreta todas as atividades da importação para saber quais são da sala. Com o limite de 5.000 linhas da importação, continua na ordem de milissegundos. Se a medida mostrar lentidão, a montagem pode filtrar pelo texto da sala antes de interpretar.
- **Atividade com erro sem sala.** Ela não aparece em nenhuma sala. A faixa de situação conta essas atividades e leva à Conferência.
- **Choque sem recusa.** Uma importação com choque pode ser confirmada. É a decisão da Change anterior (D8 dela), e a Grade só informa.
- **Tokens de cor novos.** A cor pela etapa acrescenta quatro tokens à escala fechada, cada um com a sua função e o seu par de contraste.

## Migration Plan

Nenhuma migration. A rota da Conferência é nova, e a rota do detalhe continua com o mesmo nome e o mesmo caminho, agora com a Grade. Links antigos para `?linhas=...` no detalhe passam a abrir a Grade, que mostra a aba Conferência.

## Decisões confirmadas pelo autor

- **Célula vazia:** visualmente vazia, como na planilha, porque o vazio é o próprio sinal de faixa livre. "Disponível" existe só para o leitor de tela, e a exceção é registrada na seção 9.2 das convenções.
- **Importação com erros:** a Grade continua sendo a aba padrão, também em `COM_ERROS`, e a indicação de erro leva à Conferência.
- **Filtro:** um só, a sala, com a primeira sala da lista como padrão, e a semana inteira na tela (2ª rodada da prévia, com a imagem de referência do autor). As rodadas anteriores, por etapa, curso e dia e depois por turma, foram substituídas.
- **Intervalos:** não aparecem (3ª rodada da prévia).
- **Choque e turmas juntas:** fazem parte do escopo, como visualização, sem recusa (D13).
- **Cor pela etapa:** aprovada com os tokens de D14.
- **Ordem do trabalho:** a prévia estática `grade-previa.html` foi aprovada antes dos templates e do código.

### D15. A Grade é a entrada do módulo e lê o ensalamento confirmado

Pedido do autor depois da primeira versão: o item "Ensalamento" do menu abre direto a Grade (`ensalamento/`, rota `space_allocation_grid`), e a Grade sai do detalhe da importação.

- A Grade lê `Allocation`, e não as linhas de uma importação, como D11 previa. Por isso não há card com erro nem link para a Conferência: o que não foi confirmado não aparece.
- Dois filtros na URL: `semestre` e `sala`. O semestre padrão é o atual, calculado pela data (janeiro a junho é `/1`, julho a dezembro é `/2`), e as opções são ele e os semestres com alocação confirmada. O semestre atual sem importação mostra "Nenhum ensalamento importado no semestre 2026/2.". A sala padrão é a primeira do semestre pelo nome, porque a ordem da planilha não é gravada.
- As linhas são as faixas com aula no semestre, iguais para toda sala. O card mostra a disciplina, a turma com o curso e os docentes.
- O botão "Ver importações" leva à lista das importações. O detalhe da importação volta a ser só a tabela de linhas, sem abas.
- A permissão passou a ser `ENSALAMENTO.VISUALIZAR` (D16).

### D16. Consulta separada, exclusão de importação e resumo recolhido

Pedidos do autor depois de D15:

- **`ENSALAMENTO.VISUALIZAR`** protege a grade; `ENSALAMENTO.IMPORTAR` fica só com as telas da importação. O menu leva à grade ou, para quem só importa, à lista de importações. No caminho de navegação das importações, a seção só é link quando o usuário pode abrir a tela dela (`ImportScreens.section_permission`), o que vale também para "Usuários" na importação de usuários.
- **Exclusão de importação no motor.** `Import.remove()` exclui uma importação `DESCARTADA` ou `COM_ERROS` com as linhas, numa transação com trava, e grava a auditoria `EXCLUIR` antes, porque a importação deixa de existir. A importação específica liga a exclusão declarando `delete_permission`; as duas existentes declaram `ENSALAMENTO.EXCLUIR_IMPORTACAO` e `USUARIO.EXCLUIR_IMPORTACAO`. Uma importação `CONCLUIDA` não é excluída, porque o histórico dela explica dados que continuam no domínio.
- As três permissões entram numa só migration (`accounts/0008_space_allocation_permissions`), concedidas ao `ADMINISTRADOR`.
- **Resumo recolhido.** O resumo do detalhe virou um `<details>` com a situação e o resultado na linha fechada, e a mesma animação dos grupos de permissões. A grade antiga de duas colunas com bordas desencontrava com número ímpar de campos.
- **Máscara do semestre.** O campo "Semestre" do envio aceita só números e põe a barra (`2026/1`), com o termo limitado a 1 ou 2. A reimportação de um semestre já importado continua permitida.
