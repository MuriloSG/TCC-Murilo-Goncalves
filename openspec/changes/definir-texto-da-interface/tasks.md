## 1. App `ui` e regras de texto

- [x] 1.1 Criar o app `ui` na raiz do projeto com `__init__.py`, `apps.py` e `tests/__init__.py`, e registrá-lo em `INSTALLED_APPS`, sem criar diretórios que esta Change não usa (D1)
- [x] 1.2 Criar `ui/text_rules.py` com `FORBIDDEN_PATTERNS`, `EMOJI_RANGES`, `GLOSSARY` (todas as linhas da tabela 9.4 das convenções), `PROPER_NOUNS` e `CAPITALIZED_ELEMENTS`, com docstring de módulo que aponte a seção 9 das convenções (D4)
- [x] 1.3 Implementar `find_violations(text, element=None)`, que ignora maiúsculas e acentos na comparação, respeita limites de palavra Unicode, trata palavras só com maiúsculas como sigla e aplica maiúsculas e dois-pontos só nos elementos previstos (D4)
- [x] 1.4 Escrever `ui/tests/test_text_rules.py` com um caso positivo e um negativo por regra, incluindo os exemplos da spec: "Usuário cadastrado!", "Cadastrar Usuário", "Bloquear", "com sucesso", "10:00" em título, "VAR usuário" e "Esqueci minha senha"

## 2. Verificação dos templates e das strings Python

- [x] 2.1 Implementar em `ui/text_rules.py` a extração do texto visível dos templates com o `Lexer` do Django e o `HTMLParser`: tokens de bloco e comentário descartados, variáveis como `VAR`, atributos `placeholder`, `title`, `alt`, `aria-label` e `value` de botões, e o elemento de cada trecho, com a linha de origem (D2)
- [x] 2.2 Tratar os templates `.txt` como texto integralmente visível (D2)
- [x] 2.3 Implementar a extração das strings Python com `ast`: constantes e partes constantes de f-strings com pelo menos um espaço, sem docstrings e sem argumentos de `logger.*`, excluindo `tests/` e `migrations/` (D3)
- [x] 2.4 Escrever `ui/tests/test_interface_text.py`, que percorre os templates e os módulos dos apps do projeto (sem bibliotecas instaladas) e falha listando arquivo, linha e trecho de cada violação
- [x] 2.5 Incluir em `test_interface_text.py` os cenários da spec sobre a extração: `{% if a != b %}` e `<!DOCTYPE html>` sem violação, e palavra proibida em docstring sem violação
- [x] 2.6 Rodar `make test` e registrar a lista de violações atual, que orienta as seções 3 e 4

## 3. Formatos brasileiros

- [x] 3.1 Criar `config/formats/__init__.py`, `config/formats/pt_BR/__init__.py` e `config/formats/pt_BR/formats.py` com os formatos de data, hora, data e hora, e número (D6)
- [x] 3.2 Definir `FORMAT_MODULE_PATH = ["config.formats"]` e `USE_THOUSAND_SEPARATOR = True` no `settings.py` (D6)
- [x] 3.3 Escrever `ui/tests/test_formats.py` renderizando um template com `{{ data|date }}`, `{{ hora|time }}` e `{{ numero }}` e verificando "18/09/2026", "10:00" e "1.234,5"
- [x] 3.4 Conferir nos templates de `accounts` que nenhum id ou valor técnico é renderizado com `{{ }}` em atributo sem `|unlocalize` (Risks)

## 4. Revisão dos textos de `accounts`

- [x] 4.1 Reescrever `403.html`, `accounts/home.html`, `accounts/user_list.html` e `accounts/role_detail.html` conforme a tabela do D7
- [x] 4.2 Reescrever `accounts/user_status_confirm.html` e `accounts/role_confirm_delete.html` no padrão de confirmação: título com a pergunta e o nome, consequência, botão com verbo e objeto e link "Fechar" (D7)
- [x] 4.3 Reescrever `account/logout.html`, `account/password_reset.html`, `account/password_reset_done.html` e `account/email/password_reset_key_message.txt` conforme o D7
- [x] 4.4 Ajustar a mensagem de continuidade administrativa em `accounts/models.py` para incluir a orientação do que fazer (D7)
- [x] 4.5 Criar as sobrescritas `account/messages/logged_in.txt` (vazia), `logged_out.txt` ("Sessão encerrada.") e `password_changed.txt` (vazia) em `accounts/templates` (D5)
- [x] 4.6 Sobrescrever em `AccountAdapter.error_messages` as chaves `email_password_mismatch`, `too_many_login_attempts` e `rate_limited`, e levantar as mensagens dos validadores de senha exibidas em `password_reset_from_key`, sobrescrevendo as que violarem as regras (D5)
- [x] 4.7 Definir `error_messages` do campo de e-mail em `UserCreateForm` e `UserUpdateForm`, e criar em `accounts/forms.py` as subclasses dos formulários de login e de recuperação do allauth com a mesma mensagem, registradas em `ACCOUNT_FORMS` (D5)
- [x] 4.8 Atualizar os testes existentes de `accounts` que comparam os textos alterados

## 5. Testes de comportamento dos textos

- [x] 5.1 Testar que as chaves sobrescritas existem em `DefaultAccountAdapter.error_messages` e que todas as mensagens sobrescritas passam em `find_violations` (Risks)
- [x] 5.2 Testar os fluxos: login não gera mensagem, logout mostra "Sessão encerrada.", credenciais incorretas mostram a mensagem nova, e a redefinição de senha não mostra "com sucesso"
- [x] 5.3 Testar que o e-mail inválido no cadastro de usuário, no login e na recuperação mostra "Informe um e-mail válido."
- [x] 5.4 Testar a página 403, a página inicial, a confirmação de desativação (título "Desativar <nome>?", botão "Desativar usuário" e link "Fechar"), a confirmação de exclusão de perfil e o detalhe de perfil sem descrição ("Sem descrição"), conforme os cenários da spec
- [x] 5.5 Rodar `make test` com a suíte inteira passando, sem violações apontadas por `test_interface_text.py`

## 6. Documentação

- [ ] 6.1 Conferir que a seção 9 do `openspec/conventions.md` e `ui/text_rules.py` trazem a mesma lista de expressões e o mesmo glossário (D4)
- [ ] 6.2 Validar a Change com `openspec validate definir-texto-da-interface --strict`
