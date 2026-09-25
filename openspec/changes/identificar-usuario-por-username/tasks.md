## 1. Campo e unicidade no model

- [x] 1.1 Acrescentar o campo `username` ao `User`, como `CharField(max_length=150, unique=True, null=True, blank=True)`, com `verbose_name` "nome de usuário" e docstring dizendo que é identificador de domínio, e não credencial de login (D1, D2)
- [x] 1.2 Acrescentar ao `Meta.constraints` a `UniqueConstraint(Lower('username'), name='user_username_unique_ci')`, com `violation_error_message` própria (D4)
- [x] 1.3 Estender o `User.clean()` para aparar as bordas, reduzir espaços internos repetidos a um, converter vazio em `None` e recusar duplicata por `username__iexact` excluindo o próprio `pk`, com `ValidationError` ancorada no campo (D3, D4)
- [x] 1.4 Criar a migration de esquema com `AddField` nulo e `AddConstraint`, sem migration de dados (D7)
- [x] 1.5 Testar a gravação preservando caixa e acentos (`Érica`, `Gera Jr.`, `Élcio José`), o aparo das bordas, o vazio virando `NULL`, mais de um usuário sem valor, a recusa de duplicata exata e de duplicata que difere só na caixa com erro no campo, a recusa pelo banco numa gravação direta e o valor de um usuário inativo continuando indisponível
- [x] 1.6 Commit

## 2. Operações, autenticação e auditoria

- [x] 2.1 Aceitar o `username` em `UserManager.register`, opcional, gravado na mesma transação do cadastro (D6)
- [x] 2.2 Aceitar o `username` em `User.update_details`, sem alterar a proteção do e-mail de superadmin e mantendo o `update_fields` coerente com os campos alterados
- [x] 2.3 Incluir o `username` nos valores registrados na auditoria do cadastro e na comparação de `record_changes` da edição
- [x] 2.4 Acrescentar `username` à `UserQuerySet.search`, junto com o nome e o e-mail, sem diferenciar maiúsculas
- [x] 2.5 Ajustar `test_models.py`: o conjunto esperado de campos concretos do `User` e a lista de atributos ausentes do `AbstractUser`, da qual `username` sai (D2)
- [x] 2.6 Testar que `USERNAME_FIELD` continua `email`, que `ACCOUNT_USER_MODEL_USERNAME_FIELD` continua `None`, que o formulário de login segue com `login`, `password` e `remember`, e que o login por `username` não autentica (D2)
- [x] 2.7 Testar a busca por trecho do `username` e a busca combinada com o filtro de situação
- [x] 2.8 Commit

## 3. Telas de cadastro, edição e lista

- [x] 3.1 Acrescentar o campo, opcional, ao `UserCreateForm` e ao `UserUpdateForm`, com o rótulo "Nome de usuário" e o valor atual no `initial` da edição
- [x] 3.2 Exibir o valor na tabela de usuários, sem quebrar o bloco de nome e e-mail nem a versão compacta da linha
- [x] 3.3 Testar o cadastro com e sem o valor, a edição gravando, alterando e limpando o valor, a duplicata recusada com erro sob o campo no cadastro e na edição, e o conjunto de campos de cada formulário
- [x] 3.4 Conferir as telas no navegador pelo banco `visual_check`, conforme as convenções, e registrar o que foi ajustado
- [x] 3.5 Commit

## 4. Importação de usuários

- [x] 4.0 Acrescentar `required` ao `Column` do motor e deixar o leitor de exigir a célula preenchida numa coluna opcional, mantendo a exigência no cabeçalho (D8)
- [x] 4.1 Acrescentar a coluna `Nome de usuário` ao `UserImport`, no `columns` e no `columns_by_field`, e ao `field_labels` (D8)
- [x] 4.2 Limpar o valor da coluna pelo mesmo campo de formulário usado pela tela, aplicando a mesma normalização do model
- [x] 4.3 Tratar a célula vazia como ausência de informação: sem valor no `create`, valor atual mantido no `update` (D8)
- [x] 4.4 Incluir a mudança de `username` no plano da linha, exigindo a permissão `USUARIO.EDITAR`, como o nome já faz
- [x] 4.5 Atualizar o CSV modelo para download, com a coluna nova
- [x] 4.6 Testar o cabeçalho antigo sendo recusado, o cadastro com e sem o valor, a atualização do valor, a célula vazia não apagando o valor atual, a duplicata dentro do mesmo arquivo e contra um usuário existente recebendo erro na coluna, e a mensagem igual à da tela
- [x] 4.7 Commit

## 5. Specs e fechamento

- [x] 5.1 Conferir que os deltas de `gestao-usuarios` e `autenticacao` descrevem o que foi implementado, ajustando o que divergir
- [x] 5.2 Rodar a suíte inteira com `make test` e corrigir o que quebrar
- [x] 5.3 Registrar em `openspec/conventions.md` qualquer preferência nova surgida na implementação
- [x] 5.4 Commit
