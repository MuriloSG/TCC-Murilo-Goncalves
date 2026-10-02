## Why

O calendário público é a página que os alunos abrem todos os dias para ver os horários. No celular, a coluna de cada dia tem cerca de 148 px e a de horários 64 px, então uma semana ocupa cerca de 800 px: numa tela de 360 px cabe um dia e meio, e o aluno arrasta a Grade para os lados a cada consulta, parando no meio das colunas. Além disso, os filtros ocupam a primeira tela inteira, e depois de escolher o curso é preciso rolar a página até o calendário.

A decisão D13 da Change `calendario-publico` continua valendo: a mesma Grade em qualquer largura, sem lista por dia e sem navegação entre intervalos. Esta Change só ajusta a Grade abaixo de 640 px e leva o aluno até ela depois de cada filtro.

## What Changes

- Abaixo de 640 px, a coluna de cada dia ocupa metade da largura disponível da área, descontada a coluna de horários: qualquer celular mostra exatamente dois dias inteiros.
- A rolagem horizontal encaixa no início de cada dia (`scroll-snap`), e uma sombra na borda indica que há mais dias para o lado.
- A coluna de horários fica mais estreita, e o cabeçalho do dia mostra o dia da semana abreviado e a data sem o ano, mantendo o nome completo para a tecnologia assistiva.
- O card de aula e o de agendamento mantêm o conteúdo atual; só as palavras longas passam a quebrar dentro da coluna.
- Abaixo de 640 px, ao aplicar qualquer filtro, a página desce com rolagem suave até o calendário. Os filtros continuam sempre abertos.
- A área da Grade ocupa a altura da tela.
- Em qualquer largura, o horário de cada faixa fica centralizado na célula.
- A spec deixa de citar a marca antiga e o link "Entrar", que já não existem no layout público.

### Fora do escopo

- Botões de navegação entre semanas: a troca de intervalo continua só pelos campos de data.
- Lista por dia, visão de um dia por vez, card resumido e filtros recolhidos.
- Qualquer mudança acima de 640 px além do horário centralizado, e mudanças na consulta ou na quantidade de consultas.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `calendario-publico`: o requisito "Calendário público no celular".

## Impact

- `ui/styles/app.css`: regras abaixo de `sm` para `.timetable-scroll.is-public`, `.timetable-grid.is-public` e a moldura das sombras.
- `schedule/templates/schedule/public/calendar.html`: cabeçalho do dia com rótulo curto e a moldura da área.
- `ui/static/ui/js/calendar.js`: sombras de borda e rolagem até o calendário.
- Nenhuma consulta nova.
- `openspec/conventions.md`: a regra do calendário público na seção 9.7 passa a citar os dois dias por tela e a rolagem até o calendário.
