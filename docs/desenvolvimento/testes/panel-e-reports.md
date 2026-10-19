# Testes dos apps `panel` e `reports`

Painel administrativo, mapa de calor e relatório de solicitações. Comportamento descrito em [painel e relatórios](../../funcionalidades/painel-e-relatorios.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `PanelTestCase`, em `panel/tests/test_panel.py`: relógio fixado na segunda-feira 05/10/2026 às 10:00 e semestre 2026/2 com período. É a base dos testes de `reports`.

## `panel`

### `test_panel.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Cada bloco segue sua permissão: sem análise, sem solicitações; sem importação, sem importações; sem permissões de módulo, o aviso; superadmin vê tudo |
| `EntryTests` | Quem tem o painel o abre depois do login; o docente continua abrindo a Agenda |
| `RequestTests` | Contagem por situação; início passado é atrasada e sai da lista; as cinco mais recentes em ordem de data; estado vazio |
| `OccupancyTests` | Aula compartilhada conta uma vez; ocorrência cancelada e aula encerrada não contam; agendamento sobre aula conta uma vez; espaço ativo sem ocupação é ocioso e inativo fica fora; fim de semana só com agendamentos; horas por dia; os dez mais ocupados em ordem; semestre sem período e data fora de semestre avisados; consultas fixas |
| `GridIssueTests` | Pendências da grade: aula sem espaço, sem docente por dia e faixa, docente em dois espaços ao mesmo tempo, choque de agendamento com aula posterior; aula compartilhada, faixas vizinhas, versão encerrada e vigências que não se cruzam não são pendência; sem a Agenda, sem o item de choque |
| `ImportTests` | Importações de ensalamento abertas |
| `FilterTests` | Semestre do dia por padrão, ou o mais recente se o dia não foi importado; valor inválido volta ao padrão; o filtro não muda o dia de hoje |
| `IssueModalTests` | Sem a grade, 403; choque exige a Agenda; chave desconhecida, 404; modal pelo htmx e página sem ele; espaços ociosos paginados |
| `WithoutSpaceTileTests` | Só o cartão do topo mostra aulas sem espaço |
| `IssueTableTests` | Aula sem espaço não tem botão; choque abre a Agenda |

## `reports`

### `test_heatmap.py`

Mapa de calor do semestre 2026/2 (03/08 a 18/12, 20 segundas-feiras).

| Classe | O que garante |
|---|---|
| `AccessTests` | Exige a permissão do ensalamento além da do relatório |
| `BuildTests` | Aula ocupa toda segunda; taxa sobre todas as faixas e espaços; ocorrência cancelada fora; agendamento conta só na sua semana e sobre aula conta como aula; filtros de origem, curso e espaço; o menos ocupado ignora dias sem ocupação; semestre sem período; níveis |
| `CellTests` | Modal da célula com espaços ocupados e livres; dia ou faixa desconhecidos, 404 |
| `FilterFormTests` | Valores desconhecidos voltam ao padrão; "só agendamentos" esconde etapa e curso |

### `test_requests.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Exige a permissão de análise além da do relatório |
| `PageTests` | Estados vazios e aviso de semestre sem período; rejeição leva ao detalhe da análise e espaço à Agenda |
| `BuildTests` | Só solicitações usadas no período; semanas a partir da segunda, com a atual e o detalhe por situação; taxa de aprovação sobre as decididas, com cancelada contando como aprovada; tempo de decisão pela mediana; pendentes e a mais antiga; alternativas; criadas para outro; curso e etapa deixam de fora as sem vínculo; filtro de espaço; ranking por total e nome, com dez espaços; rejeições recentes primeiro |
| `AxisTests` | Marcas do eixo; o pico é a primeira semana mais alta |
| `TextTests` | Texto da duração |
| `FilterFormTests` | Valores desconhecidos voltam ao padrão; escolhidos viram filtros; filtro acadêmico mostra a ajuda |
