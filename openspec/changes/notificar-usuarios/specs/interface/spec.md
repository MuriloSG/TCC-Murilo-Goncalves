## ADDED Requirements

### Requirement: Seleção de vários valores no componente de seleção
O componente de seleção DEVE (MUST) aceitar a escolha de vários valores no mesmo campo, com o mesmo gatilho, o mesmo painel, a mesma busca e a mesma exibição de 10 opções por vez da escolha de um valor só. Os valores escolhidos DEVEM (MUST) aparecer dentro do próprio campo, como pastilhas, cada uma com um controle que a retira, com o nome do valor no rótulo acessível desse controle. O campo DEVE (MUST) crescer em altura conforme as pastilhas ocupam mais de uma linha, sem cortar nenhuma e sem rolagem horizontal. Enquanto nada estiver escolhido, o campo DEVE (MUST) mostrar o texto que convida a escolher, e a quantidade de escolhidos DEVE (MUST) continuar disponível no nome acessível do campo. Um campo de vários valores PODE (MAY) usar fonte paginada no servidor. Escolher uma opção NÃO DEVE (MUST NOT) fechar o painel, e cada opção escolhida DEVE (MUST) ser marcada na lista por sinal visível, e não só pela cor. O campo enviado ao servidor DEVE (MUST) continuar sendo o `select` nativo com vários valores, com o mesmo nome e os mesmos valores que ele enviaria. Sem JavaScript, o campo DEVE (MUST) ser o `select` nativo de vários valores, com todas as opções e o mesmo envio. Os controles DEVEM (MUST) ter área de toque de pelo menos 44x44 px.

#### Scenario: Escolha de vários valores
- **GIVEN** o campo de usuários da publicação de notificações
- **WHEN** o usuário abre a lista e escolhe dois usuários
- **THEN** os dois aparecem marcados na lista, o painel continua aberto e o gatilho informa "2 usuários escolhidos"

#### Scenario: Valores escolhidos dentro do campo
- **GIVEN** dois usuários escolhidos
- **WHEN** o campo é exibido
- **THEN** os dois aparecem como pastilhas dentro do campo, cada uma com o controle que a retira, cujo rótulo acessível traz o nome do usuário

#### Scenario: Campo cresce com as escolhas
- **GIVEN** um campo com largura para três pastilhas por linha
- **WHEN** sete valores são escolhidos
- **THEN** o campo passa a ocupar as linhas necessárias, com todas as pastilhas visíveis e sem rolagem horizontal

#### Scenario: Retirar um valor escolhido
- **GIVEN** dois usuários escolhidos
- **WHEN** o usuário aciona o controle que retira o primeiro
- **THEN** ele sai dos escolhidos, o gatilho informa "1 usuário escolhido" e o campo enviado fica só com o segundo

#### Scenario: Campo de vários valores sem JavaScript
- **WHEN** a mesma tela é aberta com o JavaScript desligado
- **THEN** o campo é o `select` nativo de vários valores, com todas as opções, e o envio do formulário funciona igual

## MODIFIED Requirements

### Requirement: Layout base e navegação responsivos
Todas as páginas autenticadas DEVEM (MUST) estender um único layout com barra lateral de navegação, cabeçalho, área de mensagens e conteúdo principal, marcados com os elementos `aside`, `nav`, `header` e `main`, e com um link para pular direto ao conteúdo. O cabeçalho DEVE (MUST) ter a trilha de navegação até a página atual, o sino de notificações e o menu do usuário, com o nome, o perfil e a ação "Sair", nessa ordem. O sino DEVE (MUST) exibir a contagem de notificações não lidas do usuário autenticado quando ela for maior que zero, informá-la também no nome acessível do controle e abrir o painel com as notificações mais recentes dele, conforme a spec `notificacoes`. O conteúdo do sino e do painel DEVE (MUST) vir das notificações do usuário autenticado, e NÃO DEVE (MUST NOT) haver notificação de exemplo no código nem na tela. A contagem e a lista DEVEM (MUST) passar a mostrar uma notificação nova sem que o usuário recarregue a página, conforme a spec `notificacoes`. Sem JavaScript, o sino DEVE (MUST) continuar abrindo o painel e DEVE (MUST) levar à página de notificações. Cada página DEVE (MUST) ter um `h1` com uma descrição e, quando houver, a ação principal. O layout DEVE (MUST) funcionar a partir de 360 px de largura sem rolagem horizontal da página. Abaixo de 1024 px, a barra lateral DEVE (MUST) dar lugar a uma barra no topo com o botão "Menu", que dê acesso à navegação e ao botão "Sair" sem depender de JavaScript. O item de navegação da seção atual DEVE (MUST) ter `aria-current="page"` e uma indicação visual que não dependa só da cor. A navegação DEVE (MUST) mostrar só os itens liberados pelas permissões do usuário. As páginas de login e de recuperação de senha DEVEM (MUST) usar um layout sem navegação, com o painel da marca ao lado do formulário a partir de 1024 px e acima dele em larguras menores.

#### Scenario: Item atual na lista de usuários
- **WHEN** um usuário com a permissão de visualizar usuários abre a lista de usuários
- **THEN** o item "Usuários" da navegação tem `aria-current="page"` e a trilha de navegação termina em "Usuários"

#### Scenario: Navegação sem a permissão
- **WHEN** um usuário sem a permissão de visualizar perfis abre qualquer página
- **THEN** a navegação não contém o item "Perfis"

#### Scenario: Sino de notificações no cabeçalho
- **GIVEN** um usuário autenticado com 2 notificações não lidas
- **WHEN** ele abre qualquer página autenticada
- **THEN** o cabeçalho mostra o sino antes do menu do usuário, com a contagem 2 e o nome acessível informando 2 não lidas

#### Scenario: Painel com as notificações do usuário
- **GIVEN** o mesmo usuário
- **WHEN** ele abre o painel de notificações
- **THEN** o painel lista as notificações dele, da mais recente para a mais antiga, marcando as não lidas por texto e por forma, e oferece o acesso à página de notificações

#### Scenario: Notificação nova sem recarregar
- **GIVEN** um usuário com a página aberta e o sino mostrando 3
- **WHEN** uma notificação é criada para ele
- **THEN** o sino passa a mostrar 4 sem que ele recarregue a página

#### Scenario: Painel sem notificação de exemplo
- **GIVEN** um usuário autenticado sem nenhuma notificação
- **WHEN** ele abre o painel
- **THEN** o painel informa em texto que não há notificações, sem nenhum título, mensagem ou data de exemplo

#### Scenario: Menu do usuário
- **WHEN** um usuário autenticado abre qualquer página
- **THEN** o cabeçalho mostra as iniciais do usuário, e o menu aberto por elas mostra o nome, o perfil e o botão "Sair", que encerra a sessão por POST, e fecha com um clique fora dele ou com Esc

#### Scenario: Link para o conteúdo
- **WHEN** qualquer página é renderizada
- **THEN** o primeiro elemento focável é um link "Ir para o conteúdo" que aponta para o `main`

#### Scenario: Menu no celular
- **WHEN** a página é exibida com 360 px de largura
- **THEN** a navegação e o botão "Sair" ficam recolhidos atrás do botão "Menu" e são exibidos ao acioná-lo, mesmo com o JavaScript desligado


## MODIFIED Requirements

### Requirement: Fonte de opções paginada no servidor
Um campo PODE (MAY) declarar que as opções vêm de uma fonte paginada no servidor, escolha ele um valor ou vários. Nesse caso, a página do formulário NÃO DEVE (MUST NOT) conter todas as opções: DEVE (MUST) conter apenas as opções escolhidas e a primeira página. As demais DEVEM (MUST) ser buscadas numa rota de opções, que DEVE (MUST) aceitar os parâmetros de busca e de página, devolver no máximo 10 opções por página, no mesmo formato para qualquer fonte, e informar se há mais páginas. A busca DEVE (MUST) ser aplicada no servidor, sobre a fonte inteira, e não sobre a página carregada. Um campo obrigatório de formulário NÃO DEVE (MUST NOT) usar fonte paginada, porque sem JavaScript ele ficaria limitado à primeira página; um campo exigido somente quando outro campo tem determinado valor PODE (MAY) usá-la, desde que as demais formas de preencher a tela continuem completas sem JavaScript e a limitação fique registrada no design. As rotas de opções DEVEM (MUST) exigir autenticação e a permissão declarada na view, conforme a spec `controle-acesso`.

#### Scenario: Página do formulário sem a lista inteira
- **GIVEN** uma fonte paginada com 300 opções
- **WHEN** a tela que usa o campo é renderizada
- **THEN** o HTML contém as opções escolhidas e no máximo 10 opções

#### Scenario: Busca no servidor
- **GIVEN** uma fonte paginada com 300 opções, das quais 3 contêm "silva"
- **WHEN** a busca "silva" é feita no campo
- **THEN** a rota de opções devolve as 3 opções correspondentes, e não só as que já estavam carregadas

#### Scenario: Páginas seguintes
- **WHEN** a segunda página da rota de opções é pedida
- **THEN** ela devolve as 10 opções seguintes e a indicação de que há mais, quando houver

#### Scenario: Campo de vários valores com fonte paginada
- **GIVEN** o campo de usuários da publicação de notificações, com 300 usuários ativos e 2 escolhidos
- **WHEN** a tela é renderizada
- **THEN** o HTML contém os 2 escolhidos e no máximo 10 opções
- **AND** as demais chegam pela rota de opções, 10 por vez, com a busca feita no servidor
