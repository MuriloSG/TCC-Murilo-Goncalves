## Why

Os campos de escolha do sistema usam o `<select>` nativo. A lista que ele abre é desenhada pelo sistema operacional, não segue a identidade visual do projeto, aparece fora do campo e, no celular, cobre a tela inteira. Ela também não tem busca: escolher um perfil entre dezenas, ou um usuário entre centenas no filtro da auditoria, obriga a percorrer a lista inteira. Com os módulos de espaços e reservas por vir, cada tela nova repetiria o mesmo problema. O autor pediu um componente único de seleção, usado por qualquer tela, com a lista ancorada abaixo do campo, busca e exibição de 10 opções por vez.

## What Changes

- **Componente de seleção no app `ui`**, aplicado a todos os campos de escolha do sistema: perfil no cadastro e na troca de perfil, situação na lista de usuários e os quatro filtros da auditoria.
- **Lista ancorada abaixo do campo**, com a largura dele, desenhada com os tokens e os componentes do projeto, em vez da lista do sistema operacional.
- **Busca dentro da lista**, sem diferenciar maiúsculas nem acentos, com o texto do estado vazio quando nada corresponde.
- **Dez opções por vez**, com o restante carregado ao rolar a lista ou pelo controle "Mostrar mais".
- **Duas fontes de opções:** opções fixas ou de listas curtas são filtradas e paginadas no navegador; fontes que vêm do banco e podem crescer são paginadas no servidor, por uma rota de opções que devolve 10 por vez.
- **Rotas de opções** declaradas pelo app dono dos dados, com `login_required` na URL e a permissão declarada na view, como as demais rotas do projeto.
- **Sem JavaScript**, o campo continua sendo o `<select>` nativo, com o mesmo nome, o mesmo valor e o mesmo envio do formulário.
- **Teclado e leitores de tela:** o campo segue o padrão combobox, com as setas, Home, End, Enter e Esc, e anuncia a opção em foco.

### Fora do escopo

- Seleção de vários valores no mesmo campo. A escolha de permissões do perfil continua na lista de caixas de seleção que já existe.
- Criação de uma opção nova a partir do campo.
- Agrupamento de opções por categoria dentro da lista.
- Troca do filtro de busca da lista de usuários, que é um campo de texto e continua como está.

### Dependência

Esta Change depende da Change `auditar-acoes-do-sistema`, que cria a consulta da auditoria, a permissão `AUDITORIA.VISUALIZAR` e o filtro por usuário. Os deltas das specs `controle-acesso` e `auditoria` partem do texto dela, e ela DEVE ser arquivada antes desta.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `interface`: requisito novo do componente de seleção, da busca dentro dele, da exibição de 10 em 10 e do comportamento sem JavaScript, e ajuste do requisito dos componentes base.
- `controle-acesso`: as rotas de opções entram na correspondência entre operações e permissões.
- `auditoria`: o filtro por usuário passa a buscar as opções no servidor, com o limite conhecido sem JavaScript.

## Impact

- **`ui`:** componente (`ui/templates/ui/components/select.html`), estilos no `app.css`, `ui/static/ui/js/select.js`, view base das rotas de opções, e o renderizador de formulários passando a marcar os campos de escolha.
- **`accounts`:** campo de perfil e filtro de situação usando o componente, e rota de opções dos perfis.
- **`audit`:** os quatro filtros usando o componente, e rota de opções dos usuários, paginada no servidor.
- **Testes:** comportamento sem JavaScript, busca, paginação das opções, permissões das rotas de opções e as regras de classe e de texto.
- **Sem dependência nova:** o JavaScript é do próprio projeto, como o `checklist.js` e o `modal.js`.

## Alinhamento com o TCC

- **RNF05 e P7:** a escolha fica no mesmo padrão em todas as telas, com busca, o que atende ao perfil tecnológico variado dos docentes.
- **RNF03 e P6:** a lista que vem do banco é paginada no servidor, e a tela deixa de carregar todas as opções de uma vez.
- **P4 e P8:** um componente único, no app `ui`, em vez de uma solução por tela.
