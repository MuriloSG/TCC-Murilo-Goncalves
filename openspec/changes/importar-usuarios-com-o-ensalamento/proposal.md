## Why

A planilha de ensalamento simplificada pode trazer uma aba a mais, `usuários - sistema`, com as contas que precisam existir no sistema (e-mail, nome, perfil e nome de usuário). Hoje essas contas são cadastradas numa importação separada, a de usuários, a partir de um CSV montado à mão (`sources/importacao-usuarios-ensalamento.csv`) com as mesmas quatro colunas. Aproveitar a própria importação do ensalamento para cadastrar os usuários que ainda não existem elimina esse segundo arquivo e deixa as contas prontas para a correspondência com os docentes (`teacher_of`) assim que o semestre é carregado.

A aba é opcional: a planilha sem ela continua sendo importada exatamente como hoje.

## What Changes

- A importação do ensalamento passa a reconhecer a aba opcional `usuários - sistema`. Presente, cada linha de dado dela vira uma linha da importação do tipo `USUARIO`, lida antes dos catálogos e das atividades. Ausente, nenhuma linha de usuário existe e a execução passa direto ao ensalamento, sem erro nem aviso.
- A linha de usuário cadastra o usuário que ainda não existe pelas mesmas operações da importação de usuários (`UserImport.clean_values` e `UserImport.create`, que chamam `User.objects.register`): sem senha utilizável, com o link de definição de senha no outbox. O usuário já existente, reconhecido pelo e-mail, não é alterado.
- Os erros da aba (dado obrigatório ausente, e-mail inválido ou fora do domínio, perfil inexistente, e-mail ou nome de usuário repetido na aba, nome de usuário de outro usuário, falta de `USUARIO.CRIAR`) são erros de linha e deixam a importação `COM_ERROS`, como qualquer outro erro do ensalamento.
- Prévia, atualização da prévia e confirmação continuam como estão: tudo roda na mesma transação e no mesmo savepoint; a prévia desfaz os usuários, e a confirmação só os grava junto com o ensalamento.
- O motor ganha a noção de aba opcional declarada (`optional_sheets`), que não recusa o arquivo quando falta.
- Nenhum estado novo em `Import.Status` e nenhuma migration.

### Fora do escopo

- Atualizar nome, nome de usuário, perfil ou situação de usuário existente pela planilha do ensalamento. Isso continua com a tela de usuários e com a importação de usuários.
- Vínculo gravado entre `User` e `Teacher`: a correspondência continua por `teacher_of`, pelo `username`.
- Conferir se o nome de usuário corresponde a um docente da lista.
- Estados assíncronos (`PROCESSANDO`, `FALHOU`) no motor.

## Capabilities

### Modified Capabilities

- `ensalamento`: a importação do ensalamento deixa de ser proibida de criar usuário e passa a cadastrar, a partir da aba opcional `usuários - sistema`, os usuários que ainda não existem.
- `importacao-planilhas`: a leitura de planilha em grade aceita aba declarada como opcional, que não recusa o arquivo quando falta.

## Impact

- `schedule/sheets.py`, `schedule/imports.py` e a docstring de `Teacher` em `schedule/models.py`.
- `imports/definitions.py` e `imports/workbook.py` (aba opcional e texto de ajuda).
- `imports/README.md` (fase de usuários dentro da execução).
- Testes em `schedule/tests/test_spreadsheet.py` e `schedule/tests/test_import.py`.
- Sem migration, sem permissão nova, sem dependência nova.
