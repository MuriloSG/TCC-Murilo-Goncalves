## Context

As telas de `accounts` (16 templates, incluindo as sobrescritas do allauth e o e-mail de senha) foram escritas sem uma regra de texto. Um levantamento feito para esta Change encontrou:

- **Tratamento misturado:** "Você não tem permissão" (403), "você receberá" (aviso de envio), "enviaremos" (recuperação), "Recebemos um pedido" e "Se você não fez" (e-mail).
- **Saudação:** "Olá, {{ user.name }}" na página inicial e "Olá!" no e-mail.
- **Travessão como célula vazia:** lista de usuários e detalhe do perfil.
- **Confirmações** no formato "Deseja ...?", com botão de verbo solto ("Excluir", "Desativar") e link "Cancelar".
- **allauth em pt-br:** "Conectado com sucesso como ...", "Você saiu.", "Senha alterada com sucesso.", "Muitas tentativas de login falharam." e "Seja paciente, você está enviando muitas requisições."
- **Django em pt-br:** o erro padrão de e-mail inválido é "Informe um endereço de email válido.", sem hífen. O `DATE_FORMAT` padrão produz "18 de Setembro de 2026", com o mês em maiúscula. Só o `SHORT_DATE_FORMAT` dá "18/09/2026".

As decisões de tom, glossário e padrão de mensagens foram tomadas em entrevista com o autor e estão na seção 9 do `openspec/conventions.md`. Este design define como verificá-las e como corrigir os textos atuais.

Restrições: cada Change cria só o que usa, tudo roda via `make`, sem comentários `#`, e identificadores em inglês com texto em português.

## Goals / Non-Goals

**Goals:**

- Regras de texto em código, com uma única fonte da lista de expressões proibidas e do glossário.
- Um teste que percorre todos os templates e as strings Python dos apps e aponta arquivo, linha e trecho de cada violação.
- Todos os textos atuais de `accounts`, do allauth e do Django nas rotas expostas dentro das regras.
- Datas, horas e números no formato brasileiro, vindos da localização.

**Non-Goals:**

- Visual, CSS, componentes e logo (Change `definir-identidade-visual`).
- Verificar se uma frase é clara ou se uma lista tem três adjetivos. Isso fica na revisão humana, orientada pela seção 9 das convenções.
- Tradução para outros idiomas e arquivos `.po` próprios.

## Decisions

### D1. App `ui` para as regras e a verificação

Um app novo, `ui`, na raiz do projeto e registrado em `INSTALLED_APPS`, contém nesta Change só o que ela usa:

```text
ui/
  __init__.py
  apps.py
  text_rules.py        listas de expressões proibidas, glossário e nomes próprios, e as funções de verificação
  tests/
    __init__.py
    test_text_rules.py      testes unitários das funções, com os exemplos das specs
    test_interface_text.py  percorre templates e módulos Python do projeto
    test_formats.py         data, hora e número renderizados
```

Na Change `definir-identidade-visual`, o mesmo app recebe o `base.html`, os componentes, os tokens e o teste de contraste.

Alternativas consideradas:
- **Testes em `accounts/tests`:** a verificação percorre todos os apps. Deixá-la em `accounts` faria os apps futuros dependerem dos testes de um app de domínio.
- **Diretório `tests/` na raiz:** foge da convenção `<app>/tests/` e não tem onde guardar as regras nem, depois, os templates compartilhados.

### D2. Extração do texto visível dos templates

O teste lê cada arquivo de template dos diretórios de templates dos apps do projeto, excluindo os de bibliotecas instaladas, e o divide com o `Lexer` do próprio Django (`django.template.base.Lexer`). O Lexer devolve tokens de texto, variável, bloco e comentário, cada um com o número da linha.

- Tokens de bloco (`{% %}`) e de comentário (`{# #}`) são descartados. Por isso `{% if a != b %}` não conta como exclamação.
- Tokens de variável (`{{ }}`) viram o marcador neutro `VAR`, uma sigla em maiúsculas, que não dispara nenhuma regra e preserva a posição das palavras. Assim, "{{ action|capfirst }} usuário" é lido como "VAR usuário".
- **Templates `.html`:** o texto dos tokens de texto passa por um `html.parser.HTMLParser` que coleta o conteúdo, os atributos `placeholder`, `title`, `alt` e `aria-label`, e o `value` de `<input type="submit|button">`. A declaração `<!DOCTYPE>` e os comentários HTML são ignorados.
- **Templates `.txt`** (e-mail e mensagens do allauth): o texto inteiro é considerado visível.
- Cada trecho guarda o elemento em que está (`h1` a `h6`, `title`, `button`, `a`, `th`, `label`, `legend`, `dt` ou outro), usado pela regra de maiúsculas.

Alternativas consideradas:
- **Expressões regulares sobre o arquivo cru:** frágeis com tags de template dentro de atributos e com `!=`.
- **Renderizar cada template com um contexto:** exigiria montar o contexto de cada tela e não percorreria os ramos de `{% if %}` não tomados.

### D3. Extração das strings Python

O teste percorre com `ast` os módulos `.py` dos apps do projeto, exceto `tests/` e `migrations/`, e considera:

- constantes `str` e as partes constantes de f-strings (`JoinedStr`);
- só as strings com pelo menos um espaço, que são frases. Chaves e códigos (`'email'`, `'role_in_use'`) ficam de fora, e com isso `email` como identificador não conta como violação do glossário;
- nenhuma docstring: o primeiro `Expr` de módulo, classe ou função é descartado;
- nenhum argumento de chamada a `logger.*`, que é registro técnico e não aparece para o usuário.

A regra de maiúsculas não se aplica às strings Python, porque o elemento em que elas vão aparecer não é conhecido. As demais regras se aplicam.

### D4. Regras como dados em `ui/text_rules.py`

- `FORBIDDEN_PATTERNS`: pares (expressão regular, orientação). A comparação ignora maiúsculas e acentos e respeita limites de palavra Unicode. Cobre `!`, reticências (`...` e `…`), travessões (`—` e `–`), interjeições, saudações, mensagens vagas, "por favor", "com sucesso", as palavras de marketing com as flexões, e "você", "vocês", "nós" e as formas de primeira pessoa do plural encontradas no projeto ("enviaremos", "recebemos", "estamos", "conseguimos", "vamos").
- `EMOJI_RANGES`: faixas Unicode de pictogramas (U+1F000 a U+1FAFF, U+2600 a U+27BF, U+2B00 a U+2BFF) e os caracteres U+FE0F e U+200D.
- `GLOSSARY`: termo proibido para termo correto, com todas as linhas da tabela 9.4 das convenções e as flexões. Por exemplo: "bloquear", "suspender" e "inativar" para desativar; "reprovar" e "negar" para rejeitar; "apagar", "deletar" e "remover" para excluir; "logar", "deslogar" e "logout" para entrar ou sair; "email" sem hífen para e-mail; "livre" e "vago" para disponível. A mensagem de falha indica o termo correto.
- `PROPER_NOUNS`: nomes próprios permitidos com maiúscula no meio de títulos e botões ("IFNMG", "Instituto Federal", "Norte de Minas Gerais", "Campus Salinas", "Salinas"). Palavras só com maiúsculas, com duas letras ou mais, são tratadas como sigla e também são permitidas.
- `CAPITALIZED_ELEMENTS`: `h1` a `h6`, `title`, `button`, `a`, `th`, `label`, `legend` e `dt`. Nesses elementos, uma palavra com inicial maiúscula que não abre a frase e não é nome próprio nem sigla é uma violação.
- **Títulos com dois-pontos:** em `h1` a `h6` e `title`, dois-pontos seguidos de espaço são violação. "10:00" não é, porque não tem espaço depois.
- `find_violations(text, element=None)` devolve a lista de violações. É a única função usada pelos dois testes.

"Esqueci minha senha" fica permitido. É um rótulo de link escrito na voz do usuário, convenção amplamente reconhecida, e não a interface falando de si mesma. As regras vetam a primeira pessoa do plural e não o singular.

Alternativa considerada: **manter a lista só no `conventions.md`**. Texto sem teste volta a divergir com o tempo. O código é a fonte usada pela verificação, e a seção 9 das convenções é a referência de leitura. Uma mudança numa das duas exige mudar a outra no mesmo commit.

### D5. Mensagens do allauth e do Django nas rotas expostas

Só as rotas de login, logout e as quatro etapas da recuperação de senha são expostas (spec `autenticacao`). Os textos de biblioteca que aparecem nelas são sobrescritos no projeto:

| Origem | Texto atual (pt-br) | Texto novo |
|---|---|---|
| `account/messages/logged_in.txt` | Conectado com sucesso como Ana. | vazio: nenhuma mensagem, porque o cabeçalho já mostra o nome |
| `account/messages/logged_out.txt` | Você saiu. | Sessão encerrada. |
| `account/messages/password_changed.txt` | Senha alterada com sucesso. | vazio: a página de conclusão já informa "Senha definida" |
| `AccountAdapter.error_messages["email_password_mismatch"]` | O endereço de e-mail e/ou senha especificados estão incorretos. | E-mail ou senha incorretos. Confira os dados ou use "Esqueci minha senha". |
| `AccountAdapter.error_messages["too_many_login_attempts"]` | Muitas tentativas de login falharam. Tente novamente mais tarde. | Tentativas de login demais em pouco tempo. Aguarde alguns minutos e tente de novo. |
| `AccountAdapter.error_messages["rate_limited"]` | Seja paciente, você está enviando muitas requisições. | Solicitações demais em pouco tempo. Aguarde alguns minutos e tente de novo. |
| Erro padrão do `EmailField` do Django | Informe um endereço de email válido. | Informe um e-mail válido. |

O allauth só adiciona a mensagem quando o template renderizado não está vazio, por isso o template vazio suprime a mensagem.

O erro de e-mail inválido aparece nos formulários do projeto (`UserCreateForm`, `UserUpdateForm`) e nos do allauth (login e recuperação). Os do projeto definem `error_messages` no campo. Os do allauth passam a ser subclasses em `accounts/forms.py`, registradas em `ACCOUNT_FORMS` (`login` e `reset_password`), que só trocam essa mensagem no `__init__`.

Alternativas consideradas:
- **Arquivo `.po` do projeto sobrescrevendo as traduções:** exige `gettext` na imagem e `compilemessages` no fluxo de build, e a sobrescrita fica escondida num arquivo binário `.mo`.
- **Alterar a mensagem global do `EmailValidator` no `ready()` de um app:** é um monkeypatch que muda o comportamento para qualquer biblioteca e fica invisível para quem lê os formulários.

As mensagens dos validadores de senha do Django que aparecem na definição de senha são levantadas na implementação (task 4.6) e sobrescritas do mesmo modo caso violem as regras.

### D6. Formatos por módulo de formatos do projeto

`config/formats/pt_BR/formats.py` define `DATE_FORMAT = "d/m/Y"`, `SHORT_DATE_FORMAT = "d/m/Y"`, `TIME_FORMAT = "H:i"`, `DATETIME_FORMAT` e `SHORT_DATETIME_FORMAT = "d/m/Y H:i"`, `DECIMAL_SEPARATOR = ","`, `THOUSAND_SEPARATOR = "."` e `NUMBER_GROUPING = 3`. O `settings.py` passa a ter `FORMAT_MODULE_PATH = ["config.formats"]` e `USE_THOUSAND_SEPARATOR = True`. `LANGUAGE_CODE = "pt-br"` e `TIME_ZONE = "America/Sao_Paulo"` já estão configurados.

Assim, `{{ data|date }}`, `{{ hora|time }}` e `{{ numero }}` produzem o formato certo sem formato escrito no template.

Alternativas consideradas:
- **Formato explícito em cada template (`|date:"d/m/Y"`):** repete a regra em cada tela e depende de disciplina (P4, DRY).
- **Usar só `SHORT_DATE_FORMAT` nos templates:** exige lembrar do argumento. O `|date` sem argumento continuaria gerando "18 de Setembro de 2026".

Hoje nenhuma tela mostra data ou hora. O módulo é criado nesta Change mesmo assim, porque a regra é desta Change e o `test_formats.py` a verifica. Não é estrutura vazia: é configuração usada pelo teste e por toda tela futura.

### D7. Revisão dos textos atuais

| Local | Atual | Novo |
|---|---|---|
| `403.html` | Você não tem permissão para acessar esta página. Se precisar desse acesso, fale com um administrador do sistema. | Esta página exige uma permissão que o seu perfil não concede. Para obter acesso, procure um administrador do sistema. |
| `accounts/home.html`, título | Olá, {{ user.name }} | Início |
| `accounts/home.html`, sem funcionalidades | Nenhuma funcionalidade está disponível para o seu perfil no momento. Novas funcionalidades serão liberadas conforme o sistema evoluir. | O seu perfil ainda não dá acesso a nenhuma funcionalidade. Para obter acesso, procure um administrador do sistema. |
| `accounts/user_list.html`, perfil vazio | — | Sem perfil |
| `accounts/role_detail.html`, descrição vazia | — | Sem descrição |
| `accounts/user_status_confirm.html` | título "{{ action\|capfirst }} usuário" / Deseja {{ action }} {{ target.name }} ({{ target.email }})? / botão "{{ action\|capfirst }}" / link "Cancelar" | título "{{ action\|capfirst }} {{ target.name }}?" / consequência com o e-mail / botão "{{ action\|capfirst }} usuário" / link "Fechar" |
| `accounts/user_status_confirm.html`, reativar | sem consequência | O usuário volta a poder entrar no sistema com a senha que já tinha. |
| `accounts/role_confirm_delete.html` | título "Excluir perfil" / Deseja excluir o perfil {{ target.code }} ({{ target.name }})? / botão "Excluir" / link "Cancelar" | título "Excluir o perfil {{ target.name }}?" / consequência com o código / botão "Excluir perfil" / link "Fechar" |
| `account/logout.html` | Deseja encerrar a sessão? | Sair do sistema? |
| `account/password_reset.html` | Informe o e-mail cadastrado. Se ele pertencer a um usuário ativo, enviaremos um link para definir uma nova senha. | Informe o e-mail cadastrado. Se ele pertencer a um usuário ativo, o sistema envia para ele um link para definir uma nova senha. |
| `account/password_reset_done.html`, título | Verifique seu e-mail | Confira o e-mail |
| `account/password_reset_done.html` | Se o endereço informado pertencer a um usuário ativo, você receberá em instantes um e-mail com o link para definir a senha. Confira também a caixa de spam. | Se o e-mail informado pertencer a um usuário ativo, o link para definir a senha chega a ele em alguns minutos. Confira também a caixa de spam. |
| `account/email/password_reset_key_message.txt` | Olá! / Recebemos um pedido para definir ou redefinir a senha da sua conta ... / Se você não fez esse pedido, ignore este e-mail: sua senha atual continua valendo. | Foi solicitada a definição ou a redefinição da senha desta conta no sistema de agendamento de espaços do IFNMG Campus Salinas. / Se a solicitação não partiu do titular da conta, ignore este e-mail. A senha atual continua valendo. |
| `accounts/models.py`, continuidade | Operação recusada: o sistema ficaria sem nenhum usuário ativo com capacidade administrativa. | Operação recusada: o sistema ficaria sem nenhum usuário ativo com capacidade administrativa. Antes, garanta que outro usuário ativo tenha as permissões de gestão de usuários. |

Os demais textos já seguem as regras e não mudam. A lista final é a que o teste aprovar.

**"Fechar" em vez de "Voltar".** A primeira versão desta Change usava o link "Voltar". Com a decisão de levar as ações para modais (Change `definir-identidade-visual`, D16), o controle de saída passou a ser "Fechar" desde já, para que o texto não mude duas vezes. Na página de confirmação, que continua existindo sem JavaScript, "Fechar" leva de volta à tela de origem.

## Risks / Trade-offs

- [A regra de maiúsculas pode apontar falsos positivos em nomes próprios novos] → `PROPER_NOUNS` é ampliado no mesmo commit que introduz o nome, com a justificativa no próprio commit.
- [Clareza, frase de efeito e três adjetivos não são verificáveis por máquina] → ficam na seção 9 das convenções, para revisão humana. O teste cobre o que é objetivo.
- [`USE_THOUSAND_SEPARATOR` localiza qualquer número renderizado com `{{ }}`, inclusive um id usado em atributo] → ids e valores técnicos em atributos usam `{% url %}` ou `|unlocalize`. A Change `definir-identidade-visual` revisa todos os templates e confere isso.
- [Uma nova versão do allauth pode mudar as chaves de `error_messages` ou os nomes dos templates de mensagem] → `test_text_rules.py` verifica que as chaves sobrescritas existem em `DefaultAccountAdapter.error_messages`, e os testes de fluxo verificam as mensagens exibidas no login, no logout e na redefinição.
- [Testes existentes comparam textos exatos] → são atualizados junto com o texto, na mesma etapa.
- [A lista de expressões existe em dois lugares (convenções e código)] → a mudança de uma exige a da outra no mesmo commit (D4).

## Migration Plan

Sem migração de dados. As mudanças são de texto, configuração e testes, e o rollback é reverter os commits.

## Open Questions

Nenhuma.
