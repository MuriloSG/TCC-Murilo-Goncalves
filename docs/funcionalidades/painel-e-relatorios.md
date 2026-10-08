# Painel e relatórios

Telas só de leitura, calculadas a cada requisição e sem dados gravados. Não declaram `audit_resource`, portanto o acesso não entra na auditoria.

## Painel administrativo

Rota `/painel/` (`panel.views.PanelView`). A rota exige `PAINEL.VISUALIZAR`; cada bloco exige também a permissão do módulo dono dos dados e nem é calculado sem ela.

| Bloco | Permissão adicional | Conteúdo (`panel/indicators.py`) |
|---|---|---|
| Solicitações | `AGENDA.ANALISAR` | Pendentes, pendentes cujo horário já passou, aguardando resposta à alternativa e as 5 pendentes pedidas por último, ordenadas pela data de uso |
| Ocupação | `ENSALAMENTO.VISUALIZAR` | Hoje ou semana atual: os 10 espaços mais ocupados (minutos de aula e de agendamento pela união dos intervalos), a ocupação por dia e os espaços ativos sem ocupação |
| Pendências da grade | `ENSALAMENTO.VISUALIZAR` | No semestre escolhido: aulas sem espaço, aulas sem docente, possíveis conflitos de docente, espaços sem ocupação e, com `AGENDA.VISUALIZAR`, agendamentos futuros em choque com aula |
| Importações | `ENSALAMENTO.IMPORTAR` | Importações de ensalamento validadas, pendentes ou com erros |

Os itens de cada pendência abrem em modal paginado (`/painel/pendencias/<chave>/`, chaves `sem-espaco`, `sem-docente`, `conflito`, `choque`, `sem-ocupacao`). A pendência `choque` exige `AGENDA.VISUALIZAR`.

## Mapa de calor dos espaços

Rota `/relatorios/mapa-de-calor/` (`reports.views.HeatmapView`, cálculo em `reports/heatmap.py`). Exige `RELATORIO.VISUALIZAR` e `ENSALAMENTO.VISUALIZAR`.

- Grade de dia da semana por faixa de horário na semana típica do semestre. A célula é a média, entre as datas daquele dia no período do semestre, da fração de espaços ocupados.
- A ocupação de um espaço numa faixa é a interseção da faixa com a união das aulas e dos agendamentos, como no painel.
- Filtros: semestre, origem (todas, aulas, agendamentos), etapa de ensino, curso e espaços.
- Cada célula abre o detalhe paginado (`/relatorios/mapa-de-calor/<dia>/<faixa>/`).
- Exige semestre com período.

## Relatório de solicitações

Rota `/relatorios/solicitacoes/` (`reports.views.RequestsReportView`, cálculo em `reports/requests.py`). Exige `RELATORIO.VISUALIZAR` e `AGENDA.ANALISAR`.

- Uma solicitação pertence ao semestre pela data de uso dentro do período.
- Indicadores: total, criadas em nome de outro usuário, decididas, taxa de aprovação, pendentes e a mais antiga, tempo de decisão, distribuição por situação, desfecho das alternativas sugeridas, solicitações por semana, ranking de espaços e rejeições recentes.
- A solicitação cancelada conta como aprovada na taxa de aprovação, no aceite da alternativa e no ranking, porque foi aprovada antes.
- Filtros: semestre, etapa de ensino, curso e espaços.

## Gráficos

Sem biblioteca e sem `style=`: as barras usam as classes `bar-h-*` e `bar-w-*` em passos de 5% (`panel.indicators.step`). Detalhes na seção 9.9 das [convenções](../desenvolvimento/convencoes.md#99-tokens-componentes-e-layouts-do-app-ui).

## Testes

`panel/tests/test_panel.py`, `reports/tests/test_heatmap.py`, `reports/tests/test_requests.py`.
