## 1. Decisões e prévia visual

- [x] 1.1 Resolver com o autor o histórico da reimportação, a faixa disponível, as reservas e a recorrência futura, e registrar no `design.md`
- [x] 1.2 Resolver com o autor a forma da visão mensal, a permissão e o período sugerido do modal (D3, D8)
- [x] 1.3 Montar `grade-mensal-previa.html`, estático, com os tokens da `previa.html` e o mês como a Grade semanal expandida, com dados reais da planilha de referência
- [x] 1.4 Obter do autor a aprovação da prévia (P1) e a decisão sobre a sala no card (P4)
- [x] 1.5 Registrar no `design.md` o que o autor ajustar na prévia
- [x] 1.6 Commit

## 2. Período do semestre

- [x] 2.1 Acrescentar `start_date` e `end_date` ao `Semester`, com a restrição de início anterior ou igual ao fim, e a migration (D2)
- [x] 2.2 Criar `Semester.define_period`, com as recusas de início depois do fim, de uma data sem a outra e de período maior que 366 dias
- [x] 2.3 Acrescentar o recurso `SEMESTRE` ao catálogo da auditoria (retirado pela etapa 8)
- [x] 2.4 Testar a operação, as recusas sem alteração e a importação que não mexe no período
- [x] 2.5 Commit

## 3. Cálculo das ocorrências

- [x] 3.1 Criar `schedule/occupancy.py` com `Occurrence`, `AllocationSource`, `occupancy` e `grid_sources` (D4, D6)
- [x] 3.2 Testar a aula semanal numa semana, a data fora do período, o semestre sem período, a alocação sem espaço e o intervalo que atravessa dois semestres
- [x] 3.3 Testar que o cálculo não grava nada e usa a mesma quantidade de consultas numa semana, num mês e no semestre inteiro
- [x] 3.4 Testar a montagem com uma fonte de teste a mais
- [x] 3.5 Commit

## 4. Visão semanal com datas

- [x] 4.1 Levar `Week` e `Day` para datas, com "Fora do semestre", o estado da célula e "Hoje" pela data, montados das ocorrências (D7, D9)
- [x] 4.2 Acrescentar `visao` e `semana` ao `GridFilterForm`, com o padrão e o valor inválido caindo nele
- [x] 4.3 Manter a semana típica sem datas quando o semestre não tem período, com o aviso
- [x] 4.4 Atualizar `grid.html` e a célula: datas nos dias, intervalo no título, navegação por links com htmx e sem JavaScript, e a célula disponível vazia com o nome acessível, e o total de disponíveis no título do dia abaixo de 640 px
- [x] 4.5 Testar a semana padrão dentro, antes e depois do período, a navegação, a semana parcial, a semana inválida, as contagens e a faixa disponível
- [x] 4.6 Commit

## 5. Visão mensal

Só depois da tarefa 1.4.

- [x] 5.1 Generalizar `build_week` e `dated_space_week` para uma lista de datas, montando o mês com a mesma estrutura da semana, sem estrutura própria do mês (D8)
- [x] 5.2 Acrescentar `visao` e `mes` ao formulário, o padrão e o valor inválido, e o campo de seleção "Visualização" (Semana e Mês) mantendo os filtros e a data de referência
- [x] 5.3 Criar o template do mês sobre as mesmas células da semana: cabeçalho com dia e dia da semana, separador de semanas, coluna de horários e linha dos dias fixas, rolagem horizontal só na área da Grade, "Hoje" rolando até a coluna do dia
- [x] 5.4 Testar o mês com aula semanal, as mesmas células nas duas visões, turmas juntas, o limite do semestre, o mês inválido e a quantidade fixa de consultas
- [x] 5.5 Conferir no navegador a rolagem em 360 e 1.280 px e medir o tempo de resposta do mês
- [x] 5.6 Commit

## 6. Modal do período

Substituída pela etapa 8: o período passou para a importação (D3 revisto).

- [x] 6.1 Criar a rota `ensalamento/semestres/<pk>/periodo/` (pela chave, porque o código tem barra) com `login_required`, a view sobre `ModalView` com `ENSALAMENTO.IMPORTAR`, o formulário e a auditoria (D3)
- [x] 6.2 Pôr o aviso e o botão "Definir período" na Grade, só para quem tem a permissão
- [x] 6.3 Testar a rota nas quatro situações das convenções, a definição com a auditoria, a recusa como erro do formulário e o botão escondido
- [x] 6.4 Commit

## 6a. Turmas juntas e choque

- [x] 6a.1 Classificar a célula como uma turma, turmas juntas ou choque, pelas entradas dela, em `Cell` (D9a)
- [x] 6a.2 Agrupar os cards no parcial da célula, com os estilos da Grade da importação, na tabela e abaixo de 640 px
- [x] 6a.3 Testar a classificação e o agrupamento na semana datada
- [x] 6a.4 Commit

## 8. Período informado na importação (D3 revisto)

Decisões aprovadas pelo autor em 25/09/2026.

- [x] 8.1 Tirar o modal da Grade: `SemesterPeriodView`, `SemesterPeriodForm`, a rota `semester_period`, os templates `semester_period*.html`, o botão "Definir período" e os testes do modal
- [x] 8.2 Tirar a auditoria própria de `Semester.define_period`, que passa a devolver se o período mudou, e o recurso `SEMESTRE` do catálogo
- [x] 8.3 Acrescentar ao motor os ganchos `clean_upload(values)` e `upload_display(label, value)`, com testes na importação de usuários sem mudança de comportamento
- [x] 8.4 Acrescentar à importação de ensalamento os campos próprios "Início do semestre" e "Fim do semestre", as colunas lógicas `Início` e `Fim`, a validação conjunta pelo model (datas juntas, obrigatórias no semestre novo ou sem período) e a exibição em dd/mm/aaaa
- [x] 8.5 Aplicar o período em `lock()`, depois de resolver o semestre, só com as duas datas; em branco, preservar
- [x] 8.6 Acrescentar o período informado e o anterior aos metadados do resumo auditado
- [x] 8.7 Trocar o aviso da Grade sem período pelo texto que aponta para a importação
- [x] 8.8 Testar: primeira importação com período, prévia e descarte sem alteração, divergência do plano sem alteração, reimportação com datas novas e em branco, datas recusadas no envio, datas obrigatórias no semestre novo ou sem período, auditoria, Grade sem ação de período e aviso
- [x] 8.9 Conferir no navegador o envio com as datas e a Grade, e rodar `make test`
- [x] 8.10 Commit

## 7. Fechamento

- [x] 7.1 Conferir as telas no navegador pelo banco `visual_check`, nas larguras de 360, 640, 1.024 e 1.280 px, pelo teclado, sem JavaScript e com zoom de 200%, comparando com a prévia
- [x] 7.2 Medir o tempo de resposta da semana e do mês com a planilha de referência e registrar no `design.md`
- [x] 7.3 Conferir que o delta de `ensalamento` descreve o que foi implementado
- [x] 7.4 Registrar em `openspec/conventions.md` a célula disponível vazia com o nome acessível e qualquer outra preferência nova
- [x] 7.5 Rodar a suíte inteira com `make test`
- [x] 7.6 Commit
