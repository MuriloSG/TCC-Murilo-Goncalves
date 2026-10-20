# Testes

Test runner do Django estendido em `config/test_runner.py` (registra os bancos de teste para a trava dos comandos destrutivos e silencia o INFO dos loggers do projeto), no PostgreSQL do container `db`. O banco de teste é criado e removido a cada execução; o banco de desenvolvimento não é tocado.

```bash
make test                                               # suíte inteira
make manage cmd="test bookings"                         # um app
make manage cmd="test schedule.tests.test_import"       # um módulo
make manage cmd="test bookings.tests.test_models.SubmitTests.test_past_start_is_refused"   # um teste
```

Sem `make`: `docker compose run --rm web python manage.py test`.

Situação em 20/10/2026: 1780 testes, todos passando, em cerca de 100 segundos. Rode sem `--parallel`: nesse modo, um teste com falha derruba o runner ao serializar o erro, e a saída não mostra qual foi. As mensagens "Importação N falhou na tentativa..." na saída são logs esperados dos testes do worker.

A convenção do projeto é rodar a suíte inteira antes de cada commit. Não há CI no repositório.

## Organização

- Testes em `<app>/tests/test_*.py`. Auxiliares compartilhados: `accounts/tests/roles.py` (perfis montados pelas permissões), `bookings/tests/base.py`, `system_settings/tests/base.py` (`configure_smtp`), `imports/tests/definitions.py` (importação de teste sobre `auth.Group`), `imports/tests/worker.py` (roda o worker nos testes), `ui/tests/files.py` (lista templates e módulos).
- Os testes do ensalamento leem cópias da planilha real e das sugeridas em `schedule/tests/fixtures/`, e não `sources/`, para rodarem também dentro da imagem de produção, que não leva `sources/`.

## Catálogo por app

O que cada módulo e cada classe de teste garante, um documento por app:

| Documento | Conteúdo |
|---|---|
| [`accounts`](testes/accounts.md) | Autenticação, senha, autorização, continuidade administrativa, perfis, comandos, telas e importação de usuários |
| [`audit`](testes/audit.md) | Registro de acessos, autenticação e alterações; integridade; consulta |
| [`bookings`](testes/bookings.md) | Solicitação, conflitos, máquina de estados, turma, criação para outro, notificações e telas da Agenda |
| [`imports`](testes/imports.md) | Leitura de CSV e XLSX, prévia, confirmação, pendências e worker do motor de importação |
| [`notices`](testes/notices.md) | Entrega, destinatários, eventos, tempo real, sino e publicação manual |
| [`outbox`](testes/outbox.md) | Fila de e-mails, worker, tentativas e configuração SMTP |
| [`panel` e `reports`](testes/panel-e-reports.md) | Painel administrativo, mapa de calor e relatório de solicitações |
| [`schedule`](testes/schedule.md) | Entidades do ensalamento, recorrências, cancelamentos, importação da planilha, espaços, cadastros acadêmicos, calendário público e cache |
| [`system_settings`](testes/system-settings.md) | Configuração SMTP cifrada e checagens de deploy |
| [`tutorials`](testes/tutorials.md) | Catálogo e imagens da central de ajuda e visibilidade por permissão |
| [`ui`](testes/ui.md) | Varreduras de texto, classes e contraste, layout, navegação e componentes |

## Testes transversais

| Teste | O que garante |
|---|---|
| `accounts/tests/test_route_protection.py` | Toda rota está em `PROTECTED_ROUTES` (com a permissão) ou em `PUBLIC_ROUTES`. Para cada rota protegida: anônimo vai ao login com `next`, usuário sem a permissão recebe 403, POST sem CSRF recebe 403, perfil com só a permissão da rota passa (exceto as reservadas), perfil sem permissões recebe 403 qualquer que seja o nome, e o superadmin sem perfil passa. Rota nova fora da tabela faz o teste falhar |
| `ui/tests/test_interface_text.py`, `test_text_rules.py` | Texto exibido em templates e em strings Python segue a seção 9 das convenções (expressões proibidas, glossário) |
| `ui/tests/test_template_classes.py` | Templates sem `style=`, sem valores arbitrários do Tailwind e só com classes da escala de tokens |
| `ui/tests/test_contrast.py` | Pares de cores de `ui/contrast.py` acima do contraste AA, nos dois temas |
| `schedule/tests/test_public_cache.py`, `BulkWriteScanTests` | Toda escrita sem sinais nos models das telas públicas chama a invalidação do cache |
| `accounts/tests/test_catalog.py` | Catálogo de permissões coerente com a carga da `accounts/0001_initial`, e nenhum perfil com permissão reservada ou de alcance acadêmico |
| `accounts/tests/test_command_environment.py` | `flush`, `clear_data`, `delete_users` e `set_passwords` recusados fora de `DJANGO_ENVIRONMENT=local`, sem `DJANGO_LOCAL_DATABASE`, com identidade diferente da declarada, sem a marca no banco, com outra marca, com nome efetivo divergente e num banco com nome de teste fora do registro do runner; mensagens sem configuração nem credenciais; execução no banco local simulado (marca só na sessão do teste) e no banco de teste do runner; registro do runner esvaziado ao final, mesmo com falha |

## Regras para escrever testes

Resumo da seção 7 das [convenções](convencoes.md#7-testes):

- Cada regra é testada na camada mais baixa que a implementa (model ou manager). Na tela, basta conferir uma vez que o erro aparece.
- O teste do app cobre a rota executando com a permissão. Anônimo, falta de permissão e CSRF ficam na matriz central.
- Não testar comportamento do Django (`max_length`, `unique`, CASCADE, `Meta.ordering`, valores padrão, 405 de `require_POST`, `transaction.atomic`).
- Conferir textos e valores pelo `context` quando possível, não a marcação exata.
- Variações do mesmo caso com `subTest`. Totais do catálogo calculados de `accounts/permissions.py`.
- `TransactionTestCase` com `serialized_rollback = True` quando o comportamento depende de `on_commit` ou de concorrência. Toda classe `TransactionTestCase` declara esse atributo.
- Testes que executam `clear_data`, `delete_users` ou `set_passwords` declaram `@override_settings(ENVIRONMENT='local')`; o container de testes não tem a variável e recusa os comandos.
- `cache.clear()` no `setUp` de testes que passam pelos limites de tentativas do allauth.
- Testes de permissão com usuários que não são superadmin.
- Datas: testes que dependem do dia fixam o relógio com `mock.patch` em `django.utils.timezone` (ver `schedule/tests/test_recurrence_*.py`).

## Conferência visual

Não há teste automatizado de navegador no repositório. As conferências manuais usam um banco separado (`visual_check`) e Playwright em container, nunca o banco de desenvolvimento; a última tentativa não foi concluída por falta de acesso ao PyPI.

## Autorização dos comandos destrutivos nos testes

O `TransactionTestCase` chama `flush` a cada teste, e os testes dos comandos destrutivos rodam no banco de teste. `config.test_runner.TestRunner` registra, em `created_test_databases`, o par (alias, nome) de cada banco que ele criou, inclusive as cópias do `--parallel`, e `require_safe_database` libera só esses. O registro existe apenas no processo do runner: um comando digitado à mão nunca o preenche, e um banco operacional chamado `test_algo` continua recusado. O Django chama `teardown_databases` num `finally`, e o runner esvazia o registro também num `finally`, mesmo se a remoção dos bancos falhar.
