# Arquitetura

Aplicação Django monolítica no padrão MTV, com um app por domínio, PostgreSQL como única fonte de verdade e dois processos de segundo plano que usam o próprio banco como fila.

## Processos

| Serviço (`compose.yaml`) | Comando | Função |
|---|---|---|
| `web` | `python manage.py runserver 0.0.0.0:8000` | HTTP e WebSocket. Com `daphne` em `INSTALLED_APPS`, o `runserver` serve a aplicação ASGI (`config/asgi.py`) |
| `worker` | `python manage.py process_outbox` | Envia os e-mails registrados no outbox |
| `import_worker` | `python manage.py process_imports` | Executa a prévia, a atualização da prévia e a confirmação das importações |
| `db` | `postgres:17` | Banco de dados |
| `redis` | `redis:8-alpine`, sem persistência, 64 MB, `allkeys-lru` | Cache das telas públicas e camada do Channels |
| `tailwind` | `npx @tailwindcss/cli ... --watch=always` | Compila `ui/styles/app.css` em `ui/static/ui/css/app.css` |

`web`, `worker` e `import_worker` usam a mesma imagem e montam o código em `/app`. Só o `web` recarrega sozinho ao alterar o código.

## Caminho de uma requisição

1. `config/urls.py` inclui as rotas de cada app com prefixo vazio. Toda rota autenticada é envolvida por `login_required` no `urls.py` do app.
2. Middlewares, na ordem de `MIDDLEWARE`: segurança, sessão, CSRF, autenticação, mensagens, `AccountMiddleware` (allauth), `HtmxMiddleware`, `accounts.middleware.PermissionMiddleware` e `audit.middleware.AuditMiddleware`.
3. `PermissionMiddleware.process_view` lê o atributo `permission_required` da view e responde 403 quando `request.user.has_perm` recusa. Um anônimo que chegue a uma view com permissão é mandado ao login.
4. `AuditMiddleware` define o ator da requisição (usuário, IP, cliente, origem `INTERFACE`) num `ContextVar` e, depois da resposta, registra o acesso quando a view declara `audit_resource`, o método é GET, a resposta é 200 e a requisição não veio do htmx.
5. A view (sempre CBV) chama uma operação do model ou do manager. A operação abre a transação, trava o que precisa (`select_for_update`), confere as regras e lança `ValidationError` quando recusa. Na mesma transação grava a auditoria (`AuditLog.objects.record`), as notificações (`notices.events.announce`), os e-mails (`OutboxEntry.objects.enqueue`) e agenda a invalidação do cache público (`transaction.on_commit`).
6. A recusa volta como erro de formulário (`accounts.views.OperationFormView`) ou como mensagem (`ConfirmedActionView`). Ações de gestão abrem em modal pelo htmx (`ui.views.ModalView`), e a mesma URL abre a página completa sem JavaScript.

## Apps

| App | Responsabilidade |
|---|---|
| `config` | Settings, rotas raiz, ASGI e formatos `pt_BR` |
| `accounts` | `User`, perfis, permissões, catálogo de permissões, `PermissionMiddleware`, adaptador do allauth, comandos de superadmin e de dados, importação de usuários. Define as classes base `OperationFormView` e `ConfirmedActionView` |
| `ui` | Layouts, componentes, tokens do Tailwind, ícones, menu (`navigation.py`), paginação, renderizador de formulários, `ModalView`, `OptionsView` e as varreduras de texto e de visual |
| `audit` | `AuditLog`, catálogo de ações e módulos, ator da requisição, middleware e tela de consulta |
| `outbox` | Fila de e-mails e o worker |
| `system_settings` | Configuração do servidor SMTP, com a senha cifrada |
| `notices` | Notificações por destinatário, publicação manual e canal WebSocket |
| `imports` | Motor genérico de importação de planilhas e o worker. Ver [motor de importação](motor-de-importacao.md) |
| `schedule` | Ensalamento: semestres, faixas, espaços, docentes, cursos, turmas, disciplinas, alocações, exceções, importação da planilha, Grade, ocupação, calendário público e o cache público |
| `bookings` | Agenda: solicitações de agendamento e agendamentos |
| `panel` | Painel administrativo, só leitura |
| `reports` | Mapa de calor e relatório de solicitações, só leitura |

`accounts.permissions` é importado por quase todos os apps. `ui` não importa nenhum outro app. `schedule` e `accounts` dependem um do outro: a importação tardia (`from ... import` dentro da função) resolve o ciclo, como em `SpaceDecisionManager` e `check_conflicts`.

## Extensão por registro no `AppConfig.ready`

Os mecanismos genéricos não conhecem os apps que os usam. Cada app se registra no `ready()`:

| Registro | Função | Quem registra |
|---|---|---|
| `outbox.handlers.register(kind, handler)` | Monta o e-mail de um tipo de envio | `accounts` (`LINK_SENHA`) |
| `notices.events.register(name, event)` | Gera as notificações de um evento | `accounts` (perfil alterado), `bookings` (transições da Agenda) |
| `imports.registry.register(definition)` | Importação específica | `accounts` (`UserImport`), `schedule` (`SpaceAllocationImport`) |
| `schedule.occupancy.register_source(source, public=...)` | Fonte de ocupação da Grade e, com `public=True`, do calendário público | `bookings` (`BookingSource`) |
| `schedule.public_cache.watch(model, fields=...)` | Invalida o cache público a cada gravação do model | `schedule`, `bookings` |
| `audit.signals.connect()` | Liga login, saída e redefinição de senha à auditoria | `audit` |

## Padrões usados

- **Regras no model.** Operações de model e de manager concentram as regras de negócio (`User.change_role`, `BookingRequest.approve`, `Allocation.objects.change_recurrence`). Views e comandos só as chamam. Não há camada de serviços separada.
- **Conferir e executar.** Operações em duas etapas têm um método que confere sem gravar e outro que confere de novo e grava: `BookingRequest.objects.prepare`/`submit`, `Allocation.objects.plan_recurrence`/`change_recurrence`, `plan_creation`/`create_recurrence`, `plan_ending`/`end_recurrence`. A tela mostra o resumo do primeiro e confirma com o segundo.
- **Outbox transacional.** O e-mail é gravado como intenção na transação da operação e enviado depois pelo worker. Ver [e-mails](../funcionalidades/emails.md).
- **Fila no PostgreSQL.** Os dois workers reservam trabalho com `select_for_update(skip_locked=True)`. Não há Celery nem broker.
- **Prévia por executar e desfazer.** A importação executa as operações reais dentro de um savepoint e o desfaz. A confirmação só aplica se o plano for idêntico ao da prévia.
- **Ocupação calculada.** A alocação é regra semanal. As ocorrências de um intervalo são calculadas a cada consulta (`schedule.occupancy`), descontando as exceções e a vigência. Nada é materializado.
- **Auditoria só de inclusão.** Uma tabela, gravada na transação de quem chama. `AuditLog.save` recusa alteração e `delete` recusa exclusão.
- **Cache por geração.** O cache público é invalidado incrementando um contador global depois do commit. Ver [calendário público](../funcionalidades/calendario-publico.md#cache).
- **Catálogos em código.** Permissões (`accounts/permissions.py`), ações e módulos da auditoria (`audit/catalog.py`) e tipos de notificação (`notices/catalog.py`) são constantes. Um código fora do catálogo é recusado no ponto de gravação.

## Tempo real

O sino de notificações escuta `ws/notificacoes/` (`notices/consumers.py`). O aviso é enviado em `transaction.on_commit` e só diz que as notificações do usuário mudaram; a página busca a contagem por HTTP. Com `DJANGO_REDIS_URL`, a camada é o `RedisChannelLayer` (`channels_redis`), no mesmo Redis do cache público, com o prefixo `<DJANGO_CACHE_KEY_PREFIX>:channels`: uma notificação criada no `import_worker` ou em outro processo do `web` chega em tempo real. Sem a variável, e nos testes, a camada é `InMemoryChannelLayer`, que só alcança conexões do mesmo processo; fora dos testes, o check `notices.W001` avisa disso em todo comando de gestão. As chaves do Channels dividem o Redis com o cache público, sob `allkeys-lru` e 64 MB: sob pressão de memória podem ser descartadas, e quem perde a inscrição no grupo só volta a receber avisos ao reconectar (recarregar a página). O acompanhamento das importações usa polling (`IMPORT_STATUS_POLL_SECONDS`), adotado quando a camada só existia em memória.

## Fuso, idioma e formatos

`TIME_ZONE = 'America/Sao_Paulo'`, `USE_TZ = True`, `LANGUAGE_CODE = 'pt-br'`. Os formatos de data, hora e número ficam em `config/formats/pt_BR/formats.py` (dd/mm/aaaa, 24 horas, vírgula decimal).
