## 1. Prévia visual para aprovação

- [x] 1.1 Montar `grade-previa.html`, estático, com os tokens da `previa.html` e dados reais da planilha de referência
- [x] 1.2 Resolver com o autor as perguntas em aberto do `design.md` e registrar as respostas
- [x] 1.3 Registrar no `design.md` o que o autor ajustou na prévia: filtro por sala, dias nas colunas, sem intervalos, turmas juntas e choque, cor pela etapa (D3, D6, D12, D13, D14)
- [x] 1.4 Commit

## 2. Estrutura da Grade

- [x] 2.1 Criar `schedule/timetable.py` com as dataclasses `RoomWeek`, `Day`, `Cell`, `Continued` e `Entry` (D4)
- [x] 2.2 Criar a leitura das atividades da importação numa consulta, com o catálogo montado pelas linhas `SALA` e `DOCENTE` e cada atividade interpretada com `parse_weekday`, `parse_slot`, `split_header`, `Catalog.build` e `resolve`, sem função nova de interpretação de texto (D1, D2)
- [x] 2.3 Criar `room_week_from_import(importation, space_name, today)`: a lista de salas na ordem da planilha, a sala padrão, as faixas das duas abas na ordem do início, os dias de segunda a sexta e o dia atual (D3)
- [x] 2.4 Unir as faixas seguidas com as mesmas entradas e o mesmo estado num bloco com `span`, sem atravessar intervalo (D5, D6)
- [x] 2.5 Classificar a célula com mais de uma turma como turmas juntas ou choque, e contar as faixas com choque da sala e as salas com choque (D13)
- [x] 2.6 Preencher em cada entrada o estado, o texto da planilha, a ação do plano e os números das linhas, e contar as faixas ocupadas e disponíveis, os erros da sala e as linhas com erro fora da Grade (D7, D10)
- [x] 2.7 Testar contra `sources/planilha_example_corrigida.xlsx`: a ordem das salas, a sala padrão, as faixas, um card completo, um bloco de faixas seguidas, um bloco interrompido por intervalo, turmas juntas, choque, as contagens e a sala sem atividade
- [x] 2.8 Testar contra `sources/planilha_example.xlsx` o card com erro, com o texto da planilha e os números das linhas, e a contagem de erros fora da Grade
- [x] 2.9 Testar que a montagem não grava nada e usa uma quantidade fixa de consultas
- [x] 2.10 Commit

## 3. Abas no motor de importação

- [x] 3.1 Acrescentar `tabs` e `review_route` a `ImportScreens`, com os padrões que deixam a importação de usuários igual (D8)
- [x] 3.2 Mover o título, as ações, os alertas, os erros do arquivo e o resumo de `imports/detail.html` para `imports/partials/detail_head.html`, e incluir a navegação entre abas quando houver
- [x] 3.3 Acrescentar o filtro `numero` à tabela de linhas, combinado com o recorte `linhas`, com o link para todas as linhas (D9)
- [x] 3.4 Fazer os links internos da tabela (select de recortes, paginação, "Mostrar todas as linhas") usarem a rota da Conferência
- [x] 3.5 Testar a importação de usuários sem abas e sem mudança de comportamento, o filtro `numero` com um, dois e nenhum número válido, e o número inválido descartado com 200
- [x] 3.6 Commit

## 4. Tela da Grade

- [ ] 4.1 Criar a rota `ensalamento/importacoes/<pk>/conferencia/` com o nome `space_allocation_import_review` para a view atual, e pôr `SpaceAllocationImportGridView` no nome `space_allocation_import_detail`, com `login_required`, `ENSALAMENTO.IMPORTAR` e o `audit_resource` da importação (D8)
- [ ] 4.2 Criar o formulário do filtro `sala`, com as salas na ordem da planilha e a marca das salas com choque, caindo no padrão quando o valor não existe (D3, D13)
- [ ] 4.3 Criar os templates da Grade em `schedule/templates/schedule/`: o select de sala e o semestre, a faixa de situação, a tabela da semana com o cabeçalho e a coluna de horário fixos, o dia atual, os blocos com `rowspan`, a legenda e o estado da importação recusada
- [ ] 4.4 Criar o card com a disciplina, a turma com o curso e o docente, a cor da etapa, os grupos de turmas juntas e de choque, e o card com erro com ícone, texto, dica e link para a Conferência (D7, D12, D13)
- [ ] 4.5 Trocar a sala pelo htmx, atualizando só a Grade e a URL, e manter o botão "Mostrar" para quem está sem JavaScript
- [ ] 4.6 Criar a versão abaixo de 640 px, com os dias um abaixo do outro e só as faixas com atividade (D3)
- [ ] 4.7 Acrescentar ao `app.css` os tokens da etapa, com os pares em `ui/contrast.py`, e os componentes da Grade e das abas; copiar os ícones do Lucide que faltarem (D14)
- [ ] 4.8 Testar cada rota nas quatro situações das convenções
- [ ] 4.9 Testar a Grade padrão, a sala na URL, a sala inexistente caindo no padrão, o dia atual e o fim de semana, o card com erro levando à Conferência com os números certos, as turmas juntas, o choque, as contagens e a importação recusada sem grade
- [ ] 4.10 Testar que o envio, a confirmação e o descarte continuam levando à rota do detalhe, que agora mostra a Grade, e que o choque não impede a confirmação
- [ ] 4.11 Commit

## 5. Fechamento

- [ ] 5.1 Importar as duas planilhas de referência no banco `visual_check` e conferir as telas no navegador nas larguras de 360, 640, 1.024 e 1.280 px, pelo teclado, sem JavaScript e com zoom de 200%, comparando com `grade-previa.html`, e registrar no `design.md` o que foi ajustado
- [ ] 5.2 Medir o tempo de resposta da Grade com a planilha de referência e registrar no `design.md`
- [ ] 5.3 Conferir que os deltas de `ensalamento` e `importacao-planilhas` descrevem o que foi implementado, ajustando o que divergir
- [ ] 5.4 Registrar em `openspec/conventions.md` a exceção da célula vazia da Grade e qualquer outra preferência nova
- [ ] 5.5 Rodar a suíte inteira com `make test`
- [ ] 5.6 Commit
