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

## Identificação da instalação e do banco local

`flush`, `clear_data`, `delete_users` e `set_passwords` apagam dados ou trocam todas as senhas. Antes de qualquer pergunta ou escrita, `accounts.utils.require_safe_database` confirma que o banco de destino é o banco da máquina de desenvolvimento. As três condições valem juntas, nesta ordem:

| Condição | Configuração | Consulta ao banco |
|---|---|---|
| A instalação é local | `DJANGO_ENVIRONMENT` exatamente `local` (`settings.ENVIRONMENT`) | Nenhuma |
| O banco configurado é o declarado | `DJANGO_LOCAL_DATABASE` (`settings.LOCAL_DATABASE`) igual a `host:porta/nome` da conexão, formada por `POSTGRES_HOST`, `POSTGRES_PORT` e `POSTGRES_DB`. Na máquina de desenvolvimento: `db:5432/agendamento` | Nenhuma |
| O banco conectado confirma | `current_database()` igual ao nome configurado e a marca `ifagenda.environment = 'local'` gravada no próprio banco, com `make mark-local-db` | Uma leitura |

- Qualquer condição falhando recusa com `CommandError`, sem perguntar nada e sem alterar dados. A mensagem diz qual configuração conferir e não repete valores configurados nem credenciais.
- Variável ausente, vazia ou ambígua (`Local`, `local `) recusa. O padrão em `settings.py` e no `compose.yaml` é vazio para as duas variáveis.
- `DEBUG` não é considerado: `DJANGO_DEBUG=1` sem as condições acima continua recusando.
- A marca fica no banco (`ALTER DATABASE ... SET`), e não no `.env`: um banco operacional nunca a tem, qualquer que seja o nome dele, e copiar o `.env` da máquina de desenvolvimento para outra instalação não basta para liberar os comandos. Um nome com `test_`, `dev_` ou `local_` não conta.
- Na máquina de desenvolvimento, defina no `.env` `DJANGO_ENVIRONMENT=local` e `DJANGO_LOCAL_DATABASE=db:5432/agendamento` e rode `make mark-local-db` uma vez. A marca some com `make reset-db`, junto com o volume. Em homologação e produção, deixe as duas variáveis ausentes e não grave a marca. Nenhum outro comportamento do sistema depende delas.
- Nos testes, os bancos criados pelo runner deste processo (`config/test_runner.py`) são liberados sem as três condições. Ver [testes](../desenvolvimento/testes.md).

Limitações que permanecem:

- Quem tem acesso ao banco como dono pode gravar a marca num banco errado, ou rodar `SET ifagenda.environment = 'local'` na própria sessão. A trava evita o engano, e não um ato deliberado.
- A identidade compara o que está configurado (`host:porta/nome`), e não o endereço de rede resolvido. A confirmação efetiva é feita pelo nome do banco conectado e pela marca.
- Só o alias `default` existe. Um alias novo passa pela mesma trava, pela opção `--database` do `flush`, e precisa da sua própria marca e da mesma identidade declarada.

Implementação: `accounts.utils.require_safe_database`, chamada na primeira linha do `handle()` de cada comando. Testes: `accounts/tests/test_command_environment.py`.

## Variáveis que mudam o comportamento fora do desenvolvimento

| Variável | Efeito |
|---|---|
| `DJANGO_DEBUG` | Ativo só com `1`. O padrão do `compose.yaml` é `1`; em produção, omita ou use outro valor |
| `DJANGO_ALLOWED_HOSTS` | Lista separada por vírgula. Vazia com `DEBUG` desligado recusa todos os hosts. Também é a lista de origens aceitas no WebSocket das notificações; nunca use `*` |
| `DJANGO_LOG_LEVEL` | Nível dos loggers do projeto. Padrão e recomendado em produção: `INFO`. `DEBUG` inclui o traceback das falhas de importação |
| `DJANGO_SITE_URL` | Base dos links nos e-mails enviados pelo worker (que não tem requisição) |
| `DJANGO_EMAIL_BACKEND` | Padrão: console. Para enviar de fato, `django.core.mail.backends.smtp.EmailBackend`. As credenciais vêm da interface, não de variáveis |
| `DJANGO_REDIS_URL` | Usada pelo cache público e pela camada do Channels. Vazia desliga o cache público (as telas consultam o banco) e deixa a camada em memória, com o aviso `notices.W001`. Fora da máquina de desenvolvimento, com senha (`redis://:senha@host:6379/0`) e TLS (`rediss://`) quando o Redis não está na rede privada |
| `DJANGO_CACHE_KEY_PREFIX` | Diferente por instalação quando várias dividem o mesmo Redis. A camada do Channels usa `<prefixo>:channels` |
| `DJANGO_OUTBOX_*`, `DJANGO_IMPORT_*` | Tentativas, intervalos, lotes e limites dos workers. Não estão no `compose.yaml`; valem os padrões de `settings.py` |

## Logs

`LOGGING` em `config/settings.py` manda tudo para o `stdout` do container, no formato `data nível logger mensagem`, para a plataforma de hospedagem capturar.

| Logger | Nível | Eventos |
|---|---|---|
| `imports` | `DJANGO_LOG_LEVEL` | INFO: worker iniciado e encerrado; operação iniciada (número, tipo, operação, tentativa) e concluída (situação e resultado). WARNING: recusa na execução, falha com nova tentativa. ERROR: falha final, tentativas esgotadas. DEBUG: traceback da falha |
| `outbox` | `DJANGO_LOG_LEVEL` | INFO: worker iniciado e encerrado, servidor de e-mail de volta. WARNING: falha com nova tentativa, envios retidos. ERROR: falha final, tipo sem tratador |
| `accounts`, `notices`, `schedule` | `DJANGO_LOG_LEVEL` | E-mail do allauth não enviado, falha do canal de tempo real, Redis indisponível e invalidação do cache público |
| `django` | WARNING | Segurança (`DisallowedHost`, CSRF) e avisos do Django |
| `django.request` | ERROR | Só os erros 5xx, com traceback. Os 404 e 403 ficam de fora, para não encher o log a cada requisição |
| raiz | WARNING | Bibliotecas de terceiros |

Fica fora do log, de propósito: a mensagem das exceções das importações e dos envios, que pode trazer valores das linhas ou endereços de e-mail (o texto completo continua em `last_error`, na tela da importação e na auditoria); o conteúdo dos arquivos importados; senhas, cookies, sessões e credenciais do SMTP. Requisições bem-sucedidas não são registradas, além da linha de acesso do servidor de desenvolvimento.

Nos testes, o runner (`config/test_runner.py`) deixa esses loggers em WARNING, salvo `DJANGO_LOG_LEVEL` informado; o `assertLogs` continua vendo o INFO.

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
| Camada do Channels | `RedisChannelLayer` com `DJANGO_REDIS_URL`, só com timeout de conexão (a leitura bloqueia por até 5 segundos à espera de mensagens). Sem a URL e nos testes, `InMemoryChannelLayer`, por processo | `CHANNEL_LAYERS` |
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
