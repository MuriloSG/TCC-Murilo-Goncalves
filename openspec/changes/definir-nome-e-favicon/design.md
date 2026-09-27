# Nome oficial e ícone do sistema

## D1. Onde o nome antigo estava

A busca por "SaliSpace" e suas variações encontrou o nome em cinco pontos de interface e em três artefatos:

| Ponto | Arquivo |
|---|---|
| Título de toda página | `ui/templates/base.html` |
| Barra lateral, barra do topo e painel do menu do celular | `ui/templates/ui/layouts/app.html` |
| Painel da página de login | `ui/templates/ui/layouts/auth.html` |
| Cabeçalho do calendário público | `ui/templates/ui/layouts/public.html` |
| Asserções de marca | `ui/tests/test_base.py` |
| Prévia visual da Grade | `openspec/changes/visualizar-grade-do-ensalamento/grade-previa.html` |
| Requisito de identidade | spec `interface` |
| Requisito do calendário no celular | spec `calendario-publico` |

As ocorrências nas Changes já arquivadas em `openspec/changes/archive/` ficaram como estão: elas são o registro do que foi decidido na época, e reescrevê-las apagaria o histórico. As specs vigentes são atualizadas pelos deltas desta Change, no arquivamento.

## D2. "Agenda" na barra lateral

Na barra lateral o texto ao lado do símbolo é "Agenda", e não "IFAgenda", por decisão do autor: o símbolo do IF fica encostado no texto, e "IF" apareceria duas vezes na mesma linha. Nos demais pontos (título das páginas, barra do topo e painel do menu no celular, painel de login e cabeçalho do calendário público) o nome continua "IFAgenda".

## D3. O que não foi trocado

- "Instituto Federal Norte de Minas Gerais, Campus Salinas", "IFNMG Campus Salinas" e o texto de apoio do painel de login continuam como estão: identificam a instituição e o campus, e não o sistema.
- O logo horizontal negativo (`logo-horizontal-negativo.png`) e o símbolo do IF (`simbolo-if.png`) continuam sendo a arte oficial. A Change não cria identidade visual nova.

## D4. Origem do ícone

O sistema não tinha ícone, e não usa manifesto de aplicativo. O ícone é derivado de `ui/static/ui/img/simbolo-if.png` (158x213, RGBA), o mesmo símbolo já exibido na barra lateral, e não do logo horizontal, que ficaria ilegível num quadrado de 16 px. A arte é ampliada proporcionalmente e centrada num quadrado com margem, sem corte, sem alteração de cor e sem redesenho. Aos 32 px, os quadrados verdes e o ponto vermelho continuam distinguíveis.

Arquivos gerados, todos em `ui/static/ui/img/`:

| Arquivo | Conteúdo |
|---|---|
| `favicon.ico` | 16, 32 e 48 px, com transparência |
| `favicon-512.png` | 512 px, com transparência |
| `apple-touch-icon.png` | 180 px, com fundo branco |

O `apple-touch-icon` tem fundo branco porque o iOS não respeita transparência nesse ícone e a preencheria com preto.

Os três são declarados no `<head>` do `base.html`, e por isso valem para as páginas autenticadas, o login, a recuperação de senha e o calendário público, sem repetição nos layouts.

## D5. Conferência no navegador

Feita com o Playwright num container, contra o banco `visual_check`, em 1280x800 e 360x740, na página de login, em `/inicio/` e no calendário público:

- O título das três páginas termina em "· IFAgenda", e a marca da barra lateral, do topo e do painel de login mostra "IFAgenda".
- As três declarações de ícone aparecem nas três páginas, e os arquivos respondem 200 com o tipo correto.
- Nenhuma página rola na horizontal, nas duas larguras, e o layout não mudou.

Nada precisou de ajuste depois da conferência.
