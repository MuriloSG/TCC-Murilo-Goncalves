# Central de ajuda

Rota `/ajuda/` (`tutorials.views.HelpCenterView`), aberta pelo ícone de ajuda no cabeçalho e na barra do celular, para todo usuário autenticado. Cada funcionalidade é explicada em passos numerados, com capturas reais das telas, feitas com dados fictícios, no computador e no celular.

## Ajuda da tela

O ícone leva a rota de origem em `?tela=` (por exemplo `/ajuda/?tela=agenda_grid`). A página mostra só as funcionalidades da parte do sistema de onde a ajuda foi aberta, com o título da `Screen` (por exemplo "Ajuda da agenda") e a trilha Início, opção do menu e Ajuda.

A parte do sistema é a opção do menu: `Screen.prefix` é o mesmo prefixo de rota do `MenuItem` em `ui/navigation.py`, então toda rota da Agenda, inclusive Minhas solicitações e a análise, abre a ajuda da Agenda. O rótulo e o link da trilha vêm do menu (`MenuItem.url_for`), que já leva à primeira tela liberada ao usuário.

Sem `tela`, com uma rota sem ajuda própria ou a partir da própria ajuda, a página mostra a central completa: todas as funcionalidades liberadas, por módulo, com a navegação por módulo. A funcionalidade de uso geral (notificações do sino) só aparece nela.

## Conteúdo

O conteúdo fica em `tutorials/catalog.py`, como dado, no mesmo estilo do menu (`ui/navigation.py`):

| Estrutura | Campos |
|---|---|
| `Module` | Identificador, rótulo e funcionalidades, na ordem do menu |
| `Feature` | Identificador (âncora na página), título, objetivo, permissões, passos, aviso opcional e a rota do botão do fim |
| `Step` | Instrução, texto alternativo da imagem, textos dos balões dos marcadores e permissões opcionais do passo |
| `Screen` | Prefixo de rota da opção do menu, título da ajuda da tela e as funcionalidades dela |

As imagens ficam em `tutorials/static/tutorials/<funcionalidade>/<número>-computador.webp` e `-celular.webp`. O número é a posição do passo no catálogo, e não entre os passos liberados. Os textos do catálogo passam pelas regras de texto do app `ui`, como qualquer string Python do projeto.

| Módulo | Funcionalidades |
|---|---|
| Uso geral | Acompanhar as notificações |
| Painel | Consultar o painel |
| Agenda | Consultar a agenda, Solicitar agendamento, Acompanhar as solicitações, Cancelar um agendamento, Cancelar a ocorrência de uma aula, Analisar as solicitações de agendamento, Criar solicitação para outro usuário |
| Gestão acadêmica | Consultar a grade do ensalamento, Ajustar as aulas do ensalamento, Importar a planilha de horários, Gerenciar os espaços, os cursos, as disciplinas e as turmas |
| Relatórios | Consultar o mapa de calor, Consultar o relatório de solicitações |
| Notificações | Publicar uma notificação |
| Administração | Gerenciar os usuários, Importar usuários, Gerenciar os perfis e as permissões, Consultar a auditoria |
| Configurações | Configurar o servidor de e-mail |

O calendário público e o login ficaram de fora: quem ainda não entrou no sistema não chega à central.

## Permissões

- A rota exige só login (`permission_required` ausente, como `/inicio/`).
- `tutorials.catalog.entries_for`, usada pela ajuda da tela e pela central completa (`guide_for`), monta a página só com o que o usuário pode usar: a funcionalidade exige todas as `permissions` dela e cada passo exige as próprias. Funcionalidade sem passo liberado fica de fora. A decisão é sempre `User.has_perms`, sem nome de perfil.
- O que não é liberado não chega ao template: título, texto e endereço das imagens de outras funcionalidades não aparecem no HTML. Na ajuda de uma tela sem funcionalidade liberada, a página mostra o aviso "Nenhuma ajuda desta tela liberada para o seu perfil."
- `?tela=` só escolhe entre os prefixos de `SCREENS`; um valor desconhecido abre a central completa e não aparece na página.
- O botão do fim leva à tela da funcionalidade, cuja permissão está entre as da funcionalidade (`test_catalog`). A tela continua exigindo a própria permissão no servidor.
- Algumas condições não são permissão e ficam no aviso da funcionalidade: o cancelamento da ocorrência pelo docente da aula, o escopo de disciplinas e turmas e o formulário de criação para quem cria em nome de outros.

## Visual

Adaptado do padrão das telas existentes, sem imagem de referência, por decisão do autor:

- `page-head`, `card`, `card-head`, `card-body`, `card-foot`, `alert tone-info`, `step-mark` e `btn-secondary btn-go` do app `ui`, mais os componentes `guide-*` e `help-link` em `ui/styles/app.css`.
- Navegação (`tutorials/partials/nav.html`) na central completa e na ajuda de tela com mais de uma funcionalidade. A partir de 64rem, coluna fixa à esquerda com os módulos e as funcionalidades; abaixo disso, barra fixa no topo, recolhida, com o nome da funcionalidade que está na tela. Sem a navegação, o conteúdo ocupa a largura inteira.
- `tutorials/static/tutorials/js/guide.js`, carregado só nesta página: abre a navegação no computador e a recolhe no celular, recolhe depois de escolher uma funcionalidade e marca com `aria-current` a funcionalidade que está na tela. Sem JavaScript, a navegação fica aberta e os links levam às âncoras.
- A imagem de cada passo é um link para a versão ampliada da imagem mostrada (a do celular ou a do computador).
- Em cada passo, a instrução vem antes da imagem, e a legenda repete os balões em texto, para que a explicação não dependa da imagem.
- `<picture>` com a captura do celular abaixo de 640 px e a do computador acima, com `width`, `height`, `loading="lazy"` e `alt`.
- Cor dos marcadores: token `--color-guide-mark` (laranja, fora do verde da marca), com o par de contraste da legenda em `ui/contrast.py`. As imagens usam a mesma cor.

## Capturas

As 184 imagens (92 passos, no computador e no celular) foram geradas em 20/10/2026 por um roteiro automatizado com o Playwright, num projeto Compose separado, com banco vazio e só dados fictícios ("Ana Exemplo", "Bruno Exemplo" e os demais), criados pelas próprias telas. O banco de desenvolvimento, que tem dados reais, não foi usado. O roteiro e a infraestrutura dele foram retirados do repositório depois da geração, por decisão do autor.

Padrão das imagens, a seguir ao substituir uma delas:

- Computador em 1280×800; celular em 390×844 com escala 2 (780×1688). WebP com qualidade 82.
- Só dados fictícios, sem nomes, e-mails ou outros dados de pessoas reais, inclusive no rodapé do menu e nas iniciais do avatar.
- Marcações: retângulo de 3 px na cor `--color-guide-mark` em volta do elemento, número no canto, e balão escuro (`--color-tooltip`) com o mesmo número e o texto de `marks` do passo, sem cobrir a informação da tela.
- O nome do arquivo segue `Feature.image`: `<funcionalidade>/<número do passo no catálogo>-computador.webp` e `-celular.webp`.

## Manutenção

- Ao mudar uma tela explicada pela central, substitua as imagens dos passos afetados seguindo o padrão acima. `test_catalog` falha se faltar a imagem de algum passo.
- Funcionalidade nova: `Feature` no catálogo, no módulo certo, e as imagens de cada passo nas duas telas.

## Testes

`tutorials/tests/`: ver [catálogo de testes](../desenvolvimento/testes/tutorials.md).
