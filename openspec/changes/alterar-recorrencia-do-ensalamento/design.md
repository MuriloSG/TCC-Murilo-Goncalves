## Context

`Allocation` é a regra semanal (semestre, turma, disciplina, dia, faixa, espaço, docentes, origem). A identidade usada pela importação é `(semestre, turma, dia, faixa, disciplina)`, e `AllocationManager.apply` cria ou atualiza espaço e docentes por ela. As ocorrências são calculadas por `Allocation.occurs_on` (Grade, calendário público, cancelamento) e por `Allocation.objects.active_on` (conflito da Agenda). `AllocationException` cancela uma ocorrência sem alterar a regra.

## Goals / Non-Goals

**Goals:** alterar a regra a partir de uma data preservando o histórico, sem ocorrência duplicada, sem perder exceção, sem choque, atômico, auditado e resistente à reimportação.

**Non-Goals:** encerrar a recorrência sem versão nova, editar turma ou disciplina, relação alocação e usuário, histórico próprio fora da auditoria.

## Decisions

### D1. Vigência na própria alocação
`valid_from` e `valid_until` (datas, vazias = limites do semestre). A alteração encerra a alocação atual (`valid_until = corte - 1`) e cria outra com `valid_from = corte` e o `valid_until` da anterior. As versões não se sobrepõem, então nenhuma data tem duas aulas. A restrição de identidade passa a incluir `valid_from` com `nulls_distinct=False`, e uma `CheckConstraint` garante `valid_from <= valid_until`. Sem FK entre versões: a auditoria liga a original à nova.

Alternativa descartada: tabela de versões separada. Exigiria mudar todas as leituras, e a vigência na própria linha é suficiente.

### D2. Campos alteráveis
Dia da semana, horário, espaço e docentes. Turma, disciplina e semestre são a aula; mudá-los seria outra aula. A versão nova tem origem `MANUAL`.

### D3. Horário do bloco
Um card da Grade reúne alocações de faixas seguidas. O bloco muda inteiro: o formulário oferece os intervalos com a mesma quantidade de faixas seguidas do semestre, e cada alocação vai para a faixa correspondente. Nenhuma faixa é criada.

### D4. Data de corte
De hoje em diante, dentro do período do semestre, ocorrência da regra atual (dia da semana e vigência) e posterior ao início da vigência, para que a versão encerrada guarde ao menos o dia inicial.

### D5. Exceções
As exceções anteriores ao corte ficam na alocação encerrada. As do corte em diante passam para a versão nova quando a data é ocorrência dela (mesmo dia da semana), com auditoria. Se alguma não for, a alteração é recusada com as datas, e nada é removido.

### D6. Conflitos
A conferência usa as fontes da Grade (`grid_sources()`), do corte ao fim da vigência, que já deixam de fora as ocorrências canceladas e respeitam a vigência. É conflito: agendamento aprovado sobreposto, ou aula de outra alocação sobreposta com disciplina ou docentes diferentes (o choque da Grade). Aula com a mesma disciplina e os mesmos docentes é turma junta e é aceita. A mesma turma com a mesma disciplina no mesmo dia e faixa vigente no período é recusada. A importação continua sem detectar conflito (D8 da Change importar-ensalamento-da-planilha).

### D7. Reimportação
`apply` procura todas as alocações da identidade. Se alguma tem vigência definida, nada é alterado e a linha é `unchanged` com o aviso `recorrencia_alterada`. Assim a planilha não reescreve a sala da versão encerrada nem recria a regra antiga depois de uma troca de dia. Uma identidade nova da planilha continua sendo criada.

### D8. Transação, permissão e auditoria
`change_recurrence` roda numa transação: trava as alocações, confere `ENSALAMENTO.ALTERAR_RECORRENCIA`, as regras D3 a D6, encerra, cria, move as exceções e grava a auditoria. Qualquer recusa ou falha desfaz tudo. `plan_recurrence` faz a mesma conferência sem gravar, para o resumo. Cada alocação alterada gera `ALTERAR` no módulo `ENSALAMENTO`, com os campos alterados em `old_values`/`new_values` e, em `metadata`, a identificação da original, `a_partir_de`, `vigente_ate`, `nova_alocacao` e `excecoes_transferidas`. O ator vem do contexto da requisição, como no resto da auditoria.

### D9. Interface
Ícone "Alterar recorrência" no card da Grade datada, só para quem tem a permissão e só de hoje em diante. O modal (`OperationFormView`) traz o aviso de que a mudança vale para todas as aulas a partir da data, o formulário com os valores atuais e, no primeiro envio, o resumo "Antes / A partir de / Depois" com as exceções que continuam canceladas. O segundo envio executa e volta à Grade na semana do corte e na sala nova.

## Risks / Trade-offs

- A planilha deixa de atualizar aulas com versão manual. É o comportamento desejado, e o aviso da linha mostra isso a quem importa.
- A regra de conflito existe só na alteração manual. A importação pode continuar trazendo choques da planilha.
- Uma alteração no primeiro dia da vigência é recusada; antes do início do semestre, corrigir a sala continua sendo pela reimportação.
