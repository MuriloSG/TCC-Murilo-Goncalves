# Carregamento global

## D1. Um `<dialog>` modal como barreira

Os modais do projeto são `<dialog>` abertos com `showModal()` (`ui/js/modal.js`) e ficam na camada superior do navegador, acima de qualquer `z-index`. Um overlay comum não os cobriria. Por isso o carregamento também é um `<dialog>` aberto com `showModal()`: o último aberto fica por cima, e o navegador torna todo o resto inerte, inclusive um modal já aberto. Cliques, foco, teclado e leitores de tela deixam de alcançar a página, sem lógica em cada botão.

O evento `cancel` é cancelado para que o Esc não feche o carregamento.

## D2. API

`window.IFAgenda.loading` expõe `show(message)`, `hide()` e `run(operation, message)`. `run` chama `show`, executa a operação e chama `hide` no `finally`, de modo que sucesso e erro liberam a tela. Não há tempo limite automático. Chamar `show` com o carregamento aberto só troca a mensagem.

## D2a. Formulários

Todo envio de formulário e toda requisição htmx feita por um formulário, inclusive os filtros que reagem à digitação ou à troca de opção, abrem o carregamento, com o texto de `data-loading` como mensagem; `data-loading="false"` desliga para um formulário. O evento é ouvido no `document`, sem código em cada tela.

- Envio comum: a página navega e o carregamento some com ela. Ao voltar pelo histórico com a página guardada em cache (`pageshow` com `persisted`), ele é fechado.
- Requisição htmx de formulário: o carregamento abre no `htmx:beforeRequest` e fecha no `loadend` da própria requisição, com sucesso, recusa, erro ou cancelamento. O `htmx:afterRequest` não serve, porque, quando a resposta substitui o próprio formulário (calendário público), o evento é disparado num elemento fora da página e não chega ao `document`. Se a resposta traz `HX-Redirect`, o carregamento continua aberto até a nova página carregar.
- Nos filtros por digitação, o carregamento abre depois do intervalo do `hx-trigger`, e o foco volta ao campo quando ele fecha.

## D3. Acessibilidade

O `<dialog>` é rotulado pelo próprio texto. Sem mensagem, o texto "Carregando" fica só para tecnologia assistiva (`sr-only`); com mensagem, ela aparece abaixo do spinner. O `<body>` recebe `aria-busy="true"` enquanto o carregamento está aberto. O spinner é decorativo (`aria-hidden`) e, com movimento reduzido, fica parado.

## D4. Limitações

- Requisições disparadas antes do `show` continuam; o bloqueio vale para novas interações.
- O comportamento do bloqueio é conferido no navegador, porque o projeto não tem executor de testes JavaScript.
