## 1. Preparação

- [x] 1.1 Arquivar a Change `importar-ensalamento-da-planilha` antes desta, porque os requisitos modificados partem do texto dela
- [x] 1.2 Pedir ao autor as imagens de referência da lista de Espaços, dos modais de cadastro, edição e confirmação e do quadro "Espaços desta importação" (§9.8). O autor dispensou as imagens e pediu o padrão existente: a lista de usuários para a tela de Espaços e os cards e alertas do detalhe da importação para o quadro, registrados em D14 e D15

## 2. Motor de importação: pendências, `PENDENTE` e atualização da prévia

- [x] 2.1 Acrescentar `pending` a `RowPlan` e o campo `pending` a `ImportRow`, gravado junto do plano, com a migration de `imports` (D10)
- [x] 2.2 Incluir as pendências em `Plan`, com `has_pending`, na comparação de planos de `imports/execution.py` e na comparação do plano gravado, e desfazer o savepoint da linha que devolve pendência
- [x] 2.3 Acrescentar a situação `PENDENTE`, exibida como "Precisa de decisão", e definir a situação pelo plano na prévia, na divergência da confirmação e na atualização: erro → `COM_ERROS`, pendência → `PENDENTE`, nada → `VALIDADA`
- [x] 2.4 Passar a importação em curso a `run()` e a `definition.execution()`, com nenhuma na primeira prévia
- [x] 2.5 Criar `Import.refresh(definition, executor)`: trava, aceita só `PENDENTE` e `VALIDADA`, reexecuta num savepoint desfeito, substitui o plano e a situação, sem mexer em `revalidation_count` e sem auditoria, extraindo o trecho do ramo divergente de `confirm`
- [x] 2.6 Acrescentar a `ImportDefinition` o gancho opcional `check_confirmation(importation, executor)`, chamado por `confirm` depois de travar a importação e antes de reexecutar, com a recusa exibida como mensagem e sem alterar nada
- [x] 2.7 Aceitar o descarte de uma importação `PENDENTE`, recusar a confirmação e a exclusão dela, e recusar a atualização de importação em situação final
- [x] 2.8 Exibir "Precisa de decisão" com tom de aviso e ícone no histórico e no detalhe, exibir as pendências de cada linha com o rótulo declarado pela importação específica e permitir que as `ImportScreens` declarem um template de quadro próprio no detalhe
- [x] 2.9 Atualizar `imports/README.md` com a situação `PENDENTE`, a atualização da prévia, a verificação própria da confirmação e o diagrama de estados
- [x] 2.10 Testar com uma importação de teste: pendência sem erro leva a `PENDENTE`, erro prevalece sobre pendência, pendência entra na comparação, a atualização deixa `VALIDADA` sem contar divergência, o erro inesperado na atualização não muda nada, a verificação própria recusa a confirmação sem reexecutar, `PENDENTE` é descartada e não é confirmada nem excluída
- [x] 2.11 Conferir que a importação de usuários continua com o mesmo comportamento, rodando `accounts/tests/test_user_import.py` e `test_user_import_views.py`
- [x] 2.12 Commit

## 3. Nomes, origem e situação do espaço

- [ ] 3.1 Acrescentar a `Space` a origem (`MANUAL`/`PLANILHA`, rótulos "Manual" e "Planilha"), a importação de origem (FK opcional para `Import`, `PROTECT`) e `is_active` (D3, D4)
- [ ] 3.2 Criar `SpaceName`, com todos os nomes do espaço, inclusive o atual, e a unicidade sobre o nome em minúsculas garantida pelo banco (D2)
- [ ] 3.3 Criar `SpaceDecision`, com a importação (`CASCADE`), o nome encontrado, o tipo (`NOVO`, `ASSOCIAR`, `REATIVAR`), o espaço (`CASCADE`), o nome encontrado de destino, quem decidiu (`PROTECT`) e quando, e a unicidade por importação e nome em minúsculas (D9)
- [ ] 3.4 Criar a migration de esquema de `schedule`
- [ ] 3.5 Criar a migration de dados que dá a cada espaço existente a origem `PLANILHA`, a situação ativo, a importação de origem pela linha `SALA` concluída cujo `created_object` é a chave dele, e o próprio `SpaceName`, sem registro de auditoria e sem apagar espaço sem aula (D3)
- [ ] 3.6 Testar a migration de dados com um espaço rastreável até a importação, um espaço sem linha de origem e um espaço sem aula
- [ ] 3.7 Commit

## 4. Operações do cadastro de espaços

- [ ] 4.1 Criar a busca do espaço por qualquer nome, sem diferenciar a caixa, e a operação que cadastra o espaço com o nome, os outros nomes, a origem e a importação de origem, recusando com "Já existe um espaço com este nome." a grafia que já identifica outro espaço
- [ ] 4.2 Criar a operação que altera o nome e os outros nomes, guardando o nome anterior como outro nome, promovendo um outro nome a nome atual e recusando grafia de outro espaço, sem mudar origem, importação de origem nem situação
- [ ] 4.3 Criar as operações que acrescentam e retiram um outro nome, usadas pela importação
- [ ] 4.4 Criar a desativação e a reativação, sem efeito e sem registro quando a situação já é a pedida
- [ ] 4.5 Criar a exclusão, recusada com "O espaço <nome> tem aulas no ensalamento e não pode ser excluído. Desative o espaço." quando há alocação (D17)
- [ ] 4.6 Gravar em cada operação o registro do módulo `ESPACO`: `CRIAR` com nome, outros nomes, origem e importação; `ALTERAR` só com o que mudou; `DESATIVAR`; `ATIVAR`; `EXCLUIR` com os valores anteriores (D13)
- [ ] 4.7 Acrescentar o módulo `ESPACO` ("Espaços") e os rótulos dos campos novos a `audit/catalog.py`
- [ ] 4.8 Testar a unicidade entre nome e outros nomes, a preservação de acento e caixa, o nome anterior guardado na renomeação, a promoção do outro nome, a origem imutável em todas as operações, a desativação sem mexer em alocação, a exclusão recusada com alocação e os registros de auditoria de cada operação
- [ ] 4.9 Commit

## 5. Sugestão de espaços parecidos

- [ ] 5.1 Criar o módulo de semelhança em `schedule`, com a regra forte e a regra fraca de D6, sem efeito automático
- [ ] 5.2 Testar os casos reais positivos (`HV5` e `HV 5`, `Lab.3 - Info` e `Lab. 3 - Info`, `Sala 01` e `Sala 1`, `Lab. Química` e `Lab. Química I` e `II`) e negativos (`1/1` e `1/10`, `1/1` e `11`, `Lab. Análise Alim.` e `Sl. Análise Alim.`, `1/10` e `Sala 10 do Bloco 1`)
- [ ] 5.3 Commit

## 6. Permissões do recurso `ESPACO`

- [ ] 6.1 Acrescentar `ESPACO.VISUALIZAR`, `ESPACO.CRIAR`, `ESPACO.EDITAR`, `ESPACO.ALTERAR_SITUACAO` e `ESPACO.EXCLUIR` a `accounts/permissions.py`, com o rótulo "Espaços" do recurso, e a migration de dados que as concede ao `ADMINISTRADOR` sem alterar as demais concessões
- [ ] 6.2 Testar a migration numa instalação com concessões alteradas pelo superadmin e a concessão a um perfil personalizado
- [ ] 6.3 Commit

## 7. Importação: leitura e classificação dos espaços

- [ ] 7.1 Fazer a leitura das células conhecer os nomes da lista de salas e todos os `SpaceName`, e transformar a sala desconhecida em nome citado só nas aulas, em vez do erro `sala_desconhecida` (D7)
- [ ] 7.2 Criar a classificação dos nomes encontrados, com o agrupamento por nome, os nomes da lista sem aula fora da conta, a precedência reconhecido > decidido > novo proposto > precisa de decisão, os parecidos procurados conforme a origem do nome, o uso agregado (aulas, turmas e dias) e a alteração do cadastro que cada nome causará (D5)
- [ ] 7.3 Testar a classificação com as duas planilhas reais num cadastro vazio: 62 novos propostos e nenhuma pendência na corrigida; `HV 1`, `HV 3` e `HV 4` propostos, e `HV1`, `HV3`, `HV4`, `HV5`, `Zoo I`, `EaD` e `2/41` precisando de decisão na original
- [ ] 7.4 Testar o reconhecimento pelo outro nome, o espaço inativo como pendência, os vários parecidos, o nome só nas células sem parecido e a reimportação da planilha corrigida sobre os espaços adotados sem nenhuma proposta nem pendência
- [ ] 7.5 Commit

## 8. Importação: decisões e aplicação na confirmação

- [ ] 8.1 Criar `decide` e `withdraw` de `SpaceDecision`: travam a importação, exigem `PENDENTE` ou `VALIDADA`, conferem o nome e o tipo contra a classificação e a permissão de espaço do executor, gravam o registro `ALTERAR` do módulo da importação e não tocam em `Space` (D9, D11, D13)
- [ ] 8.2 Aplicar em `lock()` a classificação ao cadastro, pelas operações do capítulo 4: cadastrar com `PLANILHA` e a importação de origem, acrescentar e retirar outros nomes e reativar, guardando o resultado no `RunState` (D8)
- [ ] 8.3 Devolver nas linhas de sala `create`, `update`, `unchanged`, nenhuma ação com o aviso `sala_sem_aula` ou a pendência, e nas linhas de atividade o espaço resultante ou a pendência `espaco_a_decidir`, sem executar a linha com pendência
- [ ] 8.4 Implementar `check_confirmation` da importação de ensalamento com as permissões de espaço exigidas pelas alterações previstas e a mensagem aprovada (D11)
- [ ] 8.5 Acrescentar ao resumo auditado as quantidades de espaços cadastrados, de outros nomes associados e de espaços reativados, por `contextvar`, e gravar nos registros de espaço da confirmação a chave da importação e quem decidiu (D13)
- [ ] 8.6 Incluir na mensagem de conclusão as quantidades de espaços, omitindo as zero
- [ ] 8.7 Testar: nada no cadastro depois da prévia e da atualização; tudo aplicado na confirmação; falha na confirmação sem espaço criado; descarte e exclusão sem alteração do cadastro; associação a um espaço e a um nome da mesma importação; reativação; reconhecimento prevalecendo sobre decisão antiga; duas importações que propõem o mesmo espaço; permissões recusando decisão e confirmação sem alterar nada; confirmação por outro usuário com a permissão; auditoria por espaço na confirmação e nenhuma na prévia
- [ ] 8.8 Commit

## 9. Tela de Espaços

- [ ] 9.1 Criar a lista de espaços com busca pelo nome e pelos outros nomes, filtros `situacao` e `origem`, ordem natural, paginação, estados vazios, controles por permissão, excluir só no espaço sem aula e o link para a auditoria (D15)
- [ ] 9.2 Criar o cadastro e a edição em modal, com o nome, os outros nomes um por linha e a origem só exibida na edição
- [ ] 9.3 Criar a desativação, a reativação e a exclusão com confirmação em modal, título em pergunta e mensagens no particípio
- [ ] 9.4 Acrescentar as rotas com `login_required` e `permission_required` e o item "Espaços" no menu, com o ícone `door-open`, para quem tem `ESPACO.VISUALIZAR`
- [ ] 9.5 Testar cada rota nas quatro situações da §7 das convenções, com usuários sem superadmin, e os cenários da spec `gestao-espacos`
- [ ] 9.6 Commit

## 10. Quadro da prévia e atualização automática

- [ ] 10.1 Criar o quadro "Espaços desta importação", com as quantidades no futuro, as listas recolhidas, "Nenhuma alteração foi feita no cadastro de espaços.", "Pronta para confirmar." e o resumo junto ao confirmar (D14)
- [ ] 10.2 Criar os itens de decisão por nome, com a origem do nome, o uso agregado, os botões conforme o caso e as permissões, "Não é um espaço novo" nos novos propostos, "Alterar decisão" e a orientação para o nome só nas células
- [ ] 10.3 Criar a rota de opções de espaços para "É o mesmo que…", com `ENSALAMENTO.IMPORTAR`, sobre `ui.views.OptionsView`
- [ ] 10.4 Criar as rotas de decidir, desfazer e atualizar a prévia, com `ENSALAMENTO.IMPORTAR`, que recalculam o quadro e atualizam a prévia completa quando não resta pendência ou quando a importação estava `VALIDADA`, com e sem JavaScript (D12)
- [ ] 10.5 Mostrar a mensagem sem permissão, o quadro sem controles numa importação `COM_ERROS`, os espaços cadastrados numa importação concluída e "Não foi possível atualizar a prévia." com "Tentar novamente" só numa importação `PENDENTE` sem pendência na classificação
- [ ] 10.6 Medir o tempo da atualização da prévia com a planilha real e, se passar de poucos segundos, mostrar o estado de atualização durante a requisição
- [ ] 10.7 Testar os cenários do quadro e da atualização automática da spec `ensalamento` e as regras de texto de `ui/tests`
- [ ] 10.8 Commit

## 11. Conferência e fechamento

- [ ] 11.1 Conferir no navegador, no banco `visual_check` e com Playwright em container, a lista de Espaços, os modais e o quadro da prévia nas larguras do projeto, sem rolagem horizontal da página, com a primeira importação da planilha corrigida e da original (D18)
- [ ] 11.2 Rodar `make test` com a suíte inteira passando
- [ ] 11.3 Rodar `openspec validate --all --strict`
- [ ] 11.4 Commit
