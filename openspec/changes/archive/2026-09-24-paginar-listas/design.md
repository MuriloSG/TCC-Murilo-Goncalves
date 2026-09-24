## Context

`UserListView` e `RoleListView` são `ListView` sem paginação. A lista de usuários tem busca e filtro pela URL, e o htmx troca só o fragmento da tabela e do rodapé (`accounts/partials/user_table.html`). As telas de importação (`imports/views.py`) listam o histórico inteiro e todas as linhas de uma importação, com o filtro `?linhas=erros`. Não existe componente de paginação no app `ui`. Os testes de modal e de middleware já usam `?pagina=2` como exemplo de parâmetro.

## Goals / Non-Goals

**Goals:**

- Uma única forma de paginar, usada por todas as listas.
- Links que mantêm os demais parâmetros da URL e funcionam sem JavaScript.

**Non-Goals:**

- Tamanho de página escolhido pelo usuário, links numerados e ordenação por coluna.

## Decisions

### D1. Função `paginate` no app `ui`

`ui.pagination.paginate(request, queryset, per_page)` usa o `Paginator` do Django e `get_page(request.GET.get('pagina'))`. `get_page` devolve a primeira página para valores inválidos e a última para números além do fim, então nenhuma página inválida vira 404. As constantes são `PAGE_SIZE = 5` e, nas importações, `ROWS_PAGE_SIZE = 20`, escolhidas pelo autor. Os testes calculam os valores esperados a partir delas, para que mudar o tamanho da página não exija mudar os testes.

Alternativa considerada: **`paginate_by` da `ListView`**. Ela responde 404 para uma página fora do intervalo, o que quebraria um link salvo depois que registros forem excluídos ou filtrados. Também não serviria às linhas da importação, que não são uma `ListView`.

### D2. Link de página mantendo os parâmetros

A tag `{% page_url number %}` da biblioteca `ui` copia `request.GET`, troca `pagina` e devolve a query string. Assim, `busca`, `situacao` e `linhas` são mantidos. A página 1 omite o parâmetro, para que a URL da primeira página seja igual à URL sem paginação.

### D3. Componente `ui/components/pagination.html`

```text
[ Exibindo 6 a 10 de 57 usuários ]        [ Anterior ]  Página 2 de 3  [ Próxima ]
```

- Um `<nav aria-label="Paginação">` dentro do rodapé do cartão. O intervalo fica à esquerda e a navegação à direita. Abaixo de 640 px, ficam empilhados: o intervalo, depois "Página X de Y" numa linha própria e os dois botões dividindo a largura, porque os três lado a lado não cabem em 360 px.
- "Anterior" e "Próxima" são `btn-secondary` só com texto. A seção 9.7 das convenções põe o ícone à esquerda em botões com texto, o que não combina com "Próxima", e o texto já basta. Na primeira e na última página, o controle vira texto inerte com `aria-disabled="true"`, e não um link.
- "Página X de Y" tem `aria-current="page"`.
- Com uma só página, só o intervalo aparece. Com a lista vazia, o rodapé não aparece, porque a tabela já informa que não há registros.
- O componente recebe `page`, o substantivo no singular e no plural (`noun`, `noun_plural`) e, opcionalmente, `hx_target`. Com o alvo, os links recebem `hx-get`, `hx-target` e `hx-push-url`, como o formulário de filtros da lista de usuários, e `hx-swap="innerHTML show:top"`, para que a troca de página leve ao topo da tabela, e não deixe a tela parada no rodapé.

Os estilos ficam na classe `.pagination` do `app.css`, com os tokens existentes.

### D4. Lista de usuários

A paginação entra no fragmento `user_table.html`, junto com o rodapé, para que a busca pelo htmx e a troca de página atualizem a mesma área. O formulário de filtros não envia `pagina`, então mudar a busca volta para a primeira página. O contador do título continua mostrando o total cadastrado, e o rodapé mostra o intervalo dentro do resultado filtrado.

### D5. Importações

O histórico pagina as importações (`PAGE_SIZE` por página). A prévia e o detalhe paginam as linhas (`ROWS_PAGE_SIZE` por página), inclusive com o filtro `?linhas=erros`. O resumo continua contando todas as linhas da importação, e não só as da página.

## Risks / Trade-offs

- **[Sem links numerados]** Chegar à página 30 exige avançar uma a uma ou editar a URL. → A busca resolve o caso de achar alguém específico, e o tamanho da página pode ser aumentado nas constantes.
- **[Contagem extra]** O `Paginator` faz uma consulta de contagem por página. → É o custo normal da paginação, e evita carregar todos os registros.
