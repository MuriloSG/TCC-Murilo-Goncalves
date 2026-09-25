## 1. Capacidades novas do motor de importação

- [x] 1.1 Extrair a leitura de CSV de `imports/reader.py` para uma fonte declarada pela definição, mantendo `read_csv` como a fonte padrão e o comportamento atual intacto (D10)
- [x] 1.2 Permitir que a definição declare o tamanho máximo e a quantidade máxima de linhas, usando os valores de `config/settings.py` como padrão (D10)
- [x] 1.3 Criar `imports/workbook.py` com a fonte de planilha em grade: abre o XLSX sem recalcular fórmulas, percorre as abas declaradas, entrega uma linha por célula de dado com os valores como texto, numera as linhas na ordem de leitura e recusa o arquivo inteiro quando a estrutura declarada não é encontrada (D2, D11)
- [x] 1.4 Permitir campos próprios da definição no formulário de envio, gravando o valor de cada um como coluna lógica nos valores de todas as linhas, e recusando no formulário o campo obrigatório vazio ou inválido (D16)
- [x] 1.5 Permitir que a definição acrescente metadados aos registros de auditoria das suas importações, sem substituir os que o motor já grava, e incluir no resumo da confirmação o total de linhas com erro e a situação final (D15)
- [x] 1.6 Tornar o modelo para baixar opcional, sem oferecer a rota nem o link na importação que declara não ter modelo
- [x] 1.7 Deixar o campo de arquivo e a ajuda do formulário de envio vindos da fonte declarada
- [x] 1.8 Conferir que o plano continua com as ações `create`, `update` e `unchanged`, sem ação de exclusão, e que `execution.py` não muda (D13)
- [x] 1.9 Testar, com uma importação de teste sobre `auth.Group`: fonte de grade lendo duas abas, aba a mais ignorada, aba declarada ausente recusando o arquivo, limites declarados pela definição, campo próprio gravado nas linhas e usado na confirmação, campo próprio obrigatório vazio recusado no envio, metadados próprios na auditoria e importação sem modelo
- [x] 1.10 Conferir que a importação de usuários continua com o mesmo comportamento, inclusive a auditoria por usuário cadastrado, rodando `accounts/tests/test_user_import.py` e `test_user_import_views.py`
- [x] 1.11 Commit

## 2. App `schedule` e entidades do ensalamento

- [x] 2.1 Criar o app `schedule`, registrá-lo em `INSTALLED_APPS` e acrescentar `openpyxl` a `requirements.txt`
- [x] 2.2 Criar `Semester`, com o código único e a validação do formato `AAAA/1` ou `AAAA/2`
- [x] 2.3 Criar `Space`, `Teacher`, `Course` e `Subject`, cada um com o nome normalizado como o `username` e único sem diferenciar maiúsculas de minúsculas, por verificação no `clean()` e por `UniqueConstraint` sobre `Lower('name')` (D4, D12)
- [x] 2.4 Criar `ClassGroup`, com o curso, o rótulo normalizado, a etapa e a unicidade de curso e rótulo em minúsculas (D6)
- [x] 2.5 Criar `TimeSlot`, com o semestre, o início, o fim, a validação de início anterior ao fim e a unicidade das três colunas
- [x] 2.6 Criar `Allocation`, com o semestre, a turma, a disciplina, o espaço opcional, os docentes, o dia da semana, a faixa de horário e a origem, com a unicidade de semestre, turma, dia, faixa e disciplina, sem nenhuma restrição sobre espaço, dia e faixa (D8)
- [x] 2.7 Criar as operações de manager que procuram pela identidade antes de criar, numa transação, para cada entidade, e a operação que atualiza o espaço e os docentes de uma alocação. Nenhuma operação de exclusão de alocação (D13)
- [x] 2.8 Deixar as operações do ensalamento sem gravação de auditoria por entidade, conforme D15
- [x] 2.9 Criar os índices de consulta por semestre, espaço, dia da semana e faixa de horário
- [x] 2.10 Criar a migration inicial do app
- [x] 2.11 Testar a normalização e a preservação de acento e caixa, o valor equivalente não duplicando, o acento distinguindo dois registros, a disciplina compartilhada entre cursos, turmas homônimas de cursos diferentes, a faixa inválida recusada, a alocação sem espaço, duas alocações no mesmo espaço, dia e faixa aceitas, e a mesma turma, dia, faixa e disciplina recusada
- [x] 2.12 Commit

## 3. Leitura da planilha de ensalamento

- [x] 3.1 Declarar em `schedule/imports.py` a estrutura das duas abas de horário: linhas de cabeçalho, coluna do dia, coluna do horário, colunas de turma e colunas separadoras (D2)
- [x] 3.2 Ler o dia da semana pelo nome, aceitando `SEGUNDA` e `SEGUNDA-FEIRA`, com e sem espaço nas bordas, e recusar o arquivo quando o nome não for reconhecido
- [x] 3.3 Ler a faixa de horário no formato `HH:MM - HH:MM`, ignorar `INTERVALO` e `ALMOÇO` e recusar o arquivo com faixa fora do formato
- [x] 3.4 Ler o rótulo da turma da primeira linha de cabeçalho da aba, com a normalização de D6, e recusar o arquivo quando uma coluna com atividade não tiver cabeçalho ali
- [x] 3.5 Ler o nome do curso do título sobre o grupo de colunas, com o nome curto do cabeçalho como alternativa e o aviso `curso_sem_titulo`, e recusar o arquivo só quando não houver título nem nome curto (D5)
- [x] 3.6 Ler os catálogos de espaço e de docente da aba de validação de dados, retirando os parênteses do nome do espaço, e recusar o arquivo com catálogo vazio (D4)
- [x] 3.7 Testar a leitura contra `sources/planilha_example.xlsx`: 1.474 células de atividade que produzem 1.500 linhas, os cinco dias das duas abas, as 15 e as 11 faixas, as 39 e as 20 colunas de turma, as abas calculadas ignoradas, a coluna `AF` sem cabeçalho no bloco da sexta-feira e o curso de engenharia de alimentos com o nome curto e o aviso
- [x] 3.8 Commit

## 4. Leitura da atividade e plano da linha

- [x] 4.1 Normalizar o texto da célula e separar as atividades pelos ` / ` fora de parênteses, quando cada trecho tiver grupo entre parênteses, entregando uma linha por atividade com o ordinal na origem (D2, D3)
- [x] 4.2 Resolver o espaço pelo último grupo contra o catálogo, e tratar a atividade como sem espaço quando o grupo for um docente do catálogo
- [x] 4.3 Resolver a lista de docentes pelo grupo anterior, separada por `/`, `,` e ` e `, com correspondência exata que ignora só a caixa
- [x] 4.4 Extrair a disciplina do texto anterior à lista de docentes, preservando os parênteses internos
- [x] 4.5 Transformar em erro da linha o docente fora do catálogo, o último grupo que não é espaço nem docente, a atividade sem disciplina e a célula sem nenhum grupo entre parênteses, sem criar docente nem espaço a partir do texto da célula (D3, D11)
- [x] 4.6 Resolver o semestre a partir da coluna lógica `Semestre` dos valores da linha, e não do formulário, e tratar como erro do arquivo o código que não se resolve num semestre (D16)
- [x] 4.7 Montar o plano da linha com `create`, `update` ou `unchanged`, e com as mudanças de espaço e de docentes no `update` (D12, D13)
- [x] 4.8 Acrescentar a verificação de duplicidade de turma, dia, faixa e disciplina entre duas células, com as duas células citadas no erro
- [x] 4.9 Travar, antes da primeira linha, o semestre e as alocações do semestre, para que duas importações concorrentes sejam serializadas
- [x] 4.10 Testar cada caso de leitura com as células reais da planilha: atividade completa, disciplina com parênteses próprios, atividade sem espaço, vários docentes com cada separador, duas atividades na mesma célula, espaço fora do catálogo, espaço com grafia diferente, docente fora do catálogo, correspondência por prefixo recusada e célula sem parênteses
- [x] 4.11 Testar que as faixas seguidas geram uma alocação por faixa, inclusive quando a execução atravessa um intervalo
- [x] 4.12 Commit

## 5. Reimportação

- [x] 5.1 Garantir que a importação só acrescenta e atualiza: nenhuma linha com ação de exclusão, e nenhuma exclusão de alocação, espaço, docente, curso, disciplina, turma ou faixa de horário (D13)
- [x] 5.2 Testar a reimportação sem mudanças com todas as linhas `unchanged`, a alocação que mudou de espaço com `update`, a alocação ausente da planilha nova preservada, a alocação nova acrescentada a um semestre já importado, a alocação `MANUAL` preservada, o catálogo preservado e o outro semestre intocado
- [x] 5.3 Testar a duplicidade dentro da planilha, com as duas células citadas no erro
- [x] 5.4 Testar a divergência entre a prévia e a confirmação refazendo o plano, sem aplicar nada
- [x] 5.5 Commit

## 6. Permissão, telas e auditoria

- [x] 6.1 Acrescentar `ENSALAMENTO.IMPORTAR` a `accounts/permissions.py`, com o rótulo do recurso `ENSALAMENTO`, e criar a migration de dados que a concede ao perfil `ADMINISTRADOR` sem alterar as demais concessões
- [x] 6.2 Acrescentar ao catálogo de auditoria o módulo `IMPORTACAO_ENSALAMENTO` e os rótulos dos campos do resumo, sem acrescentar módulo de entidade do ensalamento e sem migration (D15)
- [x] 6.3 Declarar o `ImportScreens` do ensalamento, sem modelo para baixar, e criar as rotas com `login_required` e a permissão declarada nas views
- [x] 6.4 Acrescentar o campo do código do semestre ao envio, obrigatório, validado no formato, criando o semestre quando não existir (D16)
- [x] 6.5 Acrescentar o item de navegação da importação de ensalamento, visível só com a permissão
- [x] 6.6 Testar cada rota nas quatro situações: anônimo redirecionado ao login com `next`, autenticado sem a permissão com 403, com a permissão executando e POST sem CSRF com 403
- [x] 6.7 Testar o envio sem semestre e com semestre fora do formato recusados no formulário, o semestre criado no envio e a confirmação usando o semestre gravado nas linhas
- [x] 6.8 Testar o resumo de auditoria da confirmação com o semestre, o arquivo, os totais, as linhas com erro e o resultado, e a ausência de registro por entidade do ensalamento
- [x] 6.9 Testar que a importação não cria nem altera usuário, e que um docente sem usuário correspondente não impede a importação
- [x] 6.10 Conferir as telas no navegador pelo banco `visual_check`, conforme as convenções, e registrar o que foi ajustado
- [x] 6.11 Commit

## 7. Fechamento

- [x] 7.1 Importar `sources/planilha_example.xlsx` de ponta a ponta no banco `visual_check`, conferir os totais por ação e registrar no `design.md` os erros que a planilha real produz
- [x] 7.2 Conferir que os deltas de `ensalamento`, `importacao-planilhas`, `controle-acesso` e `auditoria` descrevem o que foi implementado, ajustando o que divergir
- [x] 7.3 Rodar a suíte inteira com `make test` e corrigir o que quebrar
- [x] 7.4 Registrar em `openspec/conventions.md` qualquer preferência nova surgida na implementação
- [x] 7.5 Commit
