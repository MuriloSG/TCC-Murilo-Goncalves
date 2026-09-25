## Context

### O que já existe no projeto

| Peça | Onde | Como esta Change a usa |
|---|---|---|
| `Space`, só com `name`, único sem diferenciar a caixa | `schedule/models.py` (`NamedRecord`) | ganha origem, importação de origem, situação e a tabela de nomes (D2, D3, D4) |
| `Allocation.space`, FK `PROTECT` e opcional | `schedule/models.py` | não muda: as alocações já apontam para o espaço, e nada é migrado |
| Criação de espaço pela lista de salas | `SpaceAllocationImport.execute_catalog` com `Space.objects.resolve` | deixa de criar por conta própria e passa a aplicar a classificação (D5, D8) |
| Leitura da sala na célula contra o catálogo do arquivo | `schedule/activities.py`, `resolve` e o erro `sala_desconhecida` | conhece também os nomes do cadastro, e a sala desconhecida vira pendência (D7) |
| Ciclo de vida da importação | `imports/models.py`, `imports/execution.py`, `imports/README.md` | ganha a situação `PENDENTE`, as pendências no plano, a atualização da prévia e a verificação própria da confirmação (D10) |
| Estado de uma execução em `contextvar` | `RunState` e `PERIOD_CHANGE` em `schedule/imports.py` | guarda a classificação e as alterações do cadastro para a auditoria (D8, D13) |
| Registro criado na conclusão | `ImportRow.created_object` | origem dos 86 espaços existentes (D3) |
| Permissões granulares por operação | `USUARIO.VISUALIZAR/CRIAR/EDITAR/ALTERAR_SITUACAO`, `PERFIL.EXCLUIR` | modelo das permissões `ESPACO` (D11) |
| Permissão da operação conferida na execução da importação | `accounts/imports.py`, `executor.has_perm` e o erro `permission_denied` | mesmo ponto de decisão, mas conferido na decisão e na confirmação, e não como erro de linha (D11) |
| Auditoria centralizada | `AuditLog.objects.record` e `record_changes`, `audit/catalog.py`, `acting_from_import` | módulo `ESPACO`, sem mecanismo novo (D13) |
| Lista com busca, filtro, paginação e ações em modal | lista de usuários, `OperationFormView`, `ConfirmedActionView`, `ui.pagination` | tela de Espaços (D15) |
| Exclusão recusada quando em uso | `Role.delete_role` e `RoleInUse` | exclusão de espaço sem uso (D17) |
| Campo de escolha com fonte paginada | `ui/components/select.html` e `ui.views.OptionsView` | escolha do espaço em "É o mesmo que…" (D14) |
| Regras de texto verificadas por teste | `ui/text_rules.py` | forçaram o rótulo "Precisa de decisão" e a mensagem com "O seu perfil" (D14) |

### Os dados reais

Conferidos com `sources/planilha_example.xlsx`, `sources/planilha_example_corrigida.xlsx` e o banco de desenvolvimento (importação 46, concluída):

- A lista de salas corrigida tem 86 nomes distintos, dos quais 62 são usados por aulas e 24 não.
- Na lista corrigida não existe par de nomes que a regra forte de semelhança junte, e a regra fraca só junta `Lab. Química` com `Lab. Química I` e `II`. Como `Lab. Química` não tem aula, a primeira importação da planilha corrigida num cadastro vazio tem 62 novos propostos e nenhuma pendência.
- As células da planilha original citam `HV1`, `HV3`, `HV4`, `HV5`, `Zoo I`, `EaD` e `2/41` fora da lista. `HV1`, `HV3` e `HV4` são parecidos com `HV 1`, `HV 3` e `HV 4` da lista; os outros quatro não têm parecido. Todos os erros de digitação reais estão nas células, e nenhum na lista.
- A lista corrigida tem `HV 1` a `HV 4` e `HV5`: a própria lista não segue uma grafia única, o que confirma que a grafia não identifica o espaço de forma confiável.
- Os 86 espaços do banco de desenvolvimento são rastreáveis até a importação 46 por `ImportRow.created_object`, porque a importação era o único caminho de criação.
- O TCC não traz nenhum atributo de espaço além do RF03 ("Cadastrar e manter o registro dos espaços físicos do campus"). Por isso o cadastro tem só o nome e os outros nomes.

### Dependência de ordem entre Changes

Os requisitos de `ensalamento` e de `importacao-planilhas` modificados aqui vêm das specs principais e da Change `importar-ensalamento-da-planilha`, arquivada antes desta para que os blocos `MODIFIED` partam do texto das specs principais. Nenhum deles vem de `visualizar-grade-do-ensalamento`, que continua ativa com a conferência dos seus deltas pendente (tarefa 5.3 dela). As permissões e a auditoria usam requisitos `ADDED`, como fez `visualizar-grade-do-ensalamento`, para não disputar o texto de "Catálogo de permissões e perfis do sistema" e de "Auditoria das alterações de dados" com `notificar-usuarios` e `importar-ensalamento-da-planilha`.

## Goals / Non-Goals

**Goals:**

- Cadastro de espaços com consulta, cadastro, edição, desativação, reativação e exclusão controlada (RF03).
- Identidade estável do espaço, que sobreviva a grafias diferentes da planilha e à renomeação.
- Origem `MANUAL` ou `PLANILHA`, imutável, e importação de origem.
- Importação que reconhece o que o sistema já conhece, propõe sozinha os espaços novos sem ambiguidade e pede decisão só quando há ambiguidade real, agrupada por nome.
- Nenhuma alteração do cadastro antes da confirmação, e nenhuma alteração parcial ou órfã.
- Permissões de espaço separadas da permissão de importar.

**Non-Goals:**

- Tipo, capacidade, bloco, descrição e qualquer outro atributo de espaço.
- Mesclar espaços duplicados.
- Mudar a Grade do ensalamento, editar ocupação pela Grade, reservas e disponibilidade.
- Atividade em mais de um espaço (`(2/4) (Lab.3 - Info)` continua sendo erro da planilha).
- Aviso de nome parecido no cadastro manual.
- Notificar quem gerencia espaços quando uma importação precisa de decisão.
- Classificar e decidir docentes da mesma forma: a lista de docentes continua como está.

## Decisions

### D1. `Space` continua sendo a entidade, sem reconstruir o ensalamento

O espaço já é uma entidade própria, e `Allocation.space` já é FK. A Change acrescenta dados ao `Space` e não cria entidade paralela, não toca em `Allocation`, na ocupação nem na Grade. **Alternativa descartada:** uma entidade nova de "espaço físico" ligada ao `Space` do ensalamento, que duplicaria a identidade e exigiria migrar alocações sem ganho.

### D2. Uma tabela única com todos os nomes do espaço

`SpaceName(space, name)` guarda **todos** os nomes que identificam um espaço, inclusive o nome atual, com `UniqueConstraint(Lower('name'))`. Os outros nomes são as linhas cujo nome difere de `Space.name`. `Space.name` continua existindo, com a restrição atual, como nome de exibição.

- **Por quê:** a unicidade que importa é a do conjunto nome atual mais outros nomes. Numa tabela única, o banco a garante, e duas operações concorrentes não conseguem dar a mesma grafia a dois espaços.
- **Alternativa descartada:** uma tabela só de outros nomes, com a unicidade entre ela e `Space.name` conferida no código. Essa conferência depende de trava e fica frágil sob concorrência.
- **Alternativa descartada:** outros nomes numa lista JSON, sem garantia do banco e sem índice.
- **Normalização:** a mesma de `NamedRecord`, com `normalize_name` e a comparação sem diferenciar a caixa. Os acentos continuam distinguindo nomes.
- **Invariante:** todo espaço tem exatamente um `SpaceName` igual ao `Space.name`, mantido pelas operações do model.

### D3. Origem e importação de origem imutáveis, e adoção dos espaços existentes

`Space.origin`, com o código `MANUAL` ou `PLANILHA` e os rótulos "Manual" e "Planilha", e `Space.source_import`, FK opcional para `imports.Import` com `PROTECT`. As duas são definidas só na criação, nenhuma operação as altera e nenhum formulário as declara.

- **Rótulos próprios:** o `Origin` da alocação (`IMPORTADA`/`MANUAL`) não é reaproveitado, porque o código e o rótulo são femininos e o conceito é outro.
- **`PROTECT` não trava nada:** só importações `CONCLUIDA` criam espaço, e essas não podem ser excluídas.
- **Migration de dados:** todo espaço existente recebe `PLANILHA` e ativo. `source_import` vem da linha `SALA` de uma importação `ENSALAMENTO` concluída cujo `created_object` é a chave do espaço. Cada espaço recebe o próprio `SpaceName`.
- **O que a migration não faz:** não gera registro de auditoria, porque a auditoria não inventa histórico, e não apaga os espaços sem aula.

### D4. Situação ativo/inativo

`Space.is_active`. Desativar não mexe em alocação, e a Grade continua listando o espaço onde ele tem aula, porque `spaces_of` parte das alocações. Na importação, o espaço inativo citado vira pendência (D5). O glossário usa desativar e reativar, e o catálogo de auditoria já tem `DESATIVAR` e `ATIVAR`.

### D5. A classificação é uma função única, usada pela execução e pelo quadro

A classificação dos nomes encontrados fica num módulo próprio de `schedule`. É uma função que recebe os valores das linhas, o cadastro e as decisões da importação e devolve, para cada nome encontrado, a classificação, os parecidos, o uso agregado e a alteração do cadastro que ele causará.

- **Quem a usa:** `lock()`, na execução, e o quadro da prévia, que precisa dela sem executar as linhas. Por ser a mesma função, o quadro e a execução não divergem.
- **Precedência:** reconhecido (ativo) > decidido (decisão válida) > novo proposto > precisa de decisão. O reconhecimento vencer a decisão é o que impede o duplicado quando o cadastro muda no meio do caminho.
- **A lista de salas é a referência.** Um nome da lista só perde a proposta de novo por um parecido no cadastro ou em outro nome da lista. Um nome citado só nas células nunca é proposto como novo, porque é nas células que estão os erros de digitação reais (`2/41`, `HV1`, `Lab.3 - Info`), e os parecidos dele são procurados em tudo.
- **Nomes da lista sem aula** não são nomes encontrados. Isso tira `Lab. Química` da conta e evita 24 cadastros sem uso na planilha corrigida.
- **Uso agregado:** vem das linhas de atividade que citam o nome: a quantidade de linhas, as turmas distintas e os dias distintos.

**Alternativa descartada:** gravar a classificação na importação. Ela ficaria velha a cada mudança do cadastro, e recalcular é barato, porque é leitura de texto contra um conjunto de nomes, sem uma consulta por linha.

### D6. Sugestão de parecidos encapsulada e testada com os casos reais

A semelhança fica num módulo próprio de `schedule`, com uma função que devolve os parecidos de um nome entre nomes conhecidos. As duas regras:

- **Forte:** a mesma chave, ignorando espaços, pontos, hífens, acentos, maiúsculas e zeros à esquerda.
- **Fraca:** um nome é o outro acrescido de um número ou de um romano no fim.

A heurística só gera pergunta. Os testes fixam os casos reais positivos (`HV5`, `Lab.3 - Info`, `Sala 01`, `Lab. Química`) e negativos (`1/1` × `1/10`, `Lab. Análise Alim.` × `Sl. Análise Alim.`, `1/10` × `Sala 10 do Bloco 1`). Ajustar a regra não muda a spec, desde que esses casos continuem valendo.

### D7. A leitura das células conhece a lista e o cadastro

`Catalog.build` passa a receber, para os espaços, os nomes da lista mais todos os `SpaceName`, de espaços ativos e inativos. Assim, uma grafia aprendida (`HV1` como outro nome de `HV 1`) é reconhecida mesmo fora da lista. A detecção de "sala desconhecida" continua a mesma: último grupo desconhecido com o grupo anterior formado por docentes conhecidos. Ela deixa de produzir o erro `sala_desconhecida` e passa a produzir um nome encontrado "só nas aulas". A correspondência continua exata, sem semelhança.

### D8. O cadastro é alterado em `lock()`, antes das linhas, pelas operações do model

Na execução, `lock()` calcula a classificação e aplica ao cadastro, pelas operações de `Space`, as criações, os outros nomes, as retiradas de outro nome e as reativações. Depois, as linhas só consultam o resultado guardado no `RunState`.

- **Por quê em `lock()`:**
  - Um nome citado só nas células não tem linha de sala onde a criação caiba.
  - A criação precisa existir antes da primeira atividade que usa o espaço.
  - Fazer tudo num lugar só garante que cada alteração acontece uma vez.
- **O que as linhas de sala mostram:**
  - `create`, com o nome e os outros nomes, quando o espaço foi criado com aquele nome.
  - `update`, com `outros_nomes` ou `situacao`, quando um espaço existente mudou.
  - `unchanged`, quando o nome é reconhecido.
  - Nenhuma ação e o aviso `sala_sem_aula`, quando o nome da lista não tem aula.
  - A pendência, quando o nome precisa de decisão.
- **Chave do espaço criado:** segue a regra de D17 da Change de importação. Não entra como alvo, porque a chave gerada na prévia some no rollback. O `created_object` da linha de sala é gravado na conclusão, como hoje.
- **Linhas de atividade:** a linha cujo espaço precisa de decisão recebe a pendência `espaco_a_decidir`, com o nome como chave, e não é executada.
- **Proteção contra divergência:** vem dos planos. Uma mudança no cadastro muda a ação ou as mudanças de alguma linha de sala ou de atividade (o espaço da alocação), e a confirmação diverge.
- **Falha inesperada:** uma recusa do banco numa operação de `lock()`, como uma grafia gravada por outro usuário no mesmo instante, é um erro inesperado. A prévia não é criada, e a atualização ou a confirmação ficam como estavam. A próxima execução reconhece o nome. Isso é aceito porque é raro, e a alternativa de isolar cada operação num savepoint com erro de linha não tem linha para os nomes só nas células.

**Alternativa descartada:** manter a criação em `execute_catalog`, por linha de sala. Não cobre os nomes só nas células e espalha a regra.

### D9. `SpaceDecision` guarda a decisão na importação

`SpaceDecision(importation, found_name, kind, space, target_name, decided_by, decided_at)`:

- `kind` é `NOVO`, `ASSOCIAR` ou `REATIVAR`.
- `space` é o espaço escolhido, ou o espaço inativo reativado.
- `target_name` é o nome encontrado da mesma importação que será cadastrado e que recebe este nome como outro nome.
- A unicidade é por importação e nome, sem diferenciar a caixa, e uma decisão nova substitui a anterior.

As chaves estrangeiras:
- `importation` é `CASCADE`: excluir a importação apaga as decisões.
- `space` é `CASCADE`: excluir um espaço sem uso apaga as decisões que o citavam, e o nome volta a ser pendência.
- `decided_by` é `PROTECT`, como `Import.created_by`.

As operações `decide` e `withdraw` do manager ficam no model (P2). Elas:
1. travam a importação com `select_for_update`;
2. exigem a situação `PENDENTE` ou `VALIDADA`;
3. conferem que o nome é um nome encontrado não reconhecido e que o tipo cabe na classificação dele;
4. conferem a permissão de espaço do executor (D11);
5. gravam a decisão e o registro de auditoria do módulo da importação (D13).

Nenhuma delas toca em `Space`. A decisão sem sentido não é apagada: a classificação a desconsidera (D5), e ela volta a valer se a situação voltar.

**Alternativa descartada:** gravar as decisões nos valores das linhas. Os valores lidos são o arquivo, e o motor não pode interpretar dados de uma importação específica.

**Alternativa descartada:** aplicar a decisão direto no cadastro, como na primeira análise. Deixaria alteração antes da confirmação e espaço órfão no descarte.

### D10. O motor ganha pendência, `PENDENTE`, atualização da prévia e verificação própria da confirmação

As mudanças são genéricas e não citam espaço:

- **`RowPlan.pending`:** uma lista de `{code, key}`, gravada num campo novo `ImportRow.pending`. `Plan.has_pending` e a comparação passam a incluir as pendências. `execute_row` desfaz o savepoint da linha que devolve pendência, como faz com a que devolve erro.
- **Situação `PENDENTE`:** código `PENDENTE`, rótulo "Precisa de decisão". A situação sai do plano: erro → `COM_ERROS`; pendência sem erro → `PENDENTE`; nada → `VALIDADA`. Na lista de importações, ela aparece com o tom de aviso e um ícone.
- **`Import.refresh(definition, executor)`:** trava a importação e aceita só `PENDENTE` e `VALIDADA`. Roda num savepoint desfeito, substitui o plano e a situação, e não mexe em `revalidation_count` nem gera auditoria. É o trecho do ramo divergente de `confirm` extraído para uma operação, sem o incremento.
- **`run(definition, rows, executor, importation=None)`:** passa a importação a `definition.execution(importation)`, para a importação específica ler as decisões.
- **`ImportDefinition.check_confirmation(importation, executor)`:** um gancho opcional, chamado por `confirm` depois de `lock_pending` e antes da reexecução. A recusa é uma `ValidationError` com mensagem, e nada muda.
- **Descarte:** aceita `PENDENTE`.
- **Confirmação:** aceita só `VALIDADA`. Uma divergência pode levar a `PENDENTE`.
- **Documentação:** `imports/README.md` ganha a situação e as transições novas.
- **Quadro próprio no detalhe:** a importação específica declara um template de quadro nas `ImportScreens`, com o contexto fornecido pela view dela.

A importação de usuários não declara pendência nem verificação, e o comportamento dela não muda. **Alternativa descartada:** manter a pendência como erro e tornar `COM_ERROS` não final. Isso misturaria o erro da planilha, que só se corrige com arquivo novo, com a decisão que se resolve na tela.

### D11. Permissões granulares, conferidas na decisão e na confirmação

As permissões seguem a divisão de `USUARIO`: `ESPACO.VISUALIZAR`, `ESPACO.CRIAR`, `ESPACO.EDITAR`, `ESPACO.ALTERAR_SITUACAO` e `ESPACO.EXCLUIR`.

**Nome da permissão de situação:** o autor sugeriu `ESPACO.ATIVAR` e `ESPACO.DESATIVAR`, "ou os nomes do padrão existente". O padrão é uma permissão só para as duas ações (`USUARIO.ALTERAR_SITUACAO`), e ele foi seguido.

A importação exige a permissão de espaço equivalente à alteração:

| Alteração | Permissão |
|---|---|
| Cadastrar espaço, inclusive com outros nomes da mesma importação | `ESPACO.CRIAR` |
| Acrescentar ou retirar outro nome de espaço existente | `ESPACO.EDITAR` |
| Reativar | `ESPACO.ALTERAR_SITUACAO` |

**Diferença em relação à importação de usuários.** Lá, a falta da permissão da linha é erro de linha, e a importação fica `COM_ERROS`, que é final. Aqui, isso impediria que quem gerencia os espaços concluísse a importação enviada por quem só importa, que é o fluxo aprovado. Por isso a permissão é conferida:
- na decisão, dentro de `decide` e `withdraw`;
- na confirmação, pelo gancho `check_confirmation`, a partir das alterações que a classificação atual prevê.

A permissão nunca entra no plano. Com isso, o plano não depende de quem executa, e a atualização da prévia feita por um usuário e a confirmação feita por outro chegam ao mesmo plano. O único ponto de decisão continua sendo `User.has_perm`, chamado no model, como em `accounts/imports.py`. As views só declaram `ENSALAMENTO.IMPORTAR` para as rotas de decisão e de atualização, e os templates usam as permissões só para mostrar os controles.

**Risco conhecido da granularidade:** um usuário com `ESPACO.CRIAR` e sem `ESPACO.EDITAR` só consegue responder "É um espaço novo" a um parecido, e pode criar um duplicado que outro usuário teria associado. Foi aceito com a decisão pelas permissões granulares.

### D12. Atualização automática em dois níveis

A view de decisão:
1. chama `decide` ou `withdraw`, na transação própria, e a decisão fica gravada;
2. recalcula a classificação;
3. se não resta nome que precise de decisão, ou se a importação estava `VALIDADA`, chama `Import.refresh` numa segunda transação;
4. devolve o quadro, pelo htmx, ou redireciona ao detalhe, sem JavaScript.

**Por que só a última decisão refaz a prévia completa:** a prévia completa executa as 1.500 linhas com um savepoint por linha. As decisões intermediárias não tornam a importação confirmável, e a confirmação reexecuta de qualquer forma.

**Quando a atualização falha:** a decisão continua gravada, porque está em outra transação, e a importação fica como estava. O quadro reconhece a falha sem guardar indicador: a importação está `PENDENTE` e a classificação não tem mais pendência. Nesse caso, e só nele, aparece "Não foi possível atualizar a prévia." com "Tentar novamente", que faz POST para a rota de atualização. Numa importação `VALIDADA`, uma falha deixa o plano velho, e a confirmação diverge e atualiza a prévia, o que já é seguro.

O tempo da prévia completa com a planilha real deve ser medido na implementação. Se passar de poucos segundos, o quadro mostra "Atualizando a prévia" durante a requisição.

### D13. Auditoria

- **Módulo novo:** `ESPACO` ("Espaços") entra em `audit/catalog.py`, com os rótulos dos campos novos (`outros_nomes`, `origem`, `importacao`, `nome_encontrado`, `decisao`, `espaco`, `espacos_cadastrados`, `outros_nomes_associados`, `espacos_reativados`).
- **Registro nas operações:** as operações de `Space` gravam os próprios registros, como `User` e `Role`.
- **Confirmação da importação:** os registros são gravados dentro da transação, com a origem `IMPORTACAO` e o confirmador como responsável, porque a execução roda em `acting_from_import`. A chave da importação e quem decidiu entram nas informações adicionais. Na prévia e na atualização, eles somem com o rollback.
- **Exceção da carga em lote:** a spec `auditoria` é estreitada por um requisito `ADDED` que tira o cadastro de espaços dela. O requisito "Registro de auditoria da importação de ensalamento" é modificado para citar a exceção.
- **Resumo da importação:** ganha as quantidades de espaços. Elas vêm de um `contextvar` preenchido por `lock()` e lido em `audit_metadata`, o mesmo padrão de `PERIOD_CHANGE`.
- **Decisões:** gravar ou desfazer uma decisão altera dados gravados da importação. Por isso gera um registro `ALTERAR` do módulo `IMPORTACAO_ENSALAMENTO`, exigido pelo requisito "Auditoria das alterações de dados", e nenhum do módulo `ESPACO`.
- **Atualização da prévia:** não gera registro. Ela segue o precedente da substituição do plano numa divergência, que também não gera.

### D14. Quadro "Espaços desta importação"

Fica no detalhe da importação de ensalamento, pelo template de quadro que `SPACE_ALLOCATION_IMPORT_SCREENS` declara, antes dos recortes das linhas.

**Duas adaptações de texto** foram forçadas por `ui/text_rules.py` e confirmadas pelo autor:
- **Rótulo da situação:** "Precisa de decisão". A regra proíbe "aguardando" e sugere "pendente", que o autor reserva às solicitações de reserva.
- **Mensagem de permissão:** "O seu perfil não tem permissão para essa configuração." A regra proíbe "você", e o possessivo é permitido.

**Interação:**
- Cada decisão é um POST com CSRF, disparado por um botão.
- "É o mesmo que…" abre o campo de escolha do componente `select`, com fonte paginada de espaços. A rota de opções é declarada em `schedule` com `ENSALAMENTO.IMPORTAR`, a permissão da tela que a consome.
- A lista de novos propostos fica recolhida, com "Não é um espaço novo" em cada item.

**Frases fixas:** a linguagem de futuro e "Nenhuma alteração foi feita no cadastro de espaços." aparecem enquanto a importação não é concluída.

**Importação concluída:** o quadro lista os espaços com `source_import` igual a ela. A mensagem de conclusão lê as quantidades de espaços do registro de auditoria da confirmação, que é onde elas ficam gravadas.

A tela é nova. O autor dispensou a imagem de referência (§9.8) e pediu o padrão existente: os cards, os alertas, os selos e os botões do detalhe da importação, com a paleta da `previa.html`.

### D15. Tela de Espaços no app `schedule`

O espaço é entidade de `schedule` (D14 da Change de importação). As rotas:
- `espacos/`, a lista;
- `espacos/novo/`, o cadastro;
- `espacos/<pk>/editar/`, a edição;
- `espacos/<pk>/desativar/`, `espacos/<pk>/reativar/` e `espacos/<pk>/excluir/`, as ações com confirmação.

Todas têm `login_required` na URL e `permission_required` na view. O cadastro e a edição usam `OperationFormView`, e as ações com confirmação usam `ConfirmedActionView`, tudo em modal. A lista segue a de usuários: `busca`, `situacao` e `origem` na URL, paginação da spec `interface`, ordem natural do nome (`natural_key` de `schedule/timetable.py`) e o link para a auditoria filtrada pelo módulo e pelo registro para quem tem `AUDITORIA.VISUALIZAR`. Os outros nomes são informados um por linha num campo de texto. O item "Espaços" do menu usa o ícone `door-open`, que já existe. A tela é nova. O autor dispensou a imagem de referência e pediu o padrão da lista de usuários: busca e filtros no cabeçalho do cartão, tabela com selos de origem e situação, ações da linha por `row_actions.html` e modais pelos componentes do app `ui`.

### D16. A Grade não muda

A Grade escolhe a sala pelo nome na URL (`sala=`) e cai no padrão quando o nome não existe. Depois de uma renomeação, um link antigo cai no padrão sem erro, como a spec já prevê. O espaço inativo continua aparecendo onde tem aula. Nenhuma mudança na Grade é necessária para os requisitos desta Change.

### D17. Exclusão só do espaço sem aula

`Space.delete_space()` trava o espaço, recusa com uma `ValidationError` própria quando existe alocação (`PROTECT` já impediria no banco, e a recusa dá a mensagem) e grava `EXCLUIR` antes de apagar. Os `SpaceName` e as `SpaceDecision` saem por `CASCADE`. Na prática, só um espaço cadastrado pela tela e ainda sem aula pode ser excluído, porque a importação só cria espaço usado por aula e nunca exclui alocação. **Alternativa descartada:** nunca excluir. Não haveria como corrigir um cadastro manual feito por engano.

### D18. Conferência visual

A tela de Espaços e o quadro da prévia são conferidos no navegador, no banco `visual_check` e com Playwright em container, nunca no banco de desenvolvimento, nas larguras do projeto e sem rolagem horizontal da página.

## Risks / Trade-offs

- **[Um espaço renomeado na planilha sem nenhuma semelhança vira novo proposto]** → A lista de novos propostos fica visível antes da confirmação, com "Não é um espaço novo". Corrigir depois exige mesclar espaços, que está fora do escopo.
- **[A permissão granular permite criar um duplicado quando falta `ESPACO.EDITAR`]** → Os controles mostram só as decisões possíveis. O risco foi aceito com a decisão pelas permissões granulares (D11).
- **[A prévia completa é refeita a cada mudança numa importação `VALIDADA`]** → Só a última decisão, ou a alteração de uma decisão numa importação pronta, refaz a prévia. O tempo é medido e, se preciso, mostrado.
- **[Uma recusa do banco em `lock()` é tratada como erro inesperado]** → Só acontece com gravação concorrente da mesma grafia. Nada fica aplicado, e a próxima execução reconhece o nome (D8).
- **[Os links antigos da Grade caem no padrão depois de uma renomeação]** → É o comportamento previsto pela spec da Grade. O nome antigo continua valendo para a importação.
- **[Os 24 espaços sem aula já existentes ficam no cadastro]** → Podem ser desativados. A exclusão também está disponível para eles, porque não têm alocação.
- **[A heurística de semelhança erra para mais ou para menos]** → Para mais, custa uma pergunta; para menos, gera uma proposta de novo visível antes da confirmação. Os testes fixam os casos reais.

## Migration Plan

1. Arquivar antes a Change `importar-ensalamento-da-planilha`.
2. Migration de esquema em `imports`: o campo `pending` de `ImportRow`, e a situação `PENDENTE` nas escolhas de `Import.status`, que continua com 10 caracteres.
3. Migration de esquema em `schedule`: `origin`, `source_import` e `is_active` em `Space`, e os models `SpaceName` e `SpaceDecision`.
4. Migration de dados em `schedule`: origem `PLANILHA`, ativo, `source_import` pela `ImportRow` e um `SpaceName` por espaço (D3). A reversão apaga os `SpaceName` e deixa os campos, que saem com a reversão do esquema.
5. Migration de dados em `accounts`: as cinco permissões `ESPACO`, concedidas ao `ADMINISTRADOR`, idempotente, como 0007 e 0008.
6. Nenhuma alocação, importação ou registro de auditoria existente é alterado.

## Decisões confirmadas pelo autor

| Decisão | Resultado |
|---|---|
| Espaço novo claro da lista | proposto sem clique individual e cadastrado só na confirmação (D5, D8) |
| Nome só nas células | nunca criado automaticamente (D5) |
| Nomes da lista sem aula | não cadastrados (D5) |
| Situação da importação com decisões por tomar | `PENDENTE`, exibida como "Precisa de decisão" (D10, D14) |
| Mensagem sem permissão | "A importação encontrou espaços que precisam ser cadastrados ou associados. O seu perfil não tem permissão para essa configuração." (D14) |
| Confirmação que altera o cadastro | exige a permissão de espaço equivalente, além de importar (D11) |
| Permissões | granulares, no padrão de `USUARIO`, com `ALTERAR_SITUACAO` para desativar e reativar (D11) |
| Mesclar espaços | fora desta Change |
| Espaço inativo citado | exige decisão de reativação (D5, D9) |
| Auditoria | alterações reais do cadastro auditadas por espaço, também na confirmação (D13) |
| "Conferir de novo" | não existe no fluxo normal; atualização automática, com "Tentar novamente" só na falha (D12) |

## Open Questions

- `EaD`, `CeaD` e `Ambulatórios` são espaços físicos? Enquanto não houver definição, eles seguem as regras gerais: da lista, sem parecido, são propostos como novos.
- `1/10` significa bloco e sala? Não afeta esta Change, porque o cadastro não tem bloco.
- O tempo da atualização da prévia com a planilha real, a ser medido na implementação (D12).
