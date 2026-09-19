## Why

O RNF05 pede usabilidade compatível com docentes de familiaridade tecnológica variada, sem treinamento extensivo, e a Seção 2.3.8 do TCC destaca três heurísticas de Nielsen: visibilidade do estado do sistema, correspondência com o mundo real e prevenção de erros. Hoje o texto das telas não tem regra. Ele alterna tratamentos ("você" em algumas telas, impessoal em outras), traz saudação ("Olá"), primeira pessoa do plural ("enviaremos") e travessão como marcador de célula vazia. As mensagens do allauth e do Django mostram "com sucesso", "Você saiu." e "email" sem hífen. As datas saem por extenso, com o mês em maiúscula. A regra precisa existir antes da Change `definir-identidade-visual`, que vai reescrever todas as telas de `accounts`, para que essas telas já nasçam sob verificação automática.

## What Changes

- **Regras de texto da interface**, com verificação automática: tom impessoal, expressões proibidas, padrão de mensagens de sucesso, erro e confirmação, verbos nos botões e maiúsculas só no início da frase.
- **Glossário fixo**, com um termo por conceito e os sinônimos proibidos. "Rejeitar" (RF07) no lugar de "reprovar", e "desativar" no lugar de "bloquear" ou "suspender".
- **Formatos brasileiros** de data (dd/mm/aaaa), hora (24 h, "10:00") e número (1.234,5), vindos da localização do Django.
- **Confirmações** têm como título a pergunta ("Desativar Ana Souza?") e saem pelo botão "Fechar", e não "Cancelar", porque "cancelar" é uma ação do domínio (RF08). O mesmo texto serve à página de confirmação atual e ao modal da Change `definir-identidade-visual`.
- **Botões só com ícone** têm o nome da ação no `aria-label`, que segue as mesmas regras de texto.
- **App `ui`** com as regras de texto em código e os testes que percorrem os templates e as mensagens em Python.
- **Revisão dos textos atuais** de `accounts`: templates, mensagens das views, mensagens do allauth e erros padrão do Django que aparecem nas rotas expostas.
- Seção "Interface e texto" no `openspec/conventions.md`, que já foi escrita junto com esta proposal.

### Fora do escopo

- Visual das telas, Tailwind CSS, tokens, logo e componentes: ficam com a Change `definir-identidade-visual`.
- Textos de módulos que ainda não existem (espaços, reservas, relatórios). Eles seguem as mesmas regras quando forem criados.
- Tradução para outros idiomas.

## Capabilities

### New Capabilities
- `texto-interface`: regras verificáveis para todo texto exibido pelo sistema (tom, expressões proibidas, mensagens, botões e títulos, glossário, formatos de data, hora e número) e a verificação automática delas.

### Modified Capabilities

Nenhuma. As specs existentes não fixam o texto exato das telas. A spec `autenticacao` diz explicitamente que o texto da mensagem de usuário inativo não é fixado.

## Impact

- **Código novo:** app `ui` com `text_rules.py` e os testes. Módulo de formatos `config/formats/pt_BR/formats.py`, com `FORMAT_MODULE_PATH` e `USE_THOUSAND_SEPARATOR` no `settings.py`.
- **Código alterado:** todos os templates de `accounts/templates`, mensagens em `accounts/views.py` e `accounts/models.py` quando violarem as regras, mensagens de erro do `AccountAdapter`, `error_messages` dos campos de e-mail e sobrescritas de `account/messages/*.txt` do allauth.
- **Testes existentes:** os que comparam o texto exato de mensagens ou telas precisam ser atualizados junto com o texto.
- **Dependências:** nenhuma nova.

## Alinhamento com o TCC

- **RNF05 e Seção 2.3.8:** o glossário aplica a correspondência com o mundo real ("laboratório", "reserva", "disponível"). As mensagens de erro com causa e ação aplicam a heurística 9 (ajudar a reconhecer, diagnosticar e recuperar erros).
- **RF07:** o TCC usa "rejeitar" no requisito e na Seção 2.3.8 ("pendente, aprovada ou rejeitada"), e "reprovar" no texto dos casos de uso. O glossário adota "rejeitar", o termo do requisito.
- **P8 (consistência visual):** o mesmo termo e o mesmo padrão de mensagem em todas as telas fazem parte da consistência entre telas pedida pelo RNF05.
