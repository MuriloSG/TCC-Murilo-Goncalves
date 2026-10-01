# Design

## Contexto

A alocação já tem vigência (`valid_from`, `valid_until`), origem (`IMPORTADA` ou `MANUAL`) e um conjunto de conferências escrito para a alteração da recorrência: `check_cut`, `consecutive_slots`, `interval_choices`, `check_duplicates` e `check_conflicts`. Criar uma aula pela interface é o mesmo plano sem a parte "encerrar a versão atual". O trabalho é generalizar o plano, e não escrever uma segunda regra de conflito.

## D1. O plano de criação reaproveita o plano de alteração

`RecurrencePlan` passa a aceitar mudanças sem alocação atual. A alteração continua usando `RecurrenceChange` (`current` + `version`); a criação usa `RecurrenceCreation`, com `version`, `teachers` e `execute`, sem `current`. `check_duplicates` e `check_conflicts` passam a ler só `plan.changes[*].version`, o conjunto de pks travados (vazio na criação) e `plan.cut` (o início da vigência, na criação).

**Alternativa recusada:** copiar as duas conferências para funções próprias da criação. Duas cópias da regra de choque divergem na primeira correção, e a regra de conflito é o núcleo do requisito.

## D2. A vigência é o período informado, não o semestre inteiro

Toda alocação criada no sistema tem `valid_from` preenchido, mesmo quando começa no primeiro dia do semestre. É isso que faz a reimportação tratá-la como versão manual (`is_versioned`) e não reescrevê-la — a regra já implementada em `AllocationManager.apply`. O fim fica vazio quando a aula vale até o fim do semestre, e `Allocation.ends` já resolve o vazio para `semester.end_date`.

## D3. O início da vigência é uma data, não um dia da semana solto

O formulário pede a data da primeira aula. O dia da semana vem dela e não é um campo: escolher "terça-feira" e a data 05/10 (uma segunda) é um erro que o usuário não tem como perceber no resumo. A conferência é a mesma de `check_cut`, sem a parte "ocorrência da regra atual" e sem a parte "posterior ao início da vigência", que só existem na alteração. A parte comum — de hoje em diante, dentro do período do semestre — vira `check_start`, usada pelas duas.

## D4. Duração em faixas seguidas

O campo "Duração" lista as quantidades possíveis a partir do horário escolhido (1 faixa, 2 faixas seguidas, ...), calculadas por `consecutive_slots`. Cada faixa vira uma alocação com a mesma identidade, como já acontece no ensalamento importado: o bloco da Grade é a leitura, e não a gravação. Nenhuma faixa de horário é criada pelo formulário; um horário sem a quantidade de faixas seguidas pedidas é recusado com "Escolha um horário do semestre".

## D5. Espaço opcional

O espaço pode ficar vazio, como na planilha, que traz atividade sem sala. Sem espaço não há conferência de conflito, porque a aula não ocupa espaço nenhum. Só espaços ativos são oferecidos.

## D6. Docentes continuam sem vínculo com usuário

Os docentes são escolhidos entre os já cadastrados, em campo de seleção múltipla. O componente de busca da Change `selecionar-opcoes-com-busca` não cobre seleção múltipla, então este campo permanece como está até existir um componente múltiplo. A oferta (`ClassOffering.objects.record`) é sincronizada depois de gravar, como na alteração da recorrência.

## D7. Entrada pela célula disponível da Grade

A faixa disponível da Grade datada ganha um gatilho que abre o modal com semestre, espaço, data e horário daquela célula preenchidos; falta informar turma, disciplina, docentes e duração. A célula continua visualmente vazia, com o estado em `sr-only`, como a Change `definir-texto-da-interface` exige: o gatilho ocupa a célula inteira e tem `aria-label` com o dia, a data, o horário e "Cadastrar aula". O botão no cabeçalho da Grade abre o mesmo modal sem preenchimento. A Grade sem data (visão por semana genérica) não mostra a ação, porque não há data de início para preencher.

Esconder a ação não é a proteção: a view declara a permissão e o model a confere de novo, como no resto do projeto.

## D8. Resumo antes de confirmar

O primeiro envio chama `plan_creation`, que confere tudo sem gravar e devolve o plano; a tela mostra "A aula" (turma, disciplina, docentes), "Quando" (dia, horário, vigência e a quantidade de ocorrências geradas) e "Onde" (espaço), com o botão "Cadastrar aula". O envio com `confirmar` chama `create_recurrence`, que confere de novo dentro da transação. É o fluxo de `RecurrenceChangeView`, que a view nova herda de `OperationFormView` do mesmo jeito.

## D9. Superadmin sem permissão concedida

Nada é escrito para isso. `User.has_perm` já devolve verdadeiro para o superadmin ativo em qualquer permissão fora das reservadas, e a permissão nova não é reservada. A view, o middleware e o model continuam decidindo só por `has_perm`, sem ler `is_superadmin`, como a seção 4 das convenções exige. O comportamento entra como cenário da spec para ficar protegido por teste.
