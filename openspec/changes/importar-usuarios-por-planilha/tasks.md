## 1. Pré-requisitos

- [x] 1.1 Confirmar que a Change `enviar-emails-por-outbox` foi implementada e que `User.objects.register` registra o envio `LINK_SENHA` no outbox (D12)
- [x] 1.2 Pedir ao autor as imagens de referência das telas de envio, prévia, histórico e detalhe, e registrar em D17 o que foi adaptado e o que foi retirado

## 2. Permissão e continuidade em `accounts`

- [x] 2.1 Acrescentar `USER_IMPORT` em `accounts/permissions.py` e em `ALL_PERMISSIONS`, fora de `ADMINISTRATIVE_CAPABILITY` e de `SUPERADMIN_RESERVED_PERMISSIONS` (D15)
- [x] 2.2 Criar a migration de dados `0003` que cria `USUARIO.IMPORTAR` e a concede ao `ADMINISTRADOR`, idempotente e com códigos literais (D15)
- [x] 2.3 Atualizar `accounts/tests/test_catalog.py` para onze permissões e testar que a migration preserva as concessões alteradas pelo superadmin
- [x] 2.4 Implementar `deferred_administrative_continuity()` com `ContextVar` e fazer `administrative_continuity()` pular a verificação enquanto a marca estiver ativa (D11)
- [x] 2.5 Testar que, fora do gerenciador adiado, as telas e os comandos continuam recusando a perda da continuidade, e que a marca é removida mesmo com exceção
- [x] 2.6 Commit

## 3. Motor: leitura

- [ ] 3.1 Criar o app `imports`, registrá-lo em `INSTALLED_APPS` e acrescentar `IMPORT_MAX_FILE_SIZE` e `IMPORT_MAX_ROWS` ao `settings.py`, lidos de variáveis de ambiente (D2, D5)
- [ ] 3.2 Criar `ImportDefinition`, `Column`, `RowPlan`, `RowError` e `errors_from_validation` em `imports/definitions.py` (D4)
- [ ] 3.3 Implementar `read_csv` com tamanho, UTF-8 com BOM, separador `;`, conferência do cabeçalho, mensagem do separador vírgula, numeração pela linha inicial, linhas vazias, limite de linhas e arquivo sem dados (D5)
- [ ] 3.4 Implementar no motor as verificações de linha: células a mais, células a menos, célula obrigatória vazia ou só com espaços e identificador repetido citando as linhas
- [ ] 3.5 Escrever os testes de leitura com os cenários da spec `importacao-planilhas`, incluindo aspas com `;` e quebra de linha
- [ ] 3.6 Commit

## 4. Motor: model, prévia e confirmação

- [ ] 4.1 Criar os models `Import` e `ImportRow` e a migration `0001_initial` (D6)
- [ ] 4.2 Implementar a execução com savepoint do domínio, savepoint por linha, `lock` e `check_file` (D7)
- [ ] 4.3 Implementar a normalização e a comparação do plano (D8)
- [ ] 4.4 Implementar `Import.objects.preview`, `Import.confirm` e `Import.discard` com as transições, a trava da importação, a divergência e o contador (D7, D9, D10)
- [ ] 4.5 Escrever os testes do motor com uma definição de teste: prévia sem alterar dados, todos os erros de uma vez, erro de banco numa linha, erro do arquivo, plano idêntico, divergência sem e com erros, falha no meio da confirmação, erro inesperado na prévia e na confirmação, situações finais, `created_object` só na conclusão e plano determinístico
- [ ] 4.6 Testar confirmações simultâneas com `TransactionTestCase` e `serialized_rollback = True`
- [ ] 4.7 Testar que nenhum módulo de `imports` importa `accounts`
- [ ] 4.8 Commit

## 5. Importação de usuários

- [ ] 5.1 Criar `UserImport` em `accounts/imports.py` com colunas, identificador, `lock`, rótulos e o mapa de campos para colunas (D4, D14)
- [ ] 5.2 Implementar `execute_row` com normalização, resolução do perfil, `create`, `update`, `unchanged`, aviso de inativo, com o envio do link registrado pelo próprio `register` (D12, D14)
- [ ] 5.3 Implementar as verificações de permissão por ação com `executor.has_perm` (D13)
- [ ] 5.4 Implementar `check_file` com a continuidade administrativa adiada (D11)
- [ ] 5.5 Escrever os testes com os cenários da spec `gestao-usuarios`: cadastro, troca de perfil, sem alteração, perfil inexistente, e-mail inválido, inativo, superadmin, permissões por ação, confirmação por quem tem menos permissões, rebaixar e promover, sem administrador, outbox só para cadastrados e nenhum registro na prévia ou na divergência
- [ ] 5.6 Escrever os testes de equivalência com as telas: cada recusa do cadastro, da edição e da troca de perfil tem uma linha equivalente com a mesma mensagem
- [ ] 5.7 Commit

## 6. Views, rotas e telas

- [ ] 6.1 Criar as views base em `imports/views.py` sobre a `ModalView`: lista, envio, modelo, detalhe, confirmação por POST e descarte em modal (D16, D18)
- [ ] 6.2 Criar as views e as rotas de `usuarios/importacoes/` em `accounts`, com `login_required` e `permission_required = permissions.USER_IMPORT` (D16)
- [ ] 6.3 Criar os templates de envio, prévia e detalhe, histórico e descarte a partir das referências, com os componentes e tokens de `ui` e os textos de D17
- [ ] 6.4 Acrescentar à lista de usuários o botão "Importar usuários" e o link do histórico, visíveis só com `perms.USUARIO.IMPORTAR`
- [ ] 6.5 Testar cada rota nas quatro situações da convenção §7 e o 404 de uma importação de outro tipo
- [ ] 6.6 Testar a prévia com erros sem o controle de confirmar, a mensagem de divergência, o descarte e o conteúdo do modelo baixado
- [ ] 6.7 Rodar `make test` com a suíte inteira passando, incluindo os testes de texto e de classes da interface
- [ ] 6.8 Commit

## 7. Verificação

- [ ] 7.1 Medir prévia e confirmação com arquivos de 100, 500, 1.000 e 2.000 linhas no banco `visual_check`, ajustar os limites e registrar os valores em D5
- [ ] 7.2 Abrir no Excel o modelo baixado e um CSV salvo como "CSV UTF-8" e como "CSV (separado por vírgulas)", e conferir as mensagens de cada caso
- [ ] 7.3 Conferir as telas no navegador com Playwright, no banco `visual_check`, em 360 e 1280 px
- [ ] 7.4 Validar a Change com `openspec validate importar-usuarios-por-planilha --strict`
