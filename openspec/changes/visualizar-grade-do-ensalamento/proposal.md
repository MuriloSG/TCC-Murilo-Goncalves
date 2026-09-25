## Why

A prévia da importação de ensalamento mostra hoje uma tabela de linhas: cada atividade aparece como `Horário - Graduação!F3`, com o dia, a faixa, a turma e o texto cru da célula em colunas. Serve para achar um erro, mas não para ver como ficou o ensalamento. Quem trabalha com a planilha pensa em outra forma: um bloco por dia, as faixas de horário descendo pela lateral, as turmas lado a lado agrupadas sob o nome do curso, e em cada cruzamento a disciplina, o docente e a sala. Na tabela de linhas, essa forma se perde. Com 1.500 atividades, conferir se a turma do 4º período de Sistemas de Informação ficou com a segunda-feira certa exige filtrar e ler célula por célula.

Esta Change acrescenta à importação de ensalamento a **Grade**: a semana de uma sala, com as faixas de horário nas linhas e os dias nas colunas, e em cada faixa ocupada a disciplina, a turma com o curso e o docente. A Grade passa a ser a tela que abre primeiro. A tabela de linhas continua existindo como **Conferência**, numa segunda aba, para verificar erros, inconsistências e o detalhe de cada linha.

- **Grade:** entender visualmente como ficou o ensalamento de cada sala.
- **Conferência:** verificar se os dados estão corretos e encontrar problemas.

A investigação do código mostrou que tudo o que a Grade precisa já está gravado na prévia (design, seção "Como os dados da planilha chegam à prévia"). A Grade é uma leitura das linhas da importação, e não muda a forma como a planilha é lida, executada ou confirmada. O desenho foi aprovado pelo autor numa prévia estática com dados reais (`grade-previa.html`).

## What Changes

- **Aba Grade na importação de ensalamento**, aberta por padrão no detalhe da importação, com um filtro só, a sala, e a primeira sala da lista de salas da planilha como padrão. A Grade mostra a semana inteira da sala, com o dia atual marcado, o semestre, uma faixa de situação com as faixas ocupadas e disponíveis, e a legenda (D3).
- **Card da atividade** com a disciplina, a turma com o curso e o docente, e a cor da etapa (graduação ou ensino médio) na barra lateral. A mesma atividade em faixas seguidas vira um card só, que não atravessa intervalo. Os intervalos não aparecem (D5, D6, D14).
- **Turmas juntas e choque**: quando mais de uma turma ocupa a sala na mesma faixa, a célula as agrupa como turmas juntas (mesma disciplina e mesmos docentes) ou como choque. O choque é mostrado, e não recusado (D13).
- **Erros na Grade, sem virar uma segunda tela de erros**: o card com erro tem ícone, texto e o texto da planilha, e leva à Conferência filtrada nas linhas dele. A faixa de situação conta os erros da sala e os que ficaram fora da Grade (D7).
- **Aba Conferência**: a tela atual da prévia, com o select de recortes, passa para uma rota própria, e ganha o filtro pelo número da linha (D8, D9).
- **Estrutura da Grade independente da origem**, para que a mesma tela possa mostrar depois o ensalamento confirmado a partir de `Allocation` (D4, D11).
- **Motor de importação com abas**: `ImportScreens` passa a aceitar abas no detalhe, e o cabeçalho do detalhe vira um parcial compartilhado. A importação de usuários não declara abas e continua igual (D8).
- **Tokens de cor da etapa** no `app.css`, com os pares de contraste (D14).

### Fora do escopo

- Indicar nos cards o que a reimportação vai fazer (novo, alterado, sem alteração). A estrutura já carrega a ação de cada atividade (D10).
- A Grade do ensalamento confirmado do semestre, a partir de `Allocation`, e qualquer rota fora da importação (D11).
- Visão por turma e por docente.
- Recusar a importação ou a confirmação por causa de choque.
- Edição de qualquer dado pela Grade.
- Qualquer mudança na leitura da planilha, na execução das linhas, no plano, na confirmação, nos models e nas migrations.

## Capabilities

### Modified Capabilities

- `ensalamento`: a importação de ensalamento ganha a Grade por sala, aberta por padrão no detalhe da importação, com as turmas juntas, o choque e os erros indicados nas células.
- `importacao-planilhas`: o detalhe da importação passa a poder ter abas declaradas pela importação específica, e a lista de linhas passa a aceitar o filtro pelo número da linha.

## Impact

- **`schedule/`**: `timetable.py` (novo, a estrutura da Grade e a montagem a partir das linhas da importação), `views.py` (a view da Grade), `urls.py` (a rota da Conferência), `templates/schedule/` (a Grade e as células) e `tests/`.
- **`imports/`**: `views.py` (abas em `ImportScreens`, filtro por número da linha, rota da Conferência configurável) e `templates/imports/` (o cabeçalho do detalhe como parcial e a navegação entre abas).
- **`ui/`**: os estilos da Grade e das abas e os tokens da etapa no `app.css`, os pares de contraste em `ui/contrast.py` e os ícones do Lucide que ainda não estejam em `ui/templates/ui/icons/`.
- **Sem impacto**: `imports/execution.py`, `imports/models.py`, `imports/workbook.py`, `schedule/imports.py`, `schedule/sheets.py`, `schedule/activities.py`, `schedule/models.py`, as migrations, a auditoria, as permissões e a importação de usuários.

## Alinhamento com o TCC

- **P7:** a Grade responde à pergunta do campus sobre a sala, com os termos do domínio (curso, turma, docente, sala, faixa de horário), e mostra o choque que a planilha marca com `[CHOQUE]`.
- **P6:** a Grade confirmada, numa Change futura, consulta `Allocation` pelo índice de semestre, espaço, dia e faixa.
- **P8:** a Grade usa os tokens e os componentes do app `ui`, sem cores de enfeite, e o estado de erro vem com ícone e texto.
- **P2:** a montagem da Grade é uma função do app `schedule`, testável sem a view, e os templates só apresentam a estrutura.
- **P5 e RNF01:** as duas abas exigem `ENSALAMENTO.IMPORTAR`, como as demais rotas da importação.
