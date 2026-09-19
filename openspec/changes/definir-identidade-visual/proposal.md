## Why

A Constitution (P1, P8) e o TCC (3.3.1) definem que a apresentação usa os templates do Django com o Tailwind CSS, para manter a consistência visual entre as telas e permitir ajustes visuais sem mexer em views ou models. O RNF04 e o RNF05 pedem acesso por navegador em dispositivos variados e usabilidade para docentes com familiaridade tecnológica variada. Hoje as 16 telas de `accounts` são HTML sem CSS: não há identidade do IFNMG, foco visível, alvo de toque adequado nem layout para celular. Esta Change traz o Tailwind, define a identidade visual com escala fechada de tokens e aplica o visual às telas que já existem, antes que os módulos de espaços e reservas criem novas telas.

Depende da Change `definir-texto-da-interface`, que cria o app `ui` e a verificação do texto.

## What Changes

- **Tailwind CSS 4.3.3** compilado por um serviço Node no Docker Compose, com `package.json` e `package-lock.json` de versões exatas, subindo junto no `make up`, e o alvo `make css` para gerar o CSS minificado.
- **Cores da marca** extraídas dos pixels dos logos RGB oficiais do campus (verde #309F41, vermelho #CF171F, grafite #242021), sem manual de identidade disponível. As escalas 50 a 900 são derivadas em OKLCH. O vermelho da marca só aparece dentro do símbolo do IF.
- **Escala fechada de tokens**: cores com função definida (marca, ação, estado, texto), espaçamentos, raios, sombra, tamanhos de fonte e pontos de quebra. A paleta padrão do Tailwind fica desligada.
- **Contraste AA** verificado por teste para cada par de tokens de texto e fundo e para cada borda de controle.
- **Estado nunca só pela cor**: selos com texto e ícone, e mensagens com texto, ícone e papel ARIA.
- **Símbolo oficial do IF** na barra lateral e na barra do celular, ao lado do nome do sistema em texto, e **logo horizontal na versão negativa oficial** no painel verde do login. É um PNG com transparência, derivado do JPG RGB negativo, com a arte em pelo menos 48 px de altura.
- **Open Sans** (SIL OFL 1.1) servida pelo próprio projeto, sem CDN.
- **Ícones Lucide** (ISC), só os usados, em SVG inline.
- **Layout** com barra lateral em verde claro (símbolo do IF, nome do sistema, "Menu principal", itens com ícone verde e item atual em bloco verde), cabeçalho com trilha de navegação e menu do usuário, e barra no topo com botão "Menu" abaixo de 1024 px. O login em duas colunas (painel da marca e formulário) é mantido.
- **Componentes base**: botões primário, secundário e destrutivo com ícone e cantos de 12 px, botões só com ícone Lucide nas ações de linha (dica ao passar o mouse e ao focar, e texto visível no celular), menu "Mais ações", campos, cartão de listagem com contador e rodapé, tabela com avatar de iniciais e versão empilhada abaixo de 640 px, selo em pílula e mensagens.
- **Ações em modal**: cadastrar, editar, trocar perfil, desativar, reativar, criar e editar perfil, alterar permissões e excluir perfil abrem em modal renderizado pelo servidor e carregado pelo htmx. Sem JavaScript, as mesmas URLs abrem como páginas.
- **Acessibilidade**: foco visível, alvos de toque de 44x44 px e layout funcional a partir de 360 px.
- **Aplicação do visual** às 16 telas de `accounts`, com o `base.html` movido para o app `ui`.
- **Teste de valores soltos**: `style=`, valores arbitrários do Tailwind e classes fora da escala de tokens nos templates fazem a suíte falhar.
- **Prévia visual** (`previa.html`, nesta pasta) para aprovação antes da implementação.

### Fora do escopo

- Tema escuro. Não entra agora e não recebe código preparatório. Os tokens semânticos facilitam uma Change futura.
- Agenda, selos de solicitação de reserva e estados de horário (disponível, ocupado). O design define as cores e a forma deles para as Changes de disponibilidade e reservas, mas nenhum componente é criado sem tela que o use.
- Testes visuais automatizados em navegador.
- Busca e filtro da lista de usuários: a interface é desenhada aqui, e o comportamento fica na Change `filtrar-lista-de-usuarios`.
- Sino de notificações, item "Espaços" e grupo "Administração" da tela de referência, que não existem no sistema.

## Capabilities

### New Capabilities
- `interface`: identidade visual e componentes base das telas: tokens, cores com função e contraste, estados, logo, fonte, layout e navegação responsivos, interação acessível, componentes e a verificação automática de contraste e de valores soltos.

### Modified Capabilities
- `ambiente-desenvolvimento`: o Docker Compose passa a ter o serviço de compilação do CSS, as dependências passam a incluir as de Node.js (só para o build do CSS) em `package.json` e `package-lock.json`, e o `Makefile` ganha os alvos `css` e `npm`.

## Impact

- **Código novo no app `ui`:** `templates/base.html`, `templates/ui/layouts/`, `templates/ui/components/`, `templates/ui/forms/`, `templates/ui/icons/`, `templatetags/`, `views.py` (`ModalView`), `styles/app.css` (fonte do Tailwind com os tokens), `static/ui/` (fontes, logo, htmx, `modal.js` e o CSS gerado, este fora do git), `contrast.py`, `class_rules.py` e os testes.
- **Código alterado:** todos os templates de `accounts`, com `accounts/templates/base.html` removido. As classes base `OperationFormView` e `ConfirmedActionView` passam a herdar de `ModalView`, sem mudar as views concretas. `settings.py` ganha `FORM_RENDERER`, `django.forms`, `django_htmx` e o `HtmxMiddleware`.
- **Ambiente:** `Dockerfile` com um estágio `tailwind` (Node), `compose.yaml` com o serviço `tailwind`, `Makefile`, `package.json`, `package-lock.json`, `.gitignore` e `README.md`.
- **Dependências novas:** `tailwindcss` e `@tailwindcss/cli` 4.3.3, via npm (a imagem `node` só é usada no build do CSS), e `django-htmx` 1.29.0, via pip. Open Sans 5.3.0, Lucide 1.47.0 e htmx 2.0.10 (0BSD) entram como arquivos versionados, com as licenças.
- **Sem mudança** em models, URLs, regras de negócio ou regras de acesso.

## Alinhamento com o TCC

- **3.3.1 e P1:** templates do Django combinados ao Tailwind CSS, exatamente como previsto.
- **P8 e RNF05:** a escala fechada de tokens e os componentes compartilhados garantem a consistência visual. O teste de valores soltos impede que uma tela fuja da escala.
- **RNF04 e P7:** o layout a partir de 360 px e os alvos de toque de 44 px atendem aos dispositivos variados dos docentes. A fonte e os ícones servidos pelo projeto funcionam em rede instável, sem depender de terceiros.
- **Seção 2.3.8:** a visibilidade do estado do sistema aparece nos selos e nas mensagens, sempre com texto. A prevenção de erros aparece no destaque visual das ações destrutivas e na página de confirmação.
- **P10:** não há dependência de serviços externos em tempo de execução. Fonte, ícones, htmx e CSS são servidos pelo próprio sistema.
- **P2 (MTV):** os modais continuam sendo templates renderizados pelas views do Django. O htmx só troca o HTML na página, sem lógica no navegador.
