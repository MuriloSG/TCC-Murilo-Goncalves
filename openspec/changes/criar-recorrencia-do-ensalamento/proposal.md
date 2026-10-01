## Why

Toda aula do ensalamento nasce da planilha. A Change `alterar-recorrencia-do-ensalamento` já permite mudar uma recorrência existente a partir de uma data, mas uma aula que não veio na planilha — uma disciplina que entrou depois do envio, uma turma que ganhou um horário novo no meio do semestre — só existe no sistema se a planilha inteira for reimportada. A coordenação precisa cadastrar essa aula direto na Grade, com a mesma conferência de conflito e a mesma auditoria da alteração, e sem que a próxima importação a apague.

## What Changes

- **Criação da recorrência pela interface**: uma alocação nova com semestre, turma, disciplina, docentes, espaço, dia da semana, horário e vigência, com origem `MANUAL`, gravada numa transação com auditoria.
- **Aula de mais de uma faixa**: a duração é informada em faixas seguidas do semestre, e cada faixa vira uma alocação do bloco, como no ensalamento importado e na alteração da recorrência.
- **Vigência**: início obrigatório, de hoje em diante e no período do semestre; fim opcional, que vazio vale até o fim do semestre. O início DEVE ser uma data do dia da semana escolhido.
- **Conflitos**: recusa quando o espaço está ocupado por outra aula que forma choque ou por agendamento aprovado em alguma ocorrência da vigência, e quando a turma já tem a mesma disciplina no mesmo dia e faixa num período que se sobrepõe. Turma junta continua aceita. São as mesmas conferências da alteração da recorrência, reaproveitadas.
- **Reimportação**: a alocação criada no sistema tem vigência definida, então a planilha não a altera nem a recria, e a linha recebe o mesmo aviso da versão manual.
- **Permissão** `ENSALAMENTO.CRIAR_RECORRENCIA`, concedida ao perfil de sistema `ADMINISTRADOR`, separada de `ENSALAMENTO.ALTERAR_RECORRENCIA` e de `ENSALAMENTO.IMPORTAR`. O superadmin executa sem a permissão concedida, pela regra de `User.has_perm` que já vale no sistema inteiro.
- **Usabilidade**: a ação abre da faixa disponível da Grade datada, já com o semestre, o espaço, o dia, a data e o horário daquela célula preenchidos, e também por um botão no cabeçalho da Grade, sem nada preenchido. O formulário fica em modal, com os campos de escolha com busca, e mostra o resumo "A aula" / "Quando" / "Onde", com a quantidade de ocorrências geradas, antes da confirmação.
- **Auditoria**: registro de criação no módulo `ENSALAMENTO`, com a aula, a vigência e o espaço.

### Fora do escopo

- Excluir uma alocação criada no sistema, encerrar a recorrência inteira e editar os dados de identidade fora da alteração da recorrência, que já existe.
- Criar disciplina, turma, docente, espaço, semestre ou faixa de horário a partir deste formulário: todos são escolhidos entre os já cadastrados.
- Criação em lote, cópia de uma aula para outra turma e criação por docente.
- Notificação de quem é afetado pela aula nova.

### Dependência

Esta Change parte da Change `alterar-recorrencia-do-ensalamento`, já arquivada, de onde vêm a vigência da alocação, as conferências de conflito e o padrão de modal com resumo. Quando a Change `selecionar-opcoes-com-busca` estiver arquivada, os campos de escolha única deste formulário DEVEM usar o componente dela; até lá, usam o `<select>` nativo, como as demais telas.

## Capabilities

### Modified Capabilities

- `ensalamento`: criação da recorrência pela interface, com vigência, bloco de faixas, conferência de conflito e origem `MANUAL`.
- `controle-acesso`: permissão `ENSALAMENTO.CRIAR_RECORRENCIA`.
- `auditoria`: registro da criação da alocação.

## Impact

- `schedule/models.py`: `plan_creation` e `create_recurrence` no `AllocationManager`, `RecurrenceCreation` e a generalização de `check_duplicates` e `check_conflicts` para um plano sem alocação atual.
- `schedule/forms.py`, `schedule/views.py`, `schedule/urls.py`, `schedule/templates/schedule/grid.html` e os templates do modal e do resumo.
- `accounts/permissions.py`, `audit/catalog.py`, `ui/styles/app.css`.
- Migration `accounts/0013_create_recurrence_permission`. Nenhuma migration em `schedule`: os campos já existem.
