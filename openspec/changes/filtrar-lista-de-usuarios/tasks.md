## 1. Pré-requisitos

- [ ] 1.1 Confirmar que a Change `definir-identidade-visual` foi implementada, com o cartão da lista de usuários, o htmx e a `ModalView`

## 2. Consulta

- [ ] 2.1 Implementar `User.objects.search(term, status)` com `icontains` em nome e e-mail e o filtro de situação (D2)
- [ ] 2.2 Escrever os testes do manager: trecho do nome, trecho do e-mail, maiúsculas, situação, combinação e termo vazio

## 3. View e formulário

- [ ] 3.1 Criar `UserFilterForm` em `accounts/forms.py` com `busca` e `situacao`, tratando valor inválido como `todos` (D1)
- [ ] 3.2 Alterar `UserListView` para aplicar o formulário, usar o `search`, manter a ordem e o `prefetch_related`, e enviar ao template o total e o formulário (D1, D2)
- [ ] 3.3 Extrair a tabela e o rodapé para `accounts/partials/user_table.html` e renderizar só esse fragmento quando o alvo do htmx for a tabela (D3)
- [ ] 3.4 Colocar o formulário de filtros no cabeçalho do cartão, com os atributos do htmx, os rótulos ocultos, o botão "Buscar" em `<noscript>`, a contagem "Exibindo X de Y usuários" e o estado vazio com "Limpar busca" (D3, D5)

## 4. Testes

- [ ] 4.1 Escrever os testes da view com os cenários da spec: nome, e-mail, situação, combinação, situação inválida, busca sem resultado, fragmento pelo htmx e 403 sem a permissão
- [ ] 4.2 Testar que uma desativação feita pelo htmx a partir de `usuarios/?busca=ana` responde com `HX-Redirect` para a mesma URL (D4)
- [ ] 4.3 Rodar `make test` com a suíte inteira passando, incluindo o teste de texto

## 5. Verificação

- [ ] 5.1 Conferir a busca em 360 e 1280 px, com e sem JavaScript, e o botão Voltar do navegador depois de filtrar
- [ ] 5.2 Validar a Change com `openspec validate filtrar-lista-de-usuarios --strict`
