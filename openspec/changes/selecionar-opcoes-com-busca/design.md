## Context

Todos os campos de escolha do projeto são `<select>` nativos renderizados pelo `ui/forms/field.html`, dentro de um `.select-wrap` que só acrescenta a seta e o estilo do controle. São seis campos hoje: perfil no cadastro de usuário e na troca de perfil (`ModelChoiceField` sobre `Role`), situação na lista de usuários, e usuário, ação, módulo e origem nos filtros da auditoria. O de usuário já lista todos os usuários do banco.

O projeto já tem as peças de que o componente precisa: o menu suspenso (`details.menu` com `menu.js`), o campo de busca com filtragem sem acentos e o estado vazio da seleção de permissões (`checklist.js`), as transições curtas do `app.css` e a regra de que tudo funciona sem JavaScript. O acesso é sempre decidido por `login_required` na URL e `permission_required` na view.

A referência visual da lista suspensa ainda não chegou. Esta Change define o comportamento; o desenho entra depois, conforme a seção 9.8 das convenções.

## Goals / Non-Goals

**Goals:**

- Um componente de seleção para qualquer tela, com a lista ancorada no campo, busca e 10 opções por vez.
- Nenhuma mudança na forma como as views e os formulários recebem o valor escolhido.
- Uma lista grande nunca chega inteira ao navegador quando a fonte declara paginação no servidor.

**Non-Goals:**

- Seleção múltipla, criação de opção pelo campo e agrupamento por categoria.
- Substituir o `<select>` nativo como elemento que guarda o valor.

## Decisions

### D1. Melhoria progressiva sobre o `<select>` nativo

O servidor continua renderizando um `<select>` comum, com `name`, `id`, as opções e o valor escolhido. O `select.js` esconde esse elemento, monta ao lado dele o gatilho e a lista, e devolve a escolha ao próprio `<select>`, disparando `change`. O formulário, a validação, o htmx e os parâmetros da URL continuam iguais, e nenhuma view ou formulário muda por causa do componente.

Sem JavaScript, o campo é exatamente o que é hoje: o `<select>` nativo, com todas as opções e o mesmo envio.

Alternativa considerada: **campo escondido (`<input type="hidden">`) com uma lista própria**. Recusada porque deixaria o campo sem funcionamento algum sem JavaScript e exigiria validação nova em todo formulário.

### D2. Lista ancorada no campo, e não uma camada solta

O componente é um elemento posicionado dentro do próprio campo (`position: absolute`, largura do controle, logo abaixo dele), com a superfície, a borda, o raio e a sombra do menu suspenso que já existe. Ele nunca vira uma janela do sistema operacional, nem no celular.

Dentro de um modal, a lista aberta aumenta a área rolável do modal, e o componente rola a lista para a vista ao abrir. É por isso que a lista é absoluta dentro do campo, e não fixa na tela: uma camada fixa se desprenderia do campo quando o modal rolasse.

### D3. Busca dentro da lista

A lista tem um campo de busca no topo, que filtra por trecho, sem diferenciar maiúsculas nem acentos, com a mesma normalização do `checklist.js`. Sem resultado, a lista mostra o texto do estado vazio. O campo de busca só aparece quando a fonte tem mais opções do que cabem numa página, para não poluir um campo de três opções.

### D4. Dez por vez

A lista mostra 10 opções. As demais entram ao rolar até o fim da lista e pelo controle "Mostrar mais", que existe para quem navega pelo teclado e para quem não usa rolagem. O número fica numa constante única, ao lado do `PAGE_SIZE` das listas.

### D5. Duas fontes de opções

| Fonte | Onde as opções ficam | Busca e paginação |
|---|---|---|
| **Fixa** (padrão) | todas no `<select>` renderizado pelo servidor | no navegador |
| **Paginada** (declarada pelo campo) | só a opção escolhida e a primeira página no `<select>` | no servidor, pela rota de opções |

Os campos de hoje que vêm de listas curtas (situação, ação, módulo, origem e perfil) usam a fonte fixa. O filtro por usuário da auditoria usa a fonte paginada, que é o caso que motivou o pedido.

A rota de opções responde a `?busca=` e `?pagina=`, devolvendo no máximo 10 opções por página, com o valor, o rótulo e a indicação de que há mais. O formato é o mesmo para qualquer fonte, para que o `select.js` não conheça o domínio.

**Preço da fonte paginada:** sem JavaScript, o campo mostra só a primeira página das opções. É a única situação em que o sistema não entrega a funcionalidade inteira sem JavaScript, e vale só para um filtro de consulta, em que os demais filtros continuam funcionando. Um campo obrigatório de formulário, como o perfil do usuário, NÃO usa fonte paginada por causa disso.

### D6. Rota de opções por app, com a permissão declarada

A view base fica no `ui` e não conhece o domínio: recebe a consulta, aplica a busca e a paginação e devolve o JSON. Cada app cria a própria rota, com `login_required` na URL e `permission_required` na view, como as telas de importação fazem com as views base do `imports`.

A permissão de cada rota é a da tela que consome as opções:

- **opções de usuários**, usada pelo filtro da auditoria: `AUDITORIA.VISUALIZAR`;
- **opções de perfis**, se vier a ser usada: só autenticação, porque a escolha do perfil no cadastro e na troca não pode exigir `PERFIL.VISUALIZAR` (spec `controle-acesso`), e a rota não revela nada além dos nomes dos perfis.

### D7. Teclado e leitores de tela

O gatilho é um `button` com `role="combobox"`, `aria-expanded`, `aria-controls` e o rótulo do campo associado. A lista é um `role="listbox"` com opções `role="option"` e `aria-selected`. O foco fica no campo de busca, e `aria-activedescendant` aponta a opção em destaque. As setas movem o destaque, Home e End vão às pontas, Enter escolhe, Esc fecha e devolve o foco ao gatilho, e um clique fora fecha. A área de toque de cada opção tem pelo menos 44 px de altura.

### D8. Arquivos

- `ui/templates/ui/components/select.html`: o `<select>` nativo, o gatilho, a lista, a busca e o estado vazio, tudo renderizado pelo servidor.
- `ui/static/ui/js/select.js`: liga o componente, como o `checklist.js` faz, inclusive depois de uma troca do htmx.
- `ui/views.py`: a view base das rotas de opções.
- `app.css`: as classes do componente, na camada de componentes.
- `ui/forms/field.html`: passa a incluir o componente no lugar do `.select-wrap`.

### D9. Visual, a partir da referência do autor

A referência enviada mostra um select pesquisável em cinza claro: gatilho retangular com borda fina e canto arredondado, com o texto de espera à esquerda e a seta à direita; o painel logo abaixo, separado por um espaço, com a mesma largura, borda, canto arredondado e sombra; a busca no topo do painel, com a lupa à esquerda e uma divisória abaixo dela; e as opções em texto simples, sem ícone, com espaçamento generoso entre elas.

O que foi adaptado:

- o gatilho reaproveita a altura, a borda, o raio e o preenchimento dos campos do projeto (`.input`), para ficar igual aos demais controles do formulário;
- o painel usa a superfície, a borda, o raio e a sombra do menu suspenso (`.menu-list`), que já é a camada flutuante do projeto;
- a busca usa o ícone `search` do Lucide e a mesma normalização sem acentos da seleção de permissões;
- as opções ficam com pelo menos 44 px de altura, pela regra de alvo de toque, e ganham realce no foco do teclado e no ponteiro;
- o espaçamento entre gatilho e painel é o mesmo do menu suspenso.

O que foi retirado ou trocado:

- o cinza claro da referência dá lugar aos tokens do projeto, e o foco visível verde entra sobre o gatilho, a busca e a opção em destaque;
- a sombra grande e difusa da referência vira `--shadow-overlay`, a mesma do modal e do menu (a seção 9.6 proíbe sombra grande e difusa);
- "Pesquisar..." vira "Buscar", porque a seção 9.2 proíbe reticências;
- o texto de espera é o do próprio campo ("Selecione o perfil", "Todos os usuários"), e não um exemplo;
- a opção escolhida ganha marca com o ícone `check`, além do realce, porque estado não pode ser indicado só pela cor (seção 9.7);
- o estado vazio da busca e o controle "Mostrar mais", que a referência não mostra, entram conforme D3 e D4.

## Risks / Trade-offs

- **[Fonte paginada sem JavaScript]** O filtro por usuário da auditoria fica limitado à primeira página. → É um filtro de consulta, não um campo obrigatório, e os demais filtros continuam completos. Campos obrigatórios não usam fonte paginada.
- **[Componente em toda tela]** Um defeito no `select.js` afeta todos os campos de escolha do sistema. → O `<select>` nativo continua sendo a fonte do valor, então uma falha do script degrada para o comportamento de hoje, e não para um campo quebrado.
- **[Lista dentro do modal]** A lista aberta aumenta a altura rolável do modal. → O componente rola a lista para a vista ao abrir, e a conferência no navegador cobre o caso em 360 e em 1280 px.
- **[Mais JavaScript próprio]** O projeto ganha mais um script para manter. → É o mesmo padrão dos outros componentes do `ui`, sem dependência externa nova.

## Migration Plan

1. O componente entra no `ui` e passa a ser usado pelo renderizador de campos, o que já troca todos os `<select>` das telas existentes.
2. A rota de opções de usuários entra no `audit`, e o filtro por usuário passa a usá-la.
3. Não há migration de banco, nem mudança em dados.
4. Reversão: voltar o `ui/forms/field.html` ao `.select-wrap` devolve os campos ao `<select>` nativo, sem tocar em formulários nem em views.

## Open Questions

- A referência visual da lista suspensa, que o autor vai enviar, e o registro do que for adaptado e retirado dela (D9).
