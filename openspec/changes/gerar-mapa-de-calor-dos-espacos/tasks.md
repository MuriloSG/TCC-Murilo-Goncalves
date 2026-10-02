## 0. Antes de implementar

- [x] 0.1 Mockup aprovado com o autor: eixo dia × faixa, semestre, quatro indicadores, filtros e modal da célula
- [x] 0.2 Confirmar com o autor D2 (agendamentos na semana típica), D3 (percentual) e D5 (curso e etapa com a origem "só agendamentos")

## 1. Permissão e app

- [ ] 1.1 `RELATORIO.VISUALIZAR` no catálogo e migration de dados que a concede ao ADMINISTRADOR (D9)
- [ ] 1.2 App `reports` com `apps.py`, `urls.py` (`login_required`) e a inclusão em `config` (D1)

## 2. Menu com grupos

- [ ] 2.1 `MenuGroup` no `ui/navigation.py` e o grupo "Relatórios" com "Mapa de calor dos espaços" (D8)
- [ ] 2.2 Tag `navigation` e `navigation.html` com o grupo, a marca do item atual e o `aria-expanded`
- [ ] 2.3 CSS do submenu, alternância no `sidebar.js` e o painel flutuante no menu recolhido
- [ ] 2.4 Testes do menu: grupo oculto sem item liberado, aberto no item atual

## 3. Cálculo

- [ ] 3.1 `reports/heatmap.py`: matriz dia × faixa da semana típica, com a união de intervalos do painel (D2)
- [ ] 3.2 Indicadores: taxa média, pico, mais livre e aulas × agendamentos (D3, D4)
- [ ] 3.3 Filtros por origem, etapa, curso e espaços aplicados ao cálculo (D5)
- [ ] 3.4 Testes do cálculo: aula compartilhada, agendamento sobre aula, ocorrência cancelada, semestre sem período e empates

## 4. Telas

- [ ] 4.1 `HeatmapFilterForm` com todos os campos em `ui/components/select.html`, e o de espaços múltiplo com busca (D5)
- [ ] 4.2 `HeatmapView` e o template com os filtros, os indicadores, o mapa, a legenda e as classes `heat-0` a `heat-5` (D6)
- [ ] 4.3 `HeatmapCellView` em modal pelo htmx, paginada e com "Abrir na Grade" (D7)
- [ ] 4.4 Testes das rotas nas quatro situações de acesso, incluindo a falta de `ENSALAMENTO.VISUALIZAR`

## 5. Conferência

- [ ] 5.1 Testes do app `ui` (texto, classes e contraste nos dois temas) e a suíte inteira
- [ ] 5.2 Conferência visual no banco `visual_check` em 360, 640 e 1280 px, com o menu aberto e recolhido, sem JavaScript, com zoom de 200% e nos dois temas
- [ ] 5.3 Regras do submenu e do relatório em `openspec/conventions.md`
