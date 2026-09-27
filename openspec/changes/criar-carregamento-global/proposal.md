## Why

Operações demoradas (importação de planilhas, exclusões, salvamentos, ações administrativas) ainda não têm uma barreira comum de interação. Hoje só existe o `busy.js`, que desabilita os botões de uma região marcada. Cada tela que precisasse impedir ações durante uma operação teria de montar o próprio bloqueio.

## What Changes

- **Carregamento global:** um único componente, declarado no `base.html`, que cobre a tela com um spinner e, opcionalmente, uma mensagem curta.
- **Bloqueio de interação:** enquanto ativo, nenhum clique, link, envio de formulário, menu, modal ou tecla chega à página abaixo.
- **Todos os formulários e filtros:** o envio de qualquer formulário, e toda requisição htmx feita por um formulário, ativa o carregamento, com a mensagem do atributo `data-loading` quando houver; `data-loading="false"` desliga.
- **API global:** `IFAgenda.loading.show(mensagem)`, `IFAgenda.loading.hide()` e `IFAgenda.loading.run(operacao, mensagem)`, com os atalhos `showLoading` e `hideLoading`.

### Fora do escopo

- Ligar o carregamento automaticamente a links, a requisições htmx que não partem de um formulário ou a `fetch`.
- Mudança no processamento da importação de planilhas, Celery ou notificações.
- Barra de progresso, percentual e tempo limite automático.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `interface`: passa a ter o carregamento global com bloqueio de interação.

## Impact

- **`ui`:** `base.html`, `ui/loading.html`, `ui/js/loading.js`, `imports/upload_modal.html` (mensagem da importação) e os estilos `.loading` e `.spinner` em `ui/styles/app.css`.
- **Testes:** `ui/tests/test_loading.py`.
- **Sem mudança** em models, migrations, rotas, permissões, regras de negócio ou dependências.
