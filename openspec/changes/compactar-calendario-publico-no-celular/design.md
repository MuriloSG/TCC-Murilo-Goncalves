## Context

O calendário público (raiz da aplicação, `/`; Change arquivada `2026-09-26-calendario-publico`) é uma `<table>` com as faixas de horário nas linhas e os dias úteis do intervalo nas colunas, com até 31 dias. Ele reaproveita o CSS da Grade mensal (`.timetable-scroll.is-month`, `.timetable-grid.is-month`): coluna de horários fixa com `--spacing-16`, cabeçalho dos dias fixo no topo e coluna de dia com `calc(var(--spacing-16) * 2 + var(--spacing-5))`, cerca de 148 px. O `calendar.js` rola a área até a coluna de "Hoje" e marca `aria-busy` durante a requisição do htmx.

Numa tela de 360 px, a área útil tem cerca de 326 px. Descontados os 64 px dos horários, cabe um dia e meio, e a rolagem livre para no meio das colunas. Os filtros, empilhados, ocupam a primeira tela.

A decisão D13 daquela Change continua: a mesma Grade em qualquer largura, sem representação só para o celular, e a troca de intervalo só pelos campos de data.

## Goals / Non-Goals

**Goals:**

- Ver dois dias inteiros por tela em qualquer celular, sem parar no meio de uma coluna.
- Chegar à Grade sem rolar a página depois de aplicar um filtro.
- Manter a Grade, o card, os filtros e o comportamento acima de 640 px exatamente como estão.

**Non-Goals:**

- Navegação entre semanas, lista por dia, card resumido e filtros recolhidos (decisões do autor em 02/10/2026).
- Mudança na consulta, nos filtros ou nas mensagens.

## Decisions

### D1. Dois dias por tela, pela largura da área

A área `.timetable-scroll.is-public` passa a ser um container de largura (`container-type: inline-size`). Abaixo de `sm`, a coluna de dia mede `calc((100cqi - var(--timetable-hour)) / 2)`, em que `--timetable-hour` é a largura da coluna de horários. A conta vale para qualquer largura de celular, sem um valor por aparelho; em 360 px, cada dia tem cerca de 139 px. A largura vem do container, e não da página, porque a área fica dentro do card e do recuo lateral.

Três dias por tela foram testados antes: com o card completo, a coluna ficava com cerca de 92 px e as palavras quebravam no meio. O autor escolheu dois.

A coluna de horários cai de `--spacing-16` para `--spacing-12`, com o texto em `--text-xs` e o recuo lateral menor, o suficiente para "07:30" e "08:20" um sobre o outro. A palavra "Horário" do canto fica só para a tecnologia assistiva.

### D2. Encaixe por dia

Abaixo de `sm`, a área recebe `scroll-snap-type: x mandatory` e `scroll-padding-left: var(--timetable-hour)`, e a coluna de dia recebe `scroll-snap-align: start` e `scroll-margin-left: 0`. O arrasto termina sempre no início de um dia, nunca no meio de uma coluna. A rolagem até "Hoje" do `calendar.js` continua igual: ela já desconta a coluna de horários, que é o mesmo `scroll-padding`.

### D3. Sombra na borda com mais dias

A área fica dentro de uma moldura (`.timetable-frame`). O `calendar.js` alterna as classes `has-before` e `has-after` na moldura ao rolar (evento passivo), ao mudar a largura da janela e depois de cada troca pelo htmx. Abaixo de `sm`, a borda que ainda tem dias para mostrar recebe uma sombra interna curta com a cor de `--color-control-border`. A sombra da esquerda fica logo depois da coluna de horários. Sem JavaScript, as classes não existem e não há sombra. A sombra não anima.

### D4. Cabeçalho do dia curto

Abaixo de `sm`, o cabeçalho mostra o dia da semana abreviado (`Day.short_label`, já existente, como "Qua") e a data sem o ano ("23/09"). O nome completo e a data completa ficam no `aria-label` do cabeçalho ("Hoje, Quarta-feira, 23/09/2026"), como já faz o cabeçalho da Grade mensal (`timetable_head.html`). O selo "Hoje" continua visível, porque a coluna de hoje não pode ser indicada só pela cor (seção 9.7). Acima de `sm`, o cabeçalho é o atual.

O template traz as duas formas, cada uma com uma classe que a esconde na outra largura (`timetable-long` e `timetable-short`).

### D5. Card sem mudança de conteúdo

O card de aula e o de agendamento mantêm todas as linhas (decisão do autor em 02/10/2026). Abaixo de `sm`, só o recuo interno do card e o espaço entre ícone e texto diminuem, e as palavras longas quebram com hífen (`hyphens: auto`, a página declara `lang="pt-br"`) e, em último caso, em qualquer ponto (`overflow-wrap: anywhere`), para não alargar a coluna.

### D6. Rolagem até o calendário depois de cada filtro

Os filtros ficam sempre abertos, como hoje. Abaixo de `sm`, quando uma requisição do htmx sai do formulário de filtros (selects e "Mostrar") ou do campo de turma (`data-public-group`), o `calendar.js` anota a origem no `htmx:beforeRequest`. No `htmx:afterSettle`, depois de rolar a área até "Hoje", ele chama `scrollIntoView` no calendário com `behavior: "smooth"`, ou `"auto"` quando o sistema pede movimento reduzido. O calendário tem `scroll-margin-top: var(--spacing-3)`: a barra do topo não fica fixa ao rolar, então o card encosta no topo da tela com uma folga pequena.

Acima de `sm`, filtros e calendário cabem juntos na tela e a página não rola sozinha. No primeiro carregamento também não, porque o aluno ainda vai escolher os filtros. Sem JavaScript, o formulário é enviado como hoje e a página abre no topo.

### D7. Altura da área

Abaixo de `sm`, o `max-height` da área passa de `75vh` para `calc(100dvh - var(--spacing-16) - var(--spacing-8))`: a altura visível da tela menos o cabeçalho do card (semestre e turma) e a folga do topo. Depois da rolagem do D6, o cabeçalho do card e a área inteira cabem na tela de 780 px de altura. `dvh` acompanha a barra de endereço do navegador do celular, que `vh` ignora.

### D8. Horário centralizado na célula

Em qualquer largura, o início e o fim de cada faixa ficam no centro da célula da coluna de horários, na horizontal e na vertical (`text-align: center` e `vertical-align: middle`), e a palavra "Horário" do canto fica centralizada na horizontal (pedido do autor em 02/10/2026). Com a aula de várias faixas ou com cards altos, a linha fica alta e o horário no topo ficava longe do meio do bloco. A regra vale só para `.timetable-grid.is-public`; a Grade autenticada continua com o horário no topo.

## Risks / Trade-offs

- **[Card alto]** Com cerca de 139 px por dia em 360 px, o card completo fica mais alto que no desktop. A rolagem vertical acontece dentro da área, com o cabeçalho dos dias fixo.
- **[Rolagem automática]** Quem troca o curso e ainda quer mudar as datas precisa voltar ao topo. O autor preferiu chegar direto ao calendário.
- **[Container query e `dvh`]** Exigem navegadores de 2023 em diante (Safari 16, Chrome 105). Sem suporte, a coluna volta à largura atual e a altura a `75vh`, que é o comportamento de hoje.
- **[Encaixe obrigatório]** Com `mandatory`, a rolagem pelo teclado também encaixa por dia, o que é o comportamento esperado numa Grade de dias.

## Visual

Sem imagem de referência: o autor pediu para manter o card como está (02/10/2026), e a mudança é só de largura, encaixe e rolagem.

### Adaptado

- Cabeçalho curto no celular: o mesmo padrão da Grade mensal (`timetable_head.html`), com o nome completo no `aria-label`.

### Retirado

- Card resumido com folha de detalhes, filtros recolhidos numa linha de resumo e três dias por tela: considerados e descartados pelo autor.

### Tokens novos

Nenhum. A sombra da borda usa `--color-control-border`, que já tem par de contraste.
