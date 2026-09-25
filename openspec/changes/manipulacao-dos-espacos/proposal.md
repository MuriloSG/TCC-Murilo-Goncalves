## Why

O RF03 do TCC pede que o sistema cadastre e mantenha o registro dos espaços físicos do campus, e o RF01 pede que a importação das planilhas identifique automaticamente os espaços ocupados. Hoje o model `Space` existe, e as alocações já apontam para ele por chave estrangeira, mas ele só tem o nome e só nasce da importação: não há tela para consultar, cadastrar, corrigir ou desativar um espaço, e a importação cria um espaço novo para cada grafia nova da lista de salas da planilha. A lista corrigida real traz `HV 1` a `HV 4` ao lado de `HV5`, e as células da planilha original trazem `HV1`, `Lab.3 - Info` e `2/41`: com o comportamento atual, uma grafia diferente numa próxima planilha cria um espaço duplicado sem que ninguém perceba, e renomear um espaço no sistema faria a reimportação recriar o nome antigo.

Esta Change dá aos espaços um cadastro próprio, com identidade estável e origem, e muda a importação para reconhecer os espaços que o sistema já conhece, propor sozinha o cadastro dos espaços novos sem ambiguidade e pedir decisão humana só quando há ambiguidade real. Nada muda no cadastro de espaços antes da confirmação da importação.

## What Changes

- **Cadastro de espaços** com lista, busca, filtros por situação e por origem, cadastro, edição, desativação, reativação e exclusão de espaço sem uso, com o item "Espaços" no menu.
- **Nomes do espaço**: além do nome atual, o espaço guarda os outros nomes pelos quais a planilha o cita. Nome atual e outros nomes são únicos em conjunto, sem diferenciar maiúsculas de minúsculas. Renomear guarda o nome anterior como outro nome.
- **Origem do espaço**, imutável: `MANUAL`, para o cadastro pela tela, e `PLANILHA`, para o espaço criado na confirmação de uma importação, com a referência à importação de origem. Os espaços existentes passam a `PLANILHA`, com a importação que os criou.
- **Situação do espaço**: ativo ou inativo, sem apagar histórico. A importação nunca desativa, exclui nem reativa um espaço por conta própria.
- **Importação de ensalamento com classificação dos espaços**: cada nome de espaço encontrado é reconhecido (pelo nome atual ou por outro nome de um espaço ativo), proposto como novo (vem da lista de salas, é usado por uma aula e não tem candidato parecido) ou vira uma pendência agrupada por nome (candidato parecido, nome só nas células, espaço inativo). Os nomes da lista de salas que nenhuma aula usa deixam de ser cadastrados.
- **Leitura das células** passa a reconhecer como sala também os nomes e os outros nomes do cadastro, e um nome de sala desconhecido nas células vira pendência, e não erro da linha.
- **Sugestão de espaços parecidos**, só para gerar pergunta, nunca para associar: `HV5` e `HV 5`, `Lab.3 - Info` e `Lab. 3 - Info`, `Sala 01` e `Sala 1`, `Lab. Química` e `Lab. Química I`.
- **Decisões de espaço da importação** (espaço novo, mesmo espaço que outro, reativar), gravadas na própria importação por quem tem a permissão de espaço correspondente, e aplicadas somente na confirmação, na mesma transação das alocações.
- **Situação `PENDENTE`** no motor de importação, com o rótulo "Precisa de decisão", para a importação sem erro da planilha que ainda tem pendências. `COM_ERROS` continua final e reservada aos erros da planilha.
- **Atualização automática da prévia**: cada decisão atualiza o quadro de espaços, e a última decisão refaz a prévia completa, sem botão "Conferir de novo" no fluxo normal.
- **Confirmação condicionada às permissões de espaço**: além de `ENSALAMENTO.IMPORTAR`, a confirmação exige `ESPACO.CRIAR`, `ESPACO.EDITAR` ou `ESPACO.ALTERAR_SITUACAO` conforme o que ela vai alterar no cadastro.
- **Quadro "Espaços desta importação"** na prévia, com linguagem de futuro ("serão cadastrados", "será associado") e a frase "Nenhuma alteração foi feita no cadastro de espaços." até a confirmação.
- **Permissões** `ESPACO.VISUALIZAR`, `ESPACO.CRIAR`, `ESPACO.EDITAR`, `ESPACO.ALTERAR_SITUACAO` e `ESPACO.EXCLUIR`, concedidas ao perfil `ADMINISTRADOR`.
- **Auditoria** do módulo `ESPACO` para cada alteração real do cadastro, inclusive as feitas pela confirmação da importação, que deixam de estar cobertas pela exceção da carga em lote.

### Fora do escopo

- Tipo, capacidade, bloco, descrição ou qualquer outro campo além do nome e dos outros nomes. O TCC não traz atributos de espaço além do RF03.
- Mesclar espaços duplicados.
- Reservas, solicitações de reserva e disponibilidade.
- Edição de ocupação pela Grade, e qualquer mudança na Grade do ensalamento.
- Aviso de nome parecido no cadastro manual pela tela de Espaços.
- Definir se `EaD`, `CeaD` e `Ambulatórios` são espaços físicos e se `1/10` significa bloco e sala.

## Capabilities

### New Capabilities

- `gestao-espacos`: cadastro dos espaços físicos, com nomes, origem, situação, lista, cadastro, edição, desativação, reativação, exclusão, sugestão de espaços parecidos e adoção dos espaços existentes.

### Modified Capabilities

- `ensalamento`: identidade do espaço pelos nomes, catálogo de espaços da planilha, leitura da sala nas células, classificação e decisões de espaço da importação, aplicação na confirmação, quadro de espaços da prévia e auditoria da importação.
- `importacao-planilhas`: situação `PENDENTE`, pendências no plano, atualização da prévia, execução com a importação em curso e verificação própria da confirmação.
- `controle-acesso`: permissões do recurso `ESPACO` e a correspondência delas com as operações.
- `auditoria`: registro das alterações do cadastro de espaços, inclusive pela importação.

## Impact

- **Código**: `schedule/models.py` (campos de `Space` e os models `SpaceName` e `SpaceDecision`), um módulo de sugestão de parecidos em `schedule`, `schedule/imports.py`, `schedule/activities.py`, `schedule/views.py`, `schedule/urls.py`, templates novos em `schedule/templates/schedule/`, `imports/models.py`, `imports/execution.py`, `imports/definitions.py`, `imports/views.py`, `imports/README.md`, `accounts/permissions.py`, `audit/catalog.py` e `ui/templates/ui/components/navigation.html`.
- **Banco**: migrations de esquema e de dados em `schedule` (campos novos, nomes dos espaços existentes, origem e importação de origem dos 86 espaços atuais) e migration de dados em `accounts` com as permissões do recurso `ESPACO`.
- **Dependência de ordem**: os requisitos modificados de `ensalamento` e de `importacao-planilhas` vêm da Change `importar-ensalamento-da-planilha`, arquivada antes desta, e das specs principais. Nenhum deles vem de `visualizar-grade-do-ensalamento`.
- **Telas novas**: a lista de Espaços, os modais de cadastro, edição e confirmação, e o quadro de espaços na prévia da importação. Cada tela nova pede a imagem de referência ao autor antes de ser desenhada.
- **Sem dependência externa nova.**

## Alinhamento com o TCC

- **RF03:** o cadastro e a manutenção do registro dos espaços físicos passam a existir, com consulta, cadastro, edição, desativação e exclusão controlada.
- **RF01 e RF02:** a importação continua identificando os espaços automaticamente, agora contra o cadastro, e a reimportação reconhece os nomes aprendidos.
- **RNF01:** cada operação do cadastro tem permissão própria, e a importação não concede por si só o poder de alterar o cadastro.
- **RNF05 e P7:** o usuário não preenche formulários para os espaços da planilha e só decide o que exige conhecimento do campus; a prevenção de erros vem da recusa de associação automática por semelhança.
