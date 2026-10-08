# Configuração

A lista completa das variáveis de ambiente, com os valores padrão do desenvolvimento, está no [`README.md`](../../README.md#variáveis-de-ambiente). Este documento trata do que importa para operar o sistema fora da máquina de desenvolvimento.

## Variáveis obrigatórias

`config/settings.py` lê com `os.environ[...]`, e a aplicação não inicia sem elas:

| Variável | Observação |
|---|---|
| `DJANGO_SECRET_KEY` | O padrão do `compose.yaml` é inseguro |
| `DJANGO_CREDENTIALS_KEY` | Cifra a senha SMTP gravada no banco. Trocar a chave exige informar a senha SMTP de novo na interface. O padrão do `compose.yaml` é inseguro |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Também usadas pelo container `db` na criação do banco |
| `POSTGRES_HOST`, `POSTGRES_PORT` | Fixadas no `compose.yaml` (`db`, `5432`) |

## Identificação da instalação

`DJANGO_ENVIRONMENT` vira `settings.ENVIRONMENT`. É a única forma de o sistema saber que está na máquina de desenvolvimento.

| Valor | Efeito |
|---|---|
| `local`, exatamente | Libera `clear_data`, `delete_users` e `set_passwords` |
| ausente, vazio ou qualquer outro (`producao`, `homologacao`, `staging`, `Local`, `local `) | Os três comandos são recusados com `CommandError`, antes de qualquer acesso ao banco |

- O padrão em `settings.py` e no `compose.yaml` é vazio: uma instalação sem a variável recusa os comandos.
- `DEBUG` não é considerado: `DJANGO_DEBUG=1` sem `DJANGO_ENVIRONMENT=local` continua recusando.
- Na máquina de desenvolvimento, defina `DJANGO_ENVIRONMENT=local` no `.env`. Em homologação e produção, use outro valor ou deixe a variável ausente. Nenhum outro comportamento do sistema depende dela.

Implementação: `accounts.utils.require_local_environment`, chamada na primeira linha do `handle()` de cada comando. Testes: `accounts/tests/test_command_environment.py`.

## Variáveis que mudam o comportamento fora do desenvolvimento

| Variável | Efeito |
|---|---|
| `DJANGO_DEBUG` | Ativo só com `1`. O padrão do `compose.yaml` é `1`; em produção, omita ou use outro valor |
| `DJANGO_ALLOWED_HOSTS` | Lista separada por vírgula. Vazia com `DEBUG` desligado recusa todos os hosts |
| `DJANGO_SITE_URL` | Base dos links nos e-mails enviados pelo worker (que não tem requisição) |
| `DJANGO_EMAIL_BACKEND` | Padrão: console. Para enviar de fato, `django.core.mail.backends.smtp.EmailBackend`. As credenciais vêm da interface, não de variáveis |
| `DJANGO_REDIS_URL` | Vazia desliga o cache público (as telas consultam o banco). Fora da máquina de desenvolvimento, com senha (`redis://:senha@host:6379/0`) e TLS (`rediss://`) quando o Redis não está na rede privada |
| `DJANGO_CACHE_KEY_PREFIX` | Diferente por instalação quando várias dividem o mesmo Redis |
| `DJANGO_OUTBOX_*`, `DJANGO_IMPORT_*` | Tentativas, intervalos, lotes e limites dos workers. Não estão no `compose.yaml`; valem os padrões de `settings.py` |

## Configuração guardada no banco

| Item | Onde | Quem altera |
|---|---|---|
| Servidor SMTP | `SystemSetting` (`kind = SMTP`) | Interface, `CONFIGURACAO.EDITAR`. Ver [e-mails](../funcionalidades/emails.md#servidor-smtp) |
| Perfis e permissões | `Role`, `RolePermission` | Superadmin, pela interface |
| Superadmin | `User.is_superadmin` | Comandos `create_superadmin` e `set_superadmin` |

Sem servidor SMTP cadastrado, nenhum e-mail sai, nem para o console.

## Configurações fixas no código

| Item | Valor | Onde |
|---|---|---|
| Fuso e idioma | `America/Sao_Paulo`, `pt-br` | `settings.py` |
| Cache `default` | `LocMemCache`, por processo. Usado pelos limites de tentativas do allauth | `CACHES` |
| Camada do Channels | `InMemoryChannelLayer`, por processo | `CHANNEL_LAYERS` |
| Timeout SMTP | 30 segundos | `EMAIL_TIMEOUT` |
| Limites da importação do ensalamento | 5000 linhas, 10 MiB | `schedule/imports.py` |
| Prazo de cancelamento de agendamento | 1 hora antes do início | `bookings.models.CANCEL_DEADLINE` |
| Paginação | 5 itens por página nas listas, 20 nas linhas da importação, 10 opções no select | `ui/pagination.py` |

## Não configurado no repositório

- `LOGGING`: não há configuração. Os loggers do projeto (`accounts`, `outbox`, `imports`, `schedule.public_cache`, `notices.realtime`) não têm handler; mensagens `WARNING` ou acima aparecem no stderr pelo handler padrão do Python, e `INFO` e `DEBUG` (por exemplo `CACHE INVALIDATED`) não aparecem.
- `STATIC_ROOT`: ausente. Os estáticos são servidos pelo `runserver` com `DEBUG` ligado.
- Cabeçalhos e cookies de HTTPS (`SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS`): ausentes, valem os padrões do Django (cookies sem `Secure`).
- `ACCOUNT_RATE_LIMITS`: ausente; valem os padrões do allauth.
- Mídia: não há `MEDIA_ROOT` nem `FileField`. A importação lê o arquivo enviado e grava só as linhas.
