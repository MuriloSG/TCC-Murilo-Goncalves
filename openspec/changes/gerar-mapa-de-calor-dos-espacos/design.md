## Context

O painel (`panel/indicators.py`) calcula a ocupação de hoje ou da semana pela união dos intervalos das aulas (`occurrences_of_all_spaces`) e dos agendamentos (`bookings_between`), sem percentual (D5 da Change `exibir-painel-administrativo`). O menu (`ui/navigation.py`) é uma tupla plana de `MenuItem`. O `Space` só tem nome, origem e situação. As faixas de horário são os `TimeSlot` do semestre.

O mockup aprovado em 02/10/2026 tem a sidebar com o grupo "Relatórios", o cartão de filtros, a linha de quatro indicadores, o mapa e o modal da célula.

## Goals / Non-Goals

**Goals:**

- Mostrar os horários de pico e de folga do semestre numa tela, com o detalhe por espaço a um clique.
- Abrir o menu para outros relatórios sem reestruturá-lo de novo.

**Non-Goals:**

- Exportação, intervalo de datas livre, outros eixos e atributos novos no `Space`.

## Decisions

### D1. Novo app `reports`

Os relatórios não são do painel nem do ensalamento: o app `reports` tem as views, o `heatmap.py` com o cálculo e os templates. As funções de união de intervalos do painel são reaproveitadas por import, sem cópia.

### D2. Semana típica do semestre

A célula (dia da semana, faixa) é medida em todas as datas daquele dia da semana dentro do período do semestre. A ocupação de um espaço numa data e faixa é a interseção da faixa com a união das aulas e dos agendamentos, com a mesma regra do painel (D4 dele). O valor da célula é a média, entre as datas, da fração de espaços ocupados. Assim os agendamentos, que têm data e não se repetem, entram na proporção das semanas em que ocorreram. O modal mostra em quantas semanas cada espaço esteve ocupado.

Semestre sem período (`start_date` vazio) mostra o aviso do painel e não calcula o mapa.

### D3. Percentual no relatório

Diferente do painel (D5 dele), o relatório mostra percentuais, sempre acompanhados do valor absoluto: "58%" com "412 de 710 horas disponíveis", e "91%" com "29 de 32 espaços". A base é o número de espaços do filtro vezes as faixas e os dias com aula no semestre.

### D4. Indicadores

- **Taxa média de ocupação:** horas ocupadas sobre horas disponíveis, em todas as células.
- **Horário de pico e horário mais livre:** a célula de maior valor e a de menor valor entre os dias que têm alguma faixa ocupada, para que o sábado vazio não seja sempre o mais livre. Em caso de empate, vale a primeira na ordem de dia e de faixa.
- **Aulas × agendamentos:** as horas de cada origem sobre o total ocupado; o trecho de agendamento sobre aula conta como aula, como no painel.

### D5. Filtros

`HeatmapFilterForm` declara `semestre`, `origem`, `etapa`, `curso` e `espacos` (múltiplo). Todos são renderizados com `ui/components/select.html`; o de espaços usa a versão múltipla com busca. Um valor que não é opção é ignorado e vale o padrão, como no painel. Etapa e curso restringem só as aulas: com a origem "só agendamentos", os dois campos ficam ocultos, e com "aulas e agendamentos" uma ajuda avisa que os agendamentos não são filtrados por curso.

### D6. Escala de cor

Seis classes (`heat-0` a `heat-5`): 0% e cinco passos de 20% sobre o intervalo de 0 a 100%, em tons de verde tirados dos tokens da paleta. O texto da célula passa a branco nos dois tons mais escuros. Os pares de contraste entram nos testes do app `ui`, nos dois temas. A célula é um `<button>` com `aria-label` completo ("Terça, 19:00 às 20:40: 29 de 32 espaços ocupados"), para que a cor nunca seja a única informação.

### D7. Modal da célula

`HeatmapCellView(ModalView)` em `relatorios/mapa-de-calor/<dia>/<faixa>/`, com os filtros pela URL. Ela lista os ocupados (com a marca Aula ou Agendamento e as semanas) e os livres, paginados, com "Abrir na Grade" como em `PanelIssueView.action_for`. Sem o htmx, a mesma URL mostra a página completa.

### D8. Menu com grupos

`MenuGroup(label, icon, prefix, items)` entra no `MENU` ao lado de `MenuItem`. O grupo só aparece com algum item liberado, abre sozinho quando o item atual está dentro dele e alterna com um botão `aria-expanded`. No menu recolhido, o grupo mostra os itens num painel flutuante. O `sidebar.js` cuida da alternância, e sem JavaScript o grupo fica aberto.

### D10. Ajustes do autor na implementação (02/10/2026)

- O submenu se chama só "Mapa de calor"; o título da tela continua "Mapa de calor dos espaços".
- Os cinco filtros ficam numa única linha a partir de `lg`, com o menu aberto ou recolhido: cada campo divide a largura por igual, e o select múltiplo de espaços tem a mesma altura dos outros.
- Os indicadores ficam numa linha de quatro a partir de `lg`, com o ícone de cada um e com os rótulos "Ocupação média" e "Menor ocupação". "Livre" é termo proibido pelo glossário (seção 9.4), e a tela usa "disponível".
- O grupo do menu é um `<details>`: abre e fecha sem JavaScript, e o `sidebar.js` não mudou. No menu recolhido, o cabeçalho do grupo some e os itens aparecem como ícones.

### D9. Acesso

`REPORT_VIEW = 'RELATORIO.VISUALIZAR'` é criada por migration de dados e concedida ao ADMINISTRADOR. As views declaram `permission_required = REPORT_VIEW`, e o mapa e o modal exigem também `ENSALAMENTO.VISUALIZAR`. O submenu do mapa usa as duas permissões. O relatório só lê dados e não declara `audit_resource`.

## Risks / Trade-offs

- [Cálculo por data do semestre inteiro] → `occurrences_of_all_spaces` já faz três consultas para qualquer intervalo; o custo fica em Python, proporcional a datas × espaços. Medir com o banco `visual_check` e, se necessário, agregar por (dia da semana, faixa) sem materializar as datas.
- [Primeiro submenu do projeto] → os testes de navegação passam a cobrir grupos, e o menu recolhido é conferido no navegador.
