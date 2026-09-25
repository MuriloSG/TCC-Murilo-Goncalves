## Context

O `User` atual (`accounts/models.py`) deriva de `AbstractBaseUser`, sem `PermissionsMixin`, e tem `email`, `name`, `is_active`, `is_superadmin`, `created_at` e os perfis por `UserRole`. O `USERNAME_FIELD` é `email`, o `REQUIRED_FIELDS` é `['name']` e o `config/settings.py` fixa `ACCOUNT_USER_MODEL_USERNAME_FIELD = None`, o que faz o allauth ignorar qualquer campo com esse nome no model.

A fonte do requisito é a aba `Validação de Dados` de `sources/planilha_example.xlsx`. A coluna `A`, sob o cabeçalho `Disciplina (Professor)`, tem 124 nomes e alimenta, por validação de dados, os dropdowns de três abas de horário. Os nomes que aparecem embutidos nas células do grid, como `Química\n (Juliana Diniz) (Mini 1)`, saem dessa mesma lista. O vocabulário é fechado e consistente, o que torna a correspondência exata viável.

Duas características da lista real governam as decisões abaixo:

| Característica | Exemplos na lista | Consequência |
|---|---|---|
| Não é o nome civil | `Adailton`, `Érica`, `Gera Jr.` ao lado de `Aldo Gomes` | o valor é diferente de `User.name` (D1) |
| Acentuação presente | `Élcio José`, `Sérgio`, `Thaís`, `Valéria`, `Vinícius`, `Zélia` | acentos preservados, sem `unaccent` (D5) |
| Prefixos compartilhados | `Gera Jr.` / `Gera Magela`, `Thaís Larissa` / `Thaís Rios`, `Vinícius` / `Vinícius Figueiredo` | correspondência aproximada é proibida (D5) |
| Repetição na fonte | `Ataliba` nas linhas 16 e 17 | a lista da planilha não é catálogo confiável; nada é criado a partir dela (D9) |

As peças reaproveitadas já existem:

| Peça | Onde | Uso aqui |
|---|---|---|
| Unicidade em duas camadas | `email`, com `unique=True` e `UniqueConstraint(Lower(...))` | modelo da unicidade do `username` (D4) |
| Normalização no `clean()` | `User.clean()` | ponto onde o valor é aparado (D3) |
| Recusa virando erro de formulário | `OperationFormView.form_valid` e `accounts.utils.add_operation_error` | mensagem do campo duplicado (D4) |
| Operações do model | `UserManager.register`, `User.update_details` | gravação do valor no cadastro e na edição (D6) |
| Motor de importação | `imports/`, com `ImportDefinition` | coluna nova na importação de usuários (D8) |

## Goals / Non-Goals

**Goals:**

- Um identificador textual único no `User`, informado pelo administrador, capaz de guardar exatamente o que a planilha traz.
- Correspondência futura determinística: um valor da planilha encontra no máximo um usuário, ou nenhum.
- A menor alteração possível no que já existe, sem entidade nova, sem app novo e sem permissão nova.

**Non-Goals:**

- Trocar o identificador de autenticação.
- Modelar docente, disciplina, sala ou qualquer coisa de ensalamento.
- Preencher o campo automaticamente, na migration ou em qualquer importação.
- Adivinhar a qual usuário um nome da planilha se refere quando não houver correspondência exata.

## Decisions

### D1. O campo é um identificador de domínio, distinto de `name`

`name` é o nome civil: aparece na tabela de usuários, gera as iniciais do avatar e é o que a instituição registra. `username` é como a pessoa é identificada na planilha de ensalamento. A lista real mostra que os dois divergem na maioria dos casos: quem está como `Érica` na planilha tem nome completo no sistema.

Por isso os dois campos coexistem e **nenhum deriva do outro**. Em particular, nada copia `name` para `username`, nem na migration (D7) nem no formulário.

### D2. O nome do campo é `username`, por decisão do autor

Esta Change registra a decisão e o seu custo, porque ela contraria dois pontos do projeto:

- a spec `autenticacao` afirmava "O usuário DEVE se autenticar pelo e-mail, sem campo de username";
- o teste `accounts/tests/test_models.py::UserModelTests::test_no_default_django_user_attributes` afirmava que o `User` não tem o atributo `username`, junto com `first_name`, `is_staff` e os demais do `AbstractUser`.

Foram consideradas alternativas de nome ligadas ao papel do campo, como `identifier` ou um nome referente ao ensalamento. O autor optou por `username`, e a Change segue essa decisão: o texto da spec `autenticacao` é reescrito para distinguir identificador de autenticação de identificador de domínio, e o teste passa a afirmar a ausência dos demais atributos do `AbstractUser`, mantendo `username` fora da lista.

A coincidência de nome é segura porque `USERNAME_FIELD` continua `'email'` — o Django usa o valor dessa constante, e não o nome do atributo — e porque `ACCOUNT_USER_MODEL_USERNAME_FIELD = None` já está fixado, o que impede o allauth de tocar no campo. A tarefa 2.6 verifica as duas coisas por teste, para que uma alteração futura no `settings.py` não transforme o campo em credencial por acidente.

O rótulo na interface é **Nome de usuário**, em português, conforme a seção 2 das convenções. Rótulos com a palavra "professor" estão fora de questão: o glossário do `ui/text_rules.py` recusa esse termo e indica "docente".

### D3. Gravado como informado, comparado sem diferenciar maiúsculas

O valor é gravado preservando a caixa e os acentos, porque `Érica` e `Gera Jr.` precisam voltar da planilha idênticos ao que está no banco. A normalização no `clean()` se limita a aparar os espaços das bordas e a reduzir espaços internos repetidos a um só, defesa contra erro de digitação que não altera o valor que o administrador vê.

Isso inverte o tratamento do e-mail, que é gravado em minúsculas. A diferença é deliberada e tem consequência direta em D4.

Valor em branco é gravado como `NULL`, nunca como string vazia: duas strings vazias violariam a unicidade, enquanto vários `NULL` convivem no PostgreSQL. A conversão de `''` para `None` acontece no `clean()`, um único ponto, valendo para as telas e para a importação.

### D4. Unicidade verificada no `clean()` e garantida pelo banco

O e-mail consegue ancorar o erro de duplicidade no próprio campo porque o `clean()` o normaliza para minúsculas **antes** de o `validate_unique` rodar, de modo que o `unique=True` do campo já encontra o conflito. É o que sustenta `assertIn('email', response.context['form'].errors)` em `test_user_views.py`.

No `username` isso não se repete, justamente por causa de D3: sem baixar a caixa, o `validate_unique` faz busca exata e deixa passar `érica` contra `Érica`. Só a restrição de banco pegaria. E foi verificado no `django/db/models/constraints.py` do ambiente (Django 5.2) que `UniqueConstraint.validate`, quando a restrição usa `expressions` e tem `violation_error_message` próprio, levanta um `ValidationError` **sem chave de campo**, que o `Model.validate_constraints` recolhe em `NON_FIELD_ERRORS`. A mensagem apareceria no topo do formulário, e não sob o campo, diferente de todo o resto das telas.

A solução fica no padrão do projeto, sem arquitetura nova: o `User.clean()` — que já existe e já normaliza o e-mail — passa a consultar `username__iexact`, excluindo o próprio `pk`, e a levantar `ValidationError({'username': ...})`. A `UniqueConstraint(Lower('username'))` permanece como garantia do banco contra gravações que não passam pelo formulário, exatamente a divisão que o e-mail já tem.

A mensagem é `Este nome de usuário já pertence a outro usuário. Use outro nome de usuário.`, no mesmo molde da mensagem de e-mail duplicado que o `ui/tests/test_text_rules.py` usa como exemplo de texto permitido.

### D5. Correspondência exata, ignorando só a caixa

A correspondência futura é `username__iexact` do valor da planilha, aparado. Nada além disso.

Ignorar acentos exigiria a extensão `unaccent` no PostgreSQL e um índice funcional sobre `unaccent(lower(...))`, que não é imutável sem um wrapper próprio. Para os sete nomes acentuados da lista, o custo não se justifica, e a divergência é resolvida pelo administrador na tela.

Correspondência aproximada fica proibida pelos pares da lista real: `Gera Jr.` e `Gera Magela` compartilham prefixo, assim como `Thaís Larissa` e `Thaís Rios`, e `Vinícius` é prefixo de `Vinícius Figueiredo`. Qualquer heurística de similaridade erraria nesses casos, e errar aqui significa atribuir uma aula a outra pessoa.

### D6. Opcional, e sem preenchimento automático

O campo é `null=True, blank=True`. A maior parte dos usuários — administração, coordenação, superadmin — não aparece na planilha de ensalamento e não teria valor plausível. Torná-lo obrigatório forçaria inventar um valor para essas pessoas e exigiria preencher os usuários já cadastrados antes de a restrição entrar em vigor.

É consequência simétrica da regra de negócio já acordada: um docente pode existir na planilha sem ter usuário, e um usuário pode existir sem estar na planilha.

### D7. Migration acrescenta o campo nulo, sem tocar nos dados

Uma migration de esquema com duas operações: `AddField` com `null=True`, sem `default`, e `AddConstraint` da unicidade. Os usuários existentes ficam com `NULL`, e `NULL` não conflita com `NULL` na unicidade do PostgreSQL, então nenhuma linha existente viola a restrição nova.

**Não há migration de dados.** Copiar `name` para `username` foi descartado por dois motivos: `name` não é único hoje, e uma instalação com dois usuários de mesmo nome faria a migration falhar ou gravar duplicata; e, por D1, os dois campos guardam coisas diferentes, de modo que a cópia produziria dados errados em massa, que alguém teria de corrigir um a um. O preenchimento é feito pelo administrador, pela tela de edição, depois da implantação.

### D8. A coluna da importação é obrigatória no cabeçalho e pode vir vazia

A spec `importacao-planilhas` determina que "nesta versão, toda coluna declarada DEVE ser obrigatória", e o motor recusa arquivo com coluna ausente. A coluna `Nome de usuário` entra sob essa regra: **arquivos gerados com o modelo antigo passam a ser recusados**, e o modelo para download é atualizado junto.

A célula, porém, pode vir vazia, já que o campo é opcional. A interpretação do vazio é:

- em `create`, o usuário é cadastrado sem `username`;
- em `update`, a célula vazia significa **ausência de informação**, e o valor atual do usuário é mantido.

O vazio não limpa um valor já gravado. Um arquivo que não preenche a coluna apagaria o identificador de todo mundo, e a perda seria silenciosa, espalhada por centenas de linhas e sem como distinguir "não sei" de "quero apagar" numa célula vazia de CSV. Limpar continua possível pela tela de edição, que tem um campo só e uma confirmação visível. Esta é a única assimetria deliberada em relação ao requisito de equivalência entre a importação e as telas, e por isso está escrita na spec, e não deixada implícita no código.

### D9. Nada é criado a partir da planilha

A regra já está garantida pela estrutura, e não só por disciplina: o único caminho de criação de usuário é `UserManager.register`, que exige perfil não nulo e e-mail do domínio institucional. A planilha de ensalamento não tem nenhum dos dois, então um importador futuro não conseguiria criar usuário mesmo se tentasse. A repetição de `Ataliba` na lista e a possibilidade de valores digitados à mão reforçam que a planilha não serve como catálogo de pessoas.

A Change não acrescenta nenhum caminho novo de criação.

### D10. Visual, conferido no navegador

A Change não cria tela nova: o campo entra no modal de cadastro e de edição, que já
renderiza o formulário inteiro, e o valor entra na linha da tabela de usuários, abaixo
do e-mail. Por isso não houve imagem de referência nova.

A conferência foi feita com o Playwright num container, contra o banco `visual_check`,
em 1280 e 360 px, abrindo a lista, o cadastro, a edição e a lista filtrada por um
nome de usuário, com valores reais da planilha (`Aldo Gomes`, `Érica`, `Gera Jr.`,
`Élcio José`).

**Corrigido depois da conferência:**

- **O campo de busca ficava com o texto de apoio cortado.** Ao passar a cobrir o nome
  de usuário, o rótulo virou "Buscar por nome, e-mail ou nome de usuário", e o mesmo
  texto no interior do campo era truncado em "Buscar por nome, e-mail ou nor" nas duas
  larguras. O rótulo acessível continua completo, e o texto dentro do campo passou a
  ser "Buscar usuário".

**Conferido sem ajuste:** o nome de usuário abaixo do e-mail na linha, que empilha em
360 px sem quebrar a linha nem competir com o nome; o "(opcional)" ao lado do rótulo e
o texto de ajuda, ambos gerados pelo layout de formulário que já existe.

## Risks / Trade-offs

- **Coincidência de nome com o atributo do Django.** Quem ler `user.username` pode supor que é a credencial de login. Mitigação: a docstring do campo diz o que ele é, a spec `autenticacao` passa a registrar a distinção e a tarefa 2.6 fixa por teste que `USERNAME_FIELD` continua `email` e que o formulário de login não ganha o campo.
- **Arquivos de importação antigos deixam de valer**, por D8. É inerente à regra de coluna obrigatória da spec do motor. Mitigação: o modelo para download é atualizado na mesma Change e a mensagem de recusa do motor já informa as colunas esperadas.
- **Valor incorreto passa despercebido.** Um `username` digitado com erro não gera erro nenhum agora; ele só se manifesta como ausência de correspondência na importação futura. Mitigação parcial: exibir o valor na tabela de usuários e permitir buscar por ele, o que torna a conferência possível antes de a importação existir.
- **Divergência por acento**, por D5: `Erica` cadastrado não casa com `Érica` da planilha. É um custo aceito em troca de não instalar `unaccent`. A Change futura de importação deve listar as linhas sem correspondência, e não tentar adivinhar.

## Migration Plan

1. Aplicar a migration de esquema. Nenhum dado existente é alterado e nenhuma restrição nova é violada por linha antiga.
2. Implantar. O sistema funciona normalmente com todos os usuários sem `username`.
3. O administrador preenche o campo pela tela de edição, usando a aba `Validação de Dados` da planilha como referência dos valores.
4. A Change futura de importação de ensalamento consome os valores já preenchidos e relata as linhas sem correspondência.

Não há passo de reversão especial: remover o campo é a migration inversa, e nenhum dado de outra entidade depende dele nesta Change.

## Open Questions

Nenhuma. As quatro decisões que dependiam do autor — nome do campo, obrigatoriedade, presença na busca e presença na importação — foram tomadas e estão em D2, D6, na spec de busca e em D8.
