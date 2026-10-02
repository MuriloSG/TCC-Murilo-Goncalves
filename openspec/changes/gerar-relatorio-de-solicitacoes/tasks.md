## 0. Antes de implementar

- [ ] 0.1 Imagem de referência da tela recebida e adaptada com o autor (D11)
- [ ] 0.2 Confirmar com o autor D1 (recorte pela data de uso), D2 (mediana em tempo corrido) e D3 (série única com a divisão por situação na dica)

## 1. Menu e acesso

- [ ] 1.1 Item "Solicitações" no grupo "Relatórios" do `ui/navigation.py`, com `RELATORIO.VISUALIZAR` e `AGENDA.ANALISAR` (D10)
- [ ] 1.2 Rota `relatorios/solicitacoes/` com `login_required` no `reports/urls.py`

## 2. Cálculo

- [ ] 2.1 `reports/requests.py`: recorte do semestre pela data de uso e os filtros de etapa, curso e espaços (D1, D8)
- [ ] 2.2 Indicadores: total, taxa de aprovação, mediana até a decisão e pendentes com a mais antiga (D2)
- [ ] 2.3 Contagem por semana e por situação, situação das solicitações com as alternativas, ranking de espaços e rejeições recentes (D3, D5, D6, D7)
- [ ] 2.4 Testes do cálculo: semestre sem período, semana sem solicitação, alternativa aceita contada como aprovada, solicitação sem vínculo com e sem filtro de curso, empate no ranking e período sem decisão

## 3. Gráfico

- [ ] 3.1 `reports/charts.py`: escala do eixo com passos inteiros e a geometria das colunas no `viewBox` (D3)
- [ ] 3.2 Tokens `--color-chart-bar` e `--color-chart-bar-hover`, pares no `ui/contrast.py` e os componentes `chart`, `chart-bar`, `chart-axis` e `meter` no `app.css` (D4, D6)
- [ ] 3.3 `ui/static/ui/js/chart.js`: dica no hover e no foco, com a área de acerto da semana inteira e sem animação com movimento reduzido
- [ ] 3.4 Testes da escala (zero, um, valores grandes) e da geometria (altura proporcional, coluna ausente na semana vazia)

## 4. Tela

- [ ] 4.1 `RequestsFilterForm` com todos os campos em `ui/components/select.html`, e o de espaços múltiplo com busca, compartilhando a montagem das opções com o `HeatmapFilterForm` (D8)
- [ ] 4.2 `RequestsReportView` e o template com os filtros, os indicadores, o gráfico, a tabela em `<details>`, a situação, o ranking e as rejeições recentes
- [ ] 4.3 Testes da rota nas quatro situações de acesso, incluindo a falta de `AGENDA.ANALISAR`, e dos estados vazios

## 5. Conferência

- [ ] 5.1 Testes do app `ui` (texto, classes e contraste nos dois temas) e a suíte inteira
- [ ] 5.2 Conferência visual no banco `visual_check` em 360, 640 e 1280 px, com o menu aberto e recolhido, sem JavaScript, só pelo teclado e com zoom de 200%
- [ ] 5.3 Regras do gráfico (SVG no servidor, série única, dica e tabela) em `openspec/conventions.md`, seção 9.9
