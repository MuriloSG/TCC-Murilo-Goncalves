## Context

A `UserListView` devolve todos os usuários ordenados por nome e e-mail, com os perfis pré-carregados. A Change `definir-identidade-visual` deixa a lista num cartão com cabeçalho (título, contador e descrição), tabela e rodapé, e instala o htmx e o django-htmx. O desenho da busca está na prévia dessa Change: campo com o ícone `search` e o placeholder "Buscar por nome ou e-mail", e o seletor "Todas as situações", "Ativos" e "Inativos".

## Goals / Non-Goals

**Goals:**

- Encontrar um usuário por trecho do nome ou do e-mail e ver só ativos ou só inativos.
- Estado da busca na URL, funcionando com e sem JavaScript.
- Filtragem no banco, pelo ORM.

**Non-Goals:**

- Busca sem acentos, filtro por perfil, paginação e ordenação por coluna.
- Busca na lista de perfis.

## Decisions

### D1. Parâmetros na URL, validados por formulário

`UserFilterForm` (em `accounts/forms.py`) declara:
- `busca`: `CharField`, opcional, até 100 caracteres, sem espaços nas pontas;
- `situacao`: `ChoiceField` opcional com `todos`, `ativos` e `inativos`.

A view instancia o formulário com `request.GET`. Um valor inválido de `situacao` não gera erro na tela: o formulário o descarta e a lista trata como `todos`. Os nomes dos parâmetros são em português, como os caminhos de URL (convenção 2).

Alternativa considerada: **ler `request.GET` direto na view**. Espalharia a validação e o valor padrão pela view, e o formulário já reaproveita o renderizador de campos da interface.

### D2. Filtragem no manager

`User.objects.search(term, status)` devolve o queryset filtrado:
- `Q(name__icontains=term) | Q(email__icontains=term)` quando há termo;
- `is_active=True` ou `False` conforme a situação.

A view soma a isso o `prefetch_related('roles')` e a ordem atual. O total do rodapé é `User.objects.count()`, uma consulta a mais.

Alternativas consideradas:
- **Busca textual do PostgreSQL (`SearchVector`):** é mais do que a necessidade, e trechos de e-mail não funcionam bem com ela.
- **`unaccent`:** exigiria uma migration para criar a extensão. Fica para quando houver demanda.

### D3. Formulário e htmx

O formulário de filtros fica no `card-head` da lista, com `method="get"` e `role="search"`.

- **Com htmx:**
  - `hx-get` para a própria lista, `hx-target` no bloco da tabela e do rodapé, e `hx-push-url="true"`, para a URL acompanhar o estado;
  - `hx-trigger="input changed delay:300ms from:input[name=busca], change from:select, search"`.
- **Sem JavaScript:** Enter no campo ou mudança no seletor seguida de Enter enviam o formulário. Um botão "Buscar" fica visível só quando o JavaScript está desligado, por `<noscript>`.

A view renderiza só o fragmento `accounts/partials/user_table.html` quando `request.htmx` é verdadeiro e o alvo é a tabela (`request.htmx.target`). Caso contrário, renderiza a página completa, que inclui o mesmo fragmento.

### D4. Filtros preservados depois das ações

A `ModalView` da Change visual já redireciona para `request.htmx.current_url` quando a ação parte da lista. Como os filtros estão na URL, a lista volta filtrada. Esta Change só acrescenta o teste disso.

### D5. Textos

Todos seguem a seção 9 das convenções:
- rótulos ocultos visualmente: "Buscar por nome ou e-mail" e "Situação";
- opções: "Todas as situações", "Ativos" e "Inativos";
- rodapé: "Exibindo X de Y usuários", com o singular "Exibindo 1 de 1 usuário";
- estado vazio: "Nenhum usuário encontrado para a busca." e o link "Limpar busca".

## Notas de implementação

- **Botão Voltar.** O formulário tem `hx-history="false"`. Sem isso, o htmx restaurava a lista a partir da cópia do HTML guardada antes da busca: a tabela voltava filtrada, mas o campo de busca voltava vazio, porque o texto digitado não fica no atributo `value`. Com a opção, o Voltar pede a página ao servidor, que a monta a partir da URL, com o formulário e a tabela coerentes.
- **Gatilhos do htmx.** Além dos gatilhos do D3, o formulário responde a `submit` (Enter no campo) e o `search` vem do campo de busca (`search from:input[name=busca]`), porque o evento `search` não se propaga até o formulário.
- **Conferência no navegador (task 5.1).** Busca ao digitar, filtro, contagem, estado vazio, "Limpar busca", Voltar duas vezes, ação em modal a partir da lista filtrada e a busca sem JavaScript (Enter e botão "Buscar") conferidos em 360 e 1280 px, sem rolagem horizontal.

## Risks / Trade-offs

- [`icontains` não usa índice e percorre a tabela] → o número de usuários de um campus é de centenas, e a consulta é trivial nesse volume. Se crescer, um índice trigram (`pg_trgm`) resolve sem mudar a interface.
- [A busca ao digitar gera uma requisição por pausa na digitação] → o intervalo de 300 ms e o `changed` do htmx evitam requisições repetidas com o mesmo valor.
- [A busca não ignora acentos] → registrado como fora do escopo. "Joao" não encontra "João", mas "Jo" encontra.

## Migration Plan

Sem migração de dados. O rollback é reverter os commits.

## Open Questions

Nenhuma.
