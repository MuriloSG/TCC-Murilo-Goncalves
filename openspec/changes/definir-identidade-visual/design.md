## Context

As telas de `accounts` são HTML semântico sem CSS. O `base.html` está em `accounts/templates/` e só tem cabeçalho, uma navegação com o link "Início", o nome do usuário, o botão "Sair" e a lista de mensagens. Cada ação (cadastrar, editar, trocar perfil, desativar, reativar, criar, editar e excluir perfil, alterar permissões) abre uma página própria. O ambiente tem dois serviços no Compose (`web` e `db`), imagem `python:3.13-slim` e nenhuma ferramenta de Node.js. A Change `definir-texto-da-interface`, que vem antes desta, cria o app `ui` com as regras de texto e a verificação dos templates.

As decisões de identidade foram tomadas em entrevista com o autor:

- **Manual de identidade:** não há manual disponível. As cores vêm dos pixels dos logos RGB oficiais.
- **Primária:** o verde da marca, escurecido para ação.
- **Estados:** separados da marca. Disponível é neutro (fundo branco com a palavra). Os demais estados usam uma paleta própria, sempre com texto e ícone.
- **Fonte:** Open Sans servida pelo projeto.
- **Densidade:** corpo em 16 px, tabelas em 14 px, alvos de 44 px, e tabela empilhada abaixo de 640 px.
- **Tema escuro:** não entra agora.
- **Ícones:** Lucide.
- **Build:** Node no container.
- **Escopo:** a fundação mais as telas de `accounts`.

**Primeira revisão da prévia**, a partir de uma tela de login de referência:

- cantos de 12 px em botões e campos;
- login em duas colunas, com painel verde e o logo negativo oficial;
- textos adaptados à seção 9 das convenções: saíram saudação, slogan, "jornada", "você", termos de uso e suporte inexistentes;
- sem ornamentos nem sombra no botão.

**Segunda revisão**, a partir de uma tela de listagem de referência. O autor pediu um visual mais moderno, sem degradê, mantendo o login da primeira revisão:

- **Barra lateral grafite** (#242021) com detalhes verdes, depois trocada pelo verde claro na terceira revisão.
- **Cabeçalho** com trilha de navegação à esquerda e, à direita, o menu do usuário, com avatar de iniciais, nome, perfil e a opção "Sair".
- **Listagem em cartão:**
  - título com contador e descrição;
  - busca e filtro por situação (a Change `filtrar-lista-de-usuarios` implementa a busca);
  - tabela com avatar, nome e e-mail na primeira coluna, e cabeçalhos em maiúsculas pequenas;
  - rodapé "Exibindo X de Y usuários".
- **Ações de linha só com ícone Lucide**, com a dica do nome da ação ao passar o mouse e ao focar pelo teclado. A regra anterior, "ícone nunca é a única forma de informar algo", foi revista pelo autor para essas ações. Abaixo de 640 px, onde não existe "passar o mouse", o texto aparece junto do ícone.
- **Todas as ações em modal**, carregado do servidor com htmx (D16).
- **Omitido da referência** porque não existe no sistema: o sino de notificações (as notificações do TCC são por e-mail, RF09 e RF10), o item "Espaços" (o módulo ainda não existe), o grupo "Administração" na trilha e a marca "if" num quadrado colorido, que não é o logo oficial. Também não entram as cores diferentes por avatar, que seriam cor sem função.

**Terceira revisão**, a pedido do autor:

- **Barra lateral em verde claro** (green-50 #EFFBEF), no lugar do grafite, com a barra do celular no mesmo tom.
- **Símbolo oficial do IF** (os quadrados verdes e o círculo vermelho), no lugar do logo completo, com "Agendamento de espaços" e "IFNMG Campus Salinas" em texto ao lado.
- **Item atual da navegação** em bloco verde (`action`) com texto branco.
- A dica dos botões de ícone ganhou tokens próprios (`tooltip`), porque usava os da barra lateral.

Restrições: cada Change cria só o que usa, tudo roda via `make`, sem comentários `#` e sem `{# #}`, identificadores em inglês e texto em português, e as regras da seção 9 do `openspec/conventions.md`.

## Goals / Non-Goals

**Goals:**

- Identidade do IFNMG Campus Salinas com cores tiradas dos arquivos oficiais, sem valor inventado.
- Escala fechada de tokens semânticos, com verificação automática de contraste e de valores soltos.
- Componentes base usados por todas as telas atuais, sem componente sem uso.
- Ações em modal carregado do servidor, sem perder a URL de cada ação, o CSRF e a regra "GET mostra, POST executa".
- Interface utilizável a partir de 360 px, pelo teclado e pelo toque. Sem JavaScript, as páginas continuam funcionando (D16).
- CSS compilado dentro do Docker, sem Node.js na máquina do desenvolvedor e sem Node.js na execução do Django.

**Non-Goals:**

- Tema escuro.
- Busca e filtro da lista de usuários: a interface deles é desenhada aqui, mas o comportamento fica na Change `filtrar-lista-de-usuarios`.
- Componentes de agenda e de solicitação de reserva. O D7 define as cores e a forma deles para as Changes futuras.
- JavaScript próprio além do htmx e da abertura e do fechamento do modal (D16).
- Teste visual automatizado em navegador. A verificação visual é manual, pela lista da seção 10 das tasks.
- Configuração de arquivos estáticos para produção (`collectstatic`, servidor de estáticos).

## Decisions

### D1. Estrutura do app `ui`

```text
ui/
  text_rules.py                  (Change definir-texto-da-interface)
  forms.py                       FormRenderer do projeto (D11)
  views.py                       ModalView, classe base das views que abrem em modal (D16)
  contrast.py                    pares de contraste e leitura dos tokens (D6)
  class_rules.py                 regras de valores soltos (D13)
  templatetags/
    __init__.py
    ui.py                        nav_link, icon e initials (D10, D12)
  styles/
    app.css                      fonte do Tailwind: tokens (@theme), @font-face e componentes (@layer components)
  static/ui/
    css/app.css                  gerado pelo Tailwind, fora do git
    fonts/                       Open Sans (woff2) e OFL.txt
    img/                         simbolo-if.png e logo-horizontal-negativo.png
    js/                          htmx.min.js, LICENSE-htmx e modal.js (D16)
  templates/
    base.html                    movido de accounts/templates/
    ui/
      layouts/                   app.html (barra lateral e cabeçalho) e auth.html (login)
      components/                messages.html, badge.html, modal.html, confirm_modal.html, row_actions.html
      forms/                     form.html, field.html
      icons/                     SVGs do Lucide e LICENSE
  tests/
```

O `base.html` sai de `accounts` porque passa a ser compartilhado por todos os apps. O `403.html` continua em `accounts`, porque é resposta do `PermissionMiddleware`.

Alternativas consideradas:
- **Manter tudo em `accounts`:** os apps de espaços e reservas passariam a depender de um app de domínio para ter o layout.
- **Diretório de templates do projeto (`DIRS` no settings):** separa os templates dos estáticos, dos testes e das regras que os verificam.

### D2. Build do Tailwind com Node.js no container

O `Dockerfile` ganha um estágio `tailwind`, sem alterar o estágio da aplicação:

```text
FROM node:<versão exata>-slim AS tailwind
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
```

- **`package.json`:** `tailwindcss` e `@tailwindcss/cli` em `4.3.3`, sem `^` nem `~`.
- **`compose.yaml`:** serviço `tailwind` com `build: {context: ., target: tailwind}`, bind mount `.:/app` e um volume anônimo em `/app/node_modules`. O volume preserva as dependências instaladas na imagem, que o bind mount esconderia. O comando é `npx @tailwindcss/cli -i ui/styles/app.css -o ui/static/ui/css/app.css --watch=always`.
- **O que o Tailwind lê:** a detecção automática de fontes do Tailwind 4 percorre o diretório de trabalho (`/app`) e ignora o que está no `.gitignore`. Com isso, lê os templates de todos os apps.
- **`Makefile`:**
  - `up` passa a ser `docker compose up -d --build --renew-anon-volumes`, para que um `package-lock.json` novo seja reinstalado;
  - `css` executa o CLI com `--minify`;
  - `npm` executa `npm $(cmd)` no serviço `tailwind`.
- **CSS gerado:** fica fora do git (`ui/static/ui/css/`). O `web` o serve pelo `runserver`, como qualquer estático de app.
- **Execução do Django:** a imagem da aplicação continua sem Node.js.

Alternativas consideradas:
- **CLI standalone do Tailwind (binário único):** dispensaria o npm, mas exigiria escolher o binário pela arquitetura (arm64 no Mac, x64 no servidor) e conferir o checksum no Dockerfile. O autor escolheu o Node, que é o caminho oficial mais comum e permite adicionar pacotes npm depois.
- **`django-tailwind`:** usa Node.js por baixo do mesmo jeito e acrescenta um app e comandos próprios.
- **`pytailwindcss`:** baixa o binário na primeira execução, o que falha em rede instável e deixa a versão efetiva fora do `requirements.txt`.

### D3. Cores da marca

Extraídas dos 12 JPGs de `sources/Salinas/jpg_RGB/`, todos com perfil ICC sRGB IEC61966-2.1. As versões CMYK (`tif_CMYK/`) não foram usadas para cor de tela.

Método:
- **Fundo:** é a cor mais frequente da imagem, e tudo a até 24 dela (máxima diferença por canal) é descartado.
- **Borda antisserrilhada e ruído do JPEG:** um pixel só é usado se toda a sua vizinhança 5x5 variar no máximo 12 por canal.
- **Agrupamento:** os pixels restantes são agrupados por distância de até 40 do centro do grupo.
- **Valor registrado:** a moda exata do grupo, com a proporção sobre os pixels que não são fundo.

| Cor | Hex | Arquivos | Proporção |
|---|---|---|---|
| Verde | **#309F41** | quadrados de `salinas_horizontal_jpg.jpg` e `salinas_vertical_jpg.jpg`; fundo das versões `*_verde_jpg.jpg` | 32,2% e 31,9% |
| Vermelho | **#CF171F** | círculo de `salinas_horizontal_jpg.jpg`; fundo das versões `*_vermelho_jpg.jpg` | 3,1% |
| Vermelho (divergente) | #CD2026 | círculo de `salinas_vertical_jpg.jpg` | 3,1% |
| Grafite | **#242021** | texto das versões coloridas | 11,0% e 11,2% |
| Cinza | #85868A | versões `*_cinza_jpg.jpg` | 33,6% e 33,1% |
| Quase preto | #050102 | versões preta, cinza e negativa | até 47,2% |

- **Vermelho:** vale o #CF171F, presente em 3 dos 4 arquivos com vermelho, inclusive nas versões de cor chapada. Ele não vira token e só aparece dentro do símbolo do IF, na barra lateral (D8), sem alteração.
- **Grafite #242021:** é a conversão para tela do preto de impressão. Ele é a âncora da escala neutra.
- **Cinza e quase preto:** pertencem a versões monocromáticas que a interface não usa.
- **Se um manual oficial for obtido depois:** os valores dele substituem estes, e o teste de contraste confere as escalas derivadas de novo.

Alternativas consideradas: **valores de memória de manuais da Rede Federal** e **tirar as cores dos TIF CMYK**. Os dois foram descartados. O primeiro não tem fonte verificável. O segundo dependeria de um perfil de conversão para tela que não está nos arquivos.

### D4. Derivação das escalas

- **Verde e neutro:** derivadas em OKLCH a partir da âncora.
  - O matiz é mantido, e a luminosidade segue alvos fixos por degrau: 0,975, 0,945, 0,895, 0,83, 0,745, 0,66, 0,57, 0,49, 0,41 e 0,33, do 50 ao 900.
  - A âncora entra exata no degrau: o verde no 500, por ter a luminosidade mais próxima (0,62), e o grafite no 900.
  - A cromaticidade do verde segue a curva 0,12, 0,25, 0,45, 0,70, 0,90, 1, 1, 0,92, 0,80 e 0,68 relativa à âncora, reduzida só quando sai do gamut sRGB.
  - A cromaticidade do neutro diminui em direção aos claros (0,1 no 50 até 1 no 900). Com a cromaticidade constante do grafite, os tons claros ficavam rosados (#FBF5F6).
- **Âmbar, esmeralda e vermelho de estado:** são os valores exatos das escalas `amber`, `emerald` e `red` do `theme.css` do pacote `tailwindcss` 4.3.3, convertidos de OKLCH para hexadecimal. Não são derivados pelo método acima, porque a paleta do Tailwind varia o matiz entre degraus e redefini-la não traria ganho.

| Escala | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 |
|---|---|---|---|---|---|---|---|---|---|---|
| green | #EFFBEF | #DCF5DD | #BEEABF | #95DC99 | #68C570 | **#309F41** | #198F31 | #047522 | #035B18 | #024210 |
| neutral | #F7F6F7 | #EDECED | #DDDCDC | #C8C7C7 | #AEACAC | #949192 | #797677 | #635F60 | #4D494A | **#242021** |
| amber | #FFFBEB | #FEF3C6 | #FEE685 | #FFD238 | #F9BC11 | #F59E13 | #DA7701 | #B55204 | #953E02 | #7B3306 |
| emerald | #ECFDF5 | #D0FAE5 | #A4F4CF | #5EE9B5 | #0DD295 | #07B981 | #0D9669 | #057857 | #035F46 | #014E3B |
| red | #FEF2F2 | #FFE2E2 | #FECACA | #FEA4A4 | #FF6668 | #FB2C36 | #E40017 | #BE0411 | #9F0712 | #82181A |

O `app.css` define como variáveis `--palette-*` em `:root` só os degraus referenciados por tokens semânticos (D5). Os demais ficam registrados aqui para uso futuro.

Alternativas consideradas:
- **Usar o `green` do Tailwind como primária:** perderia a relação com a marca.
- **Derivar em HSL:** a luminosidade percebida varia muito entre matizes em HSL, e o contraste de cada degrau ficaria imprevisível.

### D5. Tokens semânticos e escala fechada

O `ui/styles/app.css` começa com `@import "tailwindcss"` e, no `@theme`, zera os grupos padrão (`--color-*: initial`, `--spacing-*: initial`, `--text-*: initial`, `--radius-*: initial`, `--shadow-*: initial`, `--font-*: initial`, `--breakpoint-*: initial`, `--container-*: initial`) antes de declarar só os tokens abaixo. Os nomes são em inglês, por serem identificadores de código. Os templates usam só os tokens semânticos, e nunca a paleta.

**Cores**

| Token | Valor | Função |
|---|---|---|
| `sidebar` | green-50 #EFFBEF | marca: barra lateral e barra do topo no celular |
| `sidebar-hover` | green-100 #DCF5DD | hover dos itens da barra lateral |
| `sidebar-border` | green-200 #BEEABF | borda direita da barra lateral e divisórias dentro dela (decorativa) |
| `on-sidebar` | neutral-900 #242021 | texto da barra lateral |
| `on-sidebar-muted` | neutral-700 #635F60 | rótulo "Menu principal", nome do campus e borda do botão Menu |
| `sidebar-accent` | green-700 #047522 | ícones da navegação |
| `tooltip`, `on-tooltip` | neutral-900 #242021, #FFFFFF | dica dos botões de ícone |
| `brand-surface` | green-800 #035B18 | marca: painel do login |
| `on-brand` | #FFFFFF | texto sobre `brand-surface` |
| `on-brand-muted` | green-100 #DCF5DD | texto secundário sobre `brand-surface` |
| `page` | neutral-50 #F7F6F7 | superfície: fundo da página e cabeçalho de tabela |
| `surface` | #FFFFFF | superfície: cabeçalho, cartões, modais, campos, menus e botão Menu |
| `hover` | neutral-100 #EDECED | superfície: hover de botões de ícone e fundo de contadores |
| `divider` | neutral-100 #EDECED | borda decorativa de cartões, linhas de tabela e rodapés |
| `control-border` | neutral-500 #949192 | borda de campo e de botão secundário, sempre sobre `surface` |
| `text` | neutral-900 #242021 | texto principal |
| `text-muted` | neutral-700 #635F60 | texto secundário, ajuda de campo, cabeçalhos de tabela e ícones de ação |
| `on-fill` | #FFFFFF | texto sobre botão primário e destrutivo |
| `action` | green-700 #047522 | ação: botão primário, links e fundo do item atual da navegação |
| `action-hover` | green-800 #035B18 | ação: hover do botão primário e dos links |
| `focus` | green-600 #198F31 | ação: contorno de foco sobre superfícies claras |
| `avatar-bg`, `avatar-text` | green-50 #EFFBEF, green-800 #035B18 | marca: avatar de iniciais, igual para todos os usuários |
| `danger` | red-700 #BE0411 | ação destrutiva: botão, item de menu e texto de erro de campo |
| `danger-hover` | red-800 #9F0712 | hover do botão destrutivo |
| `error-border` | red-600 #E40017 | borda de campo com erro |
| `overlay` | #242021 com 55% de opacidade | fundo atrás do modal, sem desfoque |
| `success-bg`, `success-border`, `success-icon`, `success-text` | emerald-50, 200, 600, 800 | estado: sucesso, Ativo e, no futuro, aprovada |
| `warning-bg`, `warning-border`, `warning-icon`, `warning-text` | amber-50, 200, 600, 800 | estado: aviso e, no futuro, pendente |
| `error-bg`, `error-soft-border`, `error-icon`, `error-text` | red-50, 200, 600, 800 | estado: erro e, no futuro, rejeitada |
| `info-bg`, `info-border`, `info-icon`, `info-text` | neutral-100, 200, 600, 800 | estado: informação, Inativo e, no futuro, cancelada |

- **Bordas de selos e mensagens:** passam a usar o degrau 200, mais claro e decorativo. O estado é identificado pelo texto e pelo ícone, que tem pelo menos 3:1 (D6).
- **Campos:** a borda `control-border` (3,12:1) só é válida sobre `surface`. Por isso campos ficam sempre dentro de cartões, modais ou do formulário do login, nunca direto sobre `page`.

**Espaçamento** (`--spacing-*`)

| Passo | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 11 | 12 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Valor | 0 | 4 px | 8 px | 12 px | 16 px | 20 px | 24 px | 32 px | 40 px | 44 px | 48 px | 64 px |

- O passo 11 existe para o alvo de toque (`min-h-11`, `min-w-11`).
- O passo 12 existe para a altura do logo e dos itens da barra lateral.

**Tipografia**

| Token | Tamanho / altura de linha | Uso |
|---|---|---|
| `text-xs` | 12 px / 16 px | cabeçalhos de tabela e rótulo "Menu principal", em maiúsculas por CSS com espaçamento de letras, dica do botão de ícone e contadores |
| `text-sm` | 14 px / 20 px | e-mail sob o nome, descrições, ajuda de campo, selos e rótulos de campo |
| `text-base` | 16 px / 24 px | corpo, campos, botões e células da tabela |
| `text-lg` | 18 px / 28 px | `h3` |
| `text-xl` | 20 px / 28 px | título de cartão e de modal (`h2`) |
| `text-2xl` | 24 px / 32 px | `h1` no celular |
| `text-3xl` | 32 px / 40 px | `h1` da página a partir de 640 px e nome do sistema no painel do login |

- Família `sans`: "Open Sans", ui-sans-serif, system-ui, sans-serif.
- Pesos: 400 no texto, 600 em rótulos, botões, itens de navegação e nomes, e 700 no `h1` e no avatar.
- **Maiúsculas por CSS:** o texto no template continua em caixa de frase ("Menu principal", "Usuário"), e a regra de maiúsculas do teste de texto vale para o texto-fonte. O `text-transform` é só visual, e leitores de tela leem a palavra normal.

**Raios, sombras, larguras e pontos de quebra**

| Grupo | Tokens |
|---|---|
| Raio | `radius-md` 8 px (dica e itens de menu), `radius-lg` 12 px (botões, campos, itens da barra lateral e menus) e `radius-xl` 16 px (cartões e modais). `radius-full` para selos, contadores e avatares |
| Sombra | só `shadow-overlay` (0 12px 32px, grafite a 18%), exclusiva de camadas flutuantes: modal, menu suspenso e dica. Botões, cartões e campos não têm sombra |
| Largura máxima | `container-modal` 32 rem, `container-form` 40 rem e `container-page` 80 rem |
| Ponto de quebra | `sm` 40 rem (640 px) e `lg` 64 rem (1024 px) |
| Borda | 1 px nos controles e 2 px no contorno de foco e no campo com erro, com deslocamento de 2 px no foco |

Alternativas consideradas:
- **Expor a paleta inteira como utilitários (`bg-green-700`):** a função da cor ficaria implícita na escolha de cada template, e a regra "cor sempre com função" não teria como ser verificada.
- **Manter a escala de espaçamento contínua do Tailwind 4:** qualquer múltiplo de 4 px seria válido, e a escala deixaria de ser fechada.
- **Barra lateral escura (azul-marinho da referência ou grafite da segunda revisão):** o autor preferiu o verde claro. Ele mantém a identidade do IF sem pesar, e o símbolo colorido fica visível sobre ele (3,20:1). No green-100, o símbolo cairia para 2,95:1.
- **Sombras suaves em cartões, como na referência:** a regra 9.6 veta sombras difusas. Os cartões se separam do fundo pela borda `divider` e pelo contraste `surface` sobre `page`.

### D6. Contraste

O `ui/contrast.py` declara `CONTRAST_PAIRS`: tuplas de token de frente, token de fundo, mínimo e descrição. Ele lê do `ui/styles/app.css` as variáveis `--palette-*` e os tokens `--color-*` (que apontam para a paleta com `var()`) e calcula o contraste WCAG 2.x. O teste `ui/tests/test_contrast.py` falha para qualquer par abaixo do mínimo, e também para qualquer token de cor que não esteja em nenhum par nem na lista de isentos.

| Par | Frente / fundo | Contraste | Mínimo |
|---|---|---|---|
| Texto principal / página | #242021 / #F7F6F7 | 14,94:1 | 4,5 |
| Texto principal / superfície | #242021 / #FFFFFF | 16,11:1 | 4,5 |
| Texto secundário / superfície | #635F60 / #FFFFFF | 6,29:1 | 4,5 |
| Texto secundário / página (inclui cabeçalho de tabela) | #635F60 / #F7F6F7 | 5,84:1 | 4,5 |
| Contador / hover | #635F60 / #EDECED | 5,34:1 | 4,5 |
| Placeholder / superfície | #635F60 / #FFFFFF | 6,29:1 | 4,5 |
| Borda de controle / superfície | #949192 / #FFFFFF | 3,12:1 | 3 |
| Ícone de ação / superfície | #635F60 / #FFFFFF | 6,29:1 | 3 |
| Ícone de ação, hover | #242021 / #EDECED | 13,67:1 | 3 |
| Dica do botão de ícone | #FFFFFF / #242021 | 16,11:1 | 4,5 |
| Botão primário | #FFFFFF / #047522 | 5,88:1 | 4,5 |
| Botão primário, hover | #FFFFFF / #035B18 | 8,35:1 | 4,5 |
| Link / superfície | #047522 / #FFFFFF | 5,88:1 | 4,5 |
| Contorno de foco / superfície | #198F31 / #FFFFFF | 4,19:1 | 3 |
| Contorno de foco / página | #198F31 / #F7F6F7 | 3,88:1 | 3 |
| Botão destrutivo | #FFFFFF / #BE0411 | 6,53:1 | 4,5 |
| Botão destrutivo, hover | #FFFFFF / #9F0712 | 8,36:1 | 4,5 |
| Item de menu destrutivo e erro de campo | #BE0411 / #FFFFFF | 6,53:1 | 4,5 |
| Borda de campo com erro | #E40017 / #FFFFFF | 4,87:1 | 3 |
| Barra lateral, texto | #242021 / #EFFBEF | 15,12:1 | 4,5 |
| Barra lateral, hover | #242021 / #DCF5DD | 13,92:1 | 4,5 |
| Barra lateral, rótulo de seção e campus | #635F60 / #EFFBEF | 5,91:1 | 4,5 |
| Barra lateral, ícone | #047522 / #EFFBEF | 5,52:1 | 3 |
| Barra lateral, ícone no hover | #047522 / #DCF5DD | 5,08:1 | 3 |
| Barra lateral, item atual | #FFFFFF / #047522 | 5,88:1 | 4,5 |
| Barra lateral, símbolo verde do IF | #309F41 / #EFFBEF | 3,20:1 | 3 |
| Contorno de foco / barra lateral | #198F31 / #EFFBEF | 3,93:1 | 3 |
| Botão Menu, borda / barra do celular | #635F60 / #EFFBEF | 5,91:1 | 3 |
| Avatar | #035B18 / #EFFBEF | 7,84:1 | 4,5 |
| Painel do login, texto | #FFFFFF / #035B18 | 8,35:1 | 4,5 |
| Painel do login, texto secundário | #DCF5DD / #035B18 | 7,22:1 | 4,5 |
| Sucesso, texto / ícone | #035F46 e #0D9669 / #ECFDF5 | 7,30:1 / 3,57:1 | 4,5 / 3 |
| Aviso, texto / ícone | #953E02 e #DA7701 / #FFFBEB | 6,82:1 / 3,06:1 | 4,5 / 3 |
| Erro, texto / ícone | #9F0712 e #E40017 / #FEF2F2 | 7,64:1 / 4,45:1 | 4,5 / 3 |
| Informação, texto / ícone | #4D494A e #797677 / #EDECED | 7,53:1 / 3,82:1 | 4,5 / 3 |

**Isentos, sem mínimo:**
- `divider` (#EDECED), `sidebar-border` (#BEEABF) e as bordas 200 de selos e mensagens: são decorativas, e nenhuma informação depende delas.
- `overlay`: é o fundo atrás do modal, e o conteúdo do modal fica sobre `surface`.

**Pontos de atenção:**
- A borda de controle (3,12:1) só passa sobre `surface`. Sobre `page` daria 2,90:1, por isso campos nunca ficam direto sobre `page` (D5).
- O ícone do aviso (3,06:1) passa, mas sem margem.
- O símbolo verde do IF sobre a barra lateral (3,20:1) passa com pouca margem. Por isso a barra usa o green-50, e não o green-100.

**Histórico das correções:**
- Texto secundário: na primeira derivação da escala neutra, o neutral-600 era #7B7677 e dava 4,47:1. O texto secundário ficou em neutral-700 (6,29:1).
- O rodapé do modal chegou a ser cinza na prévia, mas a borda do botão "Fechar" daria 2,90:1. O rodapé ficou branco.

### D7. Estados

| Estado | Onde | Forma | Tom | Ícone Lucide |
|---|---|---|---|---|
| Ativo | situação do usuário | selo em pílula | success | `check` |
| Inativo | situação do usuário | selo em pílula | info | `circle-minus` |
| Sucesso | mensagem | faixa com borda clara e ícone colorido | success | `circle-check` |
| Erro | mensagem | faixa com borda clara e ícone colorido | error | `circle-x` |
| Aviso | mensagem | faixa com borda clara e ícone colorido | warning | `triangle-alert` |
| Informação | mensagem | faixa com borda clara e ícone colorido | info | `info` |
| Disponível (futuro) | horário na agenda | célula `surface` com a palavra "Disponível" | nenhum | nenhum |
| Ocupado (futuro) | horário na agenda | célula com fundo neutral-200, texto neutral-800 (6,48:1) e hachura | neutro | nenhum |
| Pendente (futuro) | solicitação de reserva | selo | warning | `clock` |
| Aprovada (futuro) | solicitação de reserva | selo | success | `circle-check` |
| Rejeitada (futuro) | solicitação de reserva | selo | error | `circle-x` |
| Cancelada (futuro) | reserva | selo | info | `circle-slash` |

- **Disponível fica neutro.** Numa agenda a maioria dos horários está livre. Pintá-los de verde espalharia a cor e a confundiria com a cor de ação.
- **Linhas marcadas "(futuro)":** orientam as Changes de disponibilidade e reservas. Nenhum ícone, token ou componente delas é criado agora.
- **Ícones de estado:** nenhum ícone de estado aparece sem a palavra do estado ao lado.

### D8. Logo e símbolo

A interface usa duas peças derivadas dos arquivos RGB oficiais, geradas uma única vez com Pillow num container temporário, sem redimensionamento e sem alteração de cor.

**Símbolo do IF** (`ui/static/ui/img/simbolo-if.png`), na barra lateral e na barra do celular:
- **Origem e recorte:** `salinas_horizontal_jpg.jpg`, recorte 49, 41, 207, 254, só os quadrados e o círculo. O texto do logo começa na coluna 236. Tamanho final: 158 x 213.
- **Transparência:** o fundo branco do JPG vira transparente. O alfa é a distância do pixel ao branco pelo menor canal (255 menos o menor canal, dividido por 207, o valor do verde), limitado a 1. A cor da borda antisserrilhada é recuperada descontando o branco. As cores sólidas continuam exatas: #309F41 nos quadrados e #CF171F no círculo.
- **Exibição:** 40 px de altura, ao lado de "Agendamento de espaços", em peso 700, e "IFNMG Campus Salinas", em `on-sidebar-muted`. Como o nome da instituição está em texto logo ao lado, a imagem tem `alt=""`, e o link para o início é identificado pelo texto. No celular, a linha do campus é omitida para não disputar espaço com o botão "Menu".
- **Contraste:** o verde do símbolo sobre `sidebar` dá 3,20:1, e o vermelho dá 5,19:1.
- **Sem manual:** não há confirmação oficial de que o símbolo possa aparecer sem o texto. Ele é usado sem nenhuma alteração, e o nome da instituição aparece em texto ao lado. Se um manual obtido depois vetar esse uso, a troca volta ao logo completo sem mudar o layout.

**Logo negativo** (`ui/static/ui/img/logo-horizontal-negativo.png`), no painel do login:
- **Origem e recorte:** `salinas_horizontal_negativo_jpg.jpg`, recorte 49, 41, 862, 266, sem a moldura clara de 1 px do JPG. Tamanho final: 813 x 225.
- **Transparência:** RGB branco e alfa pela luminância, com 0 no fundo (#050102) e 255 no branco.
- **Exibição:** 56 px de altura a partir de 1024 px e 48 px abaixo, sobre `brand-surface` (8,35:1).
- **Altura mínima de 48 px:** a linha "Norte de Minas Gerais" tem altura de maiúscula de 16,4% da arte, cerca de 7,9 px a 48 px, o equivalente a uma fonte de 11 px. Abaixo disso o texto do logo fica ilegível.
- **Texto alternativo:** "Instituto Federal Norte de Minas Gerais, Campus Salinas".

**O que não é usado:**
- as versões colorida completa e vertical;
- a marca "if" da referência e o logo recolorido, que não são a marca oficial;
- o vetor `.cdr`, porque a conversão pelo Inkscape pode alterar as cores do vetor, que costuma estar em CMYK.

### D9. Tipografia

Open Sans variável, eixo de peso, estilo normal, subconjuntos latin e latin-ext em woff2. Os arquivos vêm do pacote npm `@fontsource-variable/open-sans` 5.3.0, a versão usada na prévia, confirmada ou atualizada na task 3.1. Eles são copiados para `ui/static/ui/fonts/` junto com o `OFL.txt` (SIL Open Font License 1.1). O `@font-face` no `app.css` usa `font-display: swap` e `unicode-range` por subconjunto. Não há itálico, porque a interface não usa ênfase em itálico.

Alternativas consideradas:
- **Google Fonts por CDN:** depende de rede externa, que pode ser instável, e envia o IP de cada acesso a um terceiro.
- **Fontes do sistema:** cada aparelho mostraria uma fonte diferente, contra o P8.
- **Inter:** mesma licença, mas sem relação com o texto do logo.

### D10. Ícones

Pacote `lucide-static` 1.47.0, a versão usada na prévia, confirmada ou atualizada na task 3.2. Só os SVGs usados são copiados para `ui/templates/ui/icons/`, com `aria-hidden="true"` e `focusable="false"`, e sem `width` e `height` na tag `svg`. As dimensões internas, como as do retângulo do envelope, ficam intactas. A licença ISC vai no arquivo `LICENSE`.

A tag `{% icon "pencil" "size-5" %}` do `ui/templatetags/ui.py` inclui o SVG com a classe de tamanho: `size-4` em selos e erros de campo, e `size-5` nos demais.

| Uso | Ícones |
|---|---|
| Navegação | `house` (Início), `users` (Usuários), `shield-check` (Perfis), `menu` |
| Cabeçalho | `chevron-right` (trilha), `chevron-down` (menu do usuário), `log-out` (Sair) |
| Ações de usuário | `user-plus` (Cadastrar usuário), `pencil` (Editar), `ellipsis` (Mais ações), `arrow-left-right` (Trocar perfil), `user-x` (Desativar), `user-check` (Reativar) |
| Ações de perfil | `shield-plus` (Criar perfil), `pencil` (Editar), `list-checks` (Alterar permissões), `trash-2` (Excluir) |
| Modal e formulários | `x` (Fechar), `search`, `chevron-down` (campos de seleção), `mail` e `lock` (login), `arrow-right` (Entrar) |
| Estados e mensagens | `check`, `circle-minus`, `circle-check`, `circle-x`, `triangle-alert`, `info` |

Os ícones de estados futuros (`clock`, `circle-slash`) entram com as Changes que os usarem.

**Botão só com ícone.** As ações de linha e o botão de fechar do modal mostram só o ícone. Cada um tem:
- `aria-label` com o verbo da ação ("Editar", "Trocar perfil", "Fechar"), lido por leitores de tela e verificado pelo teste de texto;
- uma dica visível (`role="tooltip"`) com o mesmo texto, exibida no `:hover` e no `:focus-visible`;
- o texto visível ao lado do ícone abaixo de 640 px, na tabela empilhada, porque no toque não há como passar o mouse.

Botões com texto (primário, secundário e destrutivo) levam o ícone à esquerda do texto.

Alternativas consideradas:
- **Heroicons:** equivalente. O autor preferiu a variedade do Lucide.
- **Fonte de ícones:** carrega todos os glifos e é lida por leitores de tela como caracteres soltos.
- **Dica pelo atributo `title`:** não aparece no foco pelo teclado, demora a aparecer e não segue a identidade visual.

### D11. Componentes

| Componente | Implementação | Onde é usado |
|---|---|---|
| Botões `btn-primary`, `btn-secondary`, `btn-danger` | classes em `@layer components` do `app.css`; `min-h-11`, `px-5`, `text-base`, peso 600, `radius-lg`, ícone à esquerda e sem sombra | ação principal de cada tela e rodapés de modal |
| Botão de ícone `icon-btn` | 44 x 44 px, fundo transparente, ícone `text-muted`, hover `hover`, dica e `aria-label` (D10) | ações de linha e fechar modal |
| Menu suspenso `menu` | `<details>` com `<summary>` como gatilho e lista de botões com ícone e texto, `surface`, `radius-lg` e `shadow-overlay` | "Mais ações" de cada linha e menu do usuário no cabeçalho |
| Link `link` | cor `action`, sublinhado e hover `action-hover` | links em texto |
| Campos | renderizador de formulários do projeto (`ui.forms.FormRenderer`, subclasse de `TemplatesSetting` com `form_template_name = "ui/forms/form.html"` e `field_template_name = "ui/forms/field.html"`), classes `field`, `input`, `select-wrap` e `control` (campo com ícone) | todos os formulários, inclusive os do allauth |
| Cartão `card` | `surface`, borda `divider`, `radius-xl`, com `card-head` (título, contador, descrição e filtros) e `card-foot` | listas de usuários e de perfis, detalhe de perfil |
| Tabela `data-table` | cabeçalhos em `text-xs` maiúsculo sobre `page`, linhas com hover `page`, `data-label` em cada `td` e versão empilhada abaixo de 640 px | listas |
| Pessoa `person` | avatar de iniciais (`avatar-bg`, `avatar-text`, `radius-full`, `aria-hidden`), nome em peso 600 e e-mail em `text-sm` `text-muted` | primeira coluna da lista de usuários e menu do usuário |
| Selo | `ui/components/badge.html` com `tone`, `icon` e `label`, em pílula com borda 200 | situação do usuário |
| Contador `count` | pílula `hover` com número em `text-xs` | ao lado do título do cartão |
| Mensagens | `ui/components/messages.html`, incluído no layout, com borda 200, ícone 600 e texto 800 | todas as páginas |
| Modal | `ui/components/modal.html` e `ui/components/confirm_modal.html` (D16) | todas as ações |

**Campos.** O `field.html`:
- mostra o rótulo;
- acrescenta "(opcional)" quando o campo não é obrigatório;
- mostra a ajuda com `id` próprio;
- mostra os erros em texto `danger` com `id` próprio;
- define no widget `aria-describedby` com os dois `id`s e `aria-invalid="true"` quando houver erro.

O `settings.py` recebe `FORM_RENDERER = "ui.forms.FormRenderer"` e `django.forms` em `INSTALLED_APPS`, exigido pelo `TemplatesSetting`. A tela de login deixa de montar os campos à mão e passa a usar o mesmo renderizador.

**Ações por tela.** Cada tela tem no máximo um botão primário, no cabeçalho da página: "Cadastrar usuário" ou "Criar perfil". As ações de linha são botões de ícone:
- **Usuários:** "Editar" fica visível. "Mais ações" abre "Trocar perfil" e "Desativar usuário" ou "Reativar usuário".
- **Perfis:** "Editar" e "Alterar permissões" ficam visíveis. "Excluir perfil" aparece só para perfis personalizados.

Cada ação só aparece com a permissão correspondente (`perms`), como hoje.

Alternativas consideradas:
- **Classes utilitárias repetidas em cada template:** o mesmo botão escrito em 16 templates diverge com o tempo (P4, P8).
- **Pacotes como `django-crispy-forms` ou `django-widget-tweaks`:** dependência nova para algo que o renderizador de formulários do Django 5.2 resolve.

### D12. Layout, navegação e responsividade

- **Layout autenticado** (`ui/layouts/app.html`), a partir de 1024 px, em ordem:
  - link "Ir para o conteúdo", visível ao receber foco;
  - **barra lateral** (`aside`): `sidebar`, 17 rem de largura e borda direita `sidebar-border`, com:
    - o símbolo do IF e, ao lado, "Agendamento de espaços" e "IFNMG Campus Salinas", tudo num link para o início;
    - o rótulo "Menu principal" em `text-xs` maiúsculo `on-sidebar-muted`;
    - a navegação;
  - **cabeçalho** (`header`), branco com borda `divider` e 72 px de altura:
    - à esquerda, a trilha de navegação (`nav` com `aria-label="Trilha de navegação"`): "Início", o ícone `chevron-right` e a página atual com `aria-current="page"`;
    - à direita, o menu do usuário: `<details>` cujo `<summary>` mostra o avatar de iniciais, o nome, o perfil e `chevron-down`, e cuja lista tem "Sair", um botão POST com CSRF e o ícone `log-out`;
  - **conteúdo** (`main` com `id="conteudo"`) sobre `page`, com 40 px de margem:
    - o cabeçalho da página: `h1` em `text-3xl`, uma descrição em `text-muted` e o botão primário à direita;
    - a área de mensagens;
    - o cartão da tela.
- **Navegação.** É um `nav` com `aria-label="Principal"`. Os itens são "Início" (`house`), "Usuários" (`users`) e "Perfis" (`shield-check`), condicionados às permissões por `perms`, como hoje.
  - Cada item tem 48 px de altura, `radius-lg`, texto `on-sidebar` em peso 600, ícone `sidebar-accent` e hover `sidebar-hover`.
  - O item atual vira um bloco `action` com texto e ícone brancos.
- **Abaixo de 1024 px.** A barra lateral dá lugar a uma barra `sidebar` no topo, com o símbolo, o nome do sistema e o `summary` "Menu" (ícone `menu`, fundo `surface` e borda `on-sidebar-muted`).
  - O `<details>` abre o rótulo "Menu principal", a navegação e, abaixo, o nome, o perfil e o botão "Sair" com contorno.
  - A trilha de navegação some. O cabeçalho da página continua com `h1` em `text-2xl`, e o botão primário ocupa a largura toda.
  - Tudo isso funciona sem JavaScript.
- **Item atual.** A tag `{% nav_link "user_list" "Usuários" "users" prefix="user_" %}` compara o prefixo com `request.resolver_match.url_name` e, quando coincide, renderiza o link com `aria-current="page"` e o bloco verde. A indicação muda a forma do item (um bloco preenchido), e não só a cor.
- **Iniciais do avatar.** A tag `{{ user.name|initials }}` pega a primeira letra do primeiro e do último nome, em maiúsculas.
- **Foco.** A regra global `:focus-visible` desenha um contorno de 2 px em `focus`, com deslocamento de 2 px, inclusive sobre `sidebar` (3,93:1).
- **Tabela empilhada.** Abaixo de 640 px:
  - as linhas e as células da `data-table` passam a `display: block`, e o `thead` fica visualmente oculto, mas disponível a leitores de tela;
  - cada `td` mostra antes do valor o conteúdo de `data-label` por `::before`, exceto a coluna da pessoa e a de ações;
  - valores longos, como e-mails, quebram com `overflow-wrap: anywhere`;
  - as ações da linha aparecem todas, sem o menu "Mais ações", como botões com contorno, ícone e texto.
- **`data-label`.** O atributo entra na lista de atributos verificados pelo teste de texto.
- **Largura mínima.** Nenhum elemento tem largura fixa maior que 360 px menos as margens laterais de 16 px.

Alternativas consideradas:
- **Menu com JavaScript:** exigiria script próprio e deixaria de funcionar se o script falhasse. O `<details>` já resolve.
- **Tabela com rolagem lateral:** esconde a coluna de ações no celular.
- **Sino de notificações no cabeçalho:** o sistema não tem notificações na interface. As do TCC são por e-mail (RF09 e RF10), e um sino sem função seria enfeite.

### D13. Teste de valores soltos

O `ui/class_rules.py` lê do `app.css` os nomes dos tokens e monta a lista de valores aceitos por grupo de utilitário. O teste `ui/tests/test_template_classes.py` percorre os templates do projeto, extrai os atributos `class` com o mesmo Lexer usado no teste de texto (partes `{{ }}` e `{% %}` dentro do atributo são descartadas), remove os prefixos de variante (`sm:`, `lg:`, `hover:`, `focus-visible:`, `open:` e outros) e falha quando encontra:

- atributo `style`;
- classe com `[` ou `]` (valor arbitrário);
- utilitário de cor (`bg-`, `text-`, `border-`, `outline-`, `ring-`, `fill-`, `stroke-`, `decoration-`) com nome que não é token de cor;
- utilitário de espaçamento ou tamanho (`p`, `px`, `py`, `pt`, `pr`, `pb`, `pl`, `m` e variantes, `gap`, `space-x`, `space-y`, `w`, `h`, `min-w`, `min-h`, `size`) com passo numérico fora da escala;
- `text-` de tamanho, `rounded-` ou `shadow-` fora dos tokens;
- `max-w-` fora dos tokens de largura.

A mensagem indica o arquivo, a linha e a classe. As classes de componente (`btn-primary`, `field` e as demais) são aceitas por nome.

Alternativa considerada: **confiar só no `--*: initial` do tema**. Uma classe fora da escala deixaria silenciosamente de gerar CSS, sem erro, e a tela sairia sem estilo.

### D14. Aplicação às telas de `accounts`

Todos os templates passam a usar os componentes: `403.html`, `accounts/home.html`, as listas, os formulários, o detalhe e as confirmações de usuários e perfis, e as sobrescritas do allauth (`login`, `logout` e as quatro telas da recuperação de senha).

- **Listas.**
  - A lista de usuários segue a prévia: cartão "Todos os usuários" com contador, descrição, tabela com pessoa, perfil, situação e ações, e o rodapé "Exibindo X de Y usuários".
  - A busca e o filtro entram com a Change `filtrar-lista-de-usuarios`. Nesta Change, o cartão já tem o espaço dos filtros, mas não os mostra.
  - A lista de perfis usa o mesmo cartão, com código, nome, tipo, usuários vinculados e ações.
- **Formulários e confirmações.** Cadastrar, editar e trocar perfil de usuário, criar e editar perfil, alterar permissões e as confirmações de desativar, reativar e excluir perfil passam a ser modais (D16). As URLs e as views continuam as mesmas.
- **Detalhe do perfil.** Continua sendo uma página, porque é consulta e não ação. Ele mostra dados e permissões em cartões, e as ações dele abrem em modal.
- **Alterar permissões.** Os grupos por recurso ficam em `fieldset` e `legend` dentro do modal, com rolagem interna quando passarem da altura da tela.
- **Login e recuperação de senha.** Usam o layout `ui/layouts/auth.html`, sem barra lateral, mantido da primeira revisão.
  - **A partir de 1024 px:** duas colunas. À esquerda, o painel `brand-surface` com o logo negativo (56 px), "Agendamento de espaços" em `text-3xl`, a descrição "Consulta de disponibilidade e reserva de laboratórios e salas do IFNMG Campus Salinas." e, no rodapé, "IFNMG Campus Salinas". À direita, o formulário.
  - **Abaixo de 1024 px:** o painel vira uma faixa no topo.
  - **Formulário:**
    - "Entrar", com o texto "Use o e-mail institucional e a senha cadastrados no sistema.";
    - "E-mail institucional", com ícone `mail` e o placeholder "nome.sobrenome@ifnmg.edu.br", e "Senha", com ícone `lock`;
    - "Manter conectado" e "Esqueci minha senha" na mesma linha;
    - botão "Entrar" com `arrow-right`;
    - a nota "Para obter acesso, procure um administrador do sistema."
  - O botão que revela a senha fica de fora.
- **Views.** Só as classes base mudam (D16). A lógica de cada view continua igual.

### D15. Prévia

O arquivo `previa.html`, nesta pasta, é uma página estática, com o CSS escrito à mão a partir destes tokens e com a fonte, os ícones e o símbolo embutidos em base64. A versão aprovada mostra:

- a barra lateral, o cabeçalho e a listagem, com o menu "Mais ações" aberto;
- os modais de cadastro, com um erro de campo, e de confirmação de desativação;
- botões e botões de ícone com a dica, campos, mensagens, selos, tokens, contraste e escalas.

A pedido do autor, o login e as telas de celular saíram da prévia. Eles continuam definidos neste design (D12 e D14) e na spec.

A prévia não é usada pelo sistema, e o CSS dela não é a implementação. Ela fica versionada como **referência de paleta e componentes** para telas futuras: toda tela nova parte de uma imagem de referência dada pelo autor e adaptada a ela (convenção 9.8).

### D16. Ações em modal com htmx

Toda ação de gestão abre num modal sobre a tela atual. O HTML do modal é renderizado no servidor, pelo mesmo template e pela mesma view de hoje, e o htmx o carrega e envia.

**Dependências**
- **htmx 2.0.10** (licença 0BSD): arquivo `htmx.min.js` versionado em `ui/static/ui/js/`, obtido com `npm pack htmx.org@2.0.10` num container temporário, com a licença ao lado. Não é servido por CDN.
- **django-htmx 1.29.0** no `requirements.txt`: fornece `request.htmx` pelo `HtmxMiddleware` e as respostas `HttpResponseClientRedirect`.

**Fluxo**
1. O botão de ação é um link com `href` para a URL da ação (por exemplo, `usuarios/<id>/desativar/`) e com `hx-get` para a mesma URL e `hx-target="#modal"`.
2. A view detecta `request.htmx` e renderiza só o fragmento do modal (`modal_template_name`). Sem htmx, renderiza a página completa, que inclui o mesmo fragmento dentro do layout, como página própria.
3. O `ui/static/ui/js/modal.js`, com cerca de 20 linhas, escuta o evento `htmx:afterSwap` no `#modal`: abre o `<dialog>` com `showModal()` e devolve o foco ao botão de origem quando o modal fecha. O `<dialog>` modal já prende o foco, fecha com Esc e deixa o resto da página inerte.
4. O formulário do modal usa `hx-post` para a mesma URL, com o token CSRF enviado pelo cabeçalho `X-CSRFToken`. O `hx-headers` no `body` o lê do cookie.
5. **Erro de validação ou recusa de regra de negócio no formulário:** a view devolve o fragmento com os erros e o htmx troca o conteúdo do modal, que continua aberto.
6. **Sucesso:** a view responde com `HttpResponseClientRedirect` para a URL de sucesso. A página recarrega com a mensagem do `django.contrib.messages`. Se a requisição veio da lista, a URL de sucesso é a própria lista com os parâmetros atuais (`request.htmx.current_url`), o que preserva busca e filtro.
7. **Recusa em ação confirmada** (por exemplo, continuidade administrativa ao desativar): mesmo fluxo do sucesso, com a mensagem de erro, como hoje.

**Classes base.** `ui/views.py` define `ModalView`, com `get_template_names()` escolhendo o fragmento quando `request.htmx` é verdadeiro e `form_valid` e `post` respondendo com `HttpResponseClientRedirect` nesse caso. `OperationFormView` e `ConfirmedActionView` de `accounts/views.py` passam a herdar dela. Não há mixin, conforme a convenção 5.

**Estrutura do modal** (`ui/components/modal.html`):
- `<dialog>` com `aria-labelledby` no título e `aria-describedby` na descrição;
- cabeçalho com o `h2` e o botão de ícone `x` ("Fechar"), com `formmethod="dialog"`;
- corpo com o formulário;
- rodapé com "Fechar" (secundário) e o botão da ação.

A confirmação (`confirm_modal.html`) tem como título a pergunta ("Desativar Ana Souza?"), a consequência no corpo e o botão destrutivo com ícone. No celular, o modal sobe a partir da base da tela e ocupa a largura toda.

**Sem JavaScript.** Os links levam à URL da ação, que mostra o mesmo conteúdo como página, com o mesmo formulário e o mesmo POST. O comportamento, os testes de acesso existentes e a regra "GET mostra a confirmação, POST executa" continuam valendo.

**Testes.** Cada rota de ação ganha dois testes: com o cabeçalho `HX-Request`, responde só o fragmento do modal; e, no POST válido, responde 200 com `HX-Redirect`. Os testes atuais, sem o cabeçalho, continuam como estão.

Alternativas consideradas:
- **Modal renderizado pelo servidor sem htmx, com `inert`:** funciona sem JavaScript, mas recarrega a página a cada abertura. O autor preferiu o htmx.
- **JavaScript próprio com `fetch`:** reimplementaria o que o htmx já faz (troca de conteúdo, cabeçalhos, eventos, redirecionamento).
- **SPA ou framework de componentes:** contraria o P1, que define a apresentação com templates do Django.
- **Nome "Cancelar" para sair do modal:** "cancelar" é ação do domínio (RF08). Por isso o botão se chama "Fechar".

## Risks / Trade-offs

- [Cores sem manual oficial podem divergir do padrão da Rede Federal] → a origem de cada valor está no D3. Se o manual for obtido, os valores são trocados num só arquivo e o teste de contraste confere as escalas de novo.
- [Botões só com ícone podem não ser reconhecidos por quem tem pouca familiaridade] → a dica aparece no hover e no foco, o `aria-label` é lido por leitores de tela, e no celular o texto aparece junto. Os ícones escolhidos são os convencionais (lápis para editar, reticências para mais ações). A decisão é do autor e está registrada no Context.
- [O htmx passa a ser necessário para a experiência com modais] → sem JavaScript, as mesmas URLs abrem como páginas (D16). O arquivo é servido pelo próprio sistema, sem CDN.
- [A troca de conteúdo pelo htmx pode dessincronizar o foco e o anúncio para leitores de tela] → o `<dialog>` aberto com `showModal()` move o foco para dentro dele, e o `modal.js` devolve o foco ao botão de origem. A task 10.2 verifica isso com o teclado.
- [O comportamento de `--spacing-*: initial` no Tailwind 4.3.3 pode ainda aceitar múltiplos da escala] → o D13 não depende do Tailwind: o teste recusa qualquer passo fora da escala.
- [A tabela com `display: block` perde a semântica de tabela em alguns leitores de tela] → isso só vale abaixo de 640 px, e cada valor é precedido do rótulo em texto. A semântica completa continua nas larguras maiores.
- [A instalação do npm na construção da imagem depende da rede] → isso só vale na construção. A execução não baixa nada, e a imagem fica em cache local.
- [O volume anônimo de `node_modules` pode ficar desatualizado] → o `make up` usa `--renew-anon-volumes`, e o README explica o motivo.
- [O PNG recortado do JPG tem artefatos de compressão e resolução limitada] → é suficiente até cerca de 112 px de altura em telas 2x. A interface usa 48 e 56 px.
- [A borda de campo só tem contraste suficiente sobre `surface`] → campos ficam sempre em cartões, modais ou no formulário do login. O teste de contraste não cobre a posição do campo, e a revisão da seção 10 das tasks confere.
- [Verificação visual manual] → a seção 10 das tasks lista as larguras (360, 640, 1024 e 1280 px), a navegação só por teclado, os modais e o zoom de 200%.

## Migration Plan

Sem migração de dados. Depois do merge, um `make up` reconstrói as imagens e sobe o serviço `tailwind`. O rollback é reverter os commits e rodar `make up` de novo.

## Open Questions

Nenhuma.
