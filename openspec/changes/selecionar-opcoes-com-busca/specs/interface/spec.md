## ADDED Requirements

### Requirement: Componente de seleção de opções
Todo campo de escolha de um valor entre opções DEVE (MUST) usar um único componente de seleção do projeto, em qualquer tela. O componente DEVE (MUST) exibir o rótulo da opção escolhida num gatilho e abrir a lista de opções ancorada ao campo, com a largura dele e logo abaixo dele, desenhada com os tokens e os componentes do projeto. A lista NÃO DEVE (MUST NOT) ser a lista do sistema operacional, nem ocupar a tela inteira em nenhuma largura. Escolher uma opção DEVE (MUST) fechar a lista, exibir o rótulo escolhido no gatilho e registrar o valor no campo enviado ao servidor, com o mesmo nome e o mesmo valor que o `select` nativo enviaria. Sem JavaScript, o campo DEVE (MUST) ser o `select` nativo, com as mesmas opções, o mesmo nome e o mesmo envio do formulário. O componente DEVE (MUST) funcionar dentro de um modal e a partir de 360 px de largura, sem rolagem horizontal da página.

#### Scenario: Lista ancorada no campo
- **WHEN** um usuário abre o campo de perfil no cadastro de usuário
- **THEN** a lista aparece abaixo do campo, com a largura dele, e não como uma janela do sistema operacional

#### Scenario: Escolha registrada no campo enviado
- **GIVEN** a lista aberta no campo de perfil
- **WHEN** o usuário escolhe "Docente" e envia o formulário
- **THEN** o servidor recebe o mesmo valor que receberia do `select` nativo, e o cadastro segue a spec `gestao-usuarios`

#### Scenario: Campo sem JavaScript
- **WHEN** a mesma tela é aberta com o JavaScript desligado
- **THEN** o campo é o `select` nativo, com todas as opções da fonte fixa, e o envio do formulário funciona igual

#### Scenario: Seleção dentro de um modal
- **WHEN** o campo de perfil é aberto no modal de troca de perfil, com 360 px de largura
- **THEN** a lista aparece ancorada ao campo, dentro do modal, sem rolagem horizontal da página

### Requirement: Busca e exibição de 10 opções por vez
A lista de opções DEVE (MUST) exibir no máximo 10 opções por vez, e as demais DEVEM (MUST) ser carregadas ao rolar a lista até o fim e pelo controle "Mostrar mais". Quando a fonte tiver mais opções do que uma página, a lista DEVE (MUST) oferecer um campo de busca, que filtra por trecho do rótulo, sem diferenciar maiúsculas de minúsculas nem acentos. Quando nenhuma opção corresponder à busca, a lista DEVE (MUST) informar isso em texto. O campo de busca NÃO DEVE (MUST NOT) aparecer quando a fonte couber em uma página. A quantidade de opções por página DEVE (MUST) ser definida num único ponto do código.

#### Scenario: Primeiras dez opções
- **GIVEN** um campo com 57 opções
- **WHEN** a lista é aberta
- **THEN** 10 opções são exibidas, com o campo de busca no topo

#### Scenario: Mais opções
- **GIVEN** a lista aberta com as 10 primeiras de 57 opções
- **WHEN** o usuário aciona "Mostrar mais" ou rola a lista até o fim
- **THEN** as 10 seguintes são acrescentadas à lista

#### Scenario: Busca sem acentos
- **GIVEN** um campo com as opções "Coordenação" e "Direção"
- **WHEN** o usuário digita "coordenacao" na busca
- **THEN** só "Coordenação" fica na lista

#### Scenario: Busca sem resultado
- **WHEN** a busca não corresponde a nenhuma opção
- **THEN** a lista informa que nenhuma opção foi encontrada

#### Scenario: Fonte curta sem busca
- **GIVEN** o filtro de situação, com três opções
- **WHEN** a lista é aberta
- **THEN** as três opções são exibidas e não há campo de busca

### Requirement: Fonte de opções paginada no servidor
Um campo PODE (MAY) declarar que as opções vêm de uma fonte paginada no servidor. Nesse caso, a página do formulário NÃO DEVE (MUST NOT) conter todas as opções: DEVE (MUST) conter apenas a opção escolhida e a primeira página. As demais DEVEM (MUST) ser buscadas numa rota de opções, que DEVE (MUST) aceitar os parâmetros de busca e de página, devolver no máximo 10 opções por página, no mesmo formato para qualquer fonte, e informar se há mais páginas. A busca DEVE (MUST) ser aplicada no servidor, sobre a fonte inteira, e não sobre a página carregada. Um campo obrigatório de formulário NÃO DEVE (MUST NOT) usar fonte paginada, porque sem JavaScript ele ficaria limitado à primeira página. As rotas de opções DEVEM (MUST) exigir autenticação e a permissão declarada na view, conforme a spec `controle-acesso`.

#### Scenario: Página do formulário sem a lista inteira
- **GIVEN** uma fonte paginada com 300 opções
- **WHEN** a tela que usa o campo é renderizada
- **THEN** o HTML contém a opção escolhida e no máximo 10 opções

#### Scenario: Busca no servidor
- **GIVEN** uma fonte paginada com 300 opções, das quais 3 contêm "silva"
- **WHEN** a busca "silva" é feita no campo
- **THEN** a rota de opções devolve as 3 opções correspondentes, e não só as que já estavam carregadas

#### Scenario: Páginas seguintes
- **WHEN** a segunda página da rota de opções é pedida
- **THEN** ela devolve as 10 opções seguintes e a indicação de que há mais, quando houver

## MODIFIED Requirements

### Requirement: Componentes base e ações em modal
Todas as telas DEVEM (MUST) usar os componentes base definidos no design: botão primário para a ação principal da tela (no máximo um por tela), botão secundário, botão destrutivo, botão de ícone, menu suspenso "Mais ações", campos renderizados pelo renderizador de formulários do projeto, componente de seleção de opções em todo campo de escolha, cartão, tabela com versão empilhada, selo de estado, mensagens e modal. Toda ação de gestão (cadastrar, editar, trocar perfil, desativar e reativar usuário; criar, editar, alterar permissões e excluir perfil) DEVE (MUST) abrir num modal sobre a tela atual, com o conteúdo renderizado pelo servidor. Sem JavaScript, a URL da ação DEVE (MUST) exibir o mesmo conteúdo como página, com o mesmo formulário e o mesmo POST. Um erro de validação DEVE (MUST) manter o modal aberto com as mensagens, e o sucesso DEVE (MUST) recarregar a tela de origem com a mensagem de sucesso. O modal DEVE (MUST) prender o foco, fechar com Esc, pelo botão de ícone "Fechar" ou pelo botão "Fechar", e devolver o foco ao botão que o abriu. Abaixo de 640 px, cada linha de tabela DEVE (MUST) virar um bloco com cada valor precedido do rótulo da sua coluna. A lista de usuários é uma lista compacta: abaixo de 640 px, cada linha DEVE (MUST) mostrar o nome e o e-mail, uma linha de resumo com o perfil e o selo de situação, sem rótulos de coluna, e um único botão "Mais ações" com todas as ações permitidas ao usuário, com área de toque de 44x44 px. Estados vazios DEVEM (MUST) mostrar o fato em texto, sem ilustração. Cartões NÃO DEVEM (MUST NOT) ser aninhados.

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

#### Scenario: Campo de escolha com o componente
- **WHEN** qualquer tela com campo de escolha é renderizada
- **THEN** o campo usa o componente de seleção de opções do projeto
