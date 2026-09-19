## 1. Componente de paginação

- [x] 1.1 Criar `ui/pagination.py` com `paginate`, `PAGE_SIZE` e `ROWS_PAGE_SIZE` (D1)
- [x] 1.2 Criar a tag `page_url` na biblioteca `ui`, mantendo os demais parâmetros e omitindo a página 1 (D2)
- [x] 1.3 Criar `ui/components/pagination.html`, e a classe `.pagination` no `app.css` (D3)
- [x] 1.4 Testar `paginate` e `page_url`: página inválida, além do fim, parâmetros mantidos e página 1 sem parâmetro

## 2. Listas

- [x] 2.1 Paginar a lista de usuários no fragmento da tabela, com o alvo do htmx (D4)
- [x] 2.2 Paginar a lista de perfis
- [x] 2.3 Paginar o histórico de importações e as linhas da prévia e do detalhe, mantendo `linhas` (D5)
- [x] 2.4 Atualizar os testes de rodapé e escrever os cenários das specs `interface` e `gestao-usuarios`
- [x] 2.5 Rodar `make test` com a suíte inteira passando
- [x] 2.6 Commit

## 3. Verificação

- [x] 3.1 Conferir as listas no navegador, no banco `visual_check`, em 360 e 1280 px, com e sem JavaScript
- [x] 3.2 Validar a Change com `openspec validate paginar-listas --strict`
