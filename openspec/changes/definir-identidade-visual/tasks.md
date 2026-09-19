## 1. Pré-requisitos

- [x] 1.1 Confirmar que a Change `definir-texto-da-interface` foi implementada e que o app `ui` e o teste de texto existem
- [x] 1.2 Obter a aprovação do autor para a prévia visual `previa.html` (terceira versão) antes de iniciar a seção 2 (D15)

## 2. Build do Tailwind no Docker

- [x] 2.1 Criar `package.json` com `tailwindcss` e `@tailwindcss/cli` em `4.3.3`, sem `^` nem `~`, e gerar o `package-lock.json` com `npm install` num container `node` temporário (D2)
- [x] 2.2 Adicionar ao `Dockerfile` o estágio `tailwind`, com a imagem `node` em tag de versão exata, `WORKDIR /app`, cópia do `package.json` e do `package-lock.json` e `npm ci`, sem alterar o estágio da aplicação (D2)
- [x] 2.3 Adicionar ao `compose.yaml` o serviço `tailwind` com `target: tailwind`, bind mount `.:/app`, volume anônimo `/app/node_modules` e o comando do CLI em `--watch=always` (D2)
- [x] 2.4 No `Makefile`, alterar `up` para usar `--renew-anon-volumes` e adicionar os alvos `css` (CSS minificado) e `npm` (`npm $(cmd)` no serviço `tailwind`), com descrições `##` (D2)
- [x] 2.5 Adicionar `ui/static/ui/css/` e `node_modules/` ao `.gitignore`
- [x] 2.6 Executar `make up`, confirmar que os três containers sobem e que `ui/static/ui/css/app.css` é gerado e atualizado ao alterar um template

## 3. Fonte, ícones, logo e htmx

- [x] 3.1 Obter `@fontsource-variable/open-sans` 5.3.0 com `npm pack` num container temporário, copiar os woff2 de peso variável, estilo normal, latin e latin-ext para `ui/static/ui/fonts/` com o `OFL.txt` (D9)
- [x] 3.2 Obter `lucide-static` 1.47.0 do mesmo modo e copiar para `ui/templates/ui/icons/` os ícones da tabela do D10, com `aria-hidden="true"` e `focusable="false"` e sem `width` e `height` na tag `svg`, junto com o `LICENSE` (D10)
- [x] 3.3 Gerar com Pillow num container temporário, sem redimensionar: `simbolo-if.png` a partir de `salinas_horizontal_jpg.jpg` (recorte 49, 41, 207, 254, fundo branco transparente, cores sólidas #309F41 e #CF171F conferidas, 158 x 213) e `logo-horizontal-negativo.png` a partir de `salinas_horizontal_negativo_jpg.jpg` (recorte 49, 41, 862, 266, RGB branco e alfa pela luminância, 813 x 225). Conferir a ausência de halo sobre #EFFBEF e #035B18 (D8)
- [x] 3.4 Obter `htmx.org` 2.0.10 com `npm pack` e copiar `htmx.min.js` e a licença para `ui/static/ui/js/` (D16)
- [x] 3.5 Adicionar `django-htmx==1.29.0` ao `requirements.txt`, registrar `django_htmx` em `INSTALLED_APPS` e `django_htmx.middleware.HtmxMiddleware` em `MIDDLEWARE`, e reconstruir a imagem (D16)

## 4. Tokens e contraste

- [ ] 4.1 Criar `ui/styles/app.css` com `@import "tailwindcss"`, as variáveis `--palette-*` dos degraus usados, o `@theme` com os grupos padrão zerados e os tokens do D5, e o `@font-face` da Open Sans (D5, D9)
- [ ] 4.2 Criar `ui/contrast.py` com `CONTRAST_PAIRS` da tabela do D6, a lista de isentos com a justificativa, a leitura das variáveis do `app.css` e o cálculo WCAG 2.x (D6)
- [ ] 4.3 Escrever `ui/tests/test_contrast.py`: todos os pares acima do mínimo, todo token de cor coberto por um par ou isento, e um caso que troca o valor do texto secundário por #7B7677 numa cópia do `app.css` e espera a falha com 4,47:1 (cenário da spec)
- [ ] 4.4 Criar `ui/class_rules.py`, que monta os valores aceitos a partir dos tokens do `app.css`, verifica as classes e só aceita `shadow-overlay` nas classes de camada flutuante (D5, D13)
- [ ] 4.5 Escrever `ui/tests/test_template_classes.py`, que percorre os templates do projeto e falha em `style=`, valores arbitrários, cores fora dos tokens, passos fora da escala e sombra fora de camada flutuante, com os cenários da spec

## 5. Componentes

- [ ] 5.1 Escrever em `@layer components` do `app.css` as classes do D11 (`btn-primary`, `btn-secondary`, `btn-danger`, `icon-btn` com a dica, `menu`, `link`, `field`, `input`, `select-wrap`, `control`, `card`, `data-table`, `person`, `avatar`, `badge`, `count`, `alert` e `modal`) e do D12 (`sidebar`, `side-nav`, `header`, `crumbs`), só com tokens, e a regra global de `:focus-visible` (D11, D12)
- [ ] 5.2 Criar `ui/forms.py` com o `FormRenderer` e os templates `ui/forms/form.html` e `ui/forms/field.html` com rótulo, "(opcional)", ajuda, erros, `aria-describedby` e `aria-invalid`, e configurar `FORM_RENDERER` e `django.forms` em `INSTALLED_APPS` (D11)
- [ ] 5.3 Criar `ui/components/messages.html` com tom, ícone e `role` por tipo de mensagem, `ui/components/badge.html` e `ui/components/row_actions.html`, com botões de ícone, dica, `aria-label` e o menu "Mais ações" (D7, D10, D11)
- [ ] 5.4 Criar `ui/templatetags/ui.py` com as tags `icon` e `nav_link` e o filtro `initials` (D10, D12)
- [ ] 5.5 Acrescentar `data-label` à lista de atributos verificados pelo teste de texto (D12)

## 6. Modais com htmx

- [ ] 6.1 Criar `ui/components/modal.html` (dialog, título, descrição, botão de ícone "Fechar", corpo e rodapé com "Fechar" e a ação) e `ui/components/confirm_modal.html` (D16)
- [ ] 6.2 Criar `ui/static/ui/js/modal.js`, que abre o `<dialog>` com `showModal()` no `htmx:afterSwap` do `#modal` e devolve o foco ao botão de origem ao fechar (D16)
- [ ] 6.3 Criar `ui/views.py` com `ModalView`: fragmento do modal quando `request.htmx`, página completa sem ele, e `HttpResponseClientRedirect` no sucesso, para a URL atual quando a origem for a lista (D16)
- [ ] 6.4 Fazer `OperationFormView` e `ConfirmedActionView` de `accounts/views.py` herdarem de `ModalView`, sem mudar a lógica das views concretas, e definir `modal_template_name` em cada uma (D16)
- [ ] 6.5 Escrever os testes de cada rota de ação: GET com `HX-Request` responde só o fragmento, GET sem ele responde a página completa, POST inválido pelo htmx responde o fragmento com erro sem gravar, e POST válido pelo htmx responde `HX-Redirect`

## 7. Layouts

- [ ] 7.1 Mover `accounts/templates/base.html` para `ui/templates/base.html`, só com o `head`, o CSS, o htmx, o `modal.js`, o `hx-headers` com o CSRF no `body` e o `#modal` vazio (D12, D16)
- [ ] 7.2 Criar `ui/templates/ui/layouts/app.html` com o link "Ir para o conteúdo", a barra lateral (símbolo do IF, nome do sistema, campus, "Menu principal" e navegação), o cabeçalho (trilha e menu do usuário com "Sair" por POST), a barra do topo com `<details>` "Menu" abaixo de 1024 px, o `main` com `id="conteudo"`, o cabeçalho da página e as mensagens (D12)
- [ ] 7.3 Criar `ui/templates/ui/layouts/auth.html` com o painel `brand-surface` e o formulário, em duas colunas a partir de 1024 px e empilhados abaixo disso (D14)
- [ ] 7.4 Escrever `ui/tests/test_base.py`: símbolo do IF com o nome do sistema e o campus no link para o início, logo negativo com o texto alternativo no login, primeiro link "Ir para o conteúdo", `aria-current="page"` e trilha na lista de usuários, "Perfis" ausente sem a permissão, menu do usuário com iniciais, nome, perfil e "Sair", login com o painel da marca e o título "Entrar", e nenhum endereço externo em `link`, `script`, `img` e `@font-face`

## 8. Aplicação às telas de `accounts`

- [ ] 8.1 Aplicar o layout a `accounts/home.html` e `403.html` (D14)
- [ ] 8.2 Reescrever `user_list.html` no cartão da prévia: contador, descrição, tabela com pessoa, perfil, selo e ações (Editar e Mais ações), rodapé "Exibindo X de Y usuários" e botão primário "Cadastrar usuário" no cabeçalho da página (D14)
- [ ] 8.3 Transformar `user_form.html` (cadastrar, editar e trocar perfil) e `user_status_confirm.html` em modais, com as páginas completas estendendo o layout (D14, D16)
- [ ] 8.4 Reescrever `role_list.html` e `role_detail.html` em cartões, e transformar `role_form.html` (com as permissões em `fieldset` por recurso) e `role_confirm_delete.html` em modais (D14, D16)
- [ ] 8.5 Aplicar o layout de autenticação a `login.html`, com o renderizador de formulários, os campos com ícone, "E-mail institucional" e a nota de acesso, e a `logout.html` e às quatro telas da recuperação de senha (D14)
- [ ] 8.6 Escrever os testes dos cenários da spec: selos com palavra e ícone, `role="alert"` e `role="status"` nas mensagens, botão "Editar" com `aria-label` e dica, `aria-invalid` e `aria-describedby` no e-mail vazio, "(opcional)" na descrição do perfil, `data-label` nas células e o texto do estado vazio de permissões
- [ ] 8.7 Rodar `make test` com a suíte inteira passando, incluindo os testes de texto, contraste, valores soltos e modais

## 9. Documentação

- [ ] 9.1 Atualizar o `README.md`: serviço `tailwind`, alvos `css` e `npm`, motivo do `--renew-anon-volumes`, htmx e Node.js como pré-requisito dispensado
- [ ] 9.2 Acrescentar à seção 9 do `openspec/conventions.md` a referência aos tokens, aos componentes e aos layouts do app `ui`, e a instrução de usar os componentes em vez de repetir classes
- [ ] 9.3 Validar a Change com `openspec validate definir-identidade-visual --strict`

## 10. Verificação visual manual

- [ ] 10.1 Conferir todas as telas e modais em 360, 640, 1024 e 1280 px de largura, sem rolagem horizontal
- [ ] 10.2 Percorrer todas as telas só com o teclado: foco visível, dicas dos botões de ícone no foco, foco preso no modal, Esc fechando e foco voltando ao botão de origem
- [ ] 10.3 Conferir as telas com zoom de 200% e com o JavaScript desligado, incluindo o botão "Menu" e as ações abrindo como páginas
