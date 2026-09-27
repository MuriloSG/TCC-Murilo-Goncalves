# Plano de implementação: importar-usuarios-com-o-ensalamento

Plano da Change. As decisões ficam numeradas (D1 a D12) e são citadas nas docstrings da implementação, como nas demais Changes. O texto diz o que muda em cada arquivo, em que ordem e como cada parte é testada, para que a implementação não precise refazer a investigação.

---

## 1. O que a investigação encontrou

### 1.1 A planilha de referência

**Ponto de atenção.** O arquivo `sources/planilha_example_sugerida.xlsx` do repositório (commit `cd32510`, 186.666 bytes) **não tem a aba `usuários - sistema`**. As abas dele são:

| Aba | Dimensão usada | Lida hoje |
|---|---|---|
| `Horário - Graduação` | 1000 × 49 | Sim (`UNDERGRADUATE_SHEET`) |
| `Horário - Ensino Médio` | 1000 × 26 | Sim (`SECONDARY_SHEET`) |
| `Validação de Dados` | 1000 × 3 | Sim (`CATALOG_SHEET`): coluna A `Disciplina (Professor)`, 129 docentes; coluna B `Salas Disponíveis`; coluna C vazia |

Não há outra cópia do arquivo (o caminho `/mnt/data/planilha_example_sugerida.xlsx` não existe nesta máquina). A estrutura da aba de usuários foi tirada de `sources/importacao-usuarios-ensalamento.csv` (commit `6a814e0`, "adiciona a planilha de ensalamento e o arquivo de importacao de usuarios"), que é o arquivo que a aba substitui:

| Coluna | Exemplo | Observação |
|---|---|---|
| `E-mail` | `adailton@ifnmg.edu.br` | Todos no domínio institucional |
| `Nome` | `Aldo Gomes` | |
| `Perfil` | `DOCENTE` | Único valor presente, nas 129 linhas |
| `Nome de usuário` | `Aldo Gomes` | Igual, em todas as linhas, ao nome do docente na coluna A de `Validação de Dados` (é o que faz `teacher_of` funcionar) |

São as mesmas quatro colunas de `UserImport.columns` (`accounts/imports.py`). **Antes de implementar**, a primeira tarefa é obter a planilha com a aba e conferir o nome exato da aba, a linha do cabeçalho e os rótulos. Se diferirem do que está aqui, ajustar só as constantes do Passo 2 e a spec.

**Nome das abas.** O leitor atual compara os nomes de aba de forma exata (`name not in workbook.sheetnames`, em `imports/workbook.py`). Os rótulos de coluna do CSV são comparados por `imports.reader.normalize_header` (sem acento, sem caixa, sem bordas). Para a aba de usuários a comparação exata é arriscada: como a ausência é silenciosa por regra, um `Usuários - Sistema` digitado com outra caixa seria ignorado sem aviso. Por isso a aba opcional é reconhecida por `normalize_header` (D4).

### 1.2 Máquina de estados da importação

`Import.Status` (`imports/models.py`): `VALIDADA`, `PENDENTE`, `COM_ERROS`, `CONCLUIDA`, `DESCARTADA`. Os eventos são `Import.objects.preview`, `Import.refresh`, `Import.confirm`, `Import.discard` e `Import.remove`. **Não existe estado de processamento**: prévia e confirmação são síncronas, e o `imports/README.md` registra que `PROCESSANDO` e `FALHOU` não existem porque não seriam observados. A situação vale para a importação inteira, e não por etapa.

Dentro de uma prévia ou confirmação, `imports.execution.run` faz, na transação de quem chama:

```text
definition.execution(importation)      contexto da execução (RunState no ensalamento)
acting_from_import(executor)           origem "importação" na auditoria
definition.lock(rows, executor)        travas e preparação (espaços, semestre, duplicidades)
para cada linha: savepoint → definition.execute_row → RowPlan
definition.check_file(executor)        erros do arquivo inteiro
```

- Prévia (`ImportManager.preview`): tudo num savepoint desfeito com `set_rollback(True)`; grava só `Import` e `ImportRow`.
- Atualização da prévia (`Import.refresh`): igual, sobre as linhas gravadas.
- Confirmação (`Import.confirm`): trava a importação, `check_confirmation`, savepoint, reexecuta; aplica só se o plano for idêntico (`comparable()`) e sem erros; senão desfaz, grava o novo plano e conta a prévia refeita. Erro inesperado desfaz tudo e a importação continua `VALIDADA`.
- Uma linha com erro ou pendência tem o próprio savepoint desfeito (`execute_row`), e `ValidationError`/`DatabaseError` viram erro da linha.

### 1.3 Importação do ensalamento

- `schedule/imports.py` `SpaceAllocationImport`: `kind='ENSALAMENTO'`, fonte `WorkbookSource`, `sheets = (UNDERGRADUATE_SHEET, SECONDARY_SHEET, CATALOG_SHEET)`, colunas lógicas `Semestre`, `Início`, `Fim`, `Tipo`, `Célula`, `Nome`, `Dia`, `Horário`, `Turma`, `Curso`, `Atividade`; identificador `Célula`.
- `read_cells`: primeiro as linhas `SALA` e `DOCENTE` da aba de validação (`catalog_entries`), depois as `ATIVIDADE` das duas abas de horário. `ImportUploadForm` copia `Semestre`, `Início` e `Fim` para todas as linhas.
- `execute_row` despacha pelo `Tipo`: `execute_space`, `execute_catalog(Teacher, …)` e `execute_activity`.
- `lock`: `classify` e `apply_spaces` (espaços, só olham linhas `SALA`/`ATIVIDADE` em `schedule.spaces.read_found`), `Semester.objects.resolve`, `apply_period`, `repeated_activities` e trava das alocações do semestre.
- `RunState` (contextvar `RUN`) guarda o que a execução criou (`created`), para que o alvo do plano não use chave gerada na mesma execução.
- `check_confirmation`: permissões de espaço de quem confirma.
- Nada disso cria ou consulta usuário. A spec `ensalamento` hoje **proíbe** ("A importação NÃO DEVE (MUST NOT) criar, alterar nem desativar usuário", cenário "Nenhum usuário criado"), e a docstring de `Teacher` repete isso.

### 1.4 Usuário, perfil, senha

- `accounts.models.User`: `USERNAME_FIELD = 'email'`; `email` com `unique=True` e `UniqueConstraint(Lower('email'))`; `username` opcional, identificador de domínio (não é credencial), único sem caixa por `clean()` e `UniqueConstraint(Lower('username'))`, gravado como informado (`normalize_username`).
- `User.objects.register(email, name, role, username=None)`: exige perfil, exige `@ifnmg.edu.br`, `set_unusable_password()`, `full_clean()`, cria `UserRole`, põe `PASSWORD_LINK` no outbox **na mesma transação** e grava `AuditLog` `CREATE`/`USER`. É a única forma de cadastro fora do superadmin.
- Senha: `accounts.emails.password_link` gera o token no envio, pelo gerador e pela rota de recuperação de senha do allauth (`account_reset_password_from_key`), e descarta o envio se o usuário já tem senha. Nenhuma senha é lida, gerada nem guardada pela importação.
- Perfil: `Role`, com `code` único (`DOCENTE`, `ADMINISTRADOR` e os personalizados), ligado por `UserRole` (um perfil por usuário).
- `accounts/imports.py` `UserImport`: identificador `E-mail` (normalizado por `User.objects.normalize_email`); `clean_values` valida e-mail e nome pelos campos dos formulários, normaliza o nome de usuário e resolve o perfil por `Role.objects.filter(code=valor.strip().upper())`, com o erro `unknown_role` "Não existe perfil com o código X. Use o código de um perfil cadastrado."; `create` exige domínio institucional, exige `USUARIO.CRIAR` (`permission_denied`) e chama `register`; `update` altera nome, nome de usuário e perfil conforme as permissões de edição.

### 1.5 Usuário e ensalamento

```text
User ──(teacher_of: Teacher.name iexact User.username, sem FK)──> Teacher
Teacher ──(M2M)── Allocation ──> ClassOffering.sync_assignments ──> TeachingAssignment
TeachingAssignment ──(FK offering)──> ClassOffering [semester, subject, class_group]
```

`Teacher` vem da lista de docentes (`Teacher.objects.resolve`) e das atividades; `TeachingAssignment` é derivado das alocações. Nenhum deles conhece `User`. O `username` do CSV é exatamente o nome do docente, então criar o `User` com o `username` da aba basta para `teacher_of` encontrar o docente, sem relacionamento novo.

---

## 2. Decisões

**D1. A etapa de usuários é uma fase da execução, não um estado de `Import.Status`.** Os estados do motor descrevem a importação para quem a vê e decide (validada, pendente, com erros, concluída, descartada); não existe estado de processamento, e o README explica por quê. Um `PERSISTING_USERS` seria um estado que ninguém observa, numa execução síncrona e transacional. A etapa é garantida pela ordem das linhas: `read_cells` entrega as linhas `USUARIO` antes das `SALA`, `DOCENTE` e `ATIVIDADE`, e `execute_row` executa cada uma no próprio savepoint, na ordem. O fluxo conceitual fica:

```text
envio → leitura (WorkbookSource + read_cells) → prévia/confirmação:
  lock (espaços, semestre, duplicidades de atividade e de usuário, trava de usuários)
  linhas USUARIO        ← "persistência dos usuários" (só existe se a aba existir)
  linhas SALA/DOCENTE   ← catálogos
  linhas ATIVIDADE      ← alocações
  check_file
→ VALIDADA | PENDENTE | COM_ERROS  →  confirmação  →  CONCLUIDA
```

Sem a aba não há linha `USUARIO`, e a execução passa direto às linhas de catálogo: é a "transição direta" pedida, sem ramo condicional.

**D2. Mesma transação, mesmo savepoint.** A garantia "tudo ou nada" da spec `importacao-planilhas` e a comparação de planos (`comparable()`) exigem que os usuários façam parte da mesma unidade. Numa transação própria, os usuários ficariam gravados quando o ensalamento divergisse ou falhasse, e a confirmação seguinte teria outro plano (`unchanged` no lugar de `create`). O `register` já grava o link no outbox na mesma transação (D7 de `enviar-emails-por-outbox`), então a prévia desfaz o envio junto.

**D3. Chave do usuário: o e-mail.** É o `USERNAME_FIELD`, tem unicidade sem caixa no banco, é o identificador da importação de usuários e é obrigatório no cadastro. O `username` é opcional e pode faltar, e é identificador de domínio, e não de conta. A busca é `User.objects.filter(email__iexact=User.objects.normalize_email(valor))`, a mesma de `UserImport.execute_row`. O `username` continua sendo conferido: repetido na aba é erro, e já usado por outro usuário é recusado pelo `clean()` do `register`.

**D4. Aba opcional reconhecida por nome normalizado.** A constante é `USERS_SHEET = 'usuários - sistema'`, procurada entre `workbook.sheetnames` por `normalize_header`. As abas obrigatórias continuam exatas, como hoje. O motor ganha `ImportDefinition.optional_sheets = ()` só para o texto de ajuda do envio; a leitura da aba opcional fica em `schedule.sheets`, porque é a importação específica que percorre as células (contrato de `WorkbookSource`).

**D5. Cabeçalho da aba conferido na leitura.** Linha 1 é o cabeçalho, dados da linha 2 em diante, linhas totalmente vazias ignoradas. Rótulos por `normalize_header`: `E-mail`, `Nome`, `Perfil`, `Nome de usuário`. Coluna faltando ou repetida recusa o arquivo (`FileRejected`, estrutura da grade), com a aba no texto: `Falta a coluna "Perfil" na aba "usuários - sistema". Use as colunas E-mail, Nome, Perfil e Nome de usuário.` Coluna a mais é ignorada, como nas demais abas da grade. Aba sem nenhuma célula preenchida é tratada como ausente; aba só com cabeçalho não gera linha.

**D6. Reaproveitar `UserImport`, sem implementação paralela.** A linha `USUARIO` usa as colunas lógicas com os mesmos rótulos de `UserImport` (`E-mail`, `Nome`, `Perfil`, `Nome de usuário`; `Nome` já existe no ensalamento). Assim `UserImport().clean_values(values)` e `UserImport().create(cleaned, errors, executor)` rodam sobre os valores da linha sem adaptação, com as mesmas mensagens, o mesmo `unknown_role`, a mesma exigência de domínio e de `USUARIO.CRIAR` e o mesmo `register`. A única coisa acrescentada é a conferência de célula obrigatória, que a fonte CSV faz no leitor e a fonte em grade não faz: mesma mensagem e mesmo código do leitor (`required`, `Preencha a coluna X.`).

**D7. Usuário existente não é alterado.** A importação do ensalamento é autorizada por `ENSALAMENTO.IMPORTAR`; editar e trocar perfil são operações distintas da spec `gestao-usuarios` (`USUARIO.EDITAR`, `USUARIO.ALTERAR_PERFIL`), e a importação de usuários já existe para isso. O plano da linha existente é `unchanged` com `target=user.pk`, sem exigir permissão. Avisos:
- `usuario_com_outros_dados`: nome, nome de usuário (normalizado) ou perfil da planilha diferente do cadastro. Texto: "Usuário já cadastrado com outros dados. A importação do ensalamento não altera o cadastro; use a tela de usuários ou a importação de usuários."
- `usuario_inativo`: "Usuário inativo. A importação do ensalamento não o reativa."

Os avisos entram no plano comparado; se alguém editar o usuário entre a prévia e a confirmação, o plano diverge e a prévia é refeita, como para qualquer outro dado.

**D8. Duplicidade na aba é erro de todas as linhas envolvidas.** Calculada em `lock()`, como `repeated_activities`, a partir das linhas (e não do arquivo), para que a confirmação chegue ao mesmo resultado. E-mail normalizado e nome de usuário sem caixa. Código `duplicate`, na coluna do valor: "O e-mail aparece também nas células X. Deixe só uma linha por usuário." / "O nome de usuário aparece também nas células X. Use um nome de usuário por usuário."

**D9. Erros de usuário bloqueiam a importação inteira.** Qualquer erro de linha deixa a importação `COM_ERROS` (`Import.status_of`), e a confirmação só aplica planos sem erro. Não há confirmação parcial, que deixaria usuários sem o ensalamento ou o contrário.

**D10. Permissão.** Cadastrar exige `USUARIO.CRIAR` de quem gera a prévia e de quem confirma (a confirmação reexecuta com o executor dela; sem a permissão, o plano diverge com erro e a importação fica `COM_ERROS`, como na importação de usuários). Não entra em `check_confirmation`: a regra já está na linha, e a tela mostra o erro na própria linha. Linhas de usuário existente não exigem permissão.

**D11. Alvo e chave criada.** Cadastro: `action='create'`, `changes` de e-mail, nome, perfil (código) e nome de usuário, `created=user.pk` (vem de `UserImport.create`). Existente: `target=user.pk`. Como e-mail repetido é erro (D8), nenhuma linha encontra usuário criado por outra linha da mesma execução, e `RunState.created` não precisa guardar usuários.

**D12. Travas.** Em `lock()`, `select_for_update` dos usuários com os e-mails da aba (como `UserImport.lock`), serializando duas importações que cadastram o mesmo e-mail. Não é preciso `lock_active_users` nem `deferred_administrative_continuity`: cadastrar não altera a continuidade administrativa (só `update`/`change_role` alteram).

---

## 3. Comportamento

### Aba presente

1. Envio: `WorkbookSource.read` confere as abas obrigatórias; `read_cells` acha a aba de usuários (D4), confere o cabeçalho (D5) e entrega uma linha `USUARIO` por linha de dado, antes dos catálogos. `check_identifiers` confere a `Célula` (única por construção).
2. Prévia: `lock` calcula as duplicidades e trava os e-mails; cada linha `USUARIO` planeja `create` (executando `register` de verdade) ou `unchanged`; depois vêm catálogos e atividades; tudo é desfeito. Gravados: `Import` e `ImportRow`. Nenhum `User`, `UserRole`, `OutboxEntry` nem `AuditLog` de usuário sobra.
3. Confirmação: reexecução com o executor atual. Plano idêntico e sem erros: usuários, catálogos e alocações gravados juntos, links no outbox, `ImportRow.created_object` com o pk do usuário. Senão: nada gravado.

### Aba ausente

`read_cells` não encontra a aba e não gera linha `USUARIO`. `lock` não trava usuários (lista vazia), `execute_row` nunca chama o ramo de usuário, e o resultado (linhas, plano, situação, auditoria, mensagem) é idêntico ao de hoje. Sem erro e sem aviso.

### Reimportação

Primeira confirmação: `adailton@ifnmg.edu.br` sem usuário → `create`. Segunda: usuário encontrado pelo e-mail → `unchanged`, sem novo link (o `register` não é chamado). Se o cadastro foi mudado na tela, `unchanged` com aviso `usuario_com_outros_dados`; nada é sobrescrito.

### Falhas

| Situação | Onde aparece | Resultado |
|---|---|---|
| Aba com coluna faltando ou repetida | Envio | `FileRejected`, erro do formulário, nenhuma importação |
| Célula obrigatória vazia | Linha | `required`, `COM_ERROS` |
| E-mail inválido ou fora do domínio | Linha (`clean_values`/`create`) | `invalid`/código do model, `COM_ERROS` |
| Perfil inexistente | Linha | `unknown_role`, `COM_ERROS` |
| E-mail ou nome de usuário repetido na aba | Linha (D8) | `duplicate`, `COM_ERROS` |
| Nome de usuário de outro usuário | Linha (`register` → `clean`) | `username_taken`, `COM_ERROS` |
| Sem `USUARIO.CRIAR` | Linha | `permission_denied`, `COM_ERROS` |
| Banco recusa o cadastro | Linha (`execute_row`) | `database`, `COM_ERROS`, savepoint da linha desfeito |
| Erro inesperado na prévia | `preview` | Transação desfeita, importação não criada |
| Plano diverge na confirmação (usuário ou ensalamento) | `confirm` | Savepoint desfeito: nenhum usuário nem alocação; novo plano, `revalidation_count + 1` |
| Erro inesperado na confirmação, depois dos usuários | `confirm` | Transação inteira desfeita: usuários criados nas primeiras linhas somem; importação continua `VALIDADA` |

---

## 4. Passo a passo

### Passo 1. Aba opcional no motor

**`imports/definitions.py`**: em `ImportDefinition`, `optional_sheets = ()`, com a docstring da classe dizendo que a aba opcional ausente não recusa o arquivo e que a leitura dela é da importação específica.

**`imports/workbook.py`**: `WorkbookSource.help_text` acrescenta, quando houver, "e, se houver, a aba X" (texto sem travessão, conforme a seção 9 das convenções). `read` não muda: a conferência de ausência continua só sobre `definition.sheets`.

### Passo 2. Leitura da aba em `schedule/sheets.py`

Constantes:

```python
USERS_SHEET = 'usuários - sistema'
USER_KIND = 'USUARIO'
USER_EMAIL_COLUMN = 'E-mail'
USER_NAME_COLUMN = 'Nome'
USER_ROLE_COLUMN = 'Perfil'
USER_USERNAME_COLUMN = 'Nome de usuário'
USER_COLUMNS = (USER_EMAIL_COLUMN, USER_NAME_COLUMN, USER_ROLE_COLUMN, USER_USERNAME_COLUMN)
USER_HEADER_ROW = 1
```

Funções (com docstring citando D4 e D5):

- `find_sheet(workbook, title)`: a aba cujo `normalize_header(nome)` é igual ao de `title`, ou `None`.
- `user_entries(workbook)`: `None` da aba → lista vazia. Aba sem célula preenchida → lista vazia. Cabeçalho pela linha 1 com `normalize_header`, erros de coluna faltando ou repetida com `FileRejected` (mensagens do D5, reaproveitando `listing`). Para cada linha seguinte com alguma célula preenchida, um dict `{'values': {rótulo: raw_text(célula)}, 'reference': cell_reference-like 'Aba!A{linha}'}` usando o título real da aba.

Os valores ficam crus (`raw_text`), como os dos catálogos, para que a confirmação normalize igual à prévia.

### Passo 3. Linhas `USUARIO` em `schedule/imports.py`

- Colunas novas em `SpaceAllocationImport.columns`, todas `required=False` (a obrigatoriedade é por tipo de linha, D6): `Column('E-mail', required=False)`, `Column('Perfil', required=False)`, `Column('Nome de usuário', required=False)`. `Nome` já existe.
- `optional_sheets = (USERS_SHEET,)`.
- `row_filters`: `RowFilter('usuarios', 'Usuários', KIND_COLUMN, USER_KIND, (CELL_COLUMN, 'E-mail', NAME_COLUMN, 'Perfil', 'Nome de usuário'))`, primeiro da tupla (mesma ordem das linhas).
- `field_labels` += `'email': 'E-mail'`, `'role': 'Perfil'`, `'username': 'Nome de usuário'`.
- `columns_by_field` += `'email': 'E-mail'`, `'role': 'Perfil'`, `'username': 'Nome de usuário'`.
- `warning_labels` += `USER_WITH_OTHER_DATA` e `INACTIVE_USER` (D7).
- `catalog_row` e `activity_row` passam a trazer as três colunas novas vazias; `user_row(entry)` monta a linha com `KIND_COLUMN: USER_KIND`, `CELL_COLUMN: entry['reference']`, os quatro valores e as demais colunas vazias.
- `read_cells`: primeiro `for entry in user_entries(workbook): yield user_row(entry)`, depois o que já existe.
- `RunState.user_duplicates = {}` (docstring atualizada).
- `lock`: depois do que já faz, `state.user_duplicates = repeated_users(rows)` e a trava do D12 (`User.objects.filter(email__in=...)...select_for_update()`), só com as linhas `USUARIO`. Com lista vazia a consulta não roda (retorno antecipado), para que a planilha sem a aba não faça consulta a mais.
- `repeated_users(rows)`: função de módulo, ao lado de `repeated_activities` (D8).
- `execute_row`: ramo `if row_kind == USER_KIND: return self.execute_user(values, executor)` antes dos demais.
- `execute_user(values, executor)`:

```text
errors = células obrigatórias vazias (E-mail, Nome, Perfil) → RowError(coluna, 'required', f'Preencha a coluna {coluna}.')
se houver: RowPlan(errors=errors)
+ erros de duplicidade de state.user_duplicates → RowPlan(errors=...)
cleaned, errors = USERS.clean_values(values)
user = User.objects.filter(email__iexact=cleaned['email']).first()
sem usuário: return USERS.create(cleaned, errors, executor)
com usuário e errors de formato: RowPlan(target=user.pk, errors=errors)
com usuário: RowPlan(action='unchanged', target=user.pk, warnings=self.user_warnings(user, cleaned))
```

`USERS = UserImport()` como constante do módulo. `user_warnings` compara nome, `normalize_username` e `user.role.code` com o que veio, e `is_active` (D7).

- `concluded_message(summary, importation)`: quando `importation` tem linhas `USUARIO` com `action='create'`, acrescenta "N usuários cadastrados" e a frase de `accounts.imports.concluded_message` "O link para definir a senha será enviado aos usuários cadastrados." (a contagem geral `registros cadastrados` continua a mesma e já inclui esses usuários).
- `audit_metadata`: quando a importação está `CONCLUIDA`, `usuarios_cadastrados` = contagem das linhas `USUARIO` com `action='create'`, ao lado de `space_totals`. Na prévia, nada novo.
- Docstring do módulo: acrescentar a aba opcional, a ordem das linhas e o D2.

### Passo 4. Docstring de `Teacher`

**`schedule/models.py`**: trocar "a importação não cria nem consulta usuário (D7)" por: a importação cria usuário só a partir da aba opcional de usuários, e o docente continua sem vínculo com `User`; a correspondência é por `teacher_of`. Nenhuma mudança de campo, sem migration.

### Passo 5. Documentação do motor

**`imports/README.md`**: na seção "Prévia: executar e desfazer", uma nota de que uma importação específica pode ordenar as linhas em fases (o ensalamento executa usuários, catálogos e atividades nessa ordem) sem estado novo, e em "O que não existe nesta versão" manter `PROCESSANDO`/`FALHOU`. Citar a aba opcional na descrição da fonte em grade.

### Passo 6. Specs

Deltas desta Change aplicados no arquivamento: `ensalamento` (requisito "Importação do ensalamento por planilha" modificado e requisito "Usuários do sistema na planilha do ensalamento" novo) e `importacao-planilhas` ("Leitura de planilha em grade" com aba opcional). Nenhuma spec nova.

---

## 5. Testes

Todos com `make test`, no PostgreSQL. O executor dos testes com a aba precisa de `USUARIO.CRIAR` além do que `space_manager()` já dá: acrescentar um parâmetro `extra_permissions` a `space_manager` ou um `user_manager()` ao lado dele. Usuários de teste não superadmin (seção 7 das convenções).

**Auxiliar.** `workbook_file(..., users=None, users_title=USERS_SHEET, users_header=USER_COLUMNS)` em `schedule/tests/test_import.py`: `users=None` não cria a aba (mantém todos os testes atuais como regressão); uma lista de tuplas cria a aba com o cabeçalho informado.

### `schedule/tests/test_spreadsheet.py` (leitura, `SimpleTestCase`)

- Aba ausente: `user_entries` devolve lista vazia; `read_cells` não tem linha `USUARIO`.
- Aba presente: uma entrada por linha de dado, com a referência `usuários - sistema!A2`, valores crus, linhas vazias ignoradas.
- Nome da aba com outra caixa e sem acento (`Usuarios - Sistema`) é reconhecido.
- Cabeçalho com outra caixa e sem acento (`e-mail`, `nome de usuario`) é reconhecido; coluna a mais ignorada.
- Coluna faltando (`Perfil`) e coluna repetida: `FileRejected` com a aba e a coluna no texto.
- Aba vazia e aba só com cabeçalho: nenhuma entrada, sem erro.
- Linhas de usuário vêm antes das de catálogo em `read_cells`.

### `schedule/tests/test_import.py`, classe nova `UserSheetTests(ImportTestCase)`

Aba presente:
- `test_user_rows_are_recognized`: linhas do tipo `USUARIO`, primeiras na numeração, filtro "Usuários" disponível.
- `test_valid_users_are_planned`: `create` com `changes` de e-mail, nome, perfil e nome de usuário; importação `VALIDADA`.
- `test_confirmation_creates_missing_users`: usuário ativo, perfil `DOCENTE`, `username` gravado, `has_usable_password()` falso, `OutboxEntry` `LINK_SENHA` para ele, `created_object` preenchido.
- `test_role_is_applied`: com um perfil personalizado e outro `DOCENTE`, cada usuário com o seu; código em minúsculas aceito.
- `test_multiple_users_are_processed`: três usuários, três cadastros, três links.
- `test_created_user_matches_teacher`: depois da confirmação, `teacher_of(usuario)` é o `Teacher` de mesmo nome, sem FK nova.
- `test_existing_user_is_not_duplicated`: usuário pré-cadastrado → `unchanged` com `target`, um único usuário com o e-mail, nenhum link novo.
- `test_existing_user_with_other_data_is_not_updated`: nome e perfil diferentes → aviso, cadastro intacto.
- `test_inactive_user_is_not_reactivated`: aviso, continua inativo.

Aba ausente:
- `test_spreadsheet_without_users_sheet_is_valid`: `VALIDADA`, nenhuma linha `USUARIO`.
- `test_users_step_is_skipped`: `patch.object(UserImport, 'create')` e `patch.object(UserImport, 'clean_values')` não chamados; `User.objects.count()` igual antes e depois da confirmação.
- `test_schedule_is_imported_normally`: mesmas alocações, docentes e espaços que hoje.

Erros:
- `test_invalid_email`, `test_email_outside_institutional_domain`.
- `test_unknown_role`: `unknown_role` na coluna `Perfil`, nenhum `Role` novo.
- `test_duplicate_email_in_sheet` (caixas diferentes) e `test_duplicate_username_in_sheet`: todas as linhas envolvidas com `duplicate`.
- `test_missing_required_cells`: `E-mail`, `Nome` e `Perfil` vazios, cada um com `required`; `Nome de usuário` vazio aceito.
- `test_username_taken_by_other_user`: `username_taken`.
- `test_without_user_create_permission`: `permission_denied`, `COM_ERROS`.
- `test_database_error_during_user_creation`: `register` com `side_effect=DatabaseError` → erro `database` na linha, importação `COM_ERROS`, nada gravado.
- `test_user_error_blocks_whole_import`: um usuário inválido e ensalamento válido → `COM_ERROS`, nenhuma alocação, nenhum usuário.

Prévia e confirmação:
- `test_preview_does_not_persist_users`: depois da prévia e de `refresh`, nenhum `User`, `UserRole`, `OutboxEntry` nem `AuditLog` de usuário.
- `test_confirmation_persists_users`: coberto acima, com a auditoria `CREATE`/`USER` com origem de importação.
- `test_divergence_rolls_back_users`: entre prévia e confirmação, cadastrar pela tela o mesmo e-mail → plano diverge (`create` → `unchanged`), nenhum usuário novo, `revalidation_count` 1.
- `test_unexpected_error_after_users_rolls_back_everything`: `Allocation.objects.apply` com `side_effect=RuntimeError` só na confirmação → exceção, importação `VALIDADA`, nenhum usuário, nenhum link, nenhuma alocação.
- `test_confirmer_without_permission`: prévia por quem tem `USUARIO.CRIAR`, confirmação por quem não tem → não conclui, `COM_ERROS`, nada gravado.

Reimportação:
- `test_second_import_does_not_duplicate`: duas confirmações da mesma planilha → um usuário por e-mail, a segunda com `unchanged`, links só da primeira.
- `test_reimport_does_not_update_changed_user`: entre as duas, o nome muda na tela → segunda com aviso, nome da tela preservado.

Regressão:
- Toda a suíte atual de `schedule/tests/test_import.py` e `test_spreadsheet.py` roda sem a aba e sem alteração de expectativa.
- `RealSpreadsheetTests` com `planilha_example.xlsx` (sem a aba) mantém 1706 linhas e 121 erros.
- Teste com `planilha_example_sugerida.xlsx`, quando o arquivo com a aba estiver no repositório: a aba é lida e as 129 linhas planejam `create` para um banco vazio.
- `accounts/tests/test_user_import.py` intacto (a `UserImport` não muda).
- Mensagem de conclusão sem usuários igual à de hoje; com usuários, com a frase do link. Textos novos passam em `ui` (teste de texto da interface).

---

## 6. Arquivos

| Arquivo | Mudança |
|---|---|
| `imports/definitions.py` | `optional_sheets` |
| `imports/workbook.py` | Texto de ajuda com a aba opcional |
| `imports/README.md` | Fase de usuários e aba opcional |
| `schedule/sheets.py` | Constantes da aba, `find_sheet`, `user_entries` |
| `schedule/imports.py` | Colunas, filtro, rótulos, avisos, `user_row`, `read_cells`, `lock`, `repeated_users`, `execute_user`, mensagem e auditoria |
| `schedule/models.py` | Docstring de `Teacher` |
| `schedule/tests/test_spreadsheet.py` | Leitura da aba |
| `schedule/tests/test_import.py` | Auxiliar e `UserSheetTests` |

Sem mudança: `accounts/models.py`, `accounts/imports.py`, `imports/models.py`, `imports/execution.py`, `imports/reader.py`, migrations, permissões.

## 7. Riscos e pontos em aberto

- **Planilha com a aba ainda não está no repositório.** Conferir nome da aba, linha do cabeçalho e rótulos antes do Passo 2.
- **Escalonamento de perfil.** Como na importação de usuários, quem tem `USUARIO.CRIAR` pode cadastrar com qualquer perfil existente, inclusive `ADMINISTRADOR`. A spec `gestao-usuarios` deixa esse ponto pendente; esta Change não o resolve.
- **Colunas a mais na prévia "Todas as linhas".** As três colunas novas aparecem vazias nas linhas de catálogo e de atividade; os filtros por tipo mostram só as colunas de cada tipo.
