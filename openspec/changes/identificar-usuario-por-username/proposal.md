## Why

A planilha de ensalamento do campus identifica quem leciona por um nome curto, e não por e-mail. A aba `Validação de Dados` da planilha de referência (`sources/planilha_example.xlsx`) traz a lista canônica desses nomes, com 124 valores, usada pelos dropdowns das abas `Horário - Professor`, `Horário - Professor - 1` e `Horário - Professor - Separado`. Os valores são `Aldo Gomes`, `Adailton`, `Érica`, `Gera Jr.`, `Élcio José`: nome completo, primeiro nome, abreviação com ponto e acento, conforme o caso.

O `User` de hoje não tem como ser encontrado por esse valor. O `email` é o identificador de login e não aparece na planilha. O `name` é o nome civil exibido na interface, não é único e não corresponde ao que a planilha traz: quem está na planilha como `Érica` tem `name` completo no sistema. Sem um identificador próprio, a futura importação de ensalamento não teria como ligar uma linha da planilha a um usuário já cadastrado.

Esta Change acrescenta ao `User` o campo `username`, um identificador textual único de domínio, informado e alterado pelo administrador nas telas de usuários que já existem. Ela não implementa a importação de ensalamento, nem o conceito de docente, nem qualquer vínculo entre os dois: entrega só a entidade `User` preparada para que a Change futura encontre um usuário existente pelo valor da planilha.

## What Changes

- **Campo `username` no `User`**, texto livre, opcional, único no sistema sem diferenciar maiúsculas de minúsculas. Aceita espaços, acentos, pontos e abreviações, e é gravado exatamente como informado.
- **Identificador de domínio, não de login.** O `USERNAME_FIELD` continua `email` e nenhuma tela de autenticação muda. O nome do campo coincide com o do atributo tradicional do Django, mas o papel não é o mesmo, e a spec `autenticacao` passa a dizer isso de forma explícita.
- **Unicidade em duas camadas**, como o e-mail já faz: verificação no `clean()` do model, com o erro ancorado no campo, e `UniqueConstraint` sobre `Lower('username')` no banco.
- **Cadastro e edição de usuário** passam a aceitar o campo, opcional nos dois. Deixá-lo vazio é válido, e mais de um usuário pode estar sem valor.
- **Lista de usuários**: o valor aparece na tabela e a busca por `busca=` passa a procurar também nele, junto com o nome e o e-mail.
- **Importação de usuários por planilha** ganha a coluna `Nome de usuário`, obrigatória no cabeçalho como todas as demais, com a célula podendo vir vazia.
- **Migration** que acrescenta o campo como nulo e a restrição de unicidade, sem preencher nada nos usuários existentes.

### Fora do escopo

- A importação da planilha de ensalamento: leitura do XLSX, aba `Validação de Dados`, disciplinas, turmas, horários, salas, semestre, calendário e reservas.
- O conceito de docente como entidade, o model correspondente e qualquer vínculo entre ele e o `User`.
- Criação automática de usuários ou de docentes a partir de qualquer planilha.
- Correspondência aproximada, por similaridade, por prefixo ou ignorando acentos.
- Preencher o `username` dos usuários já cadastrados. Isso é feito pelo administrador, pela tela, depois que a Change estiver no ar.
- Qualquer mudança no login, na recuperação de senha ou na regra do usuário inativo.

## Capabilities

### Modified Capabilities

- `gestao-usuarios`: o `username` entra como dado do usuário, com regra própria de unicidade e normalização, e passa a fazer parte do cadastro, da edição, da busca da lista e da importação de usuários.
- `autenticacao`: o requisito do e-mail como identificador de login passa a distinguir o identificador de autenticação do identificador de domínio, em vez de afirmar que o sistema não tem campo de username.

## Impact

- **`accounts/models.py`**: o campo, a `UniqueConstraint`, a verificação de unicidade no `clean()`, a normalização, `UserManager.register`, `User.update_details`, `UserQuerySet.search` e os valores registrados na auditoria.
- **`accounts/forms.py`**: o campo em `UserCreateForm` e em `UserUpdateForm`.
- **`accounts/imports.py`**: a coluna nova, o mapa de campos, a limpeza dos valores e as ações `create` e `update`.
- **`accounts/migrations/`**: uma migration de esquema, sem migration de dados.
- **Templates**: `accounts/partials/user_table.html` e o modal de formulário de usuário.
- **Testes**: `accounts/tests/test_models.py` (o conjunto de campos do `User` e a lista de atributos que o `User` não tem), `test_user_views.py`, `test_user_search.py`, `test_user_import.py`, `test_user_import_views.py`, `test_modals.py`, `test_form_initial.py` e `test_screens.py`.
- **Sem impacto**: `audit`, `notices`, `outbox`, `ui`, `imports` (o motor genérico não muda), `config/settings.py` e o catálogo de permissões.

## Alinhamento com o TCC

- **RNF06 e P2:** a unicidade e a normalização do `username` são regra do model, e as telas e a importação apenas acionam as mesmas operações.
- **P4:** o valor é informado e corrigido num único lugar, a gestão de usuários, e não numa tela própria criada para a importação.
- **RNF01:** o campo entra nas telas já protegidas por `USUARIO.CRIAR` e `USUARIO.EDITAR`, sem permissão nova.
