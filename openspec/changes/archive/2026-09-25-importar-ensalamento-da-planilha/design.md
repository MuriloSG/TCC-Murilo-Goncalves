## Context

### O que já existe no projeto

| Peça | Onde | Uso aqui |
|---|---|---|
| Máquina de estados da importação | `imports/models.py`, `imports/execution.py`, `imports/README.md` | ciclo de vida da importação de ensalamento, sem mecanismo paralelo (D10) |
| Contrato da importação específica | `imports/definitions.py`, com `ImportDefinition`, `Column`, `RowError` e `RowPlan` | `SpaceAllocationImport` declara colunas, identificador, travamento, execução da linha e verificações do arquivo |
| Telas base da importação | `imports/views.py`, com `ImportScreens` e as seis views | envio, prévia, confirmação, descarte, histórico e detalhe do ensalamento |
| Prévia por executar e desfazer | `ImportManager.preview` | os erros que só o banco detecta aparecem antes de efetivar |
| Origem de importação na auditoria | `audit.context.acting_from_import` | os registros das operações mostram que vieram de uma planilha |
| Identificador de domínio do usuário | `User.username`, `accounts.models.normalize_username` | mesma normalização usada em `Teacher.name`, o que torna a correspondência futura possível (D6) |
| Permissão como dado | `accounts/permissions.py` e `accounts.middleware.PermissionMiddleware` | `ENSALAMENTO.IMPORTAR` declarada na view, verificada pelo middleware |

O diretório `schedule/` existe com `templates/schedule/partials/` e `tests/` vazios, e não está em `INSTALLED_APPS`. Esta Change é a primeira a povoá-lo.

### A planilha real

Toda afirmação desta seção foi verificada em `sources/planilha_example.xlsx` e está marcada **Confirmado pela planilha**. A planilha não é alterada por esta Change.

#### Estrutura das duas abas de horário

As duas abas são a mesma grade, com dimensões diferentes:

| | `Horário - Graduação` | `Horário - Ensino Médio` |
|---|---|---|
| Linha 1 | faixas mescladas com o nome do curso | idem, com duas colunas sem mescla |
| Linha de cabeçalho | 2, 23, 44, 65, 86 e 107 | 2, 17, 32, 47, 62 e 77 |
| Coluna `A` | nome do dia, mesclado no bloco (`A3:A22`, `A24:A43`, ...) | idem (`A3:A16`, `A18:A31`, ...) |
| Coluna `B` | faixa de horário, `INTERVALO` ou `ALMOÇO` | idem |
| Colunas de turma | `C` a `AW`, com `H`, `N`, `S`, `Y`, `AD`, `AI`, `AN` e `AS` vazias separando os cursos | `C` a `Z`, com `I`, `P`, `W` e `Y` vazias |
| Faixas de horário por dia | 15 | 11 |
| Colunas de turma | 39 | 20 |
| Dias | `SEGUNDA `, `TERÇA`, `QUARTA`, `QUINTA`, `SEXTA` | `SEGUNDA-FEIRA `, `TERÇA-FEIRA`, ... |

A última linha de cabeçalho de cada aba (107 e 77) não abre bloco de dia: ela fecha a grade.

As 15 faixas da graduação são `07:20 - 08:10`, `08:10 - 09:00`, `09:20 - 10:10`, `10:10 - 11:00`, `11:00 - 11:50`, `13:20 - 14:10`, `14:10 - 15:00`, `15:20 - 16:10`, `16:10 - 17:00`, `17:00 - 17:50`, `18:10 - 19:00`, `19:00 - 19:50`, `19:50 - 20:40`, `21:00 - 21:50` e `21:50 - 22:40`. O ensino médio usa exatamente as onze primeiras, e só nove delas têm atividade no arquivo real. Entre elas aparecem as linhas `INTERVALO` e `ALMOÇO`, que não têm atividade em nenhuma célula.

Nenhuma célula de atividade é mesclada: as mesclas das duas abas estão só na coluna `A` e na linha 1.

#### Conteúdo de uma célula de atividade

Há **1.474 células de atividade** nas duas abas, que produzem **1.500 atividades**, porque 19 células descrevem mais de uma (D2). O texto segue o padrão `Disciplina (Docente) (Sala)`, com variação real:

| Situação | Ocorrências | Exemplo |
|---|---|---|
| Dois grupos entre parênteses | 1.310 | `CÁLCULO III (Viviane) (2/6)` |
| Três ou mais grupos | 102 | `Gestão Ambiental (optativa) (Élcio José) (3/10)`, `Estágio Supervisionado II (120 h/a) (Lucas Diego) (LEM)` |
| Um grupo | 63 | `Educação Física (Jairo)`, `Libras ll (EAD)` |
| Mais de uma atividade na mesma célula | 19 | `Óleos e Gorduras (OPTATIVA I) (Bruna Porto) (Sl. Fenômenos) / Massas e Panificação (OPTATIVA II) (Márcia Antunes) (Sl. Oficina)` |
| Vários docentes num grupo | várias | `(Eduardo Garrido/ Thaís/ Antônio )`, `(Arilson e Agnaldo)`, `(Walter , Valéria)`, `(Roberta, Fabiano, Evelyn)` |
| Quebra de linha e espaços duplicados dentro da célula | várias | `Química\n (Juliana Diniz) (Mini 1)`, `Nutrição Animal (Antônio)  ( HV 2)` |

Tomando o **último** grupo entre parênteses e comparando com os catálogos da aba `Validação de Dados`, sem diferenciar maiúsculas de minúsculas:

| Resultado | Células | Leitura |
|---|---|---|
| É uma sala do catálogo | 1.363 | célula com sala |
| É um docente do catálogo | 54 | célula sem sala, como a educação física e as disciplinas a distância |
| Não é nem um nem outro | 58 | sala fora do catálogo, docente fora do catálogo ou marcação |

As 58 células restantes se distribuem assim: salas reais ausentes do catálogo (`Zoo I` em 8 células, `HV1`, `HV3`, `HV4` e `HV5` em 18, `Ambulatórios` em 4, `Lab.3 - Info` em 2, `2/41` em 1), marcações de ensino a distância (`EaD`, `EAD`, `CeaD`, em 9) e docentes ausentes do catálogo (`Agnaldo` em 7, `Luciene` em 2, `Luiz Fernando /Elza` em 3, `Gera Magela/Luciano` em 2, `Adaptação/PPC novo` em 1). `HV1` e `HV 4` mostram que a diferença é só de espaço em relação a `(HV 1)` e `(HV 4)`, que estão no catálogo.

#### Catálogos da aba `Validação de Dados`

| Coluna | Cabeçalho | Conteúdo | Observações |
|---|---|---|---|
| `A` | `Disciplina (Professor)` | 124 valores, das linhas 2 a 125 | `Ataliba` repetido nas linhas 16 e 17; acentos presentes (`Élcio José`, `Érica`, `Thaís`); prefixos compartilhados (`Gera Jr.` e `Gera Magela`, `Vinícius` e `Vinícius Figueiredo`) |
| `B` | `Salas Disponíveis` | 82 valores, das linhas 2 a 83 | 71 entre parênteses (`(1/10)`, `(Lab. 3 - Info)`) e 11 sem parênteses (`Lab. de Madeira`, `Lab. Reprodução Animal`); `Lab. Bromatologia` repetido nas linhas 45 e 46 |

As duas colunas são as fontes das listas de validação: `Ensalamento - Geral!C1` aponta para `'Validação de Dados'!$B:$B`, e as três abas de horário por docente apontam para `'Validação de Dados'!$A:$A`.

#### Curso e turma

A linha 1 traz o nome do curso sobre o grupo de colunas da turma. Na graduação são oito nomes legíveis (`BACHARELADO EM ENGENHARIA FLORESTAL`, `BACHARELADO EM SISTEMAS DE INFORMAÇÃO`, `BACHARELADO EM MEDICINA VETERINÁRIA`, `LICENCIATURA EM CIÊNCIAS BIOLÓGICAS`, `LICENCIATURA EM FÍSICA`, `LICENCIATURA EM MATEMÁTICA`, `LICENCIATURA EM QUÍMICA`, `LICENCIATURA EM PEDAGOGIA`) e um **defeito**: a faixa `C1:G1`, do curso de engenharia de alimentos, contém a fórmula `=UPPER(E:E)`, sem valor em cache. No ensino médio são `AGROINDÚSTRIA `, `AGROPECUÁRIA`, `INFORMÁTICA `, `QUÍMICA` e `MEIO AMBIENTE`, as duas últimas em coluna única.

O cabeçalho de cada coluna de turma tem duas linhas, com o rótulo da turma e o nome curto do curso: `2º PERÍODO\nEng. Alimentos`, `1º ANO A\nAgroindústria`. Duas variações reais: as colunas `X` e `Z` do ensino médio não têm quebra de linha (`1º ANO   Química`, `1º ANO - Meio Ambiente`), e o cabeçalho da linha 2 do ensino médio grafa `1º ANO A Agroindústria` enquanto as linhas 17, 32, 47, 62 e 77 grafam `1º ANO A - Agroindústria`. Na graduação, a coluna `AF` fica sem cabeçalho na linha 86, e a mesma coluna tem cabeçalho nas outras cinco.

#### Repetição em faixas consecutivas

A mesma atividade aparece repetida, célula por célula, em faixas seguidas. As execuções por coluna e por dia se distribuem assim: 249 de uma faixa, 486 de duas, 34 de três e 38 de quatro. **93 dessas execuções atravessam um `INTERVALO` ou o `ALMOÇO`**, isto é, cobrem faixas que não são contíguas no tempo, e em **13 casos** o mesmo texto reaparece mais adiante no mesmo dia e na mesma coluna depois de uma faixa vazia.

Não há na planilha nenhum dado que diga se duas faixas seguidas são uma atividade contínua ou duas ocupações da mesma sala: não há mescla, não há marca de continuação e a repetição do texto é o único sinal. Isso decide D9.

#### A mesma sala na mesma faixa para mais de uma turma

Em 42 combinações de dia, faixa e sala, mais de uma coluna de turma aponta para a mesma sala. Em 20 delas o texto é idêntico, e é uma aula compartilhada: `QUÍMICA ORGÂNICA (Elza) (1/13)` na segunda-feira às 13:20 aparece na coluna do 2º período de engenharia de alimentos e na do 2º período de engenharia florestal. Nas outras o texto difere, e é o caso que a fórmula da aba `Ensalamento - Geral` marcaria com `[CHOQUE]`. Isso decide D8.

## Goals / Non-Goals

**Goals:**

- Um semestre de ensalamento no banco, com semestre, espaço, curso, disciplina, docente, turma, faixa de horário e alocação recorrente.
- Reimportação segura: a mesma planilha importada de novo não duplica nada, e uma planilha corrigida atualiza o semestre sem tocar nos outros.
- Reaproveitamento integral da máquina de estados de importação, com prévia que mostra todos os problemas antes de efetivar.
- Modelagem que o calendário futuro consiga consultar por semestre, espaço, dia, faixa, turma e docente, sem interpretar texto.
- Nenhuma exigência de alteração na planilha.

**Non-Goals:**

- Calendário, reservas, disponibilidade e edição manual de alocação.
- Regra de conflito de sala ou de docente, em qualquer forma.
- Adivinhar a qual docente, sala ou disciplina um texto ambíguo se refere.
- Vincular docente a usuário, e criar usuário a partir da planilha.

## Decisions

Cada decisão indica de onde vem: **Confirmado pelo código**, **Confirmado pela planilha**, **Regra necessária para a importação** ou **Decisão do autor**, com a data. Nenhuma decisão continua pendente: as cinco que estavam abertas foram resolvidas em 24/09/2026, e o registro delas está no fim deste documento.

### D1. As duas abas de horário são as fontes, e as demais não são

*Confirmado pela planilha.* `Ensalamento - Geral`, as três abas por docente e as nove abas por curso não têm dado próprio: são fórmulas sobre as abas de horário. Ler qualquer uma delas seria ler o mesmo dado por um caminho pior, com as perdas da consulta: uma sala por vez, o texto `Janela` no lugar da faixa vaga e o prefixo `[CHOQUE]` no lugar do dado. `Validação de Dados` é fonte, mas de catálogo, e não de ocupação.

Em consequência, **as abas de consulta e de espelho não são lidas**, e o importador não depende do valor em cache de nenhuma fórmula. As únicas fórmulas relevantes da planilha são as das abas ignoradas, e o defeito de `C1` na aba de graduação é tratado em D5.

### D2. Uma linha da importação é uma atividade lida da célula

*Regra necessária para a importação; granularidade decidida pelo autor em 24/09/2026.* O motor trabalha com linhas, cada uma com valores de célula como texto, um plano e um número. A grade não tem linhas no sentido do CSV, então o leitor de planilha percorre as duas abas na ordem de leitura (aba, bloco de dia, faixa, coluna) e entrega **uma linha por atividade** lida das células não vazias. As linhas `INTERVALO` e `ALMOÇO` e as colunas separadoras são ignoradas.

A linha é a atividade, e não a célula, porque o plano do motor tem uma ação, um alvo e uma chave de registro criado por linha: uma linha planeja um registro. Como 19 células da planilha real descrevem mais de uma atividade (D3), uma linha por célula obrigaria a alargar o plano para vários alvos e várias chaves, alterando o núcleo da máquina de estados que já serve a importação de usuários, e faria as duas alocações de uma célula aparecerem fundidas numa linha só da prévia. Com a linha sendo a atividade, cada alocação tem o seu plano, e o erro de uma atividade não esconde as outras da mesma célula. No arquivo real, as 1.474 células produzem 1.500 linhas.

Os valores de cada linha, que são o que a tela mostra e o que a confirmação reexecuta, são:

| Coluna lógica | Valor, exatamente como está na planilha |
|---|---|
| `Semestre` | `2026/1`, informado no envio e não lido da planilha (D16) |
| `Tipo` | `ATIVIDADE`, `SALA` ou `DOCENTE`, o que a linha descreve |
| `Célula` | `Horário - Graduação!C10`, com o ordinal da atividade quando a célula tem mais de uma: `Horário - Graduação!F69#2`. A aba não é coluna própria, porque já está aqui |
| `Nome` | o valor do catálogo, nas linhas de `SALA` e de `DOCENTE`: `(1/10)`, `Aldo Gomes` |
| `Dia` | `SEGUNDA ` |
| `Horário` | `13:20 - 14:10` |
| `Turma` | `2º PERÍODO\nEng. Alimento` |
| `Curso` | `BACHARELADO EM ENGENHARIA FLORESTAL`, vazio quando o título não pode ser lido (D5) |
| `Atividade` | `QUÍMICA ORGÂNICA (Elza)  (1/13)` |

Os catálogos também são linhas da importação, antes das atividades, uma por valor das duas
listas da aba de validação de dados, com a célula de origem real (`Validação de Dados!A5`).
Isso não é escolha de apresentação: a confirmação reexecuta as linhas **sem o arquivo**, e o
motor só guarda os valores das linhas, então o que precisa existir na confirmação precisa
estar numa linha. É delas que sai o catálogo contra o qual as atividades são conferidas, e é
delas que saem os espaços e os docentes que a Change manda criar mesmo sem atividade (D4).
No arquivo real são 206 linhas de catálogo e 1.500 de atividade, 1.706 no total.

`Célula` é a coluna identificadora da importação, e é única por construção, porque o ordinal distingue as atividades de uma mesma célula. Isso satisfaz a verificação de identificador repetido do motor sem inventar chave. O número da linha da importação é sequencial, na ordem de leitura, porque a linha física do arquivo não identifica uma atividade. O ordinal aparece só quando a célula tem mais de uma atividade, de modo que a origem da esmagadora maioria das linhas é a referência simples da célula.

A conferência de cabeçalho do motor, escrita para CSV, não se aplica: é o leitor de planilha que confere a estrutura da grade, e as recusas dele são recusas do arquivo inteiro, como as do CSV (D11).

### D3. A atividade é lida da direita para a esquerda, contra os catálogos

*Regra necessária para a importação.* O texto da célula não tem separador confiável entre disciplina, docente e sala: a disciplina pode ter parênteses própios (`Gestão Ambiental (optativa)`, `Unidade Curricular de Extensão (UCE) II`, `Letramento (s): Dimensão Plural`), e a sala pode estar ausente. A leitura por posição fixa erraria em 165 das 1.474 células.

A regra é:

1. Normalizar o texto: trocar quebra de linha por espaço, reduzir espaços repetidos a um e aparar as bordas.
2. Separar a célula em atividades pelos ` / ` que estiverem fora de parênteses, quando cada trecho tiver pelo menos um grupo entre parênteses. Sem isso, a célula é uma atividade só. Cada atividade vira uma linha (D2).
3. Em cada atividade, tomar o último grupo entre parênteses. Se ele for um nome do catálogo de salas, é a sala; senão, a atividade não tem sala, e o último grupo é candidato a docente.
4. Tomar o grupo imediatamente anterior ao da sala, ou o último quando não houver sala, como lista de docentes, separada por `/`, `,` ou ` e `.
5. A disciplina é todo o texto antes do grupo de docentes, com os parênteses internos preservados, sem os separadores de borda (`-`, `:`), aparado.
6. Cada nome de docente precisa estar no catálogo de docentes. Um nome fora dele é erro da linha na coluna `Atividade`.
7. Um último grupo que não é sala nem docente do catálogo é erro da linha na coluna `Atividade`.

A comparação com os catálogos ignora maiúsculas e minúsculas e **preserva acentos**, como a regra do `User.username`: `Érica` e `Erica` são valores diferentes. Não há similaridade, prefixo nem remoção de acento em nenhum ponto.

As 58 células que a regra recusa hoje são o que a prévia mostra ao administrador, que corrige a planilha antes de confirmar, como já faz com o CSV de usuários. A correção é na planilha do campus, feita por quem a mantém, e não uma alteração de estrutura exigida pelo sistema: acrescentar `Zoo I` à coluna `B` da aba `Validação de Dados` ou escrever `(HV 1)` no lugar de `(HV1)` é preencher a própria planilha.

O autor confirmou esse comportamento em 24/09/2026: um docente que não está no catálogo é erro da linha, e não é criado a partir do texto da célula. A aba `Validação de Dados` é a referência dos docentes usados pela planilha, e a correção esperada é acrescentar o nome à coluna `A`. Não há criação automática, similaridade nem correspondência aproximada em nenhum ponto.

### D4. Os catálogos de sala e de docente vêm de `Validação de Dados`

*Confirmado pela planilha.* Criar sala e docente a partir do texto das células faria o sistema aceitar `HV1`, `HV 1`, `Lab.3 - Info` e `Lab. 3 - Info` como quatro registros. A aba `Validação de Dados` é a lista que o campus mantém, e é ela que alimenta as listas de validação das abas de consulta. Por isso ela é o catálogo, e o texto das células só referencia.

Do valor lido:

- **Sala:** os parênteses de borda são retirados, porque a coluna mistura `(1/10)` com `Lab. de Madeira`, e o restante é normalizado como o `username`: bordas aparadas, espaços internos reduzidos, caixa e acentos preservados. A identidade é o nome sem diferenciar maiúsculas de minúsculas, o que faz de `Lab. Bromatologia`, repetido nas linhas 45 e 46, uma sala só.
- **Docente:** mesma normalização, sem retirar parênteses. `Ataliba`, repetido nas linhas 16 e 17, é um docente só. Um valor sem sentido na lista seria criado como docente, porque o sistema não tem como saber que é lixo, e seria inofensivo: docente sem alocação não aparece em lugar nenhum.

As duas listas são lidas inteiras, e todos os valores viram registro, mesmo os que nenhuma célula referencia. É o que permite ao campus cadastrar uma sala nova na planilha antes de usá-la.

### D5. Curso vem da linha 1, com o nome curto do cabeçalho como alternativa

*Confirmado pela planilha; alternativa escolhida pelo autor em 24/09/2026.* O nome do curso é o valor da faixa mesclada da linha 1 que cobre a coluna. Quando esse valor não pode ser lido, o que hoje acontece só nas colunas `C` a `G` da graduação por causa da fórmula `=UPPER(E:E)`, o nome do curso passa a ser o nome curto da segunda linha do cabeçalho da turma (`Eng. Alimentos`), e a linha recebe o aviso `curso_sem_titulo`.

A alternativa era recusar o arquivo. O autor a descartou: a importação não deve ser recusada só porque a fórmula da faixa `C1:G1` não tem valor em cache, desde que o nome do curso possa ser identificado com segurança pelo cabeçalho existente. O aviso permanece, para deixar explícito de onde o nome veio.

O nome curto só serve quando existe: uma coluna sem título de curso **e** sem nome curto no cabeçalho é erro do arquivo, porque aí o curso não é identificável.

### D6. Turma é identificada pelo curso e pelo rótulo do cabeçalho

*Regra necessária para a importação.* A turma de uma coluna é `(curso, rótulo)`, em que o rótulo é a primeira linha do cabeçalho quando há quebra de linha (`2º PERÍODO`, `1º ANO A`) e o cabeçalho inteiro quando não há (`1º ANO Química`). O rótulo é normalizado com a mesma regra dos demais nomes, e ainda com a retirada de um ` - ` separador, o que faz `1º ANO A Agroindústria` e `1º ANO A - Agroindústria` serem a mesma turma.

O cabeçalho usado é o da **primeira** linha de cabeçalho da aba, e não o do bloco de cada dia. Duas razões, as duas confirmadas pela planilha: a coluna `AF` da graduação não tem cabeçalho na linha 86, e a grafia do ensino médio muda entre a linha 2 e as demais. Uma coluna com atividade e sem cabeçalho na primeira linha de cabeçalho é erro do arquivo.

O rótulo guarda o período da graduação e o ano com a letra da turma do ensino médio, que é o que a planilha traz. O sistema não deduz número de período nem ano a partir dele.

### D7. Docente é entidade própria, sem vínculo com usuário nesta Change

*Regra necessária para a importação, alinhada à Change `identificar-usuario-por-username`.* `Teacher` guarda o nome como a planilha o traz, com a mesma normalização e a mesma unicidade sem diferenciar maiúsculas de minúsculas do `User.username`. Nada mais.

Os dois conceitos não se misturam: nem todo docente é usuário, nem todo usuário é docente, e a importação não cria, não altera e não consulta usuário. Nenhum campo de ligação é criado agora, porque nenhuma funcionalidade desta Change o usa, e porque a correspondência futura não depende dele: `Teacher.name` e `User.username` guardam o mesmo valor com a mesma normalização, então a consulta `User.objects.filter(username__iexact=teacher.name)` devolve no máximo um usuário. A Change futura decide se guarda esse resultado num campo.

### D8. A alocação não é única por espaço, dia e faixa

*Confirmado pela planilha.* Uma restrição de unicidade sobre semestre, espaço, dia e faixa recusaria 42 combinações da planilha real, entre elas 20 aulas legitimamente compartilhadas por duas turmas de cursos diferentes, na mesma sala e no mesmo horário.

A identidade de uma alocação é, portanto, **semestre, turma, dia da semana, faixa de horário e disciplina**. Essa combinação é única: uma turma não tem duas vezes a mesma disciplina na mesma faixa do mesmo dia. O espaço e os docentes são dados da alocação, e podem mudar entre importações sem criar registro novo.

As combinações restantes, em que a mesma sala recebe disciplinas diferentes na mesma faixa, são o que a planilha marcaria com `[CHOQUE]`. O importador **não as detecta e não as recusa**: a premissa é que a planilha chega validada, e a regra de conflito é da planilha.

### D9. Cada faixa de horário é uma alocação, e faixas seguidas não são unidas

*Confirmado pela planilha.* Unir faixas seguidas exigiria uma informação que a planilha não tem. Contra a união pesam três fatos do arquivo: 93 execuções de texto repetido atravessam um `INTERVALO` ou o `ALMOÇO`, e uni-las diria que a sala está ocupada num intervalo em que ela está livre; em 13 casos o mesmo texto reaparece no mesmo dia e na mesma coluna depois de uma faixa vazia, e uni-los diria que a sala está ocupada numa faixa vazia; e nenhuma célula é mesclada, o que tiraria a ambiguidade.

Então a importação grava **uma alocação por faixa**, com o início e o fim da própria faixa, que é o dado que a planilha traz sem interpretação. Juntar `07:20 - 08:10` e `08:10 - 09:00` numa linha `07:20 - 09:00` é apresentação, e cabe ao calendário futuro, que pode fazê-lo com segurança porque o critério é local: duas alocações da mesma turma, disciplina, espaço e dia em que o fim de uma é o início da outra.

### D10. O ciclo de vida é o do motor, sem mecanismo próprio

*Confirmado pelo código.* A importação de ensalamento é uma `ImportDefinition` com o tipo `ENSALAMENTO`, e nada do ciclo de vida é reescrito: os estados `VALIDADA`, `COM_ERROS`, `CONCLUIDA` e `DESCARTADA`, a prévia que executa e desfaz num savepoint, a confirmação condicionada ao plano idêntico com `select_for_update`, o descarte, as situações finais, o tratamento de erro inesperado e o histórico são os que `imports/README.md` descreve. Os erros usam `RowError` e `RowPlan`, e não uma estrutura de erro própria.

Quatro capacidades do motor ainda não existem e são implementadas aqui, conforme o requisito "Motor desacoplado dos apps de domínio", que permite acrescentar ao motor a capacidade que a importação nova usa:

| Capacidade | Por quê |
|---|---|
| Fonte que não é CSV | a planilha é XLSX, com duas abas em grade |
| Limites declarados pela importação | o arquivo real tem centenas de KB e 1.706 linhas, acima de `IMPORT_MAX_FILE_SIZE` (1 MB no valor padrão, e o arquivo cresce) e de `IMPORT_MAX_ROWS` (1.000) |
| Modelo para baixar opcional | não existe modelo de planilha de ensalamento, e oferecer um contrariaria "não alterar a planilha" |
| Campo próprio no envio, e metadados próprios na auditoria | o envio pede o código do semestre (D16), e o resumo auditado precisa citá-lo (D15) |

As ações do plano continuam sendo `create`, `update` e `unchanged`. A decisão do autor de preservar a alocação ausente (D13) dispensa a ação `delete` e as linhas de fechamento que a versão anterior deste documento previa, e com isso a importação de ensalamento **não exclui nada**.

O motor continua sem importar código de app de domínio, e o plano continua sendo dado que ele não interpreta.

### D11. A recusa do arquivo inteiro é da estrutura da grade

*Regra necessária para a importação.* O leitor de planilha recusa o arquivo, sem criar importação, quando a estrutura não permite ler a grade: arquivo que não é um XLSX legível, ausência de uma das duas abas de horário ou da aba `Validação de Dados`, aba de horário sem nenhuma linha de cabeçalho, bloco de dia com nome de dia desconhecido, faixa de horário fora do formato `HH:MM - HH:MM`, coluna com atividade e sem cabeçalho de turma, catálogo de salas ou de docentes vazio, e arquivo acima do tamanho ou da quantidade de atividades declarados pela importação. Essas recusas aparecem como erro do formulário de envio, como as do CSV.

O que é de uma célula vira erro daquela linha, e o arquivo segue para a prévia: docente fora do catálogo, último grupo que não é sala nem docente, atividade sem disciplina depois de retirados os grupos, e célula sem nenhum grupo entre parênteses.

Colunas a mais e abas a mais **não são erro**: as nove abas de espelho, as três abas por docente e a aba `Ensalamento - Geral` existem na planilha real e são ignoradas. A regra do CSV, em que toda coluna precisa ser conhecida, não se transporta para cá, porque a planilha não é um formato do sistema.

### D12. Identificação e deduplicação de cada entidade

*Regra necessária para a importação.* Toda comparação de nome ignora maiúsculas e minúsculas e preserva acentos, e todo valor é gravado como foi lido.

| Entidade | Identidade | Criação | Atualização | Vale entre semestres |
|---|---|---|---|---|
| `Semester` | `code`, no formato `AAAA/1` ou `AAAA/2` | informada no envio, criada se não existir | nunca | não se aplica |
| `Space` | `name` | catálogo `Validação de Dados!B` | nenhuma: só o nome existe | sim |
| `Teacher` | `name` | catálogo `Validação de Dados!A` | nenhuma: só o nome existe | sim |
| `Course` | `name` | linha 1 da aba, ou D5 | `stage`, quando a mesma grade muda de aba | sim |
| `Subject` | `name` | texto da atividade | nenhuma | sim |
| `ClassGroup` | `course` e `label` | cabeçalho da coluna | `stage` segue o curso | sim |
| `TimeSlot` | `semester`, `start_time` e `end_time` | coluna `B` da aba | nunca | não |
| `Allocation` | `semester`, `class_group`, `weekday`, `time_slot` e `subject` | célula da atividade | `space` e `teachers` | não |

`Subject` é único pelo nome em todo o sistema, e não por curso, porque a planilha mostra a mesma disciplina servindo turmas de cursos diferentes na mesma sala e no mesmo horário: `QUÍMICA ORGÂNICA (Elza) (1/13)` atende o 2º período de engenharia de alimentos e o de engenharia florestal. Guardá-la duas vezes faria duas disciplinas do que o campus trata como uma.

Três linhas com `Aldo Gomes` não geram três docentes, e uma sala existente não é recriada, porque a criação passa por uma operação do manager que procura pela identidade antes de criar, numa transação, e a restrição de unicidade sobre o nome em minúsculas é a garantia do banco.

### D13. Reimportação do mesmo semestre não exclui nada

*Regra necessária para a importação; decisão do autor em 24/09/2026.* A segunda importação do mesmo semestre não duplica nada, porque toda entidade é procurada pela identidade de D12 antes de ser criada. O comportamento por caso:

| Caso | Comportamento |
|---|---|
| Registro novo na planilha | `create` |
| Registro igual ao que está no banco | `unchanged`, sem nenhuma operação |
| Alocação que mudou de sala ou de docentes | `update`, com o valor anterior e o novo no plano |
| Mesma atividade repetida em faixas seguidas | uma alocação por faixa, cada uma com o seu plano (D9) |
| Mesma célula lida duas vezes | impossível: `Célula` é a coluna identificadora e é única |
| Duas células da mesma turma, faixa, dia e disciplina | a segunda recebe erro de duplicidade, com as duas células citadas |
| Alocação do semestre ausente da planilha nova | **preservada**, em qualquer origem |
| Sala, docente, curso, disciplina, turma ou faixa ausente da planilha nova | preservado, nunca excluído |

A importação **acrescenta e atualiza, e nunca remove**. A razão é a do autor: depois da importação o sistema passa a ser a fonte dos agendamentos, e uma ausência na planilha não é uma ordem de exclusão. A planilha pode ter sido reorganizada, pode estar incompleta no momento do envio, e a alocação pode ter sido ajustada dentro do sistema por uma funcionalidade futura. Interpretar ausência como exclusão faria a importação desfazer, em silêncio, decisões tomadas fora dela.

Isso tem uma consequência que fica registrada: uma aula cancelada na planilha continua no banco até que alguém a retire pela funcionalidade de alteração manual, que é futura. Retirar uma alocação passa a ser sempre uma ação explícita de uma pessoa, nunca um efeito colateral de uma importação.

A origem `IMPORTADA` e `MANUAL` continua na modelagem, mesmo sem edição manual nesta Change. Ela não é mais necessária para proteger a alocação manual da exclusão, porque não há exclusão, mas continua sendo o que permite a uma funcionalidade futura distinguir o que veio da planilha do que foi decidido no sistema, sem uma migration de dados adivinhando a origem de cada alocação existente.

Os catálogos são preservados pela mesma razão e por uma segunda: eles valem entre semestres, e outro registro pode apontar para eles.

### D16. O semestre é informado no envio e gravado nos valores de cada linha

*Confirmado pela planilha e pelo código; decisão do autor em 24/09/2026.* Nenhuma aba da planilha traz o semestre de forma confiável: as abas de horário não o citam, e não há título, célula ou nome de aba com o código. Por isso o envio tem, ao lado do arquivo, um campo com o código do semestre, validado no formato `AAAA/1` ou `AAAA/2`, e o semestre é criado quando ainda não existir. A importação inteira fica vinculada a esse semestre, e uma importação sem semestre não é efetivada: o campo é obrigatório no envio, e um código ausente ou fora do formato é recusado ali, sem criar importação.

O código precisa sobreviver ao envio, porque a confirmação reexecuta as linhas a partir dos valores gravados, e não a partir do formulário. Como `Import` não tem campo para dados próprios de uma importação específica, o código entra como a coluna lógica `Semestre` nos valores de **cada** linha, junto de `Célula`, `Dia`, `Horário` e as demais (D2). Com isso:

- a reexecução da confirmação usa o semestre que foi visto na prévia, e não um informado de novo;
- o plano continua autossuficiente e comparável, sem estado fora das linhas;
- o resumo auditado (D15) lê o semestre das próprias linhas.

Todas as linhas de uma importação têm o mesmo código. A importação recusa o arquivo quando o código não puder ser resolvido num semestre.

### D17. Sem alvo quando o registro foi criado por outra linha da mesma execução

*Regra necessária para a importação, descoberta na implementação.* A confirmação só aplica
quando o plano refeito é idêntico ao da prévia, e a comparação inclui o alvo de cada linha.
A chave gerada na prévia desaparece no rollback, e a da confirmação é outra. Por isso uma
linha que encontra um registro criado por uma **linha anterior da mesma execução** não pode
usar a chave como alvo: o plano divergiria sempre, e a importação nunca seria confirmada.

Nesses casos a linha fica com a ação e sem alvo. A decisão continua determinística, porque a
relação entre as duas linhas é a mesma na prévia e na confirmação. Uma linha que encontra um
registro de uma importação anterior continua com o alvo, porque essa chave é estável.

Na prática isso vale para os valores repetidos dentro de uma mesma lista do catálogo, como
`Ataliba` nas linhas 16 e 17 e `Lab. Bromatologia` nas linhas 45 e 46: a primeira linha
cadastra, a segunda fica `unchanged` sem alvo, e existe um único registro. No arquivo real
são exatamente essas duas linhas `unchanged`.

Para as alocações o caso não chega a existir, porque duas atividades com a mesma identidade
são erro de duplicidade antes de qualquer gravação, conforme a Change já exigia.

### D14. Tudo do ensalamento no app `schedule`

*Regra necessária para a importação.* Um app só para as oito entidades, a importação e as telas dela, e não um app por entidade. As regras de negócio ficam nas operações dos models e dos managers, e `schedule/imports.py` só as aciona e traduz as recusas em `RowError`, como `accounts/imports.py` faz. As telas são as do motor, descritas num `ImportScreens`, com `login_required` na URL e `permission_required = permissions.SPACE_ALLOCATION_IMPORT` na view.

### D15. A auditoria registra o resumo da importação, e não cada entidade

*Decisão do autor em 24/09/2026.* Uma importação de ensalamento aplica milhares de operações: só o arquivo real traz 1.500 atividades, além dos 82 espaços, dos 124 docentes, dos cursos, das disciplinas, das turmas e das faixas. Um registro por entidade produziria um volume que não serve ao objetivo desta versão.

Então o envio, a confirmação e o descarte são registrados pelo motor, com o módulo `IMPORTACAO_ENSALAMENTO`, e **as operações de domínio das linhas não geram registro próprio**. O resumo da confirmação carrega:

| Informação | De onde vem |
|---|---|
| Quem executou | `resolved_by` da importação, já gravado pelo motor |
| Quando | data e hora do registro, definidas pelo ponto único de gravação |
| Semestre importado | coluna lógica `Semestre` das linhas (D16) |
| Arquivo e importação | `file_name` e a chave da importação, que o motor já registra |
| Registros criados, atualizados e preservados | totais por ação, contados a partir das linhas |
| Linhas com erro | total de linhas com erro, contado a partir das linhas |
| Resultado final | a situação da importação |

Os totais por ação já são calculados por `Import.summary()`, que devolve `create`, `update`, `unchanged` e `errors`. O que falta é o semestre e o resultado, e é isso que a capacidade de metadados próprios da importação específica entrega (D10).

Essa decisão modifica o requisito "Auditoria das alterações de dados" da spec `auditoria`, que hoje exige registro para toda operação que altere dados persistidos. O delta abre a exceção para a carga em lote e a limita a ela: a importação de usuários continua registrando o cadastro de cada usuário, e as telas de gestão continuam registrando cada alteração. A auditoria detalhada por entidade do ensalamento fica para depois, e não faz parte desta Change.

Nenhum código de ação novo é preciso: `IMPORTAR`, `CRIAR` e `DESCARTAR` já estão no catálogo. O módulo `ENSALAMENTO` não é acrescentado ao catálogo de auditoria, porque nenhuma operação de domínio do ensalamento é registrada nesta versão.

### D19. Ajuste pontual da planilha de referência, pelo autor

*Decisão do autor em 25/09/2026.* A regra de não alterar a planilha vale para a estrutura: o
sistema não exige coluna, aba, identificador nem marcação criados para ele. Ela não impede o
autor de tirar do arquivo de referência valores de teste que ele mesmo tinha posto.

Foram retirados três, todos introduzidos fora do uso real da planilha: o valor
`ghndgjdgjdg`, que era a última linha da lista de docentes; a sala `sala de esportes`, que
era a última da lista de salas; e a célula `Horário - Graduação!D4`, única que a
referenciava, com o texto `Matemática XXXXXX (Frederico) (sala de esportes)`.

A planilha continua versionada no git, e o estado anterior está no commit que a acrescentou.
Os números desta análise já refletem o arquivo ajustado. As sete pessoas ausentes da lista de
docentes **não** foram tocadas: elas aparecem nas células da grade, e não na lista, e quem
decide o que fazer com elas é o campus.

### D18. Visual, conferido no navegador

*Confirmado na implementação.* A Change não cria tela nova: usa as telas do motor. A
conferência foi feita com o Playwright num container, contra o banco `visual_check`, em 1280
e 360 px, com a planilha real importada, abrindo a lista, o modal de envio, o detalhe e o
detalhe filtrado pelas linhas com erro.

A importação da planilha real no `visual_check`, com o semestre `2026/1`, produziu **1.557
cadastros, 2 linhas sem alteração e 147 linhas com erro**, em 1.706 linhas. As 2 sem
alteração são os valores repetidos das listas (`Ataliba` e `Lab. Bromatologia`), conforme a
D17. As 147 com erro são as atividades que o campus precisa corrigir na planilha antes de
confirmar, detalhadas na seção "A planilha real".

**Corrigido depois da conferência:**

- **A tabela do detalhe rolava a página inteira.** Com as colunas lógicas do ensalamento, a
  tabela ficou mais larga que a página e produzia 598 px de rolagem horizontal em 1280 px, o
  que a spec `interface` proíbe. A tabela do detalhe passou a ficar dentro de um
  `.table-scroll`, componente novo do `app.css`, que rola só a tabela e recebe foco pelo
  teclado, com `role="region"` e nome acessível. Em 360 px a tabela continua virando blocos
  empilhados, e o componente não muda nada.
- **A prévia não deixava ver quais salas seriam importadas.** As 206 linhas de catálogo vinham
  intercaladas, uma sala, um docente, e ocupavam as primeiras onze páginas. Três mudanças, as
  duas primeiras no motor: as linhas de catálogo passaram a sair agrupadas, as salas primeiro
  e os docentes depois; o detalhe passou a oferecer recortes declarados pela importação
  (Salas, Docentes, Atividades), cada um com a sua quantidade e com as colunas que interessam
  a ele; e a linha de cadastro passou a mostrar o valor que será gravado, de modo que a linha
  da sala mostra `(1/13)` lido e `Nome: 1/13` gravado. O código do semestre saiu das linhas
  exibidas e passou a aparecer uma vez no resumo.
- **A coluna `Aba` repetia a `Célula`.** A captura mostrou `Validação de Dados!A2` ao lado de
  `Validação de Dados` em todas as linhas. A coluna saiu, e a aba passou a ser lida da
  referência da célula, o que estreitou a tabela e tirou a repetição.

## Risks / Trade-offs

| Risco | Mitigação |
|---|---|
| A leitura do texto da célula depende da grafia de quem preenche a planilha | a prévia executa tudo e mostra todos os erros de uma vez, sem efetivar nada; o administrador corrige a planilha e envia de novo, criando uma importação nova |
| 1.706 linhas numa prévia sincrona | o limite declarado pela importação segura o tamanho; o processamento assíncrono continua fora do escopo, como em `imports/README.md` |
| Uma aula cancelada na planilha continua no banco, porque a importação não exclui (D13) | é a decisão do autor, e o custo está registrado: a retirada passa a ser sempre ação explícita de uma pessoa, pela funcionalidade futura de alteração manual |
| Uma reimportação de uma planilha muito alterada deixa alocações antigas e novas convivendo no semestre | a prévia mostra os totais por ação antes de confirmar, e a alocação antiga fica identificável pela origem `IMPORTADA` e pela combinação de turma, dia, faixa e disciplina |
| O resumo auditado não permite saber qual entidade mudou (D15) | é a decisão do autor para esta versão; a importação, os valores lidos de cada linha e o plano ficam guardados por tempo indeterminado, e é neles que a alteração de uma linha é reconstituída |
| `Subject` único pelo nome junta disciplinas homônimas de cursos diferentes | é o comportamento que a planilha pede; se o campus vier a precisar separá-las, a distinção entra depois, com migration de dados |

## Migration Plan

1. `schedule` em `INSTALLED_APPS`, com a migration inicial das oito entidades e das restrições de unicidade.
2. Migration de dados em `accounts` com a permissão `ENSALAMENTO.IMPORTAR`, concedida ao perfil `ADMINISTRADOR` sem alterar as demais concessões.
3. `openpyxl` em `requirements.txt` e imagem reconstruída.
4. Nenhuma carga inicial de sala, docente, curso, disciplina, turma, faixa ou alocação: tudo entra pela importação.

## Decisões confirmadas pelo autor

Em 24/09/2026, as cinco questões que estavam abertas foram decididas:

| Questão | Decisão | Onde está |
|---|---|---|
| Nome do curso de engenharia de alimentos | usar o nome curto `Eng. Alimentos` do cabeçalho quando a fórmula não tiver valor em cache, sem recusar o arquivo, mantendo o aviso | D5 |
| Alocação que deixou de constar na reimportação | preservar; a importação acrescenta e atualiza, e nunca exclui. A origem `IMPORTADA` permanece na modelagem, e a edição manual continua fora do escopo | D13 |
| Docente fora do catálogo | continuar como erro da linha, sem criação automática, sem similaridade e sem correspondência aproximada; a correção é acrescentar o nome à coluna `A` da aba `Validação de Dados` | D3, D4 |
| Código do semestre | informado no envio, validado no formato, vinculando a importação inteira, e uma importação sem semestre não é efetivada | D16 |
| Granularidade da auditoria | registrar só o resumo da importação, com executor, data e hora, semestre, arquivo, criados, atualizados, preservados, linhas com erro e resultado final | D15 |

## Open Questions

Nenhuma. As decisões pendentes da versão anterior deste documento foram resolvidas na tabela acima.
