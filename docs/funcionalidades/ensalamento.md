# Ensalamento

Ocupação regular dos espaços pelas aulas de cada semestre. Implementação: app `schedule`. Regras em [regras de negócio](../regras/regras-de-negocio.md#ensalamento).

## Conceitos

| Conceito | Model | Observação |
|---|---|---|
| Semestre | `Semester` | Código `AAAA/1` ou `AAAA/2`. Período (`start_date`, `end_date`) opcional, de até 366 dias |
| Faixa de horário | `TimeSlot` | Início e fim, por semestre, criados pela importação |
| Alocação | `Allocation` | Regra semanal: semestre, turma, disciplina, dia (segunda a sexta), faixa, espaço opcional, docentes opcionais, vigência opcional |
| Ocorrência | `schedule.occupancy.Occurrence` | A alocação numa data. Calculada, nunca gravada |
| Exceção | `AllocationException` | Ocorrência cancelada numa data. Único tipo: `CANCELADA` |
| Oferta | `ClassOffering` | Disciplina oferecida a uma turma num semestre |
| Vínculo docente | `TeachingAssignment` | Docente de uma oferta, `is_current` indica se está nas alocações atuais |

Uma aula de várias faixas seguidas é um bloco de várias alocações, uma por faixa. As ações da Grade recebem os IDs de todas as alocações do bloco.

## Grade

Rota `/ensalamento/` (`SpaceAllocationGridView`), permissão `ENSALAMENTO.VISUALIZAR`.

- Filtros: semestre, sala e visualização (semana ou mês). O semestre padrão é o do dia (janeiro a junho = `/1`); as opções são ele e os semestres com alocação. A sala padrão é a primeira em ordem natural (`1/4` antes de `1/10`).
- Salas listadas: as ativas, com ou sem aula, e as inativas que têm aula no semestre (`timetable.listed_spaces`).
- Com período definido, a semana é datada e navegável (`semana`, `mes`). Sem período, mostra a semana típica com aviso.
- A célula reúne as ocorrências do ensalamento e os agendamentos aprovados da Agenda. Duas turmas na mesma faixa com a mesma disciplina e os mesmos docentes são "turmas juntas"; qualquer outra combinação é choque, só sinalizado.
- Ações por bloco, conforme a permissão: cancelar ocorrência, alterar recorrência, encerrar recorrência, e cadastrar aula numa faixa vazia.
- "Ver exceções" (`/ensalamento/excecoes/`) lista as ocorrências canceladas. Quem tem `ENSALAMENTO.CANCELAR_OCORRENCIA` vê todas; o docente vê as das próprias aulas.

## Operações sobre as aulas

Todas exigem uma data de hoje em diante, dentro do período do semestre, e gravam auditoria no módulo `ENSALAMENTO` ou `EXCECAO_ENSALAMENTO`. As três de recorrência abrem em modal com resumo antes da confirmação e conferem tudo de novo ao gravar.

| Operação | Rota | Permissão da rota | Conferência no model | Método |
|---|---|---|---|---|
| Cancelar ocorrência | `/ensalamento/ocorrencias/cancelar/` | `ENSALAMENTO.VISUALIZAR` | `ENSALAMENTO.CANCELAR_OCORRENCIA` ou ser docente da aula | `AllocationException.objects.cancel` |
| Alterar recorrência | `/ensalamento/recorrencias/alterar/` | `ENSALAMENTO.ALTERAR_RECORRENCIA` | a mesma | `Allocation.objects.change_recurrence` |
| Cadastrar aula recorrente | `/ensalamento/recorrencias/criar/` | `ENSALAMENTO.CRIAR_RECORRENCIA` | a mesma | `Allocation.objects.create_recurrence` |
| Encerrar recorrência | `/ensalamento/recorrencias/encerrar/` | `ENSALAMENTO.ENCERRAR_RECORRENCIA` | a mesma | `Allocation.objects.end_recurrence` |

**Cancelar ocorrência.** Cria uma `AllocationException` por alocação do bloco, sem alterar a regra semanal. Recusa data que não é ocorrência e ocorrência já cancelada. Alocação inexistente ou de outro docente responde 404. A mesma operação existe na Agenda (`/agenda/ocorrencias/cancelar/`, rota com `AGENDA.VISUALIZAR`).

**Alterar recorrência.** Muda, a partir de uma data de corte, o dia, o horário de início, a duração (quantidade de faixas), o espaço e os docentes. Cada alocação atual recebe `valid_until` na véspera do corte e uma nova versão começa no corte (`valid_from`), com origem `MANUAL`. Exceções do corte em diante passam para a versão nova. Ao aumentar a duração, as faixas novas recebem cópia das ocorrências canceladas; ao diminuir, as faixas que sobram só são encerradas.

**Cadastrar aula recorrente.** Turma, disciplina, docentes (opcionais), espaço (opcional), primeira aula, última aula (opcional; sem ela vai até o fim do semestre), horário de início e duração. O dia da semana vem da data da primeira aula. Registra a oferta da disciplina para a turma.

**Encerrar recorrência.** Grava `valid_until` na véspera da data em todas as alocações do bloco. Nada é excluído. Encerrar uma aula que ainda não começou deixa a recorrência sem ocorrências.

## Importação da planilha

Rotas em `/ensalamento/importacoes/`. Permissões: `ENSALAMENTO.IMPORTAR` para o fluxo e `ENSALAMENTO.EXCLUIR_IMPORTACAO` para excluir. Definição: `schedule.imports.SpaceAllocationImport`, sobre o [motor de importação](../arquitetura/motor-de-importacao.md).

### Envio

- Arquivo XLSX, até 10 MiB e 5000 linhas lógicas.
- Campos do envio: semestre (`AAAA/1` ou `AAAA/2`), início e fim do período. As datas são obrigatórias quando o semestre é novo ou ainda não tem período; em branco, o período atual é mantido. O período é aplicado ao semestre na execução, junto com as alocações.

### Estrutura esperada

| Aba | Uso |
|---|---|
| `Horário - Graduação` e `Horário - Ensino Médio` | Obrigatórias. Blocos de dia empilhados: coluna A com `DIA` no cabeçalho e o dia da semana, coluna B com a faixa (`07:20 - 08:10`) ou `INTERVALO`/`ALMOÇO`, uma coluna por turma a partir da C. Linha 1 com o nome do curso (células mescladas); primeira linha de cabeçalho com o rótulo da turma |
| `Validação de Dados` | Obrigatória. Coluna A: lista de docentes. Coluna B: lista de salas. Dados a partir da linha 2 |
| `usuários - sistema` | Opcional. Colunas `E-mail`, `Nome`, `Perfil` e `Nome de usuário` |

As demais abas (por exemplo `Ensalamento - Geral` e as abas por docente e por curso) não são lidas.

Recusas do arquivo inteiro: aba obrigatória ausente, blocos de dia não encontrados, dia da semana desconhecido, faixa fora do formato, coluna de turma com atividade sem rótulo ou sem curso.

### Leitura da célula de atividade

`schedule/activities.py` lê o texto do fim para o começo, comparando o conteúdo entre parênteses com os catálogos da aba `Validação de Dados`:

```text
Disciplina (Docente A / Docente B) (Sala)
```

- Comparação exata, ignorando só a caixa e espaços repetidos. Sem similaridade.
- Docentes separados por `/`, `,` ou ` e `. Docente fora do catálogo é erro da linha.
- Uma célula com várias atividades separadas por `/` fora de parênteses vira várias linhas (`Aba!C5#1`, `#2`), desde que cada trecho tenha parênteses.
- Sala fora do catálogo depois de uma lista de docentes conhecidos é nome citado só nas células e entra na classificação dos espaços.
- Erros de linha: sem parênteses, parênteses vazios no lugar da sala, sem disciplina, docente desconhecido, mesma alocação descrita em mais de uma célula.

### Execução

Ordem das linhas: usuários da aba opcional, valores dos catálogos (salas e depois docentes), atividades.

- `lock()` classifica e aplica os espaços, resolve o semestre, aplica o período e trava as alocações do semestre e os usuários da aba.
- Usuários da aba: e-mail novo é cadastrado como na [importação de usuários](autenticacao-e-usuarios.md#importação-de-usuários); usuário existente não é alterado, e a diferença de dados ou a situação inativa vira aviso.
- Atividade: resolve curso, turma, disciplina, faixa e docentes pelo nome, criando o que falta, e chama `Allocation.objects.apply`, que cria a alocação ou atualiza espaço e docentes. Alocação com vigência definida (alterada no sistema) não é tocada, e a linha recebe aviso.
- `finish()` registra as ofertas e sincroniza os vínculos de docente das linhas mantidas, uma vez.
- Nada é excluído. Uma alocação que saiu da planilha continua no banco.
- Reimportar é idempotente: cada item é procurado pela identidade (ver [regras de negócio](../regras/regras-de-negocio.md#importação-da-planilha)) e o registro existente é reaproveitado, com as mesmas chaves. A mesma planilha confirmada de novo não cria nem altera nenhuma linha; uma aula existente só muda de espaço ou de docentes quando a planilha traz outros.
- A importação não confere conflito com agendamentos aprovados e não os altera nem cancela. O choque aparece no painel (ver [painel](painel-e-relatorios.md)).
- A auditoria registra o resumo da importação, não cada entidade. As alterações no cadastro de espaços têm registro próprio no módulo `ESPACO`.

### Espaços encontrados

A classificação (`schedule/spaces.py`) dá a cada nome de sala encontrado uma situação, nesta precedência:

| Situação | Quando | Efeito na confirmação |
|---|---|---|
| Reconhecido | Identifica um espaço ativo pelo nome atual ou por outro nome | Nenhum |
| Decidido | Há decisão gravada | A da decisão |
| Novo proposto | Está na lista de salas, não identifica espaço e não tem parecido | Cadastra o espaço com origem `PLANILHA` |
| Precisa de decisão | Identifica espaço inativo, tem parecido no cadastro ou entre os nomes encontrados, ou foi citado só nas células | Pendência: a importação fica `PENDENTE` |

Toda sala da lista entra na classificação, com ou sem aula, para aparecer com a Grade vazia. A exceção é o nome da lista sem aula que identifica um espaço inativo: ele é ignorado, porque desativar é decisão do cadastro.

Decisões (`SpaceDecision`), tomadas no quadro "Espaços desta importação" do detalhe:

| Decisão | Efeito | Permissões de espaço exigidas |
|---|---|---|
| `NOVO` (é um espaço novo) | Cadastra | `ESPACO.CRIAR` |
| `ASSOCIAR` (é o mesmo que) | Acrescenta o nome como outro nome de um espaço cadastrado ou de outro nome da mesma importação | `ESPACO.EDITAR` |
| `REATIVAR` | Reativa o espaço inativo | `ESPACO.ALTERAR_SITUACAO` |

Gravar ou desfazer uma decisão não altera o cadastro: ela é aplicada na confirmação e pede a atualização da prévia. A sugestão de parecidos (`schedule/similarity.py`) é heurística e nunca associa sozinha: junta nomes iguais sem espaços, pontos, hífens, acentos, caixa e zeros à esquerda (`HV5` e `HV 5`) e nomes que diferem por número ou romano no fim (`Lab. Química` e `Lab. Química I`).

## Testes

`schedule/tests/`: `test_models.py`, `test_timetable.py`, `test_occupancy.py`, `test_views.py`, `test_occurrence_cancel.py`, `test_recurrence_change.py`, `test_recurrence_create.py`, `test_recurrence_end.py`, `test_import.py`, `test_import_memory.py`, `test_import_queries.py`, `test_space_import.py`, `test_space_panel.py`, `test_spreadsheet.py`, `test_similarity.py`, `test_class_offering.py`.
