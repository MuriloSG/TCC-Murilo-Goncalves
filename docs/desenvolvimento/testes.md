# Testes

Test runner padrão do Django, no PostgreSQL do container `db`. O banco de teste é criado e removido a cada execução; o banco de desenvolvimento não é tocado.

```bash
make test                                               # suíte inteira
make manage cmd="test bookings"                         # um app
make manage cmd="test schedule.tests.test_import"       # um módulo
make manage cmd="test bookings.tests.test_models.SubmitTests.test_past_start_is_refused"   # um teste
```

Sem `make`: `docker compose run --rm web python manage.py test`.

Situação em 08/10/2026: 1639 testes, todos passando, em cerca de 92 segundos. As mensagens "Importação N falhou na tentativa..." na saída são logs esperados dos testes do worker.

A convenção do projeto é rodar a suíte inteira antes de cada commit. Não há CI no repositório.

## Organização

- Testes em `<app>/tests/test_*.py`. Auxiliares compartilhados: `bookings/tests/base.py`, `system_settings/tests/base.py` (`configure_smtp`), `imports/tests/definitions.py` (importação de teste sobre `auth.Group`), `imports/tests/worker.py` (roda o worker nos testes), `ui/tests/files.py` (lista templates e módulos).
- A planilha real e as sugeridas de `sources/` são lidas pelos testes do ensalamento.

## Testes transversais

| Teste | O que garante |
|---|---|
| `accounts/tests/test_route_protection.py` | Toda rota está em `PROTECTED_ROUTES` (com a permissão) ou em `PUBLIC_ROUTES`. Para cada rota protegida: anônimo vai ao login com `next`, usuário sem a permissão recebe 403, POST sem CSRF recebe 403. Rota nova fora da tabela faz o teste falhar |
| `ui/tests/test_interface_text.py`, `test_text_rules.py` | Texto exibido em templates e em strings Python segue a seção 9 das convenções (expressões proibidas, glossário) |
| `ui/tests/test_template_classes.py` | Templates sem `style=`, sem valores arbitrários do Tailwind e só com classes da escala de tokens |
| `ui/tests/test_contrast.py` | Pares de cores de `ui/contrast.py` acima do contraste AA, nos dois temas |
| `schedule/tests/test_public_cache.py`, `BulkWriteScanTests` | Toda escrita sem sinais nos models das telas públicas chama a invalidação do cache |
| `accounts/tests/test_catalog.py` | Catálogo de permissões coerente com a migration |
| `accounts/tests/test_command_environment.py` | `clear_data`, `delete_users` e `set_passwords` recusados fora de `DJANGO_ENVIRONMENT=local` sem nenhuma consulta ao banco (`assertNumQueries(0)`), e executados com `local` |

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

Não há teste automatizado de navegador no repositório. As conferências manuais usam um banco separado (`visual_check`) e Playwright em container, nunca o banco de desenvolvimento; a última tentativa não foi concluída por falta de acesso ao PyPI. Ver [pendências](../pendencias.md#funcionalidades-não-concluídas).
