# interface Specification

## Purpose
TBD - created by archiving change definir-identidade-visual. Update Purpose after archive.
## Requirements
### Requirement: Escala fechada de tokens
Cores, espaçamentos, raios, sombras, tamanhos de fonte, famílias de fonte e pontos de quebra da interface DEVEM (MUST) vir de uma escala fechada de tokens, definida num único arquivo-fonte de CSS do projeto. A paleta padrão do Tailwind NÃO DEVE (MUST NOT) estar disponível. Os templates NÃO DEVEM (MUST NOT) conter atributo `style`, valores arbitrários do Tailwind (classes com colchetes, como `p-[13px]` ou `bg-[#fff]`) nem utilitários de cor, espaçamento, raio, sombra ou tamanho de fonte fora da escala. Sombra DEVE (MUST) existir só em camadas flutuantes (modal, menu suspenso e dica). A suíte de testes DEVE (MUST) verificar essas proibições em todos os templates do projeto e indicar o arquivo, a linha e a classe de cada violação.

#### Scenario: Valor arbitrário em template
- **WHEN** um template contém a classe `mt-[13px]`
- **THEN** o teste de valores soltos falha indicando o arquivo, a linha e a classe

#### Scenario: Cor da paleta padrão do Tailwind
- **WHEN** um template contém a classe `bg-blue-500`
- **THEN** o teste de valores soltos falha, porque `blue-500` não é um token do projeto

#### Scenario: Atributo style
- **WHEN** um template contém `style="color: red"`
- **THEN** o teste de valores soltos falha

#### Scenario: Sombra fora de camada flutuante
- **WHEN** um botão ou cartão de um template usa a classe `shadow-overlay`
- **THEN** o teste de valores soltos falha

### Requirement: Função das cores e contraste mínimo
Cada token de cor DEVE (MUST) ter uma única função entre marca, ação, estado, texto, superfície e borda, conforme a tabela de tokens do design. O vermelho da marca NÃO DEVE (MUST NOT) ser usado na interface fora do símbolo oficial do IF. A cor de ação DEVE (MUST) aparecer só em botões primários, links, foco e no fundo do item atual da navegação. Todo par de texto e fundo usado DEVE (MUST) ter contraste de pelo menos 4,5:1, e toda borda de controle, todo ícone que identifica uma ação ou um estado e todo indicador de foco DEVEM (MUST) ter pelo menos 3:1 contra o fundo em que aparecem. A suíte de testes DEVE (MUST) calcular o contraste WCAG 2.x de cada par declarado a partir dos valores do arquivo de tokens e falhar quando algum ficar abaixo do mínimo.

#### Scenario: Par abaixo do mínimo
- **GIVEN** o token de texto secundário alterado para um valor com contraste de 4,47:1 sobre a superfície branca
- **WHEN** a suíte de testes é executada
- **THEN** o teste de contraste falha indicando o par, o contraste calculado e o mínimo exigido

#### Scenario: Barra lateral
- **WHEN** o teste de contraste avalia o texto, o rótulo de seção, os ícones e o símbolo do IF sobre o verde claro da barra lateral
- **THEN** o texto e o rótulo têm pelo menos 4,5:1, e os ícones e o verde do símbolo pelo menos 3:1

#### Scenario: Borda de campo
- **WHEN** o teste de contraste avalia a borda de controle sobre a superfície
- **THEN** o contraste calculado é de pelo menos 3:1

### Requirement: Estado indicado por texto e forma
Nenhuma informação de estado DEVE (MUST) depender só da cor. Selos de estado DEVEM (MUST) conter a palavra do estado e um ícone, e as mensagens do sistema DEVEM (MUST) conter o texto, um ícone e o papel ARIA adequado (`alert` para erro e aviso, `status` para sucesso e informação). Ícones que acompanham texto DEVEM (MUST) ser decorativos para tecnologias assistivas (`aria-hidden="true"`). Ícones NÃO DEVEM (MUST NOT) aparecer ao lado de títulos.

#### Scenario: Situação do usuário na lista
- **WHEN** a lista de usuários mostra um usuário ativo e um inativo
- **THEN** cada linha mostra um selo com a palavra "Ativo" ou "Inativo" e um ícone, com ícones diferentes para os dois estados

#### Scenario: Mensagem de erro de operação
- **WHEN** uma operação é recusada e a mensagem de erro é exibida
- **THEN** a mensagem tem `role="alert"`, um ícone com `aria-hidden="true"` e o texto do erro

#### Scenario: Mensagem de sucesso
- **WHEN** um usuário é desativado
- **THEN** a mensagem de sucesso tem `role="status"`, um ícone e o texto

### Requirement: Identidade institucional
A barra lateral e a barra do topo no celular DEVEM (MUST) exibir o símbolo oficial do IF, recortado da versão colorida RGB sem alteração de cor, ao lado do nome do sistema, "SaliSpace", em texto, numa única linha e num link para a página inicial. A barra lateral NÃO DEVE (MUST NOT) repetir o nome do campus, que aparece na página de login. O painel da página de login DEVE (MUST) exibir o logo horizontal completo na versão negativa oficial, derivado da versão negativa RGB, sem outra cor além do branco, com a arte em pelo menos 48 px de altura, sem distorção e com texto alternativo que identifique a instituição. A fonte da interface DEVE (MUST) ser a Open Sans, servida pelo próprio sistema junto com o arquivo da licença. Nenhuma página DEVE (MUST) depender de requisição a servidor externo para fonte, ícone, estilo ou script.

#### Scenario: Barra lateral
- **WHEN** um usuário autenticado abre qualquer página
- **THEN** a barra lateral contém o símbolo do IF e o texto "SaliSpace", num link para a página inicial

#### Scenario: Página de login
- **WHEN** um visitante abre a página de login
- **THEN** a página exibe o painel da marca com o logo negativo, o nome do sistema e o formulário com o título "Entrar"

#### Scenario: Sem recursos externos
- **WHEN** qualquer página é renderizada
- **THEN** todos os endereços de folhas de estilo, fontes, imagens e scripts, inclusive o do htmx, são relativos ao próprio sistema

### Requirement: Layout base e navegação responsivos
Todas as páginas autenticadas DEVEM (MUST) estender um único layout com barra lateral de navegação, cabeçalho, área de mensagens e conteúdo principal, marcados com os elementos `aside`, `nav`, `header` e `main`, e com um link para pular direto ao conteúdo. O cabeçalho DEVE (MUST) ter a trilha de navegação até a página atual e o menu do usuário, com o nome, o perfil e a ação "Sair". Cada página DEVE (MUST) ter um `h1` com uma descrição e, quando houver, a ação principal. O layout DEVE (MUST) funcionar a partir de 360 px de largura sem rolagem horizontal da página. Abaixo de 1024 px, a barra lateral DEVE (MUST) dar lugar a uma barra no topo com o botão "Menu", que dê acesso à navegação e ao botão "Sair" sem depender de JavaScript. O item de navegação da seção atual DEVE (MUST) ter `aria-current="page"` e uma indicação visual que não dependa só da cor. A navegação DEVE (MUST) mostrar só os itens liberados pelas permissões do usuário. As páginas de login e de recuperação de senha DEVEM (MUST) usar um layout sem navegação, com o painel da marca ao lado do formulário a partir de 1024 px e acima dele em larguras menores.

#### Scenario: Item atual na lista de usuários
- **WHEN** um usuário com a permissão de visualizar usuários abre a lista de usuários
- **THEN** o item "Usuários" da navegação tem `aria-current="page"` e a trilha de navegação termina em "Usuários"

#### Scenario: Navegação sem a permissão
- **WHEN** um usuário sem a permissão de visualizar perfis abre qualquer página
- **THEN** a navegação não contém o item "Perfis"

#### Scenario: Menu do usuário
- **WHEN** um usuário autenticado abre qualquer página
- **THEN** o cabeçalho mostra as iniciais do usuário, e o menu aberto por elas mostra o nome, o perfil e o botão "Sair", que encerra a sessão por POST, e fecha com um clique fora dele ou com Esc

#### Scenario: Link para o conteúdo
- **WHEN** qualquer página é renderizada
- **THEN** o primeiro elemento focável é um link "Ir para o conteúdo" que aponta para o `main`

#### Scenario: Menu no celular
- **WHEN** a página é exibida com 360 px de largura
- **THEN** a navegação e o botão "Sair" ficam recolhidos atrás do botão "Menu" e são exibidos ao acioná-lo, mesmo com o JavaScript desligado

### Requirement: Interação acessível
Todo elemento interativo DEVE (MUST) ter indicador de foco visível ao navegar pelo teclado, e DEVE (MUST) ter área de toque de pelo menos 44x44 px, exceto links dentro de texto corrido, isentos pelo critério 2.5.8 da WCAG 2.2. Um botão só com ícone DEVE (MUST) ter `aria-label` com o nome da ação e uma dica visível com o mesmo texto, exibida ao passar o mouse e ao receber foco pelo teclado. Abaixo de 640 px, esse texto DEVE (MUST) aparecer junto do ícone, exceto nas listas compactas, em que as ações da linha ficam no menu "Mais ações" com o texto de cada uma. Os ícones DEVEM (MUST) ser da biblioteca Lucide, e emojis NÃO DEVEM (MUST NOT) ser usados como ícone. Todo campo de formulário DEVE (MUST) ter rótulo visível associado, e a ajuda e os erros do campo DEVEM (MUST) estar associados a ele por `aria-describedby`. Um campo com erro DEVE (MUST) ter `aria-invalid="true"` e mostrar a mensagem de erro em texto junto dele. Campos opcionais DEVEM (MUST) ter a indicação "(opcional)" no rótulo.

#### Scenario: Botão de editar na linha
- **WHEN** a lista de usuários é exibida para quem pode editar
- **THEN** cada linha tem um botão com o ícone de lápis, `aria-label="Editar"` e um elemento `role="tooltip"` com o texto "Editar"

#### Scenario: Campo com erro
- **WHEN** o formulário de cadastro de usuário é enviado com o e-mail vazio
- **THEN** o campo de e-mail tem `aria-invalid="true"` e `aria-describedby` apontando para o elemento com a mensagem de erro

#### Scenario: Campo opcional
- **WHEN** o formulário de criação de perfil é exibido
- **THEN** o rótulo do campo Descrição termina com "(opcional)"

### Requirement: Componentes base e ações em modal
Todas as telas DEVEM (MUST) usar os componentes base definidos no design: botão primário para a ação principal da tela (no máximo um por tela), botão secundário, botão destrutivo, botão de ícone, menu suspenso "Mais ações", campos renderizados pelo renderizador de formulários do projeto, cartão, tabela com versão empilhada, selo de estado, mensagens e modal. Toda ação de gestão (cadastrar, editar, trocar perfil, desativar e reativar usuário; criar, editar, alterar permissões e excluir perfil) DEVE (MUST) abrir num modal sobre a tela atual, com o conteúdo renderizado pelo servidor. Sem JavaScript, a URL da ação DEVE (MUST) exibir o mesmo conteúdo como página, com o mesmo formulário e o mesmo POST. Um erro de validação DEVE (MUST) manter o modal aberto com as mensagens, e o sucesso DEVE (MUST) recarregar a tela de origem com a mensagem de sucesso. O modal DEVE (MUST) prender o foco, fechar com Esc, pelo botão de ícone "Fechar" ou pelo botão "Fechar", e devolver o foco ao botão que o abriu. Abaixo de 640 px, cada linha de tabela DEVE (MUST) virar um bloco com cada valor precedido do rótulo da sua coluna. A lista de usuários é uma lista compacta: abaixo de 640 px, cada linha DEVE (MUST) mostrar o nome e o e-mail, uma linha de resumo com o perfil e o selo de situação, sem rótulos de coluna, e um único botão "Mais ações" com todas as ações permitidas ao usuário, com área de toque de 44x44 px. Estados vazios DEVEM (MUST) mostrar o fato em texto, sem ilustração. Cartões NÃO DEVEM (MUST NOT) ser aninhados.

#### Scenario: Abertura do modal pelo htmx
- **WHEN** a rota de desativação de um usuário recebe um GET com o cabeçalho `HX-Request`
- **THEN** a resposta contém só o fragmento do modal, com o título "Desativar <nome>?", o botão destrutivo "Desativar usuário" e o botão "Fechar"

#### Scenario: Mesma rota sem JavaScript
- **WHEN** a rota de desativação de um usuário recebe um GET sem o cabeçalho `HX-Request`
- **THEN** a resposta é a página completa, com o layout e o mesmo conteúdo do modal

#### Scenario: Erro no cadastro pelo modal
- **WHEN** o formulário de cadastro é enviado pelo htmx com um e-mail já usado
- **THEN** a resposta é o fragmento do modal com a mensagem de erro no campo, e nenhum usuário é criado

#### Scenario: Sucesso no cadastro pelo modal
- **WHEN** o formulário de cadastro é enviado pelo htmx com dados válidos
- **THEN** o usuário é criado e a resposta tem o cabeçalho `HX-Redirect` para a lista de usuários

#### Scenario: Tabela no celular
- **WHEN** a lista de usuários é exibida com 360 px de largura
- **THEN** cada usuário aparece como um bloco com os rótulos "Perfil" e "Situação" antes dos valores, e os botões de ação mostram o ícone e o texto

#### Scenario: Estado vazio
- **GIVEN** um perfil personalizado sem nenhuma permissão concedida
- **WHEN** a página de detalhe desse perfil é exibida
- **THEN** a seção de permissões mostra o texto "Este perfil não concede nenhuma permissão." e nenhuma imagem

