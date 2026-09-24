## 1. Referência visual

- [x] 1.1 Receber do autor a imagem de referência da lista suspensa (D9)
- [x] 1.2 Registrar no `design.md` o que foi adaptado e o que foi retirado da referência (seção 9.8 das convenções)

## 2. Componente

- [x] 2.1 Criar `ui/templates/ui/components/select.html`, com o `select` nativo, o gatilho, a busca, a lista e o estado vazio (D1, D2)
- [x] 2.2 Criar as classes do componente no `app.css`, com a lista ancorada ao campo e o foco visível (D2, D9)
- [x] 2.3 Criar `ui/static/ui/js/select.js`: abrir e fechar, escolher, sincronizar o `select` nativo e religar depois das trocas do htmx (D1)
- [x] 2.4 Implementar a busca sem acentos e a exibição de 10 em 10, com "Mostrar mais" e o carregamento ao rolar (D3, D4)
- [x] 2.5 Implementar o teclado e o ARIA do padrão combobox (D7)
- [x] 2.6 Passar o `ui/forms/field.html` a usar o componente no lugar do `.select-wrap` (D8)
- [x] 2.7 Testar a renderização do componente, o campo sem JavaScript e as regras de classe e de texto
- [x] 2.8 Commit

## 3. Fonte paginada no servidor

- [x] 3.1 Criar a view base das rotas de opções no `ui`, com busca, paginação e o formato único da resposta (D5, D6)
- [x] 3.2 Criar a rota de opções de usuários no `audit`, com a permissão declarada, e o filtro por usuário usando a fonte paginada (D5, D6)
- [x] 3.3 Fazer o `select.js` buscar as páginas seguintes na rota quando o campo declarar a fonte paginada (D5)
- [x] 3.4 Testar a rota nas quatro situações de acesso, a busca no servidor, o limite de 10 por página e a página do formulário sem a lista inteira
- [x] 3.5 Rodar `make test` com a suíte inteira passando
- [x] 3.6 Commit

## 4. Telas

- [ ] 4.1 Conferir o campo de perfil no cadastro e na troca de perfil, dentro do modal
- [ ] 4.2 Conferir o filtro de situação da lista de usuários, com a atualização pelo htmx
- [ ] 4.3 Conferir os quatro filtros da auditoria
- [ ] 4.4 Atualizar os testes de tela que dependem do `select` nativo
- [ ] 4.5 Rodar `make test` com a suíte inteira passando
- [ ] 4.6 Commit

## 5. Documentação e verificação

- [ ] 5.1 Documentar o componente na seção 9.9 das convenções e na seção Interface do `README.md`
- [ ] 5.2 Conferir no navegador, no banco `visual_check`, em 360 e 1280 px, com teclado, com e sem JavaScript
- [ ] 5.3 Validar a Change com `openspec validate selecionar-opcoes-com-busca --strict`
- [ ] 5.4 Commit
