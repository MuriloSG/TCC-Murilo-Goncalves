## Why

A ocupação das salas do campus decorre das aulas regulares, e hoje ela existe apenas na planilha institucional de ensalamento (`sources/planilha_example.xlsx`), atualizada a cada semestre. O sistema não tem nenhuma entidade de domínio para isso: `accounts`, `audit`, `imports`, `notices`, `outbox` e `ui` não têm model de semestre, espaço, curso, disciplina, docente, turma, horário nem alocação, e o diretório `schedule/` está vazio. Sem esses dados no banco, o calendário e a consulta de disponibilidade não têm o que consultar, e o P10 da Constitution ficaria sem cumprimento: a atualização da ocupação institucional ocorre por ação administrativa, e a planilha não substitui o banco de dados do sistema.

Esta Change transforma a planilha em dados próprios do sistema. Ela importa um semestre de ensalamento para o banco, por uma ação administrativa, reutilizando a máquina de estados de importação que já existe no app `imports`. Depois da importação, os agendamentos são dados da aplicação: nenhuma consulta em tempo de execução volta à planilha, e a planilha segue sendo usada pelo campus sem nenhuma alteração.

A análise do arquivo real determinou de onde os dados saem, e a resposta não é a aba que dá nome ao processo:

| Aba | Papel real, confirmado pelo arquivo | Fonte? |
|---|---|---|
| `Horário - Graduação` | Grade de 5 blocos de dia, 14 faixas de horário e 39 colunas de turma, com o texto da atividade digitado em cada célula | **Sim** |
| `Horário - Ensino Médio` | Mesma estrutura, com 12 faixas de horário e 20 colunas de turma | **Sim** |
| `Validação de Dados` | Coluna `A` com 124 nomes de docente e coluna `B` com 82 nomes de sala, que alimentam as listas de validação das abas de consulta | **Sim**, como catálogo |
| `Ensalamento - Geral` | Consulta: 20 células `C1` a `H24` são fórmulas `HLOOKUP` sobre as duas abas de horário, filtradas pela sala escolhida na lista de validação de `C1` | Não |
| `Horário - Professor`, `Horário - Professor - 1`, `Horário - Professor - Separado` | Consultas iguais, filtradas pelo docente escolhido em `C1` ou `D1` | Não |
| `Eng. Alimentos`, `Eng. Florestal`, `BSI`, `Med. Veterinária`, `Lic. Ciências Biológicas`, `Lic. em Física`, `Lic. em Matemática`, `Lic. em Química`, `Lic. em Pedagogia` | Espelhos: cada célula de dado é uma fórmula `='Horário - Graduação'!<célula>` | Não |

`Ensalamento - Geral` é o resultado esperado do ensalamento visto por sala, e não uma tabela de dados: além de ser calculada, ela mostra uma sala por vez, produz o texto `Janela` para a faixa vaga e o prefixo `[CHOQUE]` quando a mesma sala aparece duas vezes na mesma faixa. Essa lógica de conflito é responsabilidade da planilha e fica fora desta Change.

## What Changes

- **App `schedule`**, com os models do ensalamento: `Semester`, `Space`, `Course`, `Subject`, `Teacher`, `ClassGroup`, `TimeSlot` e `Allocation`. Nenhum desses conceitos existe no projeto, e nada aqui duplica model existente.
- **Alocação como agendamento recorrente do espaço**: semestre, espaço, turma, disciplina, docentes, dia da semana e faixa de horário, com a origem `IMPORTADA`. A origem existe desde já para que uma funcionalidade futura de alteração manual saiba distinguir o que veio da planilha do que foi decidido no sistema.
- **Dados pertencentes ao semestre**: `Semester` com o código `2026/1`, e `TimeSlot` e `Allocation` presos a ele. Importar `2026/2` não toca em nada de `2026/1`.
- **Semestre informado no envio**, ao lado do arquivo, validado no formato `AAAA/1` ou `AAAA/2`, criado quando não existir, e gravado nos valores de cada linha, para que a confirmação reexecute com o semestre que foi visto na prévia. A planilha não traz essa informação em nenhuma aba.
- **Importação que acrescenta e atualiza, e nunca exclui**: nada é removido do banco por uma importação, nem alocação, nem catálogo. Uma ausência na planilha não é ordem de exclusão, porque depois da importação o sistema é a fonte dos agendamentos.
- **Importação `ENSALAMENTO`** sobre a infraestrutura do app `imports`, com envio, prévia que executa e desfaz, confirmação condicionada ao plano idêntico, descarte, histórico e detalhe, exatamente como a importação de usuários. As ações do plano continuam sendo `create`, `update` e `unchanged`.
- **Leitura de planilha XLSX em grade** no motor de importação, ao lado do leitor de CSV que já existe. Cada célula de atividade das duas abas de horário vira uma linha da importação, identificada pela aba e pela célula.
- **Limites por importação** no motor: o arquivo real tem centenas de KB e 1.706 linhas, acima dos limites globais de hoje (`IMPORT_MAX_FILE_SIZE` de 1 MB e `IMPORT_MAX_ROWS` de 1.000).
- **Auditoria por resumo da importação**, e não por entidade criada ou alterada. O registro da confirmação passa a citar o semestre e o resultado, junto dos totais de criados, atualizados, preservados e linhas com erro que o motor já conta. Uma importação aplica milhares de operações, e um registro por entidade não serve ao objetivo desta versão.
- **Permissão `ENSALAMENTO.IMPORTAR`**, por migration de dados, concedida ao perfil `ADMINISTRADOR`.
- **Dependência `openpyxl`** em `requirements.txt`, para ler o XLSX.

### Fora do escopo

- Calendário, visualização por sala, por docente ou por turma, e consulta de disponibilidade por data e horário.
- Reservas pontuais, solicitações, aprovação, eventos e notificações de ensalamento.
- Criação ou edição manual de alocação, e exclusão de alocação, por qualquer caminho. A importação não exclui, e não há tela para excluir.
- Auditoria detalhada por entidade criada ou alterada pela importação.
- Vínculo entre `Teacher` e `User`, e qualquer tela que o apresente. A correspondência futura é possível porque `Teacher.name` e `User.username` guardam o mesmo valor com a mesma normalização, e é isso que esta Change garante.
- Responsável pelo espaço, e qualquer campo ou tela para ele.
- Criação automática de usuários a partir da planilha.
- Detecção de `[CHOQUE]`, reprodução das fórmulas de conflito, resolução dos conflitos da planilha e importação do texto `[CHOQUE]` como dado.
- Qualquer alteração na planilha, e qualquer consulta à planilha depois da importação.
- Sincronização automática com Google Sheets ou com qualquer sistema externo.
- Carga horária, ementa, matrícula de estudante e qualquer dado acadêmico que a planilha não traga.

## Capabilities

### Added Capabilities

- `ensalamento`: os dados acadêmicos e a ocupação recorrente dos espaços passam a existir no sistema, com semestre, espaço, curso, disciplina, docente, turma, faixa de horário e alocação, e com a importação da planilha institucional como forma de carregá-los.

### Modified Capabilities

- `importacao-planilhas`: o motor passa a aceitar uma fonte que não seja CSV, com a leitura de uma planilha XLSX em grade; os limites de tamanho e de quantidade de linhas passam a poder ser declarados pela importação específica; o modelo para baixar passa a ser opcional; o envio passa a poder ter campos próprios da importação específica, gravados nos valores das linhas; e a importação específica passa a poder acrescentar metadados ao registro de auditoria das suas importações.
- `controle-acesso`: o catálogo de permissões ganha `ENSALAMENTO.IMPORTAR`, concedida ao perfil `ADMINISTRADOR` pela migration que a acrescenta.
- `auditoria`: o requisito que exige registro para toda operação que altere dados persistidos abre uma exceção, limitada à carga em lote de uma importação, cujo registro é o resumo da importação. A importação de usuários e as telas de gestão continuam registrando cada alteração.

## Impact

- **`schedule/`** (app novo): `models.py`, `imports.py`, `urls.py`, `views.py`, `permissions.py`, `migrations/`, `templates/schedule/` e `tests/`.
- **`imports/`**: `reader.py` (a leitura de CSV passa a ser uma das fontes), `workbook.py` (novo, leitura da grade XLSX), `definitions.py` (fonte, limites, metadados da auditoria, ausência de modelo), `models.py` (os metadados da definição nos registros de auditoria), `forms.py` (o campo de arquivo e a ajuda vindos da fonte, e os campos próprios do envio) e `views.py` (modelo opcional e campos próprios do envio). `execution.py` e o plano não mudam.
- **`config/settings.py`**: `schedule` em `INSTALLED_APPS`; os limites globais continuam como valor padrão de quem não declara o seu.
- **`accounts/permissions.py`** e **`accounts/migrations/`**: a permissão nova e o rótulo do recurso `ENSALAMENTO`.
- **`audit/catalog.py`**: o módulo `IMPORTACAO_ENSALAMENTO` e os rótulos dos campos do resumo. Sem migration, conforme a spec `auditoria`. Nenhum módulo de entidade do ensalamento é acrescentado, porque as operações de domínio não são registradas nesta versão.
- **`requirements.txt`**: `openpyxl`.
- **`ui`**: nenhum componente novo. As telas da importação são as do motor, e o item de navegação segue a regra de permissão que já existe.
- **Sem impacto**: `notices`, `outbox` (a importação de ensalamento não produz efeito externo) e as telas de usuários e de perfis.

## Alinhamento com o TCC

- **P10 e RNF07:** a planilha é fonte de carga, acionada por ação administrativa, e o sistema passa a responder pela ocupação a partir do próprio banco, sem consulta em tempo real a sistema externo.
- **P2 e RNF06:** a identificação, a deduplicação e a criação de cada entidade são operações do model; a importação específica só as aciona e traduz as recusas em erros do plano.
- **P3:** todo o esquema entra por migrations, e o acesso aos dados é pelo ORM.
- **P6:** a alocação guarda semestre, espaço, dia e faixa de horário como campos indexados, para que a consulta de disponibilidade futura não precise interpretar texto.
- **P11:** as entidades e os relacionamentos desta Change são a base do diagrama de classes do ensalamento.
- **RNF01:** o acesso à importação exige `ENSALAMENTO.IMPORTAR`, pelo mecanismo de permissão que já existe.
