## 1. Decisões e prévia visual

- [x] 1.1 Resolver com o autor o histórico da reimportação, a faixa disponível, as reservas e a recorrência futura, e registrar no `design.md`
- [ ] 1.2 Resolver com o autor as decisões pendentes do `design.md`: a referência visual do mês (P1), o conteúdo do dia (P2), a cor da tira (P3), a permissão e o período sugerido do modal (D3)
- [ ] 1.3 Montar `grade-mensal-previa.html`, estático, com os tokens da `previa.html`, a semana com datas e navegação, a célula disponível vazia e o mês como mapa de ocupação, com dados reais da planilha de referência
- [ ] 1.4 Registrar no `design.md` o que foi adaptado e retirado da referência
- [ ] 1.5 Commit

## 2. Período do semestre

- [x] 2.1 Acrescentar `start_date` e `end_date` ao `Semester`, com a restrição de início anterior ou igual ao fim, e a migration (D2)
- [x] 2.2 Criar `Semester.define_period`, com as recusas de início depois do fim, de uma data sem a outra e de período maior que 366 dias
- [x] 2.3 Acrescentar o recurso `SEMESTRE` ao catálogo da auditoria
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

- [ ] 5.1 Criar `Month`, `MonthWeek` e `MonthDay` em `timetable.py`, montados das mesmas ocorrências e faixas da semana, com a ocupação de cada dia conforme a decisão P2 (D8)
- [ ] 5.2 Acrescentar `mes` ao formulário e a alternância "Semana" e "Mês" preservando a data de referência
- [ ] 5.3 Criar os templates do mês, com os dias como links para a semana, a navegação e a lista abaixo de 640 px; estilos no `app.css` e ícones do Lucide que faltarem
- [ ] 5.4 Testar o mês com aula semanal, o mesmo resultado nas duas visões, o dia que abre a semana, o limite do semestre e o mês inválido
- [ ] 5.5 Commit

## 6. Modal do período

- [ ] 6.1 Criar a rota `ensalamento/semestres/<code>/periodo/` com `login_required`, a view sobre `ModalView` com `ENSALAMENTO.IMPORTAR`, o formulário e a auditoria (D3)
- [ ] 6.2 Pôr o aviso e o botão "Definir período" na Grade, só para quem tem a permissão
- [ ] 6.3 Testar a rota nas quatro situações das convenções, a definição com a auditoria, a recusa como erro do formulário e o botão escondido
- [ ] 6.4 Commit

## 7. Fechamento

- [ ] 7.1 Conferir as telas no navegador pelo banco `visual_check`, nas larguras de 360, 640, 1.024 e 1.280 px, pelo teclado, sem JavaScript e com zoom de 200%, comparando com a prévia
- [ ] 7.2 Medir o tempo de resposta da semana e do mês com a planilha de referência e registrar no `design.md`
- [ ] 7.3 Conferir que o delta de `ensalamento` descreve o que foi implementado
- [ ] 7.4 Registrar em `openspec/conventions.md` a célula disponível vazia com o nome acessível e qualquer outra preferência nova
- [ ] 7.5 Rodar a suíte inteira com `make test`
- [ ] 7.6 Commit
