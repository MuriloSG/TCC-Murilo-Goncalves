## MODIFIED Requirements

### Requirement: Identidade institucional
O nome do sistema exibido DEVE (MUST) ser "IFAgenda", e o nome por extenso, quando necessário, "Sistema de Agendamento de Espaços do IFNMG – Campus Salinas". A barra lateral e a barra do topo no celular DEVEM (MUST) exibir o símbolo oficial do IF, recortado da versão colorida RGB sem alteração de cor, ao lado do nome do sistema em texto, numa única linha e num link para a página inicial. Na barra lateral, esse texto DEVE (MUST) ser "Agenda", porque o símbolo ao lado já traz o IF; nos demais pontos ele DEVE (MUST) ser "IFAgenda". A barra lateral NÃO DEVE (MUST NOT) repetir o nome do campus, que aparece na página de login. O título de toda página DEVE (MUST) terminar com o nome do sistema. O painel da página de login DEVE (MUST) exibir o logo horizontal completo na versão negativa oficial, derivado da versão negativa RGB, sem outra cor além do branco, com a arte em pelo menos 48 px de altura, sem distorção e com texto alternativo que identifique a instituição. A fonte da interface DEVE (MUST) ser a Open Sans, servida pelo próprio sistema junto com o arquivo da licença. Nenhuma página DEVE (MUST) depender de requisição a servidor externo para fonte, ícone, estilo ou script.

#### Scenario: Barra lateral
- **WHEN** um usuário autenticado abre qualquer página
- **THEN** a barra lateral contém o símbolo do IF e o texto "Agenda", num link para a página inicial

#### Scenario: Página de login
- **WHEN** um visitante abre a página de login
- **THEN** a página exibe o painel da marca com o logo negativo, o nome do sistema e o formulário com o título "Entrar"

## ADDED Requirements

### Requirement: Ícone do sistema
Toda página DEVE (MUST) declarar o ícone do sistema no `base.html`, de modo que ele valha para as páginas autenticadas, a página de login, a recuperação de senha e o calendário público, sem repetição em cada layout. O ícone DEVE (MUST) ser derivado do símbolo oficial do IF já usado na barra lateral, centrado num quadrado com margem, sem alteração de cor e sem redesenho da marca. O sistema DEVE (MUST) servir um `favicon.ico` com as versões de 16, 32 e 48 px, um PNG de 512 px e um `apple-touch-icon` de 180 px, todos a partir dos arquivos estáticos do próprio projeto. O `apple-touch-icon` DEVE (MUST) ter fundo branco, porque o sistema operacional não respeita transparência nesse ícone. Nenhuma página DEVE (MUST) referenciar arquivo de ícone inexistente nem servidor externo.

#### Scenario: Página autenticada
- **WHEN** um usuário autenticado abre qualquer página
- **THEN** o `<head>` declara `favicon.ico`, o PNG de 512 px e o `apple-touch-icon`, servidos pelos arquivos estáticos do projeto

#### Scenario: Página de login e calendário público
- **WHEN** um visitante abre a página de login ou o calendário público
- **THEN** o `<head>` declara os mesmos ícones, herdados do `base.html`
