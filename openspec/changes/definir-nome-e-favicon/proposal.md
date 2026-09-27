## Why

O nome exibido na interface era "SaliSpace", escolhido no começo do desenvolvimento. O autor definiu o nome oficial do sistema: **IFAgenda**, com o nome por extenso "Sistema de Agendamento de Espaços do IFNMG – Campus Salinas". O nome antigo aparece no título das páginas, na barra lateral, na barra do topo do celular, no painel da página de login e no cabeçalho do calendário público. Além disso, nenhuma página declara ícone, e a aba do navegador mostra o ícone padrão.

## What Changes

- **Nome do sistema** passa a ser "IFAgenda" em todo texto exibido: título das páginas (`<title>`), barra lateral, barra do topo no celular, painel da página de login e cabeçalho do calendário público.
- **Ícone do sistema** declarado no `base.html`, e portanto presente em todas as páginas, autenticadas ou públicas: `favicon.ico` com 16, 32 e 48 px, um PNG de 512 px e o `apple-touch-icon` de 180 px.
- **E-mails** passam a usar o nome oficial no prefixo do assunto (`[IFAgenda] `) e no remetente padrão, no lugar de "Agendamento IFNMG Salinas".
- **Origem do ícone:** o símbolo oficial do IF já usado na barra lateral (`ui/static/ui/img/simbolo-if.png`), centrado num quadrado com margem, sem alteração de cor nem redesenho da marca.

### Fora do escopo

- `site.webmanifest` e ícones de instalação como aplicativo, que o projeto não usa.
- Logo novo, paleta nova ou qualquer alteração de layout.
- O nome da instituição e do campus na página de login, que continuam como estão.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `interface`: o nome do sistema exibido passa a ser "IFAgenda", e toda página declara o ícone derivado do símbolo do IF.
- `calendario-publico`: a marca do cabeçalho passa a ser "IFAgenda".

## Impact

- **`ui`:** `base.html` (título e links do ícone), `ui/layouts/app.html`, `ui/layouts/auth.html`, `ui/layouts/public.html` e os arquivos de ícone em `ui/static/ui/img/`.
- **Testes:** `ui/tests/test_base.py`, nas asserções da marca da barra lateral e do painel de login, com um teste novo do título e do ícone, e `accounts/tests/test_emails.py`, no prefixo do assunto.
- **`config`:** `ACCOUNT_EMAIL_SUBJECT_PREFIX` e o remetente padrão do `compose.yaml`, com o `README.md`.
- **Sem mudança** em models, migrations, rotas, permissões, regras de negócio ou dependências.

## Alinhamento com o TCC

- **RNF05 e P7:** o sistema passa a se identificar pelo nome oficial, o mesmo usado fora do sistema.
