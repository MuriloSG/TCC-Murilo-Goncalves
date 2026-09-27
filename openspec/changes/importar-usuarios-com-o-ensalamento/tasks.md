## 1. Preparação

- [x] 1.1 Obter a planilha com a aba `usuários - sistema` e conferir nome da aba, linha do cabeçalho e rótulos contra o `plan.md` (seção 1.1)

## 2. Motor

- [x] 2.1 Criar `ImportDefinition.optional_sheets` e citar a aba opcional no texto de ajuda do `WorkbookSource`
- [x] 2.2 Atualizar `imports/README.md` com a fase de usuários e a aba opcional

## 3. Leitura da aba

- [x] 3.1 Criar em `schedule/sheets.py` as constantes da aba, `find_sheet` e `user_entries`, com a conferência do cabeçalho
- [x] 3.2 Testes de leitura em `schedule/tests/test_spreadsheet.py`

## 4. Execução

- [x] 4.1 Acrescentar colunas, filtro, rótulos e avisos de usuário a `SpaceAllocationImport`, e as linhas `USUARIO` em `read_cells`
- [x] 4.2 Duplicidades e trava dos usuários em `lock`, e `execute_user` reaproveitando `UserImport.clean_values` e `UserImport.create`
- [x] 4.3 Mensagem de conclusão e auditoria com os usuários cadastrados; docstring de `Teacher`
- [x] 4.4 `UserSheetTests` e o auxiliar `workbook_file(users=...)` em `schedule/tests/test_import.py`, com a suíte inteira passando
