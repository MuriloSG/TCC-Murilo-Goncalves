## Why

As listas do sistema mostram todos os registros numa única página. Com os docentes do campus cadastrados, e em especial depois da importação de usuários por planilha, a lista de usuários, o histórico de importações e a prévia de uma importação (até 1.000 linhas) ficam longos demais para ler e lentos para carregar. O autor pediu paginação em todas as listas existentes.

## What Changes

- **Paginação** na lista de usuários, na lista de perfis, no histórico de importações de usuários e nas linhas da prévia e do detalhe de uma importação.
- **Parâmetro `pagina` na URL**, que se combina com os demais parâmetros de cada lista (`busca` e `situacao` nos usuários, `linhas` na prévia). Mudar a busca ou o filtro volta para a primeira página.
- **Página inválida ou além da última** mostra a página válida mais próxima, sem erro.
- **Navegação** com "Anterior", "Página X de Y" e "Próxima", num componente único do app `ui`, usado por todas as listas. Sem JavaScript, os links funcionam como links comuns. Na lista de usuários, a troca de página usa o mesmo fragmento da tabela atualizado pelo htmx.
- **Rodapé** das listas passa a informar o intervalo exibido: "Exibindo 21 a 40 de 57 usuários". O total cadastrado continua no contador do título do cartão.
- **Tamanho da página:** 20 itens nas listas e 50 linhas na prévia e no detalhe de uma importação.

### Fora do escopo

- Escolha do tamanho da página pelo usuário, links para cada número de página e ordenação por coluna.
- A lista de permissões dentro do perfil, que não é uma lista paginável (é agrupada por recurso e tem poucos itens).

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities
- `interface`: novo requisito de paginação das listas.
- `gestao-usuarios`: o rodapé da lista de usuários passa a informar o intervalo exibido, e a busca e o filtro se combinam com a página.

## Impact

- **`ui`:** função de paginação, tag que monta o link de uma página mantendo os demais parâmetros, componente `ui/components/pagination.html`, e a classe `.pagination` no `app.css`.
- **`accounts`:** `UserListView`, `RoleListView` e os templates das listas de usuários e de perfis.
- **`imports`:** `ImportListView`, `ImportDetailView` e os templates do histórico e do detalhe.
- **Testes:** rodapés das listas e navegação entre páginas.
- **Sem mudança** em models, rotas, permissões ou dependências.

## Alinhamento com o TCC

- **RNF03 e P6:** as páginas das listas passam a carregar uma quantidade limitada de registros.
- **RNF05 e P7:** o intervalo exibido e a página atual ficam visíveis, e a navegação funciona igual em todas as listas.
