## Why

O painel mostra a ocupação de hoje ou da semana atual, mas não responde em quais dias e faixas o campus fica cheio ou vazio ao longo do semestre. Quem planeja o ensalamento e avalia as solicitações de agendamento precisa desse panorama para remanejar aulas e sugerir horários com folga. Esta Change abre um grupo "Relatórios" no menu, começando pelo mapa de calor dos espaços.

## What Changes

- O menu lateral ganha o grupo recolhível "Relatórios", com o submenu "Mapa de calor dos espaços". É o primeiro item com submenu.
- A nova rota `relatorios/mapa-de-calor/` mostra uma matriz com as faixas de horário nas linhas e os dias da semana nas colunas, na semana típica do semestre. Cada célula traz o percentual de espaços ocupados, em seis tons de verde e com uma legenda.
- Acima do mapa ficam quatro indicadores: a taxa média de ocupação (com as horas), o horário de pico, o horário mais livre e a divisão entre aulas e agendamentos.
- Filtros por semestre, origem da ocupação (aulas e agendamentos, só aulas ou só agendamentos), etapa de ensino, curso e espaços, todos com o componente de select do projeto (`ui/components/select.html`).
- A célula abre um modal pelo htmx com os espaços ocupados (aula ou agendamento) e os livres naquele dia e faixa, com o botão "Abrir na Grade".
- A nova permissão `RELATORIO.VISUALIZAR` é criada por migration de dados e concedida ao ADMINISTRADOR. O mapa exige também `ENSALAMENTO.VISUALIZAR`.

### Fora do escopo

- Exportação em CSV, PDF ou para impressão.
- Os eixos espaço × dia e espaço × faixa, e o intervalo de datas livre.
- Capacidade, tipo ou bloco do espaço, que o model `Space` não tem.

## Capabilities

Sem specs nesta Change, a pedido do autor (02/10/2026): o plano fica em `design.md` e `tasks.md`.

## Impact

- Novo app `reports` (views, formulário, cálculo, templates, testes e URLs).
- `accounts/permissions.py` e uma migration de dados com `RELATORIO.VISUALIZAR`.
- `ui/navigation.py`, `ui/templatetags/ui.py`, `ui/components/navigation.html`, o CSS e o `sidebar.js` passam a ter grupos com submenu.
- Usa, sem alterar, `schedule.occupancy.occurrences_of_all_spaces` e a regra de união de intervalos de `panel/indicators.py`.
