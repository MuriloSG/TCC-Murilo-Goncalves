## Why

O mapa de calor mostra como os espaços são ocupados, mas não mostra a demanda: quantas solicitações de agendamento chegam, quanto tempo esperam por decisão, quantas são rejeitadas e quais espaços concentram os pedidos. Quem analisa as solicitações e quem planeja o ensalamento precisa desses números para responder mais rápido e para enxergar espaços que faltam. Esta Change acrescenta o segundo relatório ao grupo "Relatórios", com o primeiro gráfico do sistema.

## What Changes

- O grupo "Relatórios" do menu ganha o item "Solicitações", na rota `relatorios/solicitacoes/`, com o título "Relatório de solicitações de agendamento".
- Filtros por semestre, etapa de ensino, curso e espaços, todos com o componente de select do projeto (`ui/components/select.html`), e o de espaços na versão múltipla com busca.
- Quatro indicadores: solicitações no período, taxa de aprovação, tempo mediano até a decisão e solicitações pendentes.
- O gráfico de colunas "Solicitações por semana", com uma coluna por semana do semestre, a dica com a divisão por situação no hover e no foco, e a tabela com os mesmos dados.
- O bloco "Situação das solicitações", com a contagem e o percentual de cada situação e o resultado das alternativas sugeridas.
- A tabela "Espaços mais solicitados", com os dez espaços de maior demanda, uma barra proporcional ao total e as contagens de aprovadas e rejeitadas.
- A lista "Rejeições recentes", com os dez últimos motivos de rejeição e o botão para o detalhe da solicitação.
- O relatório exige `RELATORIO.VISUALIZAR` e `AGENDA.ANALISAR`.

### Fora do escopo

- Exportação em CSV, PDF ou para impressão.
- Intervalo de datas livre, fora do período do semestre.
- Ranking por docente e por solicitante.
- Filtro da lista de análise por espaço ou por semana, para abrir as solicitações de uma coluna do gráfico.
- Biblioteca de gráficos em JavaScript.

## Capabilities

Sem specs nesta Change, como na Change `gerar-mapa-de-calor-dos-espacos`: o plano fica em `design.md` e `tasks.md`.

## Impact

- `reports`: novo módulo `requests.py` com o cálculo, `charts.py` com a geometria do gráfico, formulário, views, templates e testes.
- `ui/navigation.py`: item "Solicitações" no grupo "Relatórios".
- `ui/styles/app.css` e `ui/contrast.py`: tokens e componentes do gráfico (`chart`, `chart-bar`, `chart-axis`, `meter`) e os pares de contraste.
- `ui/static/ui/js/chart.js`: dica das colunas.
- Usa, sem alterar, `BookingRequest` e seus campos de decisão (`decided_at`, `responded_at`, `suggested_*`), `panel.indicators.chosen_semester` e a `status_badge` de `bookings/views.py`.
