## Why

A Grade do ensalamento (`ensalamento/`, Change `visualizar-grade-do-ensalamento`) mostra hoje uma **semana típica** da sala: as faixas de horário nas linhas, os dias de segunda a sexta nas colunas e as alocações confirmadas do semestre. Essa semana não tem datas. Ela responde "o que acontece nesta sala às segundas-feiras", mas não responde "a sala 1/13 está ocupada na segunda-feira, 05/10/2026, das 21:00 às 22:40?", que é a pergunta do campus (P6, P7) e a que a futura tela de reserva vai precisar responder.

A análise do código mostrou que o ensalamento já está modelado como regra recorrente: uma `Allocation` é semestre, turma, disciplina, dia da semana e faixa de horário, uma por faixa, sem uma linha por data (D9 da Change `importar-ensalamento-da-planilha`). O que falta para chegar às datas é um único dado: **o período do semestre**. `Semester` só tem o código `2026/2`, sem data de início e de fim.

Esta Change leva a Grade da semana típica para o **calendário do semestre**, sem criar uma estrutura paralela: acrescenta o período ao `Semester`, calcula as ocorrências das alocações no intervalo consultado, e mostra esse mesmo cálculo em duas visões, **semanal** e **mensal**, com as faixas **disponíveis** visíveis. O cálculo é separado por **fonte de ocupação**, para que as reservas de uma Change futura apareçam na mesma Grade sem mudar a Grade.

A Grade continua sendo uma consulta. Ela não cria, não altera e não exclui ocupação.

## What Changes

- **Período do semestre.** `Semester` ganha `start_date` e `end_date`, opcionais. Um modal "Definir período", aberto pela Grade para quem tem `ENSALAMENTO.IMPORTAR`, grava o período, com auditoria. Sem período, a Grade continua mostrando a semana típica de hoje (D2, D3).
- **Ocorrências calculadas, nunca gravadas.** Um módulo novo, `schedule/occupancy.py`, expande cada alocação nas datas do intervalo consultado que caem no dia da semana dela e dentro do período do semestre. Nenhuma ocorrência é gravada no banco. O custo da consulta não depende do tamanho do intervalo (D4, D5).
- **Fonte de ocupação.** O cálculo recebe uma lista de fontes. Esta Change tem uma só, o ensalamento (`AllocationSource`). A reserva futura será outra fonte, e a Grade vai apresentá-la sem mudança na estrutura (D6, D12).
- **Visão semanal com datas.** A semana da sala passa a ter datas nos dias, navegação para a semana anterior e a seguinte, "Hoje" pela data, e os dias fora do período do semestre marcados como tal (D7).
- **Visão mensal como mapa de ocupação.** O mesmo cálculo mostra o mês da sala de segunda a sexta, com cada dia indicando a ocupação e levando à semana dele. Não é calendário genérico nem tela de reserva (D8).
- **Faixa disponível sem poluição visual.** A célula sem ocupação continua visualmente vazia, como na planilha, e informa "disponível" à tecnologia assistiva. Ela se distingue de "Fora do semestre" e do aviso de semestre sem período (D9).
- **Arquitetura documentada para a alteração da recorrência, as exceções e as reservas**, sem implementar nenhuma delas: versões da alocação por vigência, exceção por data e fonte de reservas (D10, D11, D12).

### Fora do escopo

- Tela de reserva, formulário, edição, cancelamento, aprovação e permissões de reserva.
- Criação de ocupação pela Grade, por clique, arraste ou qualquer outro meio.
- Versionamento da alocação, tabela de exceções e cancelamento de uma ocorrência: ficam descritos no `design.md` (D10, D11) e entram numa Change própria, com a tela que os cria.
- Calendário de feriados e de dias sem aula.
- Sábado e domingo: o ensalamento só tem segunda a sexta (`Weekday`).
- Visão por turma e por docente.
- Qualquer mudança na leitura da planilha, na execução, no plano e na confirmação da importação.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `ensalamento`: o semestre ganha período; a Grade passa a mostrar ocorrências datadas, calculadas das alocações, em visão semanal e mensal, com as faixas disponíveis visíveis e o cálculo separado por fonte de ocupação.

## Impact

- **`schedule/`**: `models.py` (período do `Semester` e a operação que o define), uma migration, `occupancy.py` (novo: `Occurrence`, `AllocationSource`, `occupancy`), `timetable.py` (a semana e o mês a partir das ocorrências), `forms.py` (filtros de visão, semana e mês; formulário do período), `views.py` e `urls.py` (a Grade com as duas visões e o modal do período), `templates/schedule/` e `tests/`.
- **`audit/`**: o recurso do semestre no catálogo.
- **`ui/`**: estilos do mês, da navegação entre períodos e da célula disponível no `app.css`, e ícones do Lucide que faltarem.
- **Sem impacto**: `imports/`, `schedule/imports.py`, `schedule/sheets.py`, `schedule/activities.py`, a identidade e as restrições de `Allocation`, as permissões e o menu.

## Dependência

Esta Change parte da Grade de `visualizar-grade-do-ensalamento` (D15 e D16 daquela Change) e deve ser implementada depois que aquela for concluída e arquivada, junto com `importar-ensalamento-da-planilha`, porque os requisitos daqui acrescentam à capability `ensalamento` que elas criam.

## Alinhamento com o TCC

- **P6:** a disponibilidade de uma sala numa data é consultada sem uma linha por data, com uma quantidade fixa de consultas pelos índices que já existem.
- **P7:** "disponível" e "ocupado", datas em dd/mm/aaaa e o mês como o campus pensa o semestre.
- **P10:** o período do semestre é informado por ação administrativa, sem integração externa, e a planilha continua sendo a fonte das aulas regulares.
- **P2:** o cálculo das ocorrências é função do app `schedule`, testável sem a view, e os templates só apresentam.
- **P4:** a reserva futura entra como mais uma fonte de ocupação, sem reescrever a Grade.
