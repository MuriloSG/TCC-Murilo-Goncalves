## 1. Nome do sistema

- [x] 1.1 Trocar o nome no título das páginas em `base.html`
- [x] 1.2 Trocar o nome na barra lateral e na barra do topo (`ui/layouts/app.html`), no painel de login (`ui/layouts/auth.html`) e no cabeçalho público (`ui/layouts/public.html`)
- [x] 1.3 Deixar só "Agenda" no texto da barra lateral (D2)
- [x] 1.4 Trocar o prefixo do assunto dos e-mails e o remetente padrão
- [x] 1.5 Atualizar as asserções da marca em `ui/tests/test_base.py`

## 2. Ícone

- [x] 2.1 Gerar `favicon.ico` (16, 32 e 48 px), `favicon-512.png` e `apple-touch-icon.png` a partir de `simbolo-if.png`
- [x] 2.2 Declarar os três no `<head>` do `base.html` (D4)
- [x] 2.3 Escrever os cenários das specs `interface` e `calendario-publico`

## 3. Verificação

- [x] 3.1 Rodar `make test` com a suíte inteira passando
- [x] 3.2 Conferir o nome, o ícone e o layout no navegador, no banco `visual_check`, em 360 e 1280 px (D5)
- [x] 3.3 Validar a Change com `openspec validate definir-nome-e-favicon --strict`
