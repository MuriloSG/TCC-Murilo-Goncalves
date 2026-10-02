## 0. Antes de implementar

- [x] 0.1 Referência da tela definida com o autor: a tela do mapa de calor (D11)
- [x] 0.2 Confirmar com o autor D1 (recorte pela data de uso), D2 (mediana em tempo corrido) e D3 (série única com a divisão por situação na dica)

## 1. Menu e acesso

- [x] 1.1 Item "Solicitações" no grupo "Relatórios" do `ui/navigation.py`, com `RELATORIO.VISUALIZAR` e `AGENDA.ANALISAR` (D10)
- [x] 1.2 Rota `relatorios/solicitacoes/` com `login_required` no `reports/urls.py`

## 2. Cálculo

- [x] 2.1 `reports/requests.py`: recorte do semestre pela data de uso e os filtros de etapa, curso e espaços (D1, D8)
- [x] 2.2 Indicadores: total, taxa de aprovação, mediana até a decisão e pendentes com a mais antiga (D2)
- [x] 2.3 Contagem por semana e por situação, situação das solicitações com as alternativas, ranking de espaços e rejeições recentes (D3, D5, D6, D7)
- [x] 2.4 Testes do cálculo: semestre sem período, semana sem solicitação, alternativa aceita contada como aprovada, solicitação sem vínculo com e sem filtro de curso, empate no ranking e período sem decisão

## 3. Gráfico

- [x] 3.1 Altura das colunas e largura das barras em passos de 5%, com o `step` do painel (D3, D12)
- [x] 3.2 Tokens `--color-chart-bar` e `--color-chart-bar-hover`, pares no `ui/contrast.py` e os componentes `report-chart`, `report-week`, `report-column`, `report-meter` e `report-fill` no `app.css` (D4, D6, D12)
- [x] 3.3 Dica de cada semana com o `hint.html`, no hover e no foco, com a área de acerto da semana inteira e aberta no topo do gráfico (D12)
- [x] 3.4 Testes das semanas: altura proporcional, coluna ausente na semana vazia, rótulos alternados e lado da dica

## 4. Tela

- [x] 4.1 `RequestsFilterForm` com todos os campos em `ui/components/select.html`, e o de espaços múltiplo com busca, compartilhando a montagem das opções com o `HeatmapFilterForm` (D8)
- [x] 4.2 `RequestsReportView` e o template com os filtros, os indicadores, o gráfico, a situação, o ranking e as rejeições recentes
- [x] 4.3 Testes da rota nas quatro situações de acesso, incluindo a falta de `AGENDA.ANALISAR`, e dos estados vazios

## 5. Conferência

- [x] 5.1 Testes do app `ui` (texto, classes e contraste nos dois temas) e a suíte inteira
- [x] 5.2 Conferência visual no banco `visual_check` em 360, 640 e 1280 px, sem JavaScript, com o foco pelo teclado nas colunas e com zoom de 200%
- [x] 5.3 Regras do gráfico (classes em passos, série única e dica) em `openspec/conventions.md`, seção 9.9
