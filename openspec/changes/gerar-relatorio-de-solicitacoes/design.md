## Context

O `BookingRequest` guarda a situação (pendente, aprovada, rejeitada, alternativa sugerida, alternativa recusada), a data de criação (`created_at`), a da decisão (`decided_at`), a da resposta à alternativa (`responded_at`), o motivo da rejeição e os campos da alternativa (`suggested_*`). O vínculo acadêmico (`teaching_assignment`) leva ao curso e à etapa, e é vazio nas solicitações anteriores à Change `solicitar-agendamento-com-vinculo-academico`.

O app `reports`, a permissão `RELATORIO.VISUALIZAR` e o grupo "Relatórios" do menu existem desde a Change `gerar-mapa-de-calor-dos-espacos`. O projeto não tem biblioteca de gráficos, e os templates não aceitam `style=` nem valores arbitrários (seção 9.9 das convenções).

## Goals / Non-Goals

**Goals:**

- Mostrar a demanda por agendamento no semestre e como ela foi atendida, numa tela.
- Ter um padrão de gráfico reaproveitável pelos próximos relatórios, sem dependência nova.

**Non-Goals:**

- Exportação, intervalo de datas livre, ranking de pessoas e filtros novos na lista de análise.

## Decisions

### D1. Recorte do período

Uma solicitação pertence ao semestre pela data de uso (`date`) dentro do período do semestre, e não pela data de criação. Assim o relatório fala do mesmo período que o mapa de calor e que a Grade. Semestre sem período (`start_date` vazio) mostra o aviso do painel e não calcula o relatório.

### D2. Indicadores

- **Solicitações:** total no período, com "N criadas em nome de outro usuário" quando houver (`created_by` preenchido).
- **Taxa de aprovação:** aprovadas sobre decididas, com os valores absolutos ("72%" com "36 de 50 decididas"). Decididas são as aprovadas, as rejeitadas e as de alternativa recusada. A aprovada depois de aceitar uma alternativa conta como aprovada.
- **Tempo mediano até a decisão:** mediana de `decided_at - created_at` das solicitações com decisão, em tempo corrido, escrita como "3 horas" ou "1 dia e 4 horas". A mediana, e não a média, para que uma solicitação esquecida não distorça o valor. Sem decisão no período, o texto é "Nenhuma solicitação decidida".
- **Pendentes:** as pendentes e as de alternativa sugerida, com "a mais antiga há N dias" e o botão "Analisar" (`btn-secondary btn-go`) para a lista de análise.

### D3. Gráfico "Solicitações por semana"

- **Forma:** colunas, uma por semana do período do semestre (de segunda a domingo; a Semana 1 contém `start_date`). É uma série só, e o título a nomeia, sem legenda. A divisão por situação fica na dica, e não em colunas empilhadas, para não exigir cinco cores categóricas.
- **Desenho:** SVG gerado no servidor. `reports/charts.py` calcula a escala do eixo (passos inteiros, de 1, 2, 5 ou 10 vezes a potência de dez, com no máximo cinco linhas de grade) e a geometria de cada coluna em unidades do `viewBox`. O template só escreve `<rect>`, `<line>` e `<text>` com esses números, que são atributos SVG e não `style=`. O SVG ocupa a largura do cartão (`width="100%"` com `preserveAspectRatio="none"` só no grupo das colunas; os textos ficam fora dele para não distorcer).
- **Marcas:** coluna com 4 px de raio no topo e base reta no eixo, 2 px de folga entre colunas, linhas de grade recessivas (`--color-divider`), rótulos dos eixos em `--color-text-muted`. Semana sem solicitação não desenha coluna. Os rótulos do eixo X são "S1", "S2"..., e acima de 12 semanas aparecem só os ímpares.
- **Dica:** cada coluna é um `<rect>` com `tabindex="0"`, `role="img"` e `aria-label` completo ("Semana 5, de 01/09/2026 a 07/09/2026: 12 solicitações, 8 aprovadas, 2 rejeitadas, 2 pendentes"). O `ui/static/ui/js/chart.js` mostra no hover e no foco uma dica com o mesmo visual do `hint.html`, com a área de acerto da largura da semana inteira, e não só da coluna.
- **Tabela:** abaixo do gráfico, um `<details>` "Mostrar tabela" com a `data-table` das semanas (semana, período, total e uma coluna por situação). Sem JavaScript, a dica não aparece e a tabela é o caminho para os números.

### D4. Cor do gráfico

Uma série, uma cor: o token `--color-chart-bar` (`--palette-green-700`, o verde de ação, que passou no validador de paleta com contraste acima de 3:1 sobre a superfície) e `--color-chart-bar-hover` (`--palette-green-800`) no hover e no foco. Os pares entram no `ui/contrast.py` contra `--color-surface`, nos dois temas, como os tons do mapa de calor. Os textos do gráfico usam os tokens de texto, nunca a cor da série.

### D5. Situação das solicitações

Lista com a `status_badge` de cada situação (ícone e texto, nunca só cor), a contagem e o percentual sobre o total. Abaixo, "Alternativas sugeridas": quantas receberam alternativa (algum `suggested_*` preenchido), quantas foram aceitas (aprovadas com `responded_at`), recusadas e aguardando resposta. Sem gráfico de pizza nem barra empilhada: são poucas linhas, e a tabela é mais legível.

### D6. Espaços mais solicitados

`data-table` com os dez espaços de maior total no período: espaço, total, aprovadas, rejeitadas e taxa de rejeição. A célula do total leva o componente `meter`: um SVG de barra horizontal (`viewBox="0 0 100 8"`, largura proporcional ao maior total) seguido do número. Abaixo de 640 px, a linha vira bloco de rótulo e valor, como as demais tabelas. A linha tem o botão só com ícone "Abrir na Agenda", para a Grade da Agenda filtrada pelo espaço.

### D7. Rejeições recentes

As dez rejeições mais recentes do período, por `decided_at`: data de uso, espaço, solicitante, motivo e o botão só com ícone "Ver solicitação" para `agenda_review_detail`, que registra a leitura na auditoria. Estado vazio: "Nenhuma solicitação rejeitada no período."

### D8. Filtros

`RequestsFilterForm` declara `semestre`, `etapa`, `curso` e `espacos` (múltiplo), todos renderizados com `ui/components/select.html`, como no `HeatmapFilterForm`. Um valor que não é opção é ignorado e vale o padrão. Etapa e curso usam o vínculo acadêmico: com um dos dois escolhido, as solicitações sem vínculo ficam de fora, e a ajuda do campo avisa isso. O formulário e o do mapa compartilham a montagem das opções por uma função em `reports/forms.py`, sem classe `*Mixin`.

### D9. Cálculo

`reports/requests.py` faz uma consulta das solicitações do recorte com `values()` dos campos usados e agrega em Python: contagens por situação e por semana, a mediana (`statistics.median`), o ranking de espaços e as rejeições recentes. O volume esperado é de centenas por semestre, e uma consulta só evita uma por bloco.

### D10. Acesso

`RequestsReportView` declara `permission_required = REPORT_VIEW` e exige também `AGENDA.ANALISAR` pelos dados, com a mesma verificação do `heatmap_for`, porque o relatório mostra solicitações de todos os usuários. O item do menu usa as duas permissões como tupla. O relatório só lê dados e não declara `audit_resource`.

### D11. Tela de referência

O autor escolheu (02/10/2026) seguir a tela do mapa de calor como referência, sem imagem nova: o cartão de filtros, a linha de quatro indicadores com ícone e dica, e os cartões com tabela. Nada foi retirado.

### D12. Ajustes na implementação (02/10/2026)

- **Gráfico sem SVG e sem JavaScript novo.** O painel já tinha colunas e barras em passos de 5% (`bar-h-*`, `bar-w-*` e `panel.indicators.step`). O gráfico usa essas classes, e não um SVG com coordenadas, e a dica é o `hint.html` com o `hint.js` existente, sem o `chart.js` previsto em D3. Os componentes novos são `report-chart`, `report-week`, `report-column`, `report-meter` e `report-fill`.
- **Dica dentro do gráfico.** A área do gráfico rola na horizontal e cortaria a dica abaixo ou acima da coluna. Por isso a dica abre no topo do gráfico, do lado oposto ao da coluna (`Week.hint_align`), e a coluna ganha o tom de hover.
- **Valores no topo das colunas.** Como no gráfico de horas por dia do painel, cada coluna mostra o total acima dela. A divisão por situação fica na dica e na tabela.
- **Raio do topo das colunas:** `--radius-md`, porque a escala não tem raio menor.
- **Rótulos curtos dos indicadores:** "Aprovação" e "Até a decisão", porque "Taxa de aprovação" e "Tempo até a decisão" eram cortados na linha de quatro com o menu aberto.
- **Pendentes sem botão.** O botão "Analisar" foi para o cabeçalho de "Situação das solicitações", porque um botão dentro do indicador, que já é focável pela dica, criaria dois alvos no mesmo cartão.
- **Disposição.** "Espaços mais solicitados" ocupa a largura inteira, porque as seis colunas não cabiam ao lado de outro cartão. "Situação das solicitações" divide o próprio corpo em duas colunas a partir de `lg`: as situações e as alternativas.
- **Rolagem de 9 px em 640 px.** As dicas ocultas dos indicadores passam da borda nessa largura. O mesmo acontece no mapa de calor e no painel, então o problema vem de antes desta Change e fica fora dela.

## Risks / Trade-offs

- [Altura em passos de 5%] → duas semanas com totais próximos podem ter a mesma altura. O valor no topo da coluna, a dica e a tabela dão o número exato. Em larguras estreitas, o gráfico rola na horizontal dentro do próprio cartão, rotulado e focável, como a Grade.
- [Mediana em tempo corrido] → fim de semana e feriado aumentam o tempo. A ajuda do indicador diz "tempo corrido", e o cálculo em dias letivos fica para depois, se o autor pedir.
- [Recorte pela data de uso] → uma solicitação criada no fim do semestre anterior para uma data deste semestre conta neste. É o comportamento esperado para planejar o espaço, e fica escrito na ajuda do filtro de semestre.
