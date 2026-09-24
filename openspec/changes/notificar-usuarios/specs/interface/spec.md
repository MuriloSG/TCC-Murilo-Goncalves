## ADDED Requirements

### Requirement: Seleção de vários valores no componente de seleção
O componente de seleção DEVE (MUST) aceitar a escolha de vários valores no mesmo campo, com o mesmo gatilho, o mesmo painel, a mesma busca e a mesma exibição de 10 opções por vez da escolha de um valor só. O gatilho DEVE (MUST) informar quantos valores estão escolhidos, e o componente DEVE (MUST) listar os valores escolhidos abaixo do campo, cada um com um controle que o retira, com o nome da ação no rótulo acessível. Escolher uma opção NÃO DEVE (MUST NOT) fechar o painel, e cada opção escolhida DEVE (MUST) ser marcada na lista por sinal visível, e não só pela cor. O campo enviado ao servidor DEVE (MUST) continuar sendo o `select` nativo com vários valores, com o mesmo nome e os mesmos valores que ele enviaria. Sem JavaScript, o campo DEVE (MUST) ser o `select` nativo de vários valores, com todas as opções e o mesmo envio. Os controles DEVEM (MUST) ter área de toque de pelo menos 44x44 px.

#### Scenario: Escolha de vários valores
- **GIVEN** o campo de usuários da publicação de notificações
- **WHEN** o usuário abre a lista e escolhe dois usuários
- **THEN** os dois aparecem marcados na lista, o painel continua aberto e o gatilho informa "2 usuários escolhidos"

#### Scenario: Valores escolhidos abaixo do campo
- **GIVEN** dois usuários escolhidos
- **WHEN** o campo é exibido
- **THEN** os dois aparecem abaixo dele, cada um com o controle que o retira, cujo rótulo acessível traz o nome do usuário

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

