# Design

## Contexto

A vigência da alocação já existe e a alteração da recorrência já encerra uma alocação na véspera de uma data, só que sempre criando uma versão nova no lugar. Encerrar é a mesma metade do trabalho, sem a segunda. O que falta decidir é o que significa encerrar uma aula que ainda não começou e como o encerramento aparece na Grade.

## D1. Encerrar é dar fim à vigência, não excluir

As alocações continuam no banco com `valid_until` preenchido. É o que preserva as ocorrências passadas na Grade, na Agenda, no calendário público e na auditoria, e o que faz a reimportação tratar a aula como definida no sistema e não recriá-la, pela regra que `AllocationManager.apply` já aplica a toda alocação com vigência.

**Alternativa recusada:** excluir as linhas. A spec proíbe excluir alocação, o histórico de ocupação do espaço se perderia e a planilha recriaria a aula na importação seguinte.

## D2. Fim anterior ao início significa recorrência sem ocorrência

Encerrar uma aula a partir da própria data de início deixaria `valid_until` um dia antes de `valid_from`, que a `CheckConstraint` atual recusa. Em vez de proibir o caso — que é o da aula cadastrada por engano, ainda sem nenhuma aula dada —, a vigência passa a admitir esse par, com o significado de recorrência encerrada sem nenhuma ocorrência.

Nada muda em `occurs_on` nem em `active_on`: as duas já comparam a data com o início e com o fim, e nenhuma data satisfaz as duas comparações quando o fim é anterior ao início. Com isso nenhum par de datas é inválido — a alocação da planilha, que tem só o fim, já era um par legítimo —, e a `CheckConstraint` sai em vez de ser substituída.

**Alternativa recusada:** um campo `is_closed` à parte. Seria um segundo lugar para a mesma informação, com o risco de divergir de `valid_until` e de obrigar toda consulta de ocorrência a olhar os dois.

## D3. A data do encerramento é uma ocorrência da aula

As mesmas regras da alteração, menos uma: de hoje em diante, dentro do período do semestre e uma data em que a aula acontece. A exigência de ser posterior ao início da vigência não vale aqui, porque encerrar desde o primeiro dia é um caso legítimo (D2). Exigir que a data seja uma ocorrência mantém a ação ancorada no card da Grade, que é de onde ela é aberta.

## D4. Confirmação, e não formulário

Encerrar não tem dados a informar: a data vem do card acionado. É um `ConfirmedActionView`, como o cancelamento de ocorrência, e não o modal de duas etapas da alteração e do cadastro. A confirmação diz quantas aulas deixam de existir, a partir de quando, e que as anteriores continuam, para que a consequência fique explícita antes do POST. A contagem é calculada por `plan_ending`, sem gravar nada.

## D5. As exceções continuam onde estão

As ocorrências canceladas da aula não são apagadas nem transferidas: elas pertencem à alocação, que continua existindo. As anteriores ao encerramento seguem descrevendo o que aconteceu; as posteriores deixam de ter efeito, porque a data já não é ocorrência, e nenhuma delas conta na quantidade mostrada na confirmação.

## D6. Permissão própria

`ENSALAMENTO.ENCERRAR_RECORRENCIA` é separada de alterar, cadastrar e cancelar: encerrar uma aula do semestre inteiro é uma decisão maior do que mover um horário, e ser docente da aula não a concede. O superadmin executa sem a permissão concedida, pela regra geral de `User.has_perm`, sem que nenhuma view ou template leia `is_superadmin`.
